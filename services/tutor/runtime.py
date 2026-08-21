"""Production Tutor orchestration over the approved safety and context boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy.orm import Session

from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.config import get_settings
from services.platform.db.models import LearningMessage, LearningSession, ModelTask
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContext, TutorContextBuilder
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
    sources: list[dict[str, object]]
    intelligence: list[str]
    mode: TeachingMode
    strategy: TeachingStrategy
    safety: dict[str, str | int]


class LocalTutorProvider:
    """Deterministic test/development adapter; configured providers stream remotely."""

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        return ModelResult(
            output={"text": f"Let’s work on this step by step. {payload['question']}"},
            input_tokens=20,
            output_tokens=18,
            estimated_cost_usd=0.0,
        )

    def stream(self, route: ModelRoute, payload: dict[str, object]) -> Iterator[StreamDelta | StreamComplete]:
        result = self.execute(route, payload)
        yield StreamDelta(str(result.output["text"]))
        yield StreamComplete(result)


TUTOR_SHARED_INSTRUCTIONS = (
    "You are Lina's fixed Grade 5 Math tutor: warm, clear, patient, non-shaming, and focused on understanding. "
    "Reply primarily in the language of the Student's current message; use natural Arabic/English mixing only when "
    "the message mixes them, while retaining useful school and math terms. Current demonstrated behavior outranks "
    "historical learning notes. Never announce learner labels or internal records. The book is curriculum grounding, "
    "not a script: use valid examples, analogies, or visual descriptions when useful. For homework, allow a meaningful "
    "attempt and hint before giving an answer; if the Student is genuinely stuck, explain clearly, explain why, then ask "
    "one new application check. Do not withhold answers endlessly. Safety policy is enforced before this call; do not mention internal policies."
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
    if any(term in normalized for term in ("i solved", "i got it", "my answer is", "حللت", "أعتقد أنني")):
        return TeachingStrategy.INDEPENDENT_CHECK
    if any(term in normalized for term in ("stuck", "don't understand", "too hard", "لا أفهم", "عالق")):
        return TeachingStrategy.EXPLAIN_THEN_CHECK
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
    return {
        "instructions": TUTOR_SHARED_INSTRUCTIONS,
        "input": (
            f"Teaching mode: {mode.value}\nTeaching strategy: {strategy.value}\n\n"
            f"Student question:\n{question}\n\nSmall recent session window:\n{session_context}\n\n"
            f"Retrieved curriculum:\n{source_context}\n\nRelevant compact learning context:\n{intelligence_context}{safety_context}"
        ),
        "max_output_tokens": 350,
        "question": question,
        "sources": sources or [],
        "intelligence": intelligence or [],
        "mode": mode.value,
        "strategy": strategy.value,
    }


class TutorRuntime:
    """One-call Tutor runtime; safety, context, and gateway remain explicit boundaries."""

    def __init__(self, session: Session, *, context_builder: TutorContextBuilder, safety_policy: SafetyPolicyService, gateway: ModelGateway) -> None:
        self._session = session
        self._context_builder = context_builder
        self._safety_policy = safety_policy
        self._gateway = gateway

    def stream_turn(self, *, learning_session: LearningSession, question: str) -> Iterator[TutorTextDelta | TutorTurn]:
        content = question.strip()
        if not content:
            raise ValueError("A current Student question is required.")
        learning_session.last_activity_at = datetime.now(UTC)
        append_student_message(self._session, learning_session=learning_session, content=content)
        decision = self._safety_policy.evaluate(student_id=learning_session.student_id, text=content, interaction_ref=str(learning_session.id))
        safety = consume_safety_decision(decision)
        mode = infer_tutor_mode(content)
        strategy = select_teaching_strategy(content, mode=mode)
        if not safety.continue_to_tutor:
            yield self._persist_turn(learning_session.id, safety.redirect_directive or "Please ask a trusted grown-up for help with this topic.", None, safety, mode, strategy)
            return

        context = self._context_builder.build(learning_session=learning_session, question=content)
        payload = _payload_from_context(context, mode=mode, strategy=strategy, safety=safety)
        model_stream = self._gateway.stream(ModelTask.TUTOR, payload)
        text_parts: list[str] = []
        result: ModelResult | None = None
        completed = False
        try:
            for event in model_stream:
                if isinstance(event, StreamDelta):
                    text_parts.append(event.text)
                    yield TutorTextDelta(event.text)
                else:
                    result = event.result
                    completed = True
                    break
        finally:
            if not completed:
                for event in model_stream:
                    if isinstance(event, StreamDelta):
                        text_parts.append(event.text)
                    else:
                        result = event.result
                        completed = True
                        break
            final_text = str(result.output.get("text")) if result is not None else "".join(text_parts)
            if not final_text:
                final_text = "Let’s pause here and try the next step together."
            turn = self._persist_turn(learning_session.id, final_text, context, safety, mode, strategy)
        yield turn

    def _persist_turn(self, session_id: UUID, text: str, context: TutorContext | None, safety: TutorSafetyRuntime, mode: TeachingMode, strategy: TeachingStrategy) -> TutorTurn:
        sources = _source_metadata(context)
        intelligence = [item.text for item in context.intelligence] if context else []
        payload: dict[str, object] = {"source_refs": [source["source_ref"] for source in sources], "intelligence_used": intelligence, "safety": safety.audit_metadata(), "mode": mode.value, "strategy": strategy.value}
        if context is not None:
            payload["context_debug"] = {"session_message_ids": [str(identifier) for identifier in context.debug.session_message_ids], "retrieval_source_refs": list(context.debug.retrieval_source_refs), "intelligence_source_ids": [str(identifier) for identifier in context.debug.intelligence_source_ids]}
        self._session.add(
            LearningMessage(
                session_id=session_id,
                role="tutor",
                content=text,
                payload=payload,
                created_at=datetime.now(UTC),
            )
        )
        self._session.flush()
        return TutorTurn(text, sources, intelligence, mode, strategy, safety.audit_metadata())


def _payload_from_context(context: TutorContext, *, mode: TeachingMode, strategy: TeachingStrategy, safety: TutorSafetyRuntime) -> dict[str, object]:
    return build_tutor_model_payload(question=context.question, sources=[{"ref": block.source_ref, "text": block.text} for block in context.retrieval], intelligence=[item.text for item in context.intelligence], safety_directive=safety.tutor_directive, mode=mode, strategy=strategy, session_messages=[{"role": message.role, "content": message.content} for message in context.session_messages])


def _source_metadata(context: TutorContext | None) -> list[dict[str, object]]:
    return [] if context is None else [{"source_ref": block.source_ref, "page_number": block.page_number, "block_type": block.block_type} for block in context.retrieval]


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
