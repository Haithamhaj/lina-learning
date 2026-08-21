"""Provider-independent model routing with durable execution records."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from collections.abc import Iterator
from typing import Mapping, Protocol

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

    def execute(self, task: ModelTask, payload: dict[str, object]) -> ModelResult:
        """Call the selected adapter and always record its operational outcome."""

        route = self.route_for(task)
        provider = self._providers.get(route.provider)
        if provider is None:
            raise ValueError(f"No provider is configured for {route.provider!r}.")

        started = perf_counter()
        try:
            result = provider.execute(route, payload)
        except Exception as error:
            self._record(task, route, started, success=False, failure_code=type(error).__name__)
            raise

        self._record(
            task,
            route,
            started,
            success=True,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            cache_write_tokens=result.cache_write_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        )
        return result

    def stream(self, task: ModelTask, payload: dict[str, object]) -> Iterator[ModelStreamEvent]:
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
                    self._record(
                        task,
                        route,
                        started,
                        success=True,
                        input_tokens=event.result.input_tokens,
                        cached_input_tokens=event.result.cached_input_tokens,
                        cache_write_tokens=event.result.cache_write_tokens,
                        output_tokens=event.result.output_tokens,
                        estimated_cost_usd=event.result.estimated_cost_usd,
                    )
                    yield event
                    return
                raise ValueError("Streaming provider returned an invalid event.")
            raise ValueError("Streaming provider ended without a final result.")
        except Exception as error:
            if not completed:
                self._record(task, route, started, success=False, failure_code=type(error).__name__)
            raise

    def _record(
        self,
        task: ModelTask,
        route: ModelRoute,
        started: float,
        *,
        success: bool,
        input_tokens: int | None = None,
        cached_input_tokens: int | None = None,
        cache_write_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        failure_code: str | None = None,
    ) -> None:
        self._session.add(
            AIExecution(
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
            )
        )
        self._session.flush()
