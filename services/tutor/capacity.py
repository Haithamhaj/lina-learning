"""Final deterministic capacity guardrail for already-selected Tutor context."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Callable

from services.tutor.context import TutorContext
from services.tutor.exchanges import ConversationExchangeContext


TUTOR_CONTEXT_CAPACITY_POLICY_VERSION = "tutor-context-capacity-v1"
TUTOR_CONTEXT_CAPACITY_MEASUREMENT_KIND = "serialized-model-request-characters-v1"


@dataclass(frozen=True)
class DroppedContextUnit:
    kind: str
    source_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    reason: str = "FINAL_CAPACITY"

    def as_metadata(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "source_ids": list(self.source_ids),
            "source_refs": list(self.source_refs),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TutorContextCapacityLineage:
    capacity_limit: int
    initial_measured_size: int
    final_measured_size: int
    selected_context: dict[str, object]
    kept_context: dict[str, object]
    dropped_context: tuple[DroppedContextUnit, ...]
    capacity_policy_version: str = TUTOR_CONTEXT_CAPACITY_POLICY_VERSION
    measurement_kind: str = TUTOR_CONTEXT_CAPACITY_MEASUREMENT_KIND

    def as_metadata(self) -> dict[str, object]:
        return {
            "capacity_policy_version": self.capacity_policy_version,
            "measurement_kind": self.measurement_kind,
            "capacity_limit": self.capacity_limit,
            "initial_measured_size": self.initial_measured_size,
            "final_measured_size": self.final_measured_size,
            "selected_context": self.selected_context,
            "kept_context": self.kept_context,
            "dropped_context": [item.as_metadata() for item in self.dropped_context],
        }


class TutorContextCapacityExceeded(RuntimeError):
    """Raised before the primary Tutor call when protected input alone exceeds capacity."""

    def __init__(self, lineage: TutorContextCapacityLineage) -> None:
        super().__init__("The final Tutor request exceeds protected context capacity.")
        self.lineage = lineage


@dataclass(frozen=True)
class GuardrailedTutorContext:
    context: TutorContext
    payload: dict[str, object]
    lineage: TutorContextCapacityLineage


def serialized_model_request_characters(payload: dict[str, object]) -> int:
    """Measure the provider-facing request fields with stable JSON serialization."""

    request = {
        key: payload[key]
        for key in ("instructions", "input", "response_schema")
        if key in payload
    }
    return len(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def apply_context_capacity_guardrail(
    context: TutorContext,
    *,
    capacity_limit: int,
    payload_builder: Callable[[TutorContext], dict[str, object]],
) -> GuardrailedTutorContext:
    """Keep protected input whole and drop optional selected units only when needed."""

    if capacity_limit <= 0:
        raise ValueError("Tutor context capacity must be positive.")
    selected_context = _context_metadata(context)
    working = context
    payload = payload_builder(working)
    initial_size = serialized_model_request_characters(payload)
    dropped: list[DroppedContextUnit] = []
    while serialized_model_request_characters(payload) > capacity_limit:
        next_context, dropped_unit = _drop_next_optional_unit(working)
        if dropped_unit is None:
            lineage = TutorContextCapacityLineage(
                capacity_limit=capacity_limit,
                initial_measured_size=initial_size,
                final_measured_size=serialized_model_request_characters(payload),
                selected_context=selected_context,
                kept_context=_context_metadata(working),
                dropped_context=tuple(dropped),
            )
            raise TutorContextCapacityExceeded(lineage)
        working = next_context
        dropped.append(dropped_unit)
        payload = payload_builder(working)
    lineage = TutorContextCapacityLineage(
        capacity_limit=capacity_limit,
        initial_measured_size=initial_size,
        final_measured_size=serialized_model_request_characters(payload),
        selected_context=selected_context,
        kept_context=_context_metadata(working),
        dropped_context=tuple(dropped),
    )
    return GuardrailedTutorContext(
        context=_with_final_context_debug(working),
        payload=payload,
        lineage=lineage,
    )


def _drop_next_optional_unit(context: TutorContext) -> tuple[TutorContext, DroppedContextUnit | None]:
    """Apply CTX-03D's deterministic layer order without changing upstream relevance."""

    if context.personal_memory is not None:
        return (
            replace(
                context,
                personal_memory=None,
                debug=replace(
                    context.debug,
                    personal_memory_status="PERSONAL_MEMORY_OMITTED_CAPACITY",
                ),
            ),
            DroppedContextUnit("PERSONAL_MEMORY", reason="PERSONAL_MEMORY_OMITTED_CAPACITY"),
        )
    if context.semantic_recall_exchanges:
        exchange = _lowest_priority_semantic_exchange(context)
        return (
            replace(
                context,
                semantic_recall_exchanges=tuple(
                    item for item in context.semantic_recall_exchanges if item != exchange
                ),
                semantic_recall_priority_message_ids=tuple(
                    message_ids
                    for message_ids in context.semantic_recall_priority_message_ids
                    if message_ids != exchange.message_ids
                ),
            ),
            _exchange_drop("SEMANTIC_RECALL_EXCHANGE", exchange),
        )
    if context.recent_exchanges:
        exchange = context.recent_exchanges[0]
        return (
            replace(context, recent_exchanges=context.recent_exchanges[1:]),
            _exchange_drop("RECENT_RAW_EXCHANGE", exchange),
        )
    if context.retrieval:
        block = context.retrieval[-1]
        return (
            replace(context, retrieval=context.retrieval[:-1]),
            DroppedContextUnit("CURRICULUM_BLOCK", source_refs=(block.source_ref,)),
        )
    if context.intelligence:
        item = context.intelligence[-1]
        return (
            replace(context, intelligence=context.intelligence[:-1]),
            DroppedContextUnit("LEARNER_INTELLIGENCE", source_ids=(str(item.source_id),)),
        )
    return context, None


def _exchange_drop(kind: str, exchange: ConversationExchangeContext) -> DroppedContextUnit:
    return DroppedContextUnit(kind, source_ids=tuple(_exchange_ids(exchange)))


def _lowest_priority_semantic_exchange(context: TutorContext) -> ConversationExchangeContext:
    """Use CTX-03C's stored priority; presentation order is never a removal signal."""

    if len(context.semantic_recall_exchanges) == 1:
        return context.semantic_recall_exchanges[0]
    by_message_ids = {exchange.message_ids: exchange for exchange in context.semantic_recall_exchanges}
    for message_ids in reversed(context.semantic_recall_priority_message_ids):
        exchange = by_message_ids.get(message_ids)
        if exchange is not None:
            return exchange
    raise ValueError("Semantic Recall Exchanges require CTX-03C priority lineage before capacity reduction.")


def _context_metadata(context: TutorContext) -> dict[str, object]:
    """Record identifiers and refs only; raw hidden prompt text stays out of lineage."""

    return {
        "immediate_exchange_message_ids": _exchange_ids(context.immediate_exchange),
        "recent_exchange_message_ids": [
            str(identifier)
            for exchange in context.recent_exchanges
            for identifier in exchange.message_ids
        ],
        "semantic_recall_exchange_message_ids": [
            str(identifier)
            for exchange in context.semantic_recall_exchanges
            for identifier in exchange.message_ids
        ],
        "curriculum_refs": [block.source_ref for block in context.retrieval],
        "intelligence_source_ids": [str(item.source_id) for item in context.intelligence],
        "personal_memory": {
            "included": context.personal_memory is not None,
            "status": context.debug.personal_memory_status,
        },
        "counts": {
            "personal_memory_included": int(context.personal_memory is not None),
            "recent_raw_exchanges": len(context.recent_exchanges),
            "semantic_recall_exchanges": len(context.semantic_recall_exchanges),
            "curriculum_blocks": len(context.retrieval),
            "learner_intelligence_entries": len(context.intelligence),
        },
    }


def _with_final_context_debug(context: TutorContext) -> TutorContext:
    """Keep persisted debug metadata aligned with the final model-facing context only."""

    recent_message_ids = _raw_exchange_ids(context.recent_exchanges)
    semantic_message_ids = _raw_exchange_ids(context.semantic_recall_exchanges)
    personal_memory_status = context.debug.personal_memory_status
    if context.personal_memory is None and personal_memory_status == "PERSONAL_MEMORY_INCLUDED":
        personal_memory_status = "PERSONAL_MEMORY_OMITTED_CAPACITY"
    return replace(
        context,
        debug=replace(
            context.debug,
            older_continuity_message_ids=(*recent_message_ids, *semantic_message_ids),
            recent_exchange_message_ids=recent_message_ids,
            semantic_recall_exchange_message_ids=semantic_message_ids,
            retrieval_source_refs=tuple(block.source_ref for block in context.retrieval),
            intelligence_source_ids=tuple(item.source_id for item in context.intelligence),
            personal_memory_status=personal_memory_status,
        ),
    )


def _raw_exchange_ids(exchanges: tuple[ConversationExchangeContext, ...]) -> tuple[object, ...]:
    return tuple(
        identifier
        for exchange in exchanges
        for identifier in getattr(exchange, "message_ids", ())
    )


def _exchange_ids(exchange: object | None) -> list[str]:
    """Read modern Exchange objects and the tuple-only CTX-02 test seam alike."""

    if exchange is None:
        return []
    message_ids = getattr(exchange, "message_ids", None)
    if isinstance(message_ids, tuple):
        return [str(identifier) for identifier in message_ids]
    if isinstance(exchange, tuple):
        return [
            str(identifier)
            for message in exchange
            if (identifier := getattr(message, "message_id", None)) is not None
        ]
    return []
