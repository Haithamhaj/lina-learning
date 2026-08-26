"""Final model-facing capacity contracts for CTX-03D."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from services.intelligence.selection import RelevantIntelligence
from services.retrieval.service import RetrievedBlock
from services.tutor.capacity import (
    TUTOR_CONTEXT_CAPACITY_POLICY_VERSION,
    TutorContextCapacityExceeded,
    apply_context_capacity_guardrail,
    serialized_model_request_characters,
)
from services.tutor.context import TutorContext, TutorContextDebug
from services.tutor.exchanges import ConversationExchangeContext
from services.tutor.runtime import build_tutor_model_payload
from services.tutor.segments import StructuredSegmentState


def _exchange(label: str, *, created_at: datetime | None = None) -> ConversationExchangeContext:
    return ConversationExchangeContext(
        session_id=uuid4(),
        segment_id=uuid4(),
        student_message_id=uuid4(),
        tutor_message_id=uuid4(),
        student_content=f"{label} student " + "s" * 120,
        tutor_content=f"{label} tutor " + "t" * 120,
        student_created_at=created_at,
        tutor_created_at=created_at + timedelta(seconds=1) if created_at is not None else None,
    )


def _block(label: str) -> RetrievedBlock:
    return RetrievedBlock(
        text=f"{label} curriculum " + "c" * 120,
        source_ref=f"book#{label}",
        page_number=1,
        block_type="TEXT",
        score=1.0,
        semantic_key=label,
        semantic_type=None,
        concept_key=None,
        source_refs=(f"book#{label}",),
        page_numbers=(1,),
        matched=True,
    )


def _context() -> TutorContext:
    current_id = uuid4()
    immediate = _exchange("immediate")
    recent = _exchange("recent")
    semantic_a = _exchange("older-higher-relevance", created_at=datetime(2026, 8, 1, tzinfo=UTC))
    semantic_b = _exchange("newer-lower-relevance", created_at=datetime(2026, 8, 2, tzinfo=UTC))
    intelligence = (
        RelevantIntelligence("STATE", uuid4(), "intelligence-a " + "i" * 120, None, 2),
        RelevantIntelligence("STATE", uuid4(), "intelligence-b " + "i" * 120, None, 1),
    )
    return TutorContext(
        question="Current Student turn " + "q" * 160,
        subject="MATH",
        grade_level=5,
        focus=None,
        session_messages=(),
        retrieval=(_block("retrieval-a"), _block("retrieval-b")),
        intelligence=intelligence,
        debug=TutorContextDebug(
            None,
            (),
            ("book#retrieval-a", "book#retrieval-b"),
            tuple(item.source_id for item in intelligence),
            (),
            current_turn_message_id=current_id,
            immediate_exchange_message_ids=immediate.message_ids,
            older_continuity_message_ids=(*recent.message_ids, *semantic_a.message_ids, *semantic_b.message_ids),
            recent_exchange_message_ids=recent.message_ids,
            semantic_recall_exchange_message_ids=(*semantic_a.message_ids, *semantic_b.message_ids),
        ),
        immediate_exchange=immediate,
        recent_exchanges=(recent,),
        semantic_recall_exchanges=(semantic_a, semantic_b),
        semantic_recall_priority_message_ids=(semantic_a.message_ids, semantic_b.message_ids),
    )


def _exchange_payload(exchange: ConversationExchangeContext | None) -> list[dict[str, object]]:
    if exchange is None:
        return []
    values: list[dict[str, object]] = []
    if exchange.student_message_id is not None and exchange.student_content is not None:
        values.append({"message_id": str(exchange.student_message_id), "role": "student", "content": exchange.student_content})
    values.append({"message_id": str(exchange.tutor_message_id), "role": "tutor", "content": exchange.tutor_content})
    return values


def _payload(
    context: TutorContext,
    *,
    latest_segment_state: StructuredSegmentState | None = None,
) -> dict[str, object]:
    return build_tutor_model_payload(
        question=context.question,
        sources=[{"ref": block.source_ref, "text": block.text} for block in context.retrieval],
        intelligence=[item.text for item in context.intelligence],
        safety_directive="Safety directive must remain.",
        immediate_exchange=_exchange_payload(context.immediate_exchange),
        recent_exchanges=[_exchange_payload(exchange) for exchange in context.recent_exchanges],
        semantic_recall_exchanges=[_exchange_payload(exchange) for exchange in context.semantic_recall_exchanges],
        candidate_source_message_id=context.debug.current_turn_message_id,
        latest_segment_state=latest_segment_state,
        effective_parent_boundaries={"SEXUAL_CONTENT": "REDIRECT_TO_PARENT"},
    )


def test_under_or_exact_capacity_keeps_every_selected_unit() -> None:
    """Catches a guardrail that trims context even though the final request fits."""

    context = _context()
    exact_limit = serialized_model_request_characters(_payload(context))

    for limit in (exact_limit + 1, exact_limit):
        result = apply_context_capacity_guardrail(context, capacity_limit=limit, payload_builder=_payload)

        assert result.context == context
        assert result.lineage.dropped_context == ()
        assert result.lineage.initial_measured_size == exact_limit
        assert result.lineage.final_measured_size == exact_limit
        assert result.lineage.capacity_policy_version == TUTOR_CONTEXT_CAPACITY_POLICY_VERSION


def test_capacity_drops_lowest_priority_semantic_exchange_not_first_chronological_exchange() -> None:
    """Catches capacity treating Luna's chronological presentation as CTX-03C relevance order."""

    context = _context()
    full_size = serialized_model_request_characters(_payload(context))
    result = apply_context_capacity_guardrail(context, capacity_limit=full_size - 1, payload_builder=_payload)

    assert result.context.immediate_exchange == context.immediate_exchange
    assert result.context.question == context.question
    assert result.context.semantic_recall_exchanges == (context.semantic_recall_exchanges[0],)
    assert result.lineage.dropped_context[0].kind == "SEMANTIC_RECALL_EXCHANGE"
    assert result.lineage.dropped_context[0].source_ids == tuple(str(identifier) for identifier in context.semantic_recall_exchanges[1].message_ids)
    assert context.semantic_recall_exchanges[1].student_content not in str(result.payload["input"])
    assert context.semantic_recall_exchanges[1].tutor_content not in str(result.payload["input"])
    assert context.semantic_recall_exchanges[0].student_content in str(result.payload["input"])
    assert context.immediate_exchange.student_content in str(result.payload["input"])
    assert context.immediate_exchange.tutor_content in str(result.payload["input"])
    assert "Safety directive must remain." in str(result.payload["input"])
    assert "Effective Parent Boundary settings" in str(result.payload["input"])
    assert result.lineage == apply_context_capacity_guardrail(context, capacity_limit=full_size - 1, payload_builder=_payload).lineage


def test_capacity_drops_ordinary_semantic_exchange_before_state_pinned_exchange() -> None:
    """Catches capacity pressure removing an existing CTX-03C State pin before ordinary recall."""

    context = _context()
    pinned, ordinary = context.semantic_recall_exchanges
    full_size = serialized_model_request_characters(_payload(context))

    result = apply_context_capacity_guardrail(context, capacity_limit=full_size - 1, payload_builder=_payload)

    assert result.context.semantic_recall_exchanges == (pinned,)
    assert result.lineage.dropped_context[0].source_ids == tuple(str(identifier) for identifier in ordinary.message_ids)


def test_capacity_final_debug_and_lineage_describe_the_same_guarded_context() -> None:
    """Catches persisted debug IDs/refs claiming capacity-dropped units were sent to Luna."""

    context = _context()
    protected = TutorContext(
        question=context.question,
        subject=context.subject,
        grade_level=context.grade_level,
        focus=context.focus,
        session_messages=context.session_messages,
        retrieval=(),
        intelligence=(),
        debug=context.debug,
        immediate_exchange=context.immediate_exchange,
    )
    result = apply_context_capacity_guardrail(
        context,
        capacity_limit=serialized_model_request_characters(_payload(protected)),
        payload_builder=_payload,
    )

    debug = result.context.debug
    selected = result.lineage.selected_context
    kept = result.lineage.kept_context
    dropped = result.lineage.dropped_context
    assert debug.current_turn_message_id == context.debug.current_turn_message_id
    assert debug.immediate_exchange_message_ids == context.debug.immediate_exchange_message_ids
    assert debug.recent_exchange_message_ids == ()
    assert debug.semantic_recall_exchange_message_ids == ()
    assert debug.retrieval_source_refs == ()
    assert debug.intelligence_source_ids == ()
    assert kept["recent_exchange_message_ids"] == []
    assert kept["semantic_recall_exchange_message_ids"] == []
    assert kept["curriculum_refs"] == []
    assert kept["intelligence_source_ids"] == []
    assert selected["semantic_recall_exchange_message_ids"]
    assert selected["recent_exchange_message_ids"]
    assert selected["curriculum_refs"]
    assert selected["intelligence_source_ids"]
    dropped_source_ids = {source_id for item in dropped for source_id in item.source_ids}
    dropped_source_refs = {source_ref for item in dropped for source_ref in item.source_refs}
    assert set(selected["recent_exchange_message_ids"]).issubset(dropped_source_ids)
    assert set(selected["semantic_recall_exchange_message_ids"]).issubset(dropped_source_ids)
    assert set(selected["intelligence_source_ids"]).issubset(dropped_source_ids)
    assert set(selected["curriculum_refs"]).issubset(dropped_source_refs)
    assert {item.kind for item in dropped} == {
        "SEMANTIC_RECALL_EXCHANGE",
        "RECENT_RAW_EXCHANGE",
        "CURRICULUM_BLOCK",
        "LEARNER_INTELLIGENCE",
    }


def test_capacity_reduction_exhausts_layers_in_the_approved_deterministic_order() -> None:
    """Catches an unstable collection order or any re-ranking by the capacity layer."""

    context = _context()
    protected = TutorContext(
        question=context.question,
        subject=context.subject,
        grade_level=context.grade_level,
        focus=context.focus,
        session_messages=context.session_messages,
        retrieval=(),
        intelligence=(),
        debug=context.debug,
        immediate_exchange=context.immediate_exchange,
    )
    result = apply_context_capacity_guardrail(
        context,
        capacity_limit=serialized_model_request_characters(_payload(protected)),
        payload_builder=_payload,
    )

    assert result.context.question == protected.question
    assert result.context.immediate_exchange == protected.immediate_exchange
    assert result.context.recent_exchanges == ()
    assert result.context.semantic_recall_exchanges == ()
    assert result.context.retrieval == ()
    assert result.context.intelligence == ()
    assert result.context.debug.recent_exchange_message_ids == ()
    assert result.context.debug.semantic_recall_exchange_message_ids == ()
    assert result.context.debug.retrieval_source_refs == ()
    assert result.context.debug.intelligence_source_ids == ()
    assert [item.kind for item in result.lineage.dropped_context] == [
        "SEMANTIC_RECALL_EXCHANGE",
        "SEMANTIC_RECALL_EXCHANGE",
        "RECENT_RAW_EXCHANGE",
        "CURRICULUM_BLOCK",
        "CURRICULUM_BLOCK",
        "LEARNER_INTELLIGENCE",
        "LEARNER_INTELLIGENCE",
    ]


def test_capacity_reduction_keeps_structured_segment_state_and_schema() -> None:
    """Catches treating Segment State or the response contract as disposable context."""

    context = _context()
    state = StructuredSegmentState(
        schema_version="structured-segment-state-v1",
        active_goal="Finish equivalent fractions.",
        source_message_ids=[context.debug.current_turn_message_id],
    )
    protected = TutorContext(
        question=context.question,
        subject=context.subject,
        grade_level=context.grade_level,
        focus=context.focus,
        session_messages=context.session_messages,
        retrieval=(),
        intelligence=(),
        debug=context.debug,
        immediate_exchange=context.immediate_exchange,
    )
    result = apply_context_capacity_guardrail(
        context,
        capacity_limit=serialized_model_request_characters(_payload(protected, latest_segment_state=state)),
        payload_builder=lambda selected: _payload(selected, latest_segment_state=state),
    )

    assert "Finish equivalent fractions." in str(result.payload["input"])
    assert result.payload["response_schema"] == _payload(protected, latest_segment_state=state)["response_schema"]
    assert "Safety directive must remain." in str(result.payload["input"])


def test_protected_only_overflow_fails_before_any_lossy_protected_mutation() -> None:
    """Catches silently truncating the current turn, immediate exchange, or model contract."""

    context = _context()
    protected_only = TutorContext(
        question=context.question,
        subject=context.subject,
        grade_level=context.grade_level,
        focus=context.focus,
        session_messages=context.session_messages,
        retrieval=(),
        intelligence=(),
        debug=context.debug,
        immediate_exchange=context.immediate_exchange,
    )

    with pytest.raises(TutorContextCapacityExceeded) as error:
        apply_context_capacity_guardrail(protected_only, capacity_limit=1, payload_builder=_payload)

    assert error.value.lineage.dropped_context == ()
    assert error.value.lineage.final_measured_size > error.value.lineage.capacity_limit


def test_measurement_includes_structured_response_schema() -> None:
    """Catches measuring only instructions/input while omitting model-facing structured output."""

    payload = _payload(_context())
    without_schema = {key: value for key, value in payload.items() if key != "response_schema"}

    assert serialized_model_request_characters(payload) > serialized_model_request_characters(without_schema)
