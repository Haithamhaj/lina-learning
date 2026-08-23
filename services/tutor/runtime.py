"""Production Tutor orchestration over the approved safety and context boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy.orm import Session

from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.config import get_settings
from services.platform.db.models import CandidateEvent, LearningMessage, LearningSession, ModelTask
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContext, TutorContextBuilder
from services.tutor.candidate_events import (
    CandidateEventContractError,
    TUTOR_OUTPUT_RESPONSE_SCHEMA,
    normalize_suggested_actions,
    parse_candidate_event_metadata,
)
from services.tutor.safety import TutorSafetyRuntime, consume_safety_decision
from services.tutor.student_sessions import append_student_message


class TeachingMode(str, Enum):
    LEARN = "LEARN"
    HOMEWORK = "HOMEWORK"
    EXPLORE = "EXPLORE"
    REVIEW = "REVIEW"
    QUIZ = "QUIZ"


class TeachingStrategy(str, Enum):
    EXPLAIN_WITH_EXAMPLE = "EXPLAIN_WITH_EXAMPLE"
    HINT_FIRST = "HINT_FIRST"
    EXPLAIN_THEN_CHECK = "EXPLAIN_THEN_CHECK"
    INDEPENDENT_CHECK = "INDEPENDENT_CHECK"


@dataclass(frozen=True)
class TutorTextDelta:
    text: str


@dataclass(frozen=True)
class TutorTurn:
    text: str
    suggested_actions: list[str]
    sources: list[dict[str, object]]
    intelligence: list[str]
    mode: TeachingMode
    strategy: TeachingStrategy
    safety: dict[str, str | int]


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
    "Speak naturally to an intelligent approximately 10-year-old: do not use baby-talk or unnecessary formal educational wording. "
    "Reply primarily in the language of the Student's current message on every turn: Arabic message means primarily Arabic, English message means primarily English. "
    "Follow an immediate Arabic/English language switch without treating it as a topic switch or creating separate learner profiles, intelligence, or learning state. "
    "Use natural Arabic/English mixing only when the Student mixes languages or useful school/math terminology benefits from it. "
    "Keep the same relevant conversational context across a language switch. Current demonstrated behavior outranks historical learning notes. "
    "Never announce learner labels or internal records. The book is curriculum grounding, not a script: use valid examples, analogies, or visual descriptions when useful. "
    "Prefer short sentences and manageable chunks. Default to one concept or one or two small steps, then invite interaction or a check instead of giving a long lecture. "
    "If the Student remains confused, change representation or support rather than repeating: use a concrete example, visual or mental representation, worked example, or guided step as useful. "
    "Use adaptive scaffolding such as worked example, guided attempt, lighter hint, and independent attempt; it is not a fixed sequence. "
    "For homework, allow a meaningful attempt and hint before giving an answer; if the Student is genuinely stuck, explain clearly, explain why, then ask one new application check. "
    "A Student saying they understand or choosing an action is not proof of understanding or mastery; normally use a small independent or application check when it matters. "
    "Praise only specific observed effort, reasoning, correction, or persistence; avoid automatic or exaggerated praise. Use zero to three emojis only when they add warmth or meaning, never on every sentence. "
    "Student-facing text must be plain text: no Markdown markers, headings, bold, or code fences. Do not use LaTeX or raw LaTeX notation. Use simple Grade-5-readable math notation and put equations on their own line when it improves Arabic/English readability. "
    "Safety policy is enforced before this call; do not mention internal policies. Return student-facing reply only in the structured text field. "
    "Return suggested_actions as zero to four short, visible choices when useful; otherwise return an empty array. Suggested actions must use the same primary language as the response and contain no URLs, Markdown, or hidden metadata. "
    "Set hidden candidate_metadata to null for greetings, thanks, generic chat, self-reported understanding, button selection, or when no meaningful observable learning signal occurred. "
    "Emit Candidate Event metadata only for a specific, source-linked observable learning signal such as solving, explaining, applying, self-correcting, or transferring an idea. "
    "Never treat a chosen Tutor strategy as an outcome without an observable Student result. Never mention hidden metadata in text."
)


def infer_tutor_mode(question: str) -> TeachingMode:
    normalized = question.lower()
    if any(term in normalized for term in ("homework", "worksheet", "assignment", "واجبي", "الواجب")):
        return TeachingMode.HOMEWORK
    if any(term in normalized for term in ("quiz", "test me", "اختبرني")):
        return TeachingMode.QUIZ
    if any(term in normalized for term in ("review", "revise", "again", "راجع", "مراجعة")):
        return TeachingMode.REVIEW
    if any(
        term in normalized
        for term in (
            "outside our school topic",
            "outside the school topic",
            "outside the lesson",
            "not part of our lesson",
            "outside class",
            "خارج موضوع الدرس",
            "خارج المنهج",
            "خارج الدرس",
        )
    ):
        return TeachingMode.EXPLORE
    return TeachingMode.LEARN


def select_teaching_strategy(question: str, *, mode: TeachingMode | None = None) -> TeachingStrategy:
    normalized = question.lower()
    if any(term in normalized for term in (
        "stuck", "don't understand", "i don't understand", "still confused", "still not clear", "too hard",
        "لا أفهم", "ما فهمت", "مش فاهمة", "مش واضحة", "لسه مش واضحة", "عالق",
    )):
        return TeachingStrategy.EXPLAIN_THEN_CHECK
    if any(term in normalized for term in (
        "i solved", "i got it", "i understand", "got it", "my answer is", "حللت", "أعتقد أنني",
        "فهمت", "فهمت الآن", "تمام فهمت",
    )):
        return TeachingStrategy.INDEPENDENT_CHECK
    if mode is TeachingMode.HOMEWORK:
        return TeachingStrategy.HINT_FIRST
    return TeachingStrategy.EXPLAIN_WITH_EXAMPLE


def build_tutor_model_payload(
    *,
    question: str,
    sources: list[dict[str, object]] | None = None,
    intelligence: list[str] | None = None,
    safety_directive: str | None = None,
    mode: TeachingMode = TeachingMode.LEARN,
    strategy: TeachingStrategy = TeachingStrategy.EXPLAIN_WITH_EXAMPLE,
    session_messages: list[dict[str, str]] | None = None,
    candidate_source_message_id: UUID | None = None,
) -> dict[str, object]:
    """Build bounded model input from the project-owned Tutor context only."""

    source_context = "\n\n".join(
        f"Curriculum source ({source['ref']}):\n{source['text']}" for source in (sources or [])
    ) or "No matching curriculum excerpt was retrieved."
    intelligence_context = "\n".join(intelligence or []) or "No relevant compact learning note was selected."
    session_context = "\n".join(
        f"{message['role']}: {message['content']}" for message in (session_messages or [])
    ) or "No prior session messages were selected."
    safety_context = f"\n\nAge-handling directive:\n{safety_directive}" if safety_directive else ""
    candidate_context = (
        "\n\nHidden Candidate Event source link:\n"
        f"If metadata is meaningful, use only this raw Student message ID: {candidate_source_message_id}."
        if candidate_source_message_id is not None
        else ""
    )
    return {
        "instructions": TUTOR_SHARED_INSTRUCTIONS,
        "input": (
            f"Teaching mode: {mode.value}\nTeaching strategy: {strategy.value}\n\n"
            f"Student question:\n{question}\n\nSmall recent session window:\n{session_context}\n\n"
            f"Retrieved curriculum:\n{source_context}\n\nRelevant compact learning context:\n{intelligence_context}{safety_context}{candidate_context}"
        ),
        "max_output_tokens": 800,
        "question": question,
        "sources": sources or [],
        "intelligence": intelligence or [],
        "mode": mode.value,
        "strategy": strategy.value,
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
        is_suggested_action: bool = False,
    ) -> Iterator[TutorTextDelta | TutorTurn]:
        content = question.strip()
        if not content:
            raise ValueError("A current Student question is required.")
        learning_session.last_activity_at = datetime.now(UTC)
        student_message = append_student_message(
            self._session,
            learning_session=learning_session,
            content=content,
            interaction_payload={"input_kind": "suggested_action"} if is_suggested_action else None,
        )
        decision = self._safety_policy.evaluate(student_id=learning_session.student_id, text=content, interaction_ref=str(learning_session.id))
        safety = consume_safety_decision(decision)
        mode = infer_tutor_mode(content)
        strategy = select_teaching_strategy(content, mode=mode)
        if not safety.continue_to_tutor:
            yield self._persist_turn(
                learning_session,
                safety.redirect_directive or "Please ask a trusted grown-up for help with this topic.",
                [],
                None,
                safety,
                mode,
                strategy,
                candidate_metadata_status="not_requested",
            )
            return

        context = self._context_builder.build(learning_session=learning_session, question=content)
        payload = _payload_from_context(
            context,
            mode=mode,
            strategy=strategy,
            safety=safety,
            candidate_source_message_id=student_message.id,
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
                    mode=mode,
                    strategy=strategy,
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
            mode=mode,
            strategy=strategy,
        )
        yield turn

    def _persist_completed_turn(
        self,
        *,
        learning_session: LearningSession,
        student_message: LearningMessage,
        result: ModelResult,
        context: TutorContext,
        safety: TutorSafetyRuntime,
        mode: TeachingMode,
        strategy: TeachingStrategy,
    ) -> TutorTurn:
        candidate_metadata_status, candidate_metadata_error = self._persist_candidates(
            learning_session=learning_session,
            source_message=student_message,
            result=result,
        )
        return self._persist_turn(
            learning_session,
            str(result.output.get("text")),
            normalize_suggested_actions(result.output.get("suggested_actions")),
            context,
            safety,
            mode,
            strategy,
            candidate_metadata_status=candidate_metadata_status,
            candidate_metadata_error=candidate_metadata_error,
            ai_execution_id=result.execution_id,
        )

    def _persist_candidates(
        self,
        *,
        learning_session: LearningSession,
        source_message: LearningMessage,
        result: ModelResult | None,
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
        if not metadata.candidates:
            return "absent", None
        route = self._gateway.route_for(ModelTask.TUTOR)
        for candidate in metadata.candidates:
            self._session.add(
                CandidateEvent(
                    session_id=learning_session.id,
                    message_id=source_message.id,
                    event_type=candidate.event_type,
                    concept_ref=candidate.concept_ref,
                    signal=candidate.signal,
                    payload={
                        "candidate_schema_version": metadata.version,
                        "summary": candidate.summary,
                        "school_or_extended": candidate.school_or_extended,
                        "source_message_ids": [str(identifier) for identifier in candidate.source_message_ids],
                        "subject": learning_session.subject,
                        "observed_student_outcome": candidate.observed_student_outcome,
                        "model_route": {"provider": route.provider, "model": route.model},
                    },
                    ai_execution_id=result.execution_id,
                )
            )
        self._session.flush()
        return "persisted", None

    def _persist_turn(
        self,
        learning_session: LearningSession,
        text: str,
        suggested_actions: list[str],
        context: TutorContext | None,
        safety: TutorSafetyRuntime,
        mode: TeachingMode,
        strategy: TeachingStrategy,
        *,
        candidate_metadata_status: str,
        candidate_metadata_error: str | None = None,
        ai_execution_id: UUID | None = None,
    ) -> TutorTurn:
        sources = _source_metadata(context)
        intelligence = [item.text for item in context.intelligence] if context else []
        payload: dict[str, object] = {"source_refs": [source["source_ref"] for source in sources], "intelligence_used": intelligence, "safety": safety.audit_metadata(), "mode": mode.value, "strategy": strategy.value, "candidate_metadata_status": candidate_metadata_status, "suggested_actions": suggested_actions}
        if candidate_metadata_error is not None:
            payload["candidate_metadata_error"] = candidate_metadata_error
        if context is not None:
            payload["context_debug"] = {"session_message_ids": [str(identifier) for identifier in context.debug.session_message_ids], "retrieval_source_refs": list(context.debug.retrieval_source_refs), "intelligence_source_ids": [str(identifier) for identifier in context.debug.intelligence_source_ids]}
        self._session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content=text,
                payload=payload,
                ai_execution_id=ai_execution_id,
                created_at=datetime.now(UTC),
            )
        )
        learning_session.last_activity_at = datetime.now(UTC)
        self._session.flush()
        return TutorTurn(text, suggested_actions, sources, intelligence, mode, strategy, safety.audit_metadata())


def _payload_from_context(
    context: TutorContext,
    *,
    mode: TeachingMode,
    strategy: TeachingStrategy,
    safety: TutorSafetyRuntime,
    candidate_source_message_id: UUID,
) -> dict[str, object]:
    return build_tutor_model_payload(question=context.question, sources=[{"ref": block.source_ref, "text": block.text} for block in context.retrieval], intelligence=[item.text for item in context.intelligence], safety_directive=safety.tutor_directive, mode=mode, strategy=strategy, session_messages=[{"role": message.role, "content": message.content} for message in context.session_messages], candidate_source_message_id=candidate_source_message_id)


def _source_metadata(context: TutorContext | None) -> list[dict[str, object]]:
    return [] if context is None else [{"source_ref": block.source_ref, "page_number": block.page_number, "block_type": block.block_type} for block in context.retrieval]


def _is_non_evidentiary_interaction(message: LearningMessage) -> bool:
    payload = message.payload if isinstance(message.payload, dict) else {}
    if payload.get("input_kind") == "suggested_action":
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
