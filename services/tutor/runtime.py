"""Production Tutor orchestration over the approved safety and context boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import unicodedata
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import (
    AIExecutionLineage,
    ModelGateway,
    ModelResult,
    ModelRoute,
    StreamComplete,
    StreamDelta,
    StreamParentBoundaryDecision,
)
from services.platform.config import get_settings
from services.studio.tutor_context import (
    STUDIO_TUTOR_CONTEXT_SCHEMA_VERSION,
    StudioTutorWorkspaceContext,
    cancel_studio_tutor_observation,
    mark_studio_tutor_observation_failed,
    select_studio_tutor_context,
)
from services.studio.router import (
    ActiveSceneCapability,
    WorkspaceAuthorityContext,
    WorkspaceExecutionDecision,
    WorkspaceDecisionStatus,
    route_workspace_intent,
)
from services.studio.subjects import PRODUCTION_CURRENT_PROFILE_VERSIONS, production_subject_registry
from services.studio.workspace_capabilities import build_workspace_capability_context
from services.studio.workspace_intent import WorkspaceIntentContractError, parse_workspace_intent
from services.platform.db.models import CandidateEvent, LearningMessage, LearningSegment, LearningSession, ModelTask
from services.platform.safety import ParentBoundaryResolution, SafetyAction, SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.intelligence.subjects import BROAD_SUBJECT_KEYS, is_supported_broad_subject
from services.tutor.capacity import (
    TutorContextCapacityExceeded,
    TutorContextCapacityLineage,
    apply_context_capacity_guardrail,
)
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextBuilder
from services.tutor.candidate_events import (
    CandidateEventContractError,
    CandidateEventMetadata,
    CandidateEventMetadataItem,
    MisconceptionEvidence,
    PersistedGuidedLearningCheck,
    SuggestedAction,
    SuggestedActionKind,
    TUTOR_OUTPUT_RESPONSE_SCHEMA,
    TUTOR_TURN_SCHEMA_VERSION,
    normalize_guided_learning_check,
    normalize_suggested_actions,
    parse_candidate_event_metadata,
    persisted_guided_learning_check,
)
from services.tutor.parent_boundaries import (
    ParentBoundaryDecision,
    ParentBoundaryModelAction,
    parse_parent_boundary_decision,
    parse_redirect_fragments,
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
from services.tutor.student_sessions import (
    append_student_message,
    latest_prior_tutor_teaching_method,
    latest_tutor_guided_check_choice,
)
from services.tutor.teaching_decisions import (
    PRIOR_METHOD_RELATION_CALIBRATION_GUIDANCE,
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
logger = logging.getLogger(__name__)


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
    guided_check: PersistedGuidedLearningCheck | None = None
    studio_observation_id: UUID | None = None
    studio_ai_execution_id: UUID | None = None
    studio_source_message_id: UUID | None = None


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
                "guided_check": None,
                "teaching_mode": None,
                "teaching_strategy": None,
                "teaching_method_id": None,
                "prior_method_relation": None,
                "candidate_metadata": None,
                "provisional_broad_subject": None,
                "workspace_intent": None,
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
    "You are Lina's Math tutor: warm, conversational, patient, non-shaming, and focused on understanding. "
    "Use the authoritative Student Core Context when it contains age or grade to calibrate your language and examples. Do not infer or invent the Student's age, grade, identity, or profile details when those fields are absent. Speak naturally in easy conversational Arabic when replying in Arabic, natural child-appropriate English when replying in English, and mirror the Student's reasonable level of formality. Do not use baby-talk or unnecessary formal educational wording. "
    "Personal Memory contains prior explicit Student-provided personal context. Use it only when it naturally improves an example, analogy, conversational continuity, warmth, or interpretation of an explicit personal reference; do not force it into every response, do not infer extra traits from it, and do not expose storage mechanics. If current Student conversation conflicts with Personal Memory, current Student conversation wins immediately. Student Core Context remains authoritative for identity, age, and grade. "
    "Reply primarily in the language clearly expressed by the Student's current message on every turn: Arabic message means primarily Arabic, English message means primarily English. A language-neutral current turn, such as only a number, fraction, equation, mathematical expression, or answer-choice symbol, is not a language switch: do not choose Arabic or English from neutral notation alone; preserve the established primary conversational language from the immediate active exchange/current context. English active exchange followed by 21 stays primarily English; Arabic active exchange followed by 21 stays primarily Arabic. Only a clear current Arabic or English message overrides that established language; a clear explicit language switch overrides the prior language without treating it as a topic switch or creating separate learner profiles, intelligence, or learning state. Use natural bilingual school/math terminology when the Student mixes languages or it is useful. "
    "Keep the same relevant conversational context across a language switch. Current demonstrated behavior outranks historical learning notes. "
    "Prioritize the Student's immediate real-world safety over continuing any lesson, experiment, activity, or exercise. If the current conversation reasonably suggests an immediate safety concern, respond first with calm, simple, age-appropriate safety guidance; do not overreact to ordinary educational discussion of potentially dangerous concepts, and resume normal learning naturally when appropriate. "
    "Never announce learner labels or internal records. The book is curriculum grounding, not a script: use valid examples, analogies, or visual descriptions when useful. "
    "Prefer short sentences and manageable chunks. Default to one concept or one or two small steps, then invite interaction or a check instead of giving a long lecture. "
    "If the Student remains confused, change representation or support rather than repeating: use a concrete example, visual or mental representation, worked example, or guided step as useful. "
    "Use adaptive scaffolding such as worked example, guided attempt, lighter hint, and independent attempt; it is not a fixed sequence. "
    "For homework, allow a meaningful attempt and hint before giving an answer; if the Student is genuinely stuck, explain clearly, explain why, then ask one new application check. "
    "A Student saying they understand or choosing an action is not proof of understanding or mastery; normally use a small independent or application check when it matters. "
    "After repeated, independently reasoned success on substantially the same current idea, avoid another near-identical practice item that adds little information: normally prefer meaningful variation, deeper reasoning, transfer, useful progression, or restore Student agency, or naturally finish the practice. Do not infer mastery. Do not use a fixed number of correct answers; continued practice may still be useful when performance is fragile, supported, uncertain, contradictory, or recently repaired, or when the next task tests a genuinely different aspect. "
    "Praise only specific observed effort, reasoning, correction, or persistence; avoid automatic or exaggerated praise. Use zero to three emojis only when they add warmth or meaning, never on every sentence. "
    "Student-facing text must be plain text: no Markdown markers, headings, bold, or code fences. Do not use LaTeX or raw LaTeX notation. Use simple Grade-5-readable math notation and put equations on their own line when it improves Arabic/English readability. "
    "The non-overridable hard safety baseline is enforced before this call. Parent Boundary settings are server-owned and the server enforces the final visible response after this call; do not mention internal policies. Return ordinary student-facing reply only in the structured text field. "
    "Return suggested_actions as zero to four short, visible conversational controls with label and kind. Every suggested_action click is non-evidentiary, including any action historically labeled ANSWER_CHOICE. Use NAVIGATION for agency, support preference, or self-report actions. Suggested actions must use the same primary language as the response and contain no URLs, Markdown, or hidden metadata. After an explanatory, help, or confusion turn, normally provide two to four useful actions when that reduces friction or supports agency. "
    "Use guided_check only for one concrete academic response opportunity: include its exact question prompt and two to four answer choices. Do not use guided_check for navigation, topic selection, support preferences, self-reports, or agency. The server—not you—creates the durable check identity. A selected valid guided_check choice may emit only an existing bounded attempt/correction type when its raw answer is meaningful; never emit independent success, mastery, or misconception_signal merely from a click. "
    "Set hidden candidate_metadata to null for greetings, thanks, generic chat, self-reported understanding, generic action selection alone, or when no meaningful observable learning signal occurred. "
    "Emit Candidate Event metadata only for a specific, source-linked observable learning signal such as solving, explaining, applying, self-correcting, or transferring an idea. "
    "For Candidate event type selection, independent_success means the Student succeeds on the target response without meaningful task-specific support that materially supplies or narrows the solution path; correctness alone is insufficient without an observable successful learning signal. Earlier general teaching does not by itself make a later fresh-task success guided, and ordinary task presentation or encouragement is not guidance: a Student may learn the concept earlier and still demonstrate independent_success on a new task. guided_success requires meaningful immediate, task-specific scaffolding that materially helps produce the target response, such as a specific hint, supplied operation, key intermediate step, decomposed next step, materially narrowed path, or directly supplied key relationship. The distinction is support for the observed target response. Do not classify based merely on whether the Tutor taught earlier, TeachingStrategy alone, TeachingMethod alone, Student confidence, or response length. "
    "Confusion is not a misconception. Uncertainty, a request for another explanation, a wrong answer without stated reasoning, and a calculation slip are not misconceptions by themselves. When the Student is confused, respond pedagogically and change support or representation when useful. A misconception_signal is allowed only when the Student-authored current raw message explicitly demonstrates a specific incorrect mental model, rule, relationship, or interpretation. When only an answer is wrong without stated reasoning, prefer incorrect_attempt when appropriate. Every misconception_signal must include misconception_evidence with version misconception-evidence-v1, a concise incorrect_model, the current Student source_message_id, and an explicit_student_reasoning field that must copy the supporting Student reasoning span exactly from that raw message; do not paraphrase or use Tutor text. "
    "Never treat a chosen Tutor strategy as an outcome without an observable Student result. provisional_broad_subject is optional, must be null for casual or ambiguous turns, and when present must select only the supplied controlled Broad Subject key from the current conversation. It is a non-authoritative runtime hint only: it is not Evidence, learner intelligence, or final Segment Subject authority. workspace_intent is required but nullable: use null when no Workspace support is needed. When useful, it may express only a bounded educational need, current academic Subject, learning goal, representation need, Student response mode, source reference, and safe text fallback. Never choose a renderer, implementation technology, provider, model, Scene ID, event, reducer, validator, or specialist execution. Never mention hidden metadata in text."
)


def build_tutor_model_payload(
    *,
    question: str,
    sources: list[dict[str, object]] | None = None,
    intelligence: list[str] | None = None,
    student_core_context: dict[str, object] | None = None,
    personal_memory: str | None = None,
    safety_directive: str | None = None,
    immediate_exchange: list[dict[str, object]] | None = None,
    recent_exchanges: list[list[dict[str, object]]] | None = None,
    semantic_recall_exchanges: list[list[dict[str, object]]] | None = None,
    candidate_source_message_id: UUID | None = None,
    prior_method: PriorTeachingMethodContext | None = None,
    suggested_action_source: LearningMessage | None = None,
    latest_segment_state: StructuredSegmentState | None = None,
    effective_parent_boundaries: dict[str, str] | None = None,
    studio_context: StudioTutorWorkspaceContext | None = None,
) -> dict[str, object]:
    """Build bounded model input from the project-owned Tutor context only."""

    source_context = "\n\n".join(
        f"Curriculum source ({source['ref']}):\n{source['text']}" for source in (sources or [])
    ) or "No matching curriculum excerpt was retrieved."
    intelligence_context = "\n".join(intelligence or []) or "No relevant compact learning note was selected."
    supplied_core_context = student_core_context or {}
    student_core_context = {
        field: supplied_core_context[field]
        for field in ("display_name", "age_years", "grade_level")
        if supplied_core_context.get(field) is not None
    }
    core_context_text = json.dumps(student_core_context, ensure_ascii=False) if student_core_context else "No Student Core Profile fields are available."
    personal_memory_context = (
        "Personal Memory — prior Student-provided context (advisory; current Student conversation wins on conflict):\n"
        f"{personal_memory}\n\n"
        if personal_memory
        else ""
    )
    immediate_exchange_context = "\n".join(
        _format_lineage_message(message) for message in (immediate_exchange or [])
    ) or "No immediate exchange was selected."
    recent_exchange_context = "\n\n".join(
        "\n".join(_format_lineage_message(message) for message in exchange)
        for exchange in (recent_exchanges or [])
    ) or "No recent raw complete Exchanges were selected."
    semantic_recall_context = "\n\n".join(
        "\n".join(_format_lineage_message(message) for message in exchange)
        for exchange in (semantic_recall_exchanges or [])
    ) or "No relevant older complete Exchanges from this Segment were selected."
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
    decision_context += "\n\n" + PRIOR_METHOD_RELATION_CALIBRATION_GUIDANCE
    decision_context += "\n\nControlled Broad Subject keys for optional provisional_broad_subject:\n" + ", ".join(BROAD_SUBJECT_KEYS)
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
    parent_boundary_context = "\n\nEffective Parent Boundary settings (server-owned; never change them):\n" + "\n".join(
        f"- {category}: {state}"
        for category, state in sorted((effective_parent_boundaries or {}).items())
    )
    parent_boundary_context += (
        "\nParent Boundary semantic decision: classify only the conceptual current request. "
        "Use applies=false, category=null, model_action=ALLOW, redirect=null for ordinary, incidental, or ambiguous language. "
        "Biology, pregnancy, fetal development, placenta, and age-appropriate birth education are ordinary educational discussion, not SEXUAL_CONTENT. "
        "Neutral descriptive discussion of religions is ordinary educational discussion. A scientific question that happens to mention God is ordinary discussion. "
        "Use applies=true only when the current request itself is within a configured family-sensitive category. "
        "When REDIRECT_TO_PARENT is the effective setting, provide only brief acknowledgement, parent_reference, and safe_offer fragments in parent_boundary.redirect; do not put redirect wording in text. "
        "The server enforces the final visible response and may ignore your model_action or fragments."
    )
    workspace_capability_context = build_workspace_capability_context(
        studio_context,
        authorized_source_references=tuple(
            str(source["ref"]) for source in (sources or []) if isinstance(source, dict) and isinstance(source.get("ref"), str)
        ),
    )
    studio_workspace_context = (
        "\n\nStudio Workspace Context (current authoritative Workspace state; unseen Events are meaningful Student actions since the last successful Tutor observation):\n"
        f"{json.dumps(studio_context.as_model_payload(), ensure_ascii=False)}\n"
        "Workspace Capability Context (compact server-owned availability, not an implementation menu):\n"
        f"{json.dumps(workspace_capability_context.as_model_payload(), ensure_ascii=False)}\n"
        "Respond naturally to current Workspace behavior when useful. Do not mention internal event, storage, or observation terminology. "
        "Studio validation is not Learning Evidence or mastery. You must not mutate Studio state. If Workspace support would help, use only the strict workspace_intent field to express educational need; Studio selects any capability deterministically."
        if studio_context is not None
        else ""
    )
    return {
        "instructions": TUTOR_SHARED_INSTRUCTIONS,
        "input": (
            f"Student Core Context (Parent/System-authoritative identity only; never learning evidence):\n{core_context_text}\n\n"
            f"{personal_memory_context}"
            f"Current Turn:\nStudent question:\n{question}{current_turn_source_context}\n\nImmediate Exchange:\n{immediate_exchange_context}\n\n"
            f"Recent raw complete Exchanges:\n{recent_exchange_context}\n\n"
            f"Relevant older complete Exchanges from current Segment:\n{semantic_recall_context}\n\n"
            f"Retrieved curriculum:\n{source_context}\n\nRelevant compact learning context:\n{intelligence_context}{studio_workspace_context}{safety_context}{candidate_context}{decision_context}{prior_method_context}{suggested_action_source_context}{segment_context}{segment_state_context}{parent_boundary_context}"
        ),
        "max_output_tokens": get_settings().tutor_max_output_tokens,
        "question": question,
        "sources": sources or [],
        "intelligence": intelligence or [],
        "student_core_context": student_core_context,
        "personal_memory": personal_memory,
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
        guided_check_id: UUID | None = None,
        guided_check_source_tutor_message_id: UUID | None = None,
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
        guided_check_source = self._guided_check_source(
            learning_session=learning_session,
            content=content,
            guided_check_id=guided_check_id,
            source_tutor_message_id=guided_check_source_tutor_message_id,
        )
        if action_kind is not None and guided_check_source is not None:
            raise ValueError("A Student interaction cannot be both a suggested action and a guided check choice.")
        interaction_payload = None
        if guided_check_source is not None and guided_check_id is not None:
            interaction_payload = {
                "input_kind": "guided_learning_check_answer",
                "guided_check_id": str(guided_check_id),
                "guided_check_source_tutor_message_id": str(guided_check_source.id),
            }
        elif action_kind is not None:
            interaction_payload = {"input_kind": "suggested_action"}
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
        get_bind = getattr(self._session, "get_bind", None)
        studio_selection = (
            None
            if not callable(get_bind)
            else select_studio_tutor_context(
                bind=get_bind(),
                student_id=learning_session.student_id,
                learning_session_id=learning_session.id,
            )
        )
        context_arguments = {
            "learning_session": learning_session,
            "question": content,
            "current_turn_message_id": student_message.id,
        }
        # Preserve the established no-Studio builder boundary.  A Studio field is
        # supplied only for a real, active Runtime selection; this also keeps
        # existing in-memory test builders (which intentionally model no DB
        # Runtime) compatible with the ordinary Tutor path.
        if studio_selection is not None:
            context_arguments["studio_context"] = studio_selection.context
        context = self._context_builder.build(**context_arguments)
        latest_segment = latest_segment_for_session(self._session, session_id=learning_session.id)
        latest_segment_state = latest_valid_structured_segment_state(
            self._session,
            segment=latest_segment,
        )
        effective_parent_boundaries = self._effective_parent_boundaries(student_id=learning_session.student_id)
        try:
            guarded = apply_context_capacity_guardrail(
                context,
                capacity_limit=get_settings().tutor_context_capacity,
                payload_builder=lambda selected: _payload_from_context(
                    selected,
                    safety=safety,
                    candidate_source_message_id=student_message.id,
                    prior_method=prior_method,
                    suggested_action_source=guided_check_source or suggested_action_source,
                    latest_segment_state=latest_segment_state,
                    effective_parent_boundaries=effective_parent_boundaries,
                ),
            )
        except TutorContextCapacityExceeded as error:
            if context.studio_workspace is not None and context.studio_workspace.observation_id is not None:
                mark_studio_tutor_observation_failed(
                    bind=self._session.get_bind(),
                    student_id=learning_session.student_id,
                    observation_id=context.studio_workspace.observation_id,
                    failure_code="CAPACITY_EXCEEDED",
                )
            logger.warning(
                "Tutor context capacity exceeded before the primary model call.",
                extra={"tutor_context_capacity": error.lineage.as_metadata()},
            )
            raise
        context = guarded.context
        payload = guarded.payload
        capacity_lineage = guarded.lineage
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
        buffered_deltas: list[str] = []
        parent_decision: ParentBoundaryDecision | None = None
        parent_resolution: ParentBoundaryResolution | None = None
        try:
            for event in model_stream:
                if isinstance(event, StreamDelta):
                    if parent_resolution is None:
                        buffered_deltas.append(event.text)
                    elif parent_resolution.action is not SafetyAction.REDIRECT_TO_PARENT:
                        yield TutorTextDelta(event.text)
                elif isinstance(event, StreamParentBoundaryDecision):
                    parent_decision = parse_parent_boundary_decision(event.payload)
                    parent_resolution = self._resolve_parent_boundary(
                        student_id=learning_session.student_id,
                        decision=parent_decision,
                    )
                    if parent_resolution.action is not SafetyAction.REDIRECT_TO_PARENT:
                        for buffered in buffered_deltas:
                            yield TutorTextDelta(buffered)
                    buffered_deltas.clear()
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
                    parent_decision=parent_decision,
                    parent_resolution=parent_resolution,
                    capacity_lineage=capacity_lineage,
                )
            if context.studio_workspace is not None and context.studio_workspace.observation_id is not None:
                cancel_studio_tutor_observation(
                    bind=self._session.get_bind(),
                    student_id=learning_session.student_id,
                    observation_id=context.studio_workspace.observation_id,
                )
            raise
        except Exception as error:
            if context.studio_workspace is not None and context.studio_workspace.observation_id is not None:
                mark_studio_tutor_observation_failed(
                    bind=self._session.get_bind(),
                    student_id=learning_session.student_id,
                    observation_id=context.studio_workspace.observation_id,
                    failure_code="PROVIDER_FAILURE",
                )
            raise TutorModelStreamFailure("The primary Tutor model stream failed.") from error

        if result is None:
            if context.studio_workspace is not None and context.studio_workspace.observation_id is not None:
                mark_studio_tutor_observation_failed(
                    bind=self._session.get_bind(),
                    student_id=learning_session.student_id,
                    observation_id=context.studio_workspace.observation_id,
                    failure_code="TERMINAL_FAILURE",
                )
            raise TutorModelStreamFailure("The primary Tutor model stream ended without a final result.")
        deferred_deltas: list[str] = []
        if parent_resolution is None:
            parent_decision = parse_parent_boundary_decision(result.output.get("parent_boundary"))
            parent_resolution = self._resolve_parent_boundary(
                student_id=learning_session.student_id,
                decision=parent_decision,
            )
            if parent_resolution.action is not SafetyAction.REDIRECT_TO_PARENT:
                deferred_deltas = buffered_deltas
        try:
            turn = self._persist_completed_turn(
                learning_session=learning_session,
                student_message=student_message,
                result=result,
                context=context,
                safety=safety,
                prior_method=prior_method,
                prior_segment_state=latest_segment_state,
                parent_decision=parent_decision,
                parent_resolution=parent_resolution,
                capacity_lineage=capacity_lineage,
            )
        except Exception:
            if context.studio_workspace is not None and context.studio_workspace.observation_id is not None:
                mark_studio_tutor_observation_failed(
                    bind=self._session.get_bind(),
                    student_id=learning_session.student_id,
                    observation_id=context.studio_workspace.observation_id,
                    failure_code="TERMINAL_FAILURE",
                )
            raise
        for buffered in deferred_deltas:
            yield TutorTextDelta(buffered)
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

    def _guided_check_source(
        self,
        *,
        learning_session: LearningSession,
        content: str,
        guided_check_id: UUID | None,
        source_tutor_message_id: UUID | None,
    ) -> LearningMessage | None:
        if guided_check_id is None and source_tutor_message_id is None:
            return None
        if guided_check_id is None or source_tutor_message_id is None:
            raise ValueError("Guided learning check binding is incomplete.")
        message = self._suggested_action_source(
            learning_session=learning_session,
            source_tutor_message_id=source_tutor_message_id,
        )
        payload = message.payload if isinstance(message.payload, dict) else {}
        guided_check = persisted_guided_learning_check(payload.get("guided_check"))
        if guided_check is None or guided_check.id != guided_check_id:
            raise ValueError("Guided learning check source is unavailable for this learning session.")
        latest = latest_tutor_guided_check_choice(
            self._session,
            learning_session=learning_session,
            guided_check_id=guided_check_id,
            label=content,
        )
        if latest is None or latest.source_tutor_message_id != message.id:
            raise ValueError("Guided learning check source is unavailable for this learning session.")
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
        parent_decision: ParentBoundaryDecision | None = None,
        parent_resolution: ParentBoundaryResolution | None = None,
        capacity_lineage: TutorContextCapacityLineage | None = None,
    ) -> TutorTurn:
        if parent_resolution is None:
            parent_decision = parse_parent_boundary_decision(result.output.get("parent_boundary"))
            parent_resolution = self._resolve_parent_boundary(
                student_id=learning_session.student_id,
                decision=parent_decision,
            )
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
            immediate_exchange=_exchange_messages(context.immediate_exchange),
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
        parent_audit = _parent_boundary_audit_metadata(
            decision=parent_decision,
            resolution=parent_resolution,
            response_origin="model_text",
        )
        if parent_resolution.action is SafetyAction.REDIRECT_TO_PARENT:
            redirect_text, response_origin = _compose_parent_redirect(
                question=context.question,
                decision=parent_decision,
            )
            parent_audit["enforced"] = True
            parent_audit["response_origin"] = response_origin
            turn = self._persist_turn(
                learning_session,
                redirect_text,
                [],
                context,
                safety,
                None,
                None,
                candidate_metadata_status="parent_boundary_redirect",
                decision_status="parent_boundary_redirect",
                ai_execution_id=result.execution_id,
                segment_id=resolved_segment.segment.id,
                parent_boundary=parent_audit,
                capacity_lineage=capacity_lineage,
            )
            if state is not None:
                resolved_segment.segment.structured_state = state.model_dump(mode="json")
                self._session.flush()
            return turn
        teaching_decision = _validate_teaching_decision(
            mode_value=result.output.get("teaching_mode"),
            strategy_value=result.output.get("teaching_strategy"),
            method_value=result.output.get("teaching_method_id"),
            relation_value=result.output.get("prior_method_relation"),
            prior_method=prior_method,
        )
        provisional_broad_subject = _validated_provisional_broad_subject(
            result.output.get("provisional_broad_subject")
        )
        workspace_audit = self._workspace_audit(context=context, raw_intent=result.output.get("workspace_intent"))
        candidate_metadata_status, candidate_metadata_error = self._persist_candidates(
            learning_session=learning_session,
            source_message=student_message,
            result=result,
            prior_method=prior_method,
        )
        proposed_guided_check = normalize_guided_learning_check(result.output.get("guided_check"))
        guided_check = (
            PersistedGuidedLearningCheck(id=uuid4(), **proposed_guided_check.model_dump())
            if proposed_guided_check is not None
            else None
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
            provisional_broad_subject=provisional_broad_subject,
            ai_execution_id=result.execution_id,
            segment_id=resolved_segment.segment.id,
            parent_boundary=parent_audit,
            capacity_lineage=capacity_lineage,
            guided_check=guided_check,
            workspace_audit=workspace_audit,
        )
        if state is not None:
            resolved_segment.segment.structured_state = state.model_dump(mode="json")
            self._session.flush()
        return turn

    def _effective_parent_boundaries(self, *, student_id: UUID) -> dict[str, str]:
        settings = getattr(self._safety_policy, "effective_parent_boundaries", None)
        if not callable(settings):
            return {}
        value = settings(student_id=student_id)
        return value if isinstance(value, dict) else {}

    def _workspace_audit(self, *, context: TutorContext, raw_intent: object) -> dict[str, object]:
        """Keep optional Workspace routing bounded, hidden, and unable to fail Chat."""

        try:
            intent = parse_workspace_intent(raw_intent)
        except WorkspaceIntentContractError:
            return {
                "intent_status": "INVALID",
                "intent": None,
                "decision": WorkspaceExecutionDecision(
                    version="workspace-execution-decision-v1",
                    status=WorkspaceDecisionStatus.FALLBACK,
                    mode=None,
                    reason_code="INTENT_INVALID",
                    target_scene_id=None,
                    target_source_reference=None,
                ).as_audit_payload(),
            }
        if intent is None:
            return {
                "intent_status": "ABSENT",
                "intent": None,
                "decision": WorkspaceExecutionDecision(
                    version="workspace-execution-decision-v1",
                    status=WorkspaceDecisionStatus.NO_CHANGE,
                    mode=None,
                    reason_code="NO_WORKSPACE_INTENT",
                    target_scene_id=None,
                    target_source_reference=None,
                ).as_audit_payload(),
            }
        scene = context.studio_workspace.current_scene_capability if context.studio_workspace is not None else None
        decision = route_workspace_intent(
            intent,
            WorkspaceAuthorityContext(
                active_scene_id=None if scene is None else str(scene.scene_id),
                active_subject_key=None if scene is None else scene.subject_key,
                active_scene=(
                    None if scene is None else ActiveSceneCapability(
                        scene_id=str(scene.scene_id), subject_key=scene.subject_key,
                        subject_profile_version=scene.subject_profile_version, activity_key=scene.activity_key,
                        activity_version=scene.activity_version, renderer_key=scene.renderer_key,
                        renderer_version=scene.renderer_version, source_references=scene.source_references,
                    )
                ),
                authorized_source_references=context.debug.retrieval_source_refs,
                registry=production_subject_registry(),
                current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,
            ),
        )
        return {
            "intent_status": "VALID",
            "intent": intent.model_dump(mode="json"),
            "decision": decision.as_audit_payload(),
        }

    def _resolve_parent_boundary(
        self,
        *,
        student_id: UUID,
        decision: ParentBoundaryDecision | None,
    ) -> ParentBoundaryResolution:
        resolver = getattr(self._safety_policy, "resolve_parent_boundary", None)
        if callable(resolver):
            return resolver(student_id=student_id, decision=decision)
        return ParentBoundaryResolution(
            action=SafetyAction.ALLOW,
            category=None,
            policy_source="DEFAULT_OPEN",
            policy_version=1,
            reason_code="SEMANTIC_NOT_APPLICABLE",
            boundary_state=None,
        )

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
        candidates = _filter_misconception_candidates(
            metadata.candidates,
            source_message=source_message,
        )
        metadata = metadata.model_copy(update={"candidates": candidates})
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
            if candidate.event_type == "misconception_signal":
                evidence = MisconceptionEvidence.model_validate(candidate.misconception_evidence)
                payload["misconception_evidence"] = evidence.model_dump(mode="json")
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
        parent_boundary: dict[str, object] | None = None,
        capacity_lineage: TutorContextCapacityLineage | None = None,
        guided_check: PersistedGuidedLearningCheck | None = None,
        provisional_broad_subject: str | None = None,
        workspace_audit: dict[str, object] | None = None,
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
            "guided_check": guided_check.model_dump(mode="json") if guided_check is not None else None,
            "tutor_turn_schema_version": TUTOR_TURN_SCHEMA_VERSION,
            "provisional_broad_subject": provisional_broad_subject,
            "workspace": workspace_audit or {
                "intent_status": "NOT_REQUESTED",
                "intent": None,
                "decision": None,
            },
        }
        if selected_method is not None:
            payload["teaching_method_registry_version"] = TEACHING_METHOD_REGISTRY_VERSION
        if method_status != "not_selected":
            payload["teaching_method_status"] = method_status
        if candidate_metadata_error is not None:
            payload["candidate_metadata_error"] = candidate_metadata_error
        if parent_boundary is not None:
            payload["parent_boundary"] = parent_boundary
        if capacity_lineage is not None:
            payload["context_capacity"] = capacity_lineage.as_metadata()
        if context is not None:
            payload["context_debug"] = {
                "current_turn_message_id": (
                    str(context.debug.current_turn_message_id)
                    if context.debug.current_turn_message_id is not None
                    else None
                ),
                "immediate_exchange_message_ids": [str(identifier) for identifier in context.debug.immediate_exchange_message_ids],
                "older_continuity_message_ids": [
                    str(identifier) for identifier in context.debug.older_continuity_message_ids
                ],
                "recent_exchange_message_ids": [str(identifier) for identifier in context.debug.recent_exchange_message_ids],
                "semantic_recall_exchange_message_ids": [str(identifier) for identifier in context.debug.semantic_recall_exchange_message_ids],
                "session_message_ids": [str(identifier) for identifier in context.debug.session_message_ids],
                "retrieval_source_refs": list(context.debug.retrieval_source_refs),
                "intelligence_source_ids": [str(identifier) for identifier in context.debug.intelligence_source_ids],
                "personal_memory_status": context.debug.personal_memory_status,
                "studio": {
                    "included": context.studio_workspace is not None,
                    "context_schema_version": (
                        None if context.studio_workspace is None else STUDIO_TUTOR_CONTEXT_SCHEMA_VERSION
                    ),
                    "runtime_id": (
                        None if context.debug.studio_runtime_id is None else str(context.debug.studio_runtime_id)
                    ),
                    "snapshot_sequence": context.debug.studio_snapshot_sequence,
                    "observation_id": (
                        None if context.debug.studio_observation_id is None else str(context.debug.studio_observation_id)
                    ),
                    "from_sequence": context.debug.studio_from_sequence,
                    "through_sequence": context.debug.studio_through_sequence,
                    "selected_event_sequences": list(context.debug.studio_selected_event_sequences),
                },
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
        return TutorTurn(
            text,
            suggested_actions,
            sources,
            intelligence,
            mode,
            strategy,
            safety.audit_metadata(),
            guided_check,
            None if context is None or context.studio_workspace is None else context.studio_workspace.observation_id,
            ai_execution_id,
            None if context is None or context.studio_workspace is None else context.debug.current_turn_message_id,
        )


def _validated_provisional_broad_subject(value: object) -> str | None:
    """Keep the optional primary-call hint registry-bounded and non-authoritative."""

    return value if isinstance(value, str) and is_supported_broad_subject(value) else None


def _payload_from_context(
    context: TutorContext,
    *,
    safety: TutorSafetyRuntime,
    candidate_source_message_id: UUID,
    prior_method: PriorTeachingMethodContext | None = None,
    suggested_action_source: LearningMessage | None = None,
    latest_segment_state: StructuredSegmentState | None = None,
    effective_parent_boundaries: dict[str, str] | None = None,
) -> dict[str, object]:
    return build_tutor_model_payload(
        question=context.question,
        sources=[{"ref": block.source_ref, "text": block.text} for block in context.retrieval],
        intelligence=[item.text for item in context.intelligence],
        student_core_context=context.student_core_context.as_model_input(),
        personal_memory=context.personal_memory,
        safety_directive=safety.tutor_directive,
        immediate_exchange=_exchange_payload(context.immediate_exchange),
        recent_exchanges=[_exchange_payload(exchange) for exchange in context.recent_exchanges],
        semantic_recall_exchanges=[_exchange_payload(exchange) for exchange in context.semantic_recall_exchanges],
        candidate_source_message_id=candidate_source_message_id,
        prior_method=prior_method,
        suggested_action_source=suggested_action_source,
        latest_segment_state=latest_segment_state,
        effective_parent_boundaries=effective_parent_boundaries,
        studio_context=context.studio_workspace,
    )


def _format_lineage_message(message: dict[str, object]) -> str:
    """Render a raw conversational source with its exact hidden persistence identity."""

    role = str(message.get("role", "message"))
    content = str(message.get("content", ""))
    message_id = message.get("message_id")
    if isinstance(message_id, (str, UUID)):
        return f"{role} message [{message_id}]:\n{content}"
    return f"{role}: {content}"


def _exchange_messages(exchange: object) -> tuple[SessionContextMessage, ...]:
    """Normalize the CTX-03C exchange object while tolerating old test seams."""

    if exchange is None:
        return ()
    if isinstance(exchange, tuple):
        return tuple(message for message in exchange if isinstance(message, SessionContextMessage))
    values = (
        ("student_message_id", "student", "student_content"),
        ("tutor_message_id", "tutor", "tutor_content"),
    )
    return tuple(
        SessionContextMessage(getattr(exchange, identifier), role, getattr(exchange, content))
        for identifier, role, content in values
        if isinstance(getattr(exchange, identifier, None), UUID) and isinstance(getattr(exchange, content, None), str)
    )


def _exchange_payload(exchange: object) -> list[dict[str, object]]:
    return [
        {"message_id": str(message.message_id), "role": message.role, "content": message.content}
        for message in _exchange_messages(exchange)
    ]


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


def _parent_boundary_audit_metadata(
    *,
    decision: ParentBoundaryDecision | None,
    resolution: ParentBoundaryResolution,
    response_origin: str,
) -> dict[str, object]:
    """Keep semantic-vs-server decisions visible without storing hidden model text."""

    return {
        "semantic_category": decision.category.value if decision and decision.category else None,
        "applies": decision.applies if decision is not None else False,
        "model_action": decision.model_action.value if decision is not None else ParentBoundaryModelAction.ALLOW.value,
        "effective_action": resolution.action.value,
        "boundary_source": resolution.policy_source,
        "reason_code": resolution.reason_code,
        "policy_version": resolution.policy_version,
        "enforced": False,
        "response_origin": response_origin,
    }


def _compose_parent_redirect(
    *,
    question: str,
    decision: ParentBoundaryDecision | None,
) -> tuple[str, str]:
    """Use only bounded fragments; malformed fragments fall back without failing a turn."""

    fragments = parse_redirect_fragments(decision.redirect) if decision is not None else None
    if fragments is not None:
        pieces = [fragments.acknowledgement, fragments.parent_reference, fragments.safe_offer]
        if all(_is_plain_parent_fragment(piece) for piece in pieces):
            return " ".join(pieces), "server_composed_redirect"
    if _contains_arabic(question):
        return (
            "هذا موضوع يناسب الحديث عنه مع أحد والديك. أستطيع مساعدتك في سؤال دراسي آخر.",
            "server_fallback_redirect",
        )
    return (
        "This is a topic that is best to discuss with a parent. I can help with another learning question.",
        "server_fallback_redirect",
    )


def _is_plain_parent_fragment(value: str) -> bool:
    lowered = value.casefold()
    return (
        bool(value.strip())
        and "\n" not in value
        and "\r" not in value
        and "http://" not in lowered
        and "https://" not in lowered
        and "www." not in lowered
        and "`" not in value
        and "{" not in value
        and "}" not in value
    )


def _contains_arabic(value: str) -> bool:
    return any("\u0600" <= character <= "\u06ff" for character in value)


def _is_non_evidentiary_interaction(message: LearningMessage) -> bool:
    payload = message.payload if isinstance(message.payload, dict) else {}
    if payload.get("input_kind") in {"suggested_action", "suggested_action_navigation", "suggested_action_answer_choice"}:
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
    return payload.get("input_kind") == "guided_learning_check_answer"


def _bounded_answer_choice_metadata(metadata: CandidateEventMetadata) -> CandidateEventMetadata:
    allowed_event_types = {"learning_attempt", "guided_success", "incorrect_attempt"}
    return metadata.model_copy(
        update={"candidates": [candidate for candidate in metadata.candidates if candidate.event_type in allowed_event_types]}
    )


def _filter_misconception_candidates(
    candidates: list[CandidateEventMetadataItem],
    *,
    source_message: LearningMessage,
) -> list[CandidateEventMetadataItem]:
    """Keep only misconception Candidates grounded in the current raw Student turn."""

    validated: list[CandidateEventMetadataItem] = []
    normalized_source = _normalize_grounding_text(source_message.content)
    for candidate in candidates:
        if candidate.event_type != "misconception_signal":
            validated.append(candidate)
            continue
        try:
            evidence = MisconceptionEvidence.model_validate(candidate.misconception_evidence)
        except ValidationError:
            continue
        if evidence.source_message_id != source_message.id:
            continue
        if evidence.source_message_id not in candidate.source_message_ids:
            continue
        if _normalize_grounding_text(evidence.explicit_student_reasoning) not in normalized_source:
            continue
        validated.append(candidate.model_copy(update={"misconception_evidence": evidence}))
    return validated


def _normalize_grounding_text(value: str) -> str:
    """Apply only Unicode and whitespace normalization before exact span grounding."""

    return " ".join(unicodedata.normalize("NFKC", value).split())


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
