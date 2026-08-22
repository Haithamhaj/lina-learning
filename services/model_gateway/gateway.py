"""Provider-independent model routing with durable execution records."""

from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter
from collections.abc import Iterator
from typing import Mapping, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from services.platform.db.models import AIExecution, ModelTask


@dataclass(frozen=True)
class ModelRoute:
    """The selected provider/model for one application task."""

    provider: str
    model: str


@dataclass(frozen=True)
class ModelResult:
    """Normalized output and usage from a provider adapter."""

    output: dict[str, object]
    # Normal (non-cached) input tokens. Provider adapters normalize any
    # provider-specific total-input figure before returning this result.
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    execution_id: UUID | None = None
    operation_id: UUID | None = None


@dataclass(frozen=True)
class AIExecutionLineage:
    """Identifier-only context supplied by the application operation owner.

    The gateway persists this compact boundary alongside the existing operational
    ledger, but never stores prompt, response, message text, or embedding values.
    """

    operation: str
    operation_id: UUID | None = None
    parent_execution_id: UUID | None = None
    student_id: UUID | None = None
    learning_session_id: UUID | None = None
    source_message_id: UUID | None = None
    intelligence_processing_run_id: UUID | None = None
    document_id: UUID | None = None
    semantic_processing_run_id: UUID | None = None
    content_index_run_id: UUID | None = None
    source_candidate_event_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class StreamDelta:
    """One provider-produced text delta for a streaming model response."""

    text: str


@dataclass(frozen=True)
class StreamComplete:
    """The provider's final normalized result after its streamed response."""

    result: ModelResult


ModelStreamEvent = StreamDelta | StreamComplete


class ModelProvider(Protocol):
    """A provider adapter receives only a route and task-owned payload."""

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        """Perform one model request."""


class StreamingModelProvider(Protocol):
    """Optional streaming extension for a provider-neutral model adapter."""

    def stream(
        self, route: ModelRoute, payload: dict[str, object]
    ) -> Iterator[ModelStreamEvent]:
        """Perform one streamed model request."""


class StaticModelProvider:
    """Deterministic provider for tests and the local fixture demonstration."""

    def __init__(self, result: ModelResult) -> None:
        self._result = result

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route, payload
        return self._result

    def stream(
        self, route: ModelRoute, payload: dict[str, object]
    ) -> Iterator[ModelStreamEvent]:
        result = self.execute(route, payload)
        text = result.output.get("text")
        if isinstance(text, str) and text:
            yield StreamDelta(text)
        yield StreamComplete(result)


class ModelGateway:
    """Execute by application task while the caller remains provider-agnostic."""

    def __init__(
        self,
        session: Session,
        *,
        routes: Mapping[ModelTask, ModelRoute],
        providers: Mapping[str, ModelProvider],
    ) -> None:
        self._session = session
        self._routes = dict(routes)
        self._providers = dict(providers)

    def set_route(self, task: ModelTask, route: ModelRoute) -> None:
        """Change routing without requiring callers to know provider details."""

        self._routes[task] = route

    def route_for(self, task: ModelTask) -> ModelRoute:
        """Expose route metadata without exposing a provider adapter."""

        route = self._routes.get(task)
        if route is None:
            raise ValueError(f"No model route is configured for task {task.value!r}.")
        return route

    def execute(
        self,
        task: ModelTask,
        payload: dict[str, object],
        *,
        lineage: AIExecutionLineage | None = None,
    ) -> ModelResult:
        """Call the selected adapter and always record its operational outcome."""

        route = self.route_for(task)
        provider = self._providers.get(route.provider)
        if provider is None:
            raise ValueError(f"No provider is configured for {route.provider!r}.")

        started = perf_counter()
        try:
            result = provider.execute(route, payload)
        except Exception as error:
            self._record(task, route, started, lineage=lineage, success=False, failure_code=type(error).__name__)
            raise

        execution = self._record(
            task,
            route,
            started,
            lineage=lineage,
            success=True,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            cache_write_tokens=result.cache_write_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        )
        return replace(result, execution_id=execution.id, operation_id=execution.operation_id)

    def stream(
        self,
        task: ModelTask,
        payload: dict[str, object],
        *,
        lineage: AIExecutionLineage | None = None,
    ) -> Iterator[ModelStreamEvent]:
        """Stream one task call and record it exactly once on completion or failure."""

        route = self.route_for(task)
        provider = self._providers.get(route.provider)
        if provider is None:
            raise ValueError(f"No provider is configured for {route.provider!r}.")
        stream = getattr(provider, "stream", None)
        if not callable(stream):
            raise ValueError(f"Provider {route.provider!r} does not support streaming.")

        started = perf_counter()
        completed = False
        try:
            for event in stream(route, payload):
                if isinstance(event, StreamDelta):
                    yield event
                    continue
                if isinstance(event, StreamComplete):
                    completed = True
                    execution = self._record(
                        task,
                        route,
                        started,
                        lineage=lineage,
                        success=True,
                        input_tokens=event.result.input_tokens,
                        cached_input_tokens=event.result.cached_input_tokens,
                        cache_write_tokens=event.result.cache_write_tokens,
                        output_tokens=event.result.output_tokens,
                        estimated_cost_usd=event.result.estimated_cost_usd,
                    )
                    yield StreamComplete(
                        replace(
                            event.result,
                            execution_id=execution.id,
                            operation_id=execution.operation_id,
                        )
                    )
                    return
                raise ValueError("Streaming provider returned an invalid event.")
            raise ValueError("Streaming provider ended without a final result.")
        except Exception as error:
            if not completed:
                self._record(task, route, started, lineage=lineage, success=False, failure_code=type(error).__name__)
            raise

    def _record(
        self,
        task: ModelTask,
        route: ModelRoute,
        started: float,
        *,
        lineage: AIExecutionLineage | None,
        success: bool,
        input_tokens: int | None = None,
        cached_input_tokens: int | None = None,
        cache_write_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        failure_code: str | None = None,
    ) -> AIExecution:
        selected_lineage = lineage or AIExecutionLineage(operation=task.value)
        execution = AIExecution(
                task=task.value,
                provider=route.provider,
                model=route.model,
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                cache_write_tokens=cache_write_tokens,
                output_tokens=output_tokens,
                latency_ms=round((perf_counter() - started) * 1000),
                estimated_cost_usd=estimated_cost_usd,
                success=success,
                failure_code=failure_code,
                operation_id=selected_lineage.operation_id or uuid4(),
                operation_type=selected_lineage.operation,
                parent_execution_id=selected_lineage.parent_execution_id,
                student_id=selected_lineage.student_id,
                learning_session_id=selected_lineage.learning_session_id,
                source_message_id=selected_lineage.source_message_id,
                intelligence_processing_run_id=selected_lineage.intelligence_processing_run_id,
                document_id=selected_lineage.document_id,
                semantic_processing_run_id=selected_lineage.semantic_processing_run_id,
                content_index_run_id=selected_lineage.content_index_run_id,
                source_candidate_event_ids=[str(identifier) for identifier in selected_lineage.source_candidate_event_ids],
            )
        self._session.add(execution)
        self._session.flush()
        return execution
