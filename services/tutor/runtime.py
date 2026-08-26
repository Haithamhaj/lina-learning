"""Production Tutor orchestration over the approved safety and context boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.config import get_settings
from services.platform.db.models import CandidateEvent, LearningMessage, LearningSegment, LearningSession, ModelTask
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContext, TutorContextBuilder
from services.tutor.candidate_events import (
    CandidateEventContractError,
    CandidateEventMetadata,
    SuggestedAction,
    SuggestedActionKind,
    TUTOR_OUTPUT_RESPONSE_SCHEMA,
    normalize_suggested_actions,
    parse_candidate_event_metadata,
)
from services.tutor.safety import TutorSafetyRuntime, consume_safety_decision
from services.tutor.segments import (
    SEGMENT_RELATION_SCHEMA_VERSION,
    SEGMENT_STATE_SCHEMA_VERSION,
    SegmentRelation,
    StructuredSegmentState,
    StructuredSegmentStateError,
    assign_message_to_segment,
    create_next_segment,
    latest_segment_for_session,
    latest_valid_structured_segment_state,
    parse_structured_segment_state,
)
from services.tutor.student_sessions import append_student_message, latest_prior_tutor_teaching_method
from services.tutor.teaching_decisions import (
    PRIOR_METHOD_RELATION_DEFINITIONS,
    TEACHING_MODE_DEFINITIONS,
    TEACHING_STRATEGY_DEFINITIONS,
    PriorMethodRelation,
    TeachingMode,
    TeachingStrategy,
    parse_enum,
)
from services.tutor.teaching_methods import (
    ACTIVE_TEACHING_METHODS,
    TEACHING_METHOD_REGISTRY_VERSION,
    PriorTeachingMethodContext,
    TeachingMethod,
    is_supported_teaching_method,
    teaching_method_definitions,
)


SUGGESTED_ACTION_SOURCE_CONTEXT_CHARACTERS = 4000


@dataclass(frozen=True)
class TutorTextDelta:
    text: str


@dataclass(frozen=True)
class TutorTurn:
    text: str
    suggested_actions: list[SuggestedAction]
    sources: list[dict[str, object]]
    intelligence: list[str]
    mode: TeachingMode | None
    strategy: TeachingStrategy | None
    safety: dict[str, str | int]


@dataclass(frozen=True)
class _ResolvedSegmentRelation:
    segment: LearningSegment
    relation: str | None
    relation_source: str


class TutorModelStreamFailure(Exception):
    """A primary Tutor model stream failed after the Student interaction was accepted."""


class LocalTutorProvider:
    """Deterministic test/development adapter; configured providers stream remotely."""

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        return ModelResult(
            output={
                "text": f"Let’s work on this step by step. {payload['question']}",
                "suggested_actions": [],
                "teaching_mode": None,
                "teaching_strategy": None,
                "teaching_method_id": None,
                "prior_method_relation": None,
                "candidate_metadata": None,
            },
            input_tokens=20,
            output_tokens=18,
            estimated_cost_usd=0.0,
        )

    def stream(self, route: ModelRoute, payload: dict[str, object]) -> Iterator[StreamDelta | StreamComplete]:
        result = self.execute(route, payload)
        yield StreamDelta(str(result.output["text"]))
        yield StreamComplete(result)


TUTOR_SHARED_INSTRUCTIONS = (
    "You are Lina's fixed Grade 5 Math tutor: warm, conversational, patient, non-shaming, and focused on understanding. "
    "Speak naturally to an intelligent approximately 10-year-old: use easy conversational Arabic rather than unnecessary formality, natural child-appropriate English, and mirror the Student's reasonable level of formality. Do not use baby-talk or unnecessary formal educational wording. "
    "Reply primarily in the language of the Student's current message on every turn: Arabic message means primarily Arabic, English message means primarily English. "
    "Follow an immediate Arabic/English language switch without treating it as a topic switch or creating separate learner profiles, intelligence, or learning state. "
    "Use natural Arabic/English mixing only when the Student mixes languages or useful school/math terminology benefits from it. "
    "Keep the same relevant conversational context across a language switch. Current demonstrated behavior outranks historical learning notes. "
    "Prioritize the Student's immediate real-world safety over continuing any lesson, experiment, activity, or exercise. If the current conversation reasonably suggests an immediate safety concern, respond first with calm, simple, age-appropriate safety guidance; do not overreact to ordinary educational discussion of potentially dangerous concepts, and resume normal learning naturally when appropriate. "
    "Never announce learner labels or internal records. The book is curriculum grounding, not a script: use valid examples, analogies, or visual descriptions when useful. "
    "Prefer short sentences and manageable chunks. Default to one concept or one or two small steps, then invite interaction or a check instead of giving a long lecture. "
    "If the Student remains confused, change representation or support rather than repeating: use a concrete example, visual or mental representation, worked example, or guided step as useful. "
    "Use adaptive scaffolding such as worked example, guided attempt, lighter hint, and independent attempt; it is not a fixed sequence. "
    "For homework, allow a meaningful attempt and hint before giving an answer; if the Student is genuinely stuck, explain clearly, explain why, then ask one new application check. "
    "A Student saying they understand or choosing an action is not proof of understanding or mastery; normally use a small independent or application check when it matters. "
    "Praise only specific observed effort, reasoning, correction, or persistence; avoid automatic or exaggerated praise. Use zero to three emojis only when they add warmth or meaning, never on every sentence. "
    "Student-facing text must be plain text: no Markdown markers, headings, bold, or code fences. Do not use LaTeX or raw LaTeX notation. Use simple Grade-5-readable math notation and put equations on their own line when it improves Arabic/English readability. "
    "Safety policy is enforced before this call; do not mention internal policies. Return student-facing reply only in the structured text field. "
    "Return suggested_actions as zero to four short, visible objects with label and kind. Kind must be NAVIGATION for agency, support preference, or self-report actions, and ANSWER_CHOICE only for a guided answer choice. Suggested actions must use the same primary language as the response and contain no URLs, Markdown, or hidden metadata. After an explanatory, help, or confusion turn, normally provide two to four useful actions when that reduces friction or supports agency. Do not force buttons when a natural free response is pedagogically better, the Student needs to explain in their own words, generic chat/thanks does not benefit, or Safety produces a deterministic response. "
    "Set hidden candidate_metadata to null for greetings, thanks, generic chat, self-reported understanding, navigation/action selection alone, or when no meaningful observable learning signal occurred. A guided ANSWER_CHOICE may emit only an existing bounded attempt/correction/misconception type when its raw answer is meaningful; never emit independent success or mastery merely from a click. "
    "Emit Candidate Event metadata only for a specific, source-linked observable learning signal such as solving, explaining, applying, self-correcting, or transferring an idea. "
    "Never treat a chosen Tutor strategy as an outcome without an observable Student result. Never mention hidden metadata in text."
)


def build_tutor_model_payload(
    *,
    question: str,
    sources: list[dict[str, object]] | None = None,
    intelligence: list[str] | None = None,
    safety_directive: str | None = None,
    immediate_exchange: list[dict[str, object]] | None = None,
    session_messages: list[dict[str, str]] | None = None,
    candidate_source_message_id: UUID | None = None,
    prior_method: PriorTeachingMethodContext | None = None,
    suggested_action_source: LearningMessage | None = None,
    latest_segment_state: StructuredSegmentState | None = None,
) -> dict[str, object]:
    """Build bounded model input from the project-owned Tutor context only."""

    source_context = "\n\n".join(
        f"Curriculum source ({source['ref']}):\n{source['text']}" for source in (sources or [])
    ) or "No matching curriculum excerpt was retrieved."
    intelligence_context = "\n".join(intelligence or []) or "No relevant compact learning note was selected."
    immediate_exchange_context = "\n".join(
        _format_lineage_message(message) for message in (immediate_exchange or [])
    ) or "No immediate exchange was selected."
    session_context = "\n".join(
        f"{message['role']}: {message['content']}" for message in (session_messages or [])
    ) or "No older current-session continuity was selected."
    safety_context = f"\n\nAge-handling directive:\n{safety_directive}" if safety_directive else ""
    candidate_context = (
        "\n\nHidden Candidate Event source link:\n"
        f"If metadata is meaningful, use only this raw Student message ID: {candidate_source_message_id}."
        if candidate_source_message_id is not None
        else ""
    )
    current_turn_source_context = (
        f"\nCurrent Student raw source ID: [{candidate_source_message_id}]"
        if candidate_source_message_id is not None
        else ""
    )
    decision_context = "\n\nTeachingMode definitions:\n" + "\n".join(f"- {item.identifier}: {item.description}" for item in TEACHING_MODE_DEFINITIONS)
    decision_context += "\n\nTeachingStrategy definitions:\n" + "\n".join(f"- {item.identifier}: {item.description}" for item in TEACHING_STRATEGY_DEFINITIONS)
    decision_context += "\n\nActive TeachingMethod definitions:\n" + "\n".join(f"- {definition.method_id.value}: {definition.description}" for definition in teaching_method_definitions())
    decision_context += "\n\nPriorMethodRelation definitions:\n" + "\n".join(f"- {item.identifier}: {item.description}" for item in PRIOR_METHOD_RELATION_DEFINITIONS)
    decision_context += "\n\nChoose each semantic decision from the current conversation. All four decision fields may be null for a casual or non-instructional turn. A non-null TeachingMethod needs a non-null mode and strategy. A relation is only about the immediate previous persisted Tutor method. A different topic is not DID_NOT_HELP: use NOT_RELEVANT or null unless the Student actually judges that immediate prior representation. DID_NOT_HELP must not accompany the same method. Use EXPLICIT_REPEAT_REQUEST only when the selected method equals the immediate prior method; a request to return to an older, non-immediate representation is NOT_RELEVANT or null. The relation itself is never Candidate Evidence."
    prior_method_context = (
        f"\nPrevious Tutor TeachingMethod: {prior_method.teaching_method_id.value} "
        f"(registry {prior_method.registry_version})."
        if prior_method is not None
        else ""
    )
    suggested_action_source_context = (
        "\n\nSelected suggested-action source:\n"
        f"Tutor message ID: {suggested_action_source.id}\n"
        f"Tutor message:\n{suggested_action_source.content[:SUGGESTED_ACTION_SOURCE_CONTEXT_CHARACTERS]}"
        if suggested_action_source is not None
        else ""
    )
    segment_state_context = (
        "\n\nLatest confirmed Segment State (hidden conversational orientation, not learner intelligence):\n"
        f"{json.dumps(latest_segment_state.model_dump(mode='json'), ensure_ascii=False)}\n"
        "Its source_message_ids are prior State lineage only; they remain available for an updated State."
        if latest_segment_state is not None
        else "\n\nNo valid latest Segment State is available."
    )
    segment_context = (
        "\n\nHidden Segment relation:\n"
        "Choose segment_relation for the Current Student Turn only: CONTINUE when it belongs to the latest confirmed session Segment; "
        "NEW_SEGMENT for a meaningful transition; UNCERTAIN when you cannot confidently choose. "
        "Do not split one coherent topic into a new Segment for every question or explanation, and do not treat an Arabic/English language switch alone as a topic change. "
        "structured_segment_state is an optional compact, source-linked conversational orientation only. It is never Evidence, learner intelligence, mastery, a learner profile, Safety, or curriculum authority. "
        "For structured_segment_state.source_message_ids, cite only exact raw IDs explicitly available in this hidden context: the Current Student raw source ID, Immediate Exchange message IDs, and prior State source IDs. "
        "Never cite the Tutor message generated by this call because it does not exist yet; it may become a source on the next turn after persistence."
    )
    return {
        "instructions": TUTOR_SHARED_INSTRUCTIONS,
        "input": (
            f"Current Turn:\nStudent question:\n{question}{current_turn_source_context}\n\nImmediate exchange:\n{immediate_exchange_context}\n\n"
            f"Bounded older current-session continuity:\n{session_context}\n\n"
            f"Retrieved curriculum:\n{source_context}\n\nRelevant compact learning context:\n{intelligence_context}{safety_context}{candidate_context}{decision_context}{prior_method_context}{suggested_action_source_context}{segment_context}{segment_state_context}"
        ),
        "max_output_tokens": 800,
        "question": question,
        "sources": sources or [],
        "intelligence": intelligence or [],
        "active_teaching_methods": [method.value for method in ACTIVE_TEACHING_METHODS],
        "response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA,
        "candidate_source_message_id": str(candidate_source_message_id) if candidate_source_message_id is not None else None,
    }


class TutorRuntime:
    """One-call Tutor runtime; safety, context, and gateway remain explicit boundaries."""

    def __init__(self, session: Session, *, context_builder: TutorContextBuilder, safety_policy: SafetyPolicyService, gateway: ModelGateway) -> None:
        self._session = session
        self._context_builder = context_builder
        self._safety_policy = safety_policy
        self._gateway = gateway

    def stream_turn(
        self,
        *,
        learning_session: LearningSession,
        question: str,
        suggested_action_kind: SuggestedActionKind | str | None = None,
        suggested_action_source_tutor_message_id: UUID | None = None,
    ) -> Iterator[TutorTextDelta | TutorTurn]:
        content = question.strip()
        if not content:
            raise ValueError("A current Student question is required.")
        learning_session.last_activity_at = datetime.now(UTC)
        action_kind = SuggestedActionKind(suggested_action_kind) if suggested_action_kind is not None else None
        suggested_action_source = self._suggested_action_source(
            learning_session=learning_session,
            source_tutor_message_id=suggested_action_source_tutor_message_id,
        )
        interaction_payload = None
        if action_kind is not None:
            interaction_payload = {"input_kind": f"suggested_action_{action_kind.value.lower()}"}
            if suggested_action_source is not None:
                interaction_payload["suggested_action_source_tutor_message_id"] = str(suggested_action_source.id)
        student_message = append_student_message(
            self._session,
            learning_session=learning_session,
            content=content,
            interaction_payload=interaction_payload,
        )
        decision = self._safety_policy.evaluate(student_id=learning_session.student_id, text=content, interaction_ref=str(learning_session.id))
        safety = consume_safety_decision(decision)
        if not safety.continue_to_tutor:
            yield self._persist_turn(
                learning_session,
                safety.redirect_directive or "Please ask a trusted grown-up for help with this topic.",
                [],
                None,
                safety,
                None,
                None,
                candidate_metadata_status="not_requested",
            )
            return

        prior_method = latest_prior_tutor_teaching_method(
            self._session,
            learning_session=learning_session,
            before_message=student_message,
        )
        context = self._context_builder.build(
            learning_session=learning_session,
            question=content,
            current_turn_message_id=student_message.id,
        )
        latest_segment = latest_segment_for_session(self._session, session_id=learning_session.id)
        latest_segment_state = latest_valid_structured_segment_state(
            self._session,
            segment=latest_segment,
        )
        payload = _payload_from_context(
            context,
            safety=safety,
            candidate_source_message_id=student_message.id,
            prior_method=prior_method,
            suggested_action_source=suggested_action_source,
            latest_segment_state=latest_segment_state,
        )
        model_stream = self._gateway.stream(
            ModelTask.TUTOR,
            payload,
            lineage=AIExecutionLineage(
                operation="tutor_turn",
                student_id=learning_session.student_id,
                learning_session_id=learning_session.id,
                source_message_id=student_message.id,
            ),
        )
        result: ModelResult | None = None
        try:
            for event in model_stream:
                if isinstance(event, StreamDelta):
                    yield TutorTextDelta(event.text)
                elif isinstance(event, StreamComplete):
                    result = event.result
                    break
        except GeneratorExit:
            if result is None:
                try:
                    for event in model_stream:
                        if isinstance(event, StreamComplete):
                            result = event.result
                            break
                except Exception:
                    pass
            if result is not None:
                self._persist_completed_turn(
                    learning_session=learning_session,
                    student_message=student_message,
                    result=result,
                    context=context,
                    safety=safety,
                    prior_method=prior_method,
                    prior_segment_state=latest_segment_state,
                )
            raise
        except Exception as error:
            raise TutorModelStreamFailure("The primary Tutor model stream failed.") from error

        if result is None:
            raise TutorModelStreamFailure("The primary Tutor model stream ended without a final result.")
        turn = self._persist_completed_turn(
            learning_session=learning_session,
            student_message=student_message,
            result=result,
            context=context,
            safety=safety,
            prior_method=prior_method,
            prior_segment_state=latest_segment_state,
        )
        yield turn

    def _suggested_action_source(
        self,
        *,
        learning_session: LearningSession,
        source_tutor_message_id: UUID | None,
    ) -> LearningMessage | None:
        if source_tutor_message_id is None:
            return None
        message = self._session.get(LearningMessage, source_tutor_message_id)
        if (
            not isinstance(message, LearningMessage)
            or message.session_id != learning_session.id
            or message.role != "tutor"
        ):
            raise ValueError("Suggested action source is unavailable for this learning session.")
        return message

    def _persist_completed_turn(
        self,
        *,
        learning_session: LearningSession,
        student_message: LearningMessage,
        result: ModelResult,
        context: TutorContext,
        safety: TutorSafetyRuntime,
        prior_method: PriorTeachingMethodContext | None,
        prior_segment_state: StructuredSegmentState | None,
    ) -> TutorTurn:
        resolved_segment = self._resolve_segment_relation(
            learning_session=learning_session,
            relation_value=result.output.get("segment_relation"),
        )
        assign_message_to_segment(
            self._session,
            message=student_message,
            segment=resolved_segment.segment,
        )
        state, state_status = self._validated_segment_state(
            segment=resolved_segment.segment,
            state_value=result.output.get("structured_segment_state"),
            current_student_message=student_message,
            immediate_exchange=context.immediate_exchange,
            prior_segment_state=prior_segment_state,
        )
        self._merge_student_conversation_metadata(
            student_message=student_message,
            segment=resolved_segment.segment,
            relation=resolved_segment.relation,
            relation_source=resolved_segment.relation_source,
            state=state,
            state_status=state_status,
        )
        teaching_decision = _validate_teaching_decision(
            mode_value=result.output.get("teaching_mode"),
            strategy_value=result.output.get("teaching_strategy"),
            method_value=result.output.get("teaching_method_id"),
            relation_value=result.output.get("prior_method_relation"),
            prior_method=prior_method,
        )
        candidate_metadata_status, candidate_metadata_error = self._persist_candidates(
            learning_session=learning_session,
            source_message=student_message,
            result=result,
            prior_method=prior_method,
        )
        turn = self._persist_turn(
            learning_session,
            str(result.output.get("text")),
            normalize_suggested_actions(result.output.get("suggested_actions")),
            context,
            safety,
            teaching_decision.mode,
            teaching_decision.strategy,
            selected_method=teaching_decision.method,
            prior_method_relation=teaching_decision.relation,
            method_status=teaching_decision.method_status,
            decision_status=teaching_decision.status,
            candidate_metadata_status=candidate_metadata_status,
            candidate_metadata_error=candidate_metadata_error,
            ai_execution_id=result.execution_id,
            segment_id=resolved_segment.segment.id,
        )
        if state is not None:
            resolved_segment.segment.structured_state = state.model_dump(mode="json")
            self._session.flush()
        return turn

    def _resolve_segment_relation(
        self,
        *,
        learning_session: LearningSession,
        relation_value: object,
    ) -> "_ResolvedSegmentRelation":
        """Resolve Luna's same-call semantic decision without inventing topic meaning."""

        latest = latest_segment_for_session(self._session, session_id=learning_session.id)
        try:
            relation = SegmentRelation(relation_value) if isinstance(relation_value, str) else None
        except ValueError:
            relation = None
        if latest is None:
            return _ResolvedSegmentRelation(
                segment=create_next_segment(self._session, learning_session=learning_session),
                relation=None,
                relation_source="STRUCTURAL_FIRST_SEGMENT",
            )
        if relation is SegmentRelation.CONTINUE:
            return _ResolvedSegmentRelation(segment=latest, relation=relation.value, relation_source="LUNA")
        if relation in {SegmentRelation.NEW_SEGMENT, SegmentRelation.UNCERTAIN}:
            return _ResolvedSegmentRelation(
                segment=create_next_segment(self._session, learning_session=learning_session),
                relation=relation.value,
                relation_source="LUNA",
            )
        return _ResolvedSegmentRelation(
            segment=create_next_segment(self._session, learning_session=learning_session),
            relation=SegmentRelation.UNCERTAIN.value,
            relation_source="FALLBACK",
        )

    def _validated_segment_state(
        self,
        *,
        segment: LearningSegment,
        state_value: object,
        current_student_message: LearningMessage,
        immediate_exchange: tuple[object, ...],
        prior_segment_state: StructuredSegmentState | None,
    ) -> tuple[StructuredSegmentState | None, str]:
        if state_value is None:
            return None, "absent"
        visible_source_ids = {current_student_message.id}
        visible_source_ids.update(
            message.message_id for message in immediate_exchange
            if isinstance(getattr(message, "message_id", None), UUID)
        )
        if prior_segment_state is not None:
            visible_source_ids.update(prior_segment_state.source_message_ids)
        source_ids = visible_source_ids & self._segment_source_message_ids(segment_id=segment.id)
        try:
            return parse_structured_segment_state(
                state_value,
                allowed_source_message_ids=source_ids,
            ), "persisted"
        except StructuredSegmentStateError:
            return None, "invalid"

    def _segment_source_message_ids(self, *, segment_id: UUID) -> set[UUID]:
        if hasattr(self._session, "scalars"):
            return set(self._session.scalars(
                select(LearningMessage.id).where(LearningMessage.segment_id == segment_id)
            ))
        return {
            row.id for row in getattr(self._session, "rows", ())
            if isinstance(row, LearningMessage) and row.segment_id == segment_id
        }

    def _merge_student_conversation_metadata(
        self,
        *,
        student_message: LearningMessage,
        segment: LearningSegment,
        relation: str | None,
        relation_source: str,
        state: StructuredSegmentState | None,
        state_status: str,
    ) -> None:
        payload = dict(student_message.payload) if isinstance(student_message.payload, dict) else {}
        conversation = dict(payload.get("conversation")) if isinstance(payload.get("conversation"), dict) else {}
        conversation.update({
            "relation_schema_version": SEGMENT_RELATION_SCHEMA_VERSION,
            "segment_relation": relation,
            "relation_source": relation_source,
            "segment_id": str(segment.id),
            "state_schema_version": SEGMENT_STATE_SCHEMA_VERSION if state is not None else None,
            "state_status": state_status,
        })
        payload["conversation"] = conversation
        student_message.payload = payload
        self._session.flush()

    def _persist_candidates(
        self,
        *,
        learning_session: LearningSession,
        source_message: LearningMessage,
        result: ModelResult | None,
        prior_method: PriorTeachingMethodContext | None,
    ) -> tuple[str, str | None]:
        if _is_non_evidentiary_interaction(source_message):
            return "not_evidence", None
        if result is not None:
            metadata_error = result.output.get("candidate_metadata_error")
            if isinstance(metadata_error, str):
                return "invalid", metadata_error
        raw_metadata = result.output.get("candidate_metadata") if result is not None else None
        if raw_metadata is None:
            return "absent", None
        try:
            metadata = parse_candidate_event_metadata(
                raw_metadata,
                allowed_source_message_ids={source_message.id},
            )
        except CandidateEventContractError:
            return "invalid", "candidate_contract_invalid"
        if _is_answer_choice_interaction(source_message):
            metadata = _bounded_answer_choice_metadata(metadata)
            if not metadata.candidates:
                return "answer_choice_filtered", None
        candidates = list(metadata.candidates)
        missing_strategy_lineage = False
        if any(candidate.event_type == "strategy_outcome" for candidate in candidates) and prior_method is None:
            candidates = [candidate for candidate in candidates if candidate.event_type != "strategy_outcome"]
            missing_strategy_lineage = True
        if not candidates:
            return ("strategy_outcome_lineage_missing", None) if missing_strategy_lineage else ("absent", None)
        route = self._gateway.route_for(ModelTask.TUTOR)
        for candidate in candidates:
            payload: dict[str, object] = {
                "candidate_schema_version": metadata.version,
                "summary": candidate.summary,
                "school_or_extended": candidate.school_or_extended,
                "source_message_ids": [str(identifier) for identifier in candidate.source_message_ids],
                "subject": learning_session.subject,
                "observed_student_outcome": candidate.observed_student_outcome,
                "model_route": {"provider": route.provider, "model": route.model},
            }
            if candidate.event_type == "strategy_outcome" and prior_method is not None:
                payload.update({
                    "strategy_key": prior_method.teaching_method_id.value,
                    "strategy_source_tutor_message_id": str(prior_method.tutor_message_id),
                    "strategy_registry_version": prior_method.registry_version,
                })
            self._session.add(
                CandidateEvent(
                    session_id=learning_session.id,
                    message_id=source_message.id,
                    event_type=candidate.event_type,
                    concept_ref=candidate.concept_ref,
                    signal=candidate.signal,
                    payload=payload,
                    ai_execution_id=result.execution_id,
                )
            )
        self._session.flush()
        return ("strategy_outcome_lineage_missing", None) if missing_strategy_lineage else ("persisted", None)

    def _persist_turn(
        self,
        learning_session: LearningSession,
        text: str,
        suggested_actions: list[SuggestedAction],
        context: TutorContext | None,
        safety: TutorSafetyRuntime,
        mode: TeachingMode | None,
        strategy: TeachingStrategy | None,
        *,
        candidate_metadata_status: str,
        selected_method: TeachingMethod | None = None,
        prior_method_relation: PriorMethodRelation | None = None,
        method_status: str = "not_selected",
        decision_status: str = "valid",
        candidate_metadata_error: str | None = None,
        ai_execution_id: UUID | None = None,
        segment_id: UUID | None = None,
    ) -> TutorTurn:
        sources = _source_metadata(context)
        intelligence = [item.text for item in context.intelligence] if context else []
        payload: dict[str, object] = {
            "source_refs": [source["source_ref"] for source in sources],
            "intelligence_used": intelligence,
            "safety": safety.audit_metadata(),
            "teaching_mode": mode.value if mode is not None else None,
            "teaching_strategy": strategy.value if strategy is not None else None,
            "teaching_method_id": selected_method.value if selected_method is not None else None,
            "prior_method_relation": prior_method_relation.value if prior_method_relation is not None else None,
            "teaching_decision_status": decision_status,
            "candidate_metadata_status": candidate_metadata_status,
            "suggested_actions": [action.model_dump() for action in suggested_actions],
        }
        if selected_method is not None:
            payload["teaching_method_registry_version"] = TEACHING_METHOD_REGISTRY_VERSION
        if method_status != "not_selected":
            payload["teaching_method_status"] = method_status
        if candidate_metadata_error is not None:
            payload["candidate_metadata_error"] = candidate_metadata_error
        if context is not None:
            payload["context_debug"] = {
                "current_turn_message_id": (
                    str(context.debug.current_turn_message_id)
                    if context.debug.current_turn_message_id is not None
                    else None
                ),
                "immediate_exchange_message_ids": [
                    str(identifier) for identifier in context.debug.immediate_exchange_message_ids
                ],
                "older_continuity_message_ids": [
                    str(identifier) for identifier in context.debug.older_continuity_message_ids
                ],
                "session_message_ids": [str(identifier) for identifier in context.debug.session_message_ids],
                "retrieval_source_refs": list(context.debug.retrieval_source_refs),
                "intelligence_source_ids": [str(identifier) for identifier in context.debug.intelligence_source_ids],
            }
        self._session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content=text,
                payload=payload,
                ai_execution_id=ai_execution_id,
                segment_id=segment_id,
                created_at=datetime.now(UTC),
            )
        )
        learning_session.last_activity_at = datetime.now(UTC)
        self._session.flush()
        return TutorTurn(text, suggested_actions, sources, intelligence, mode, strategy, safety.audit_metadata())


def _payload_from_context(
    context: TutorContext,
    *,
    safety: TutorSafetyRuntime,
    candidate_source_message_id: UUID,
    prior_method: PriorTeachingMethodContext | None = None,
    suggested_action_source: LearningMessage | None = None,
    latest_segment_state: StructuredSegmentState | None = None,
) -> dict[str, object]:
    return build_tutor_model_payload(
        question=context.question,
        sources=[{"ref": block.source_ref, "text": block.text} for block in context.retrieval],
        intelligence=[item.text for item in context.intelligence],
        safety_directive=safety.tutor_directive,
        immediate_exchange=[
            {"message_id": str(message.message_id), "role": message.role, "content": message.content}
            for message in context.immediate_exchange
        ],
        session_messages=[
            {"role": message.role, "content": message.content}
            for message in context.session_messages
        ],
        candidate_source_message_id=candidate_source_message_id,
        prior_method=prior_method,
        suggested_action_source=suggested_action_source,
        latest_segment_state=latest_segment_state,
    )


def _format_lineage_message(message: dict[str, object]) -> str:
    """Render a raw conversational source with its exact hidden persistence identity."""

    role = str(message.get("role", "message"))
    content = str(message.get("content", ""))
    message_id = message.get("message_id")
    if isinstance(message_id, (str, UUID)):
        return f"{role} message [{message_id}]:\n{content}"
    return f"{role}: {content}"


@dataclass(frozen=True)
class _ValidatedTeachingDecision:
    mode: TeachingMode | None
    strategy: TeachingStrategy | None
    method: TeachingMethod | None
    relation: PriorMethodRelation | None
    method_status: str
    status: str


def _validate_teaching_decision(
    *,
    mode_value: object,
    strategy_value: object,
    method_value: object,
    relation_value: object,
    prior_method: PriorTeachingMethodContext | None,
) -> _ValidatedTeachingDecision:
    """Validate Luna's canonical values without inferring their meaning from words."""

    mode = parse_enum(mode_value, TeachingMode)
    strategy = parse_enum(strategy_value, TeachingStrategy)
    relation = parse_enum(relation_value, PriorMethodRelation)
    method = is_supported_teaching_method(method_value, registry_version=TEACHING_METHOD_REGISTRY_VERSION)
    status = "valid"
    method_status = "selected" if method is not None else "not_selected"
    if mode_value is not None and mode is None:
        status = "invalid_mode"
    elif strategy_value is not None and strategy is None:
        status = "invalid_strategy"
    elif method_value is not None and method is None:
        method_status = "invalid"
        status = "invalid_method"
    elif relation_value is not None and relation is None:
        status = "invalid_prior_method_relation"
    elif method is not None and (mode is None or strategy is None):
        status = "instructional_context_missing"
    if relation is not None:
        if prior_method is None:
            relation = None
            status = "prior_method_relation_without_prior"
        elif relation is PriorMethodRelation.DID_NOT_HELP and method == prior_method.teaching_method_id:
            relation = None
            status = "prior_method_relation_inconsistent"
        elif relation is PriorMethodRelation.EXPLICIT_REPEAT_REQUEST and method != prior_method.teaching_method_id:
            relation = None
            status = "prior_method_relation_inconsistent"
    return _ValidatedTeachingDecision(mode, strategy, method, relation, method_status, status)


def _source_metadata(context: TutorContext | None) -> list[dict[str, object]]:
    return [] if context is None else [{"source_ref": block.source_ref, "page_number": block.page_number, "block_type": block.block_type} for block in context.retrieval]


def _is_non_evidentiary_interaction(message: LearningMessage) -> bool:
    payload = message.payload if isinstance(message.payload, dict) else {}
    if payload.get("input_kind") == "suggested_action_navigation":
        return True
    self_report = message.content.casefold().strip(" .!؟?👍✨✍️")
    return self_report in {
        "فهمت",
        "فهمت الآن",
        "تمام فهمت",
        "i got it",
        "i understand",
        "got it",
        "yes",
    }


def _is_answer_choice_interaction(message: LearningMessage) -> bool:
    payload = message.payload if isinstance(message.payload, dict) else {}
    return payload.get("input_kind") == "suggested_action_answer_choice"


def _bounded_answer_choice_metadata(metadata: CandidateEventMetadata) -> CandidateEventMetadata:
    allowed_event_types = {"learning_attempt", "guided_success", "incorrect_attempt", "misconception_signal"}
    return metadata.model_copy(
        update={"candidates": [candidate for candidate in metadata.candidates if candidate.event_type in allowed_event_types]}
    )


def create_tutor_runtime(session: Session) -> TutorRuntime:
    settings = get_settings()
    retrieval = RetrievalService(session) if settings.model_provider == "mock" else None
    return TutorRuntime(session, context_builder=TutorContextBuilder(session, retrieval_service=retrieval), safety_policy=SafetyPolicyService(session), gateway=create_tutor_gateway(session, local_provider=LocalTutorProvider(), settings=settings))


def start_session(session: Session, *, student_id: UUID) -> LearningSession:
    """Compatibility helper for the development-only sandbox session route."""

    learning_session = LearningSession(student_id=student_id, subject="MATH")
    session.add(learning_session)
    session.flush()
    return learning_session


def tutor_turn(session: Session, *, learning_session: LearningSession, question: str) -> TutorTurn:
    """Compatibility adapter that drains the production stream for the sandbox route."""

    final: TutorTurn | None = None
    for event in create_tutor_runtime(session).stream_turn(
        learning_session=learning_session, question=question
    ):
        if isinstance(event, TutorTurn):
            final = event
    if final is None:
        raise RuntimeError("Tutor stream ended without a final response.")
    return final
