"""One-call deterministic local Tutor runtime for the authorized sandbox demo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from services.intelligence.core import select_relevant_intelligence
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.models import CandidateEvent, LearningMessage, LearningSession, ModelTask
from services.platform.safety import SafetyAction, SafetyPolicyService
from services.retrieval.service import RetrievalService


class DemoTutorProvider:
    """Local deterministic adapter used only when MODEL_PROVIDER=mock."""

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        question = str(payload["question"])
        sources = payload.get("sources", [])
        intelligence = payload.get("intelligence", [])
        excerpt = str(sources[0]["text"])[:360] if sources else "Let’s work from the idea step by step."
        memory = " I remember a helpful recent learning note, so I’ll keep the next step small." if intelligence else ""
        text = f"Let’s try it together. {excerpt} Your question was: {question}.{memory} What happens to the decimal point when we multiply by 10?"
        return ModelResult(output={"text": text}, input_tokens=50, output_tokens=70, estimated_cost_usd=0.0)


@dataclass(frozen=True)
class TutorTurn:
    text: str
    sources: list[dict[str, object]]
    candidate_event_id: UUID | None
    intelligence: list[str]


def start_session(session: Session, *, student_id: UUID) -> LearningSession:
    learning_session = LearningSession(student_id=student_id, subject="MATH")
    session.add(learning_session); session.flush()
    return learning_session


def tutor_turn(session: Session, *, learning_session: LearningSession, question: str) -> TutorTurn:
    """Persist raw messages, apply safety, retrieve context, then make one Tutor call."""

    learning_session.last_activity_at = datetime.now(UTC)
    student_message = LearningMessage(session_id=learning_session.id, role="student", content=question)
    session.add(student_message); session.flush()
    decision = SafetyPolicyService(session).evaluate(student_id=learning_session.student_id, text=question, interaction_ref=str(learning_session.id))
    if decision.action is not SafetyAction.ALLOW:
        text = "I can’t help with that topic here. Please ask your parent or another trusted grown-up so you can get the right support."
        session.add(LearningMessage(session_id=learning_session.id, role="tutor", content=text, payload={"safety": decision.reason_code}))
        return TutorTurn(text=text, sources=[], candidate_event_id=None, intelligence=[])
    sources = RetrievalService(session).retrieve(student_id=learning_session.student_id, question=question)
    intelligence = select_relevant_intelligence(session, student_id=learning_session.student_id, subject="MATH", question=question)
    provider = DemoTutorProvider()
    gateway = ModelGateway(session, routes={ModelTask.TUTOR: ModelRoute("local-demo", "deterministic-tutor-v1")}, providers={"local-demo": provider})
    result = gateway.execute(ModelTask.TUTOR, {"question": question, "sources": [{"text": source.text, "ref": source.source_ref} for source in sources], "intelligence": intelligence})
    text = str(result.output["text"])
    session.add(LearningMessage(session_id=learning_session.id, role="tutor", content=text, payload={"source_refs": [source.source_ref for source in sources], "intelligence_used": intelligence}))
    candidate = None
    if any(character.isdigit() for character in question):
        signal = "independent_success" if "34.52" in question else "needs_hint"
        candidate = CandidateEvent(session_id=learning_session.id, message_id=student_message.id, event_type="learning_attempt", concept_ref="place_value_multiply_by_10", signal=signal, payload={"source": "tutor-turn-v1"})
        session.add(candidate); session.flush()
    return TutorTurn(text=text, sources=[{"source_ref": source.source_ref, "page_number": source.page_number, "block_type": source.block_type} for source in sources], candidate_event_id=candidate.id if candidate else None, intelligence=intelligence)
