"""Development-only sandbox path for manually exercising the Phase 1–3 loop."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.core import close_and_consolidate, consolidate_student_history
from services.platform.config import get_settings
from services.platform.db.models import (
    CandidateEvent, ContentDocument, CurrentLearningState, DecisionView,
    LearnerIntelligenceCard, LearnerPattern, LearningEvidence, LearningEvent,
    LearningMessage, LearningSession, Student, User,
)
from services.platform.db.session import get_session
from services.tutor.runtime import start_session, tutor_turn

router = APIRouter(prefix="/api/v1/demo", tags=["development-demo"])
SANDBOX_SUBJECT = "sandbox-eureka-grade5"


class TurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def _require_development() -> None:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=404, detail="Not found.")


def _sandbox_student(session: Session) -> Student:
    _require_development()
    user = session.execute(select(User).where(User.identity_provider == "development-demo", User.external_subject == SANDBOX_SUBJECT)).scalar_one_or_none()
    if user is None:
        user = User(identity_provider="development-demo", external_subject=SANDBOX_SUBJECT, display_name="Sandbox Test Learner")
        session.add(user); session.flush()
        student = Student(user_id=user.id, display_name="Sandbox Test Learner")
        session.add(student); session.flush()
        return student
    return session.execute(select(Student).where(Student.user_id == user.id)).scalar_one()


@router.post("/bootstrap")
def bootstrap(session: Session = Depends(get_session)) -> dict[str, str]:
    student = _sandbox_student(session)
    return {"student_id": str(student.id), "display_name": student.display_name or "Sandbox Test Learner"}


@router.post("/sessions")
def create_session(session: Session = Depends(get_session)) -> dict[str, str]:
    learning_session = start_session(session, student_id=_sandbox_student(session).id)
    return {"session_id": str(learning_session.id), "status": learning_session.status}


def _perform_turn(session: Session, session_id: UUID, request: TurnRequest) -> dict[str, object]:
    _require_development()
    learning_session = session.get(LearningSession, session_id)
    student = _sandbox_student(session)
    if learning_session is None or learning_session.student_id != student.id or learning_session.status != "OPEN":
        raise HTTPException(status_code=404, detail="Open sandbox session not found.")
    turn = tutor_turn(session, learning_session=learning_session, question=request.text)
    return {"text": turn.text, "sources": turn.sources, "intelligence_used": turn.intelligence}


@router.post("/sessions/{session_id}/turn")
def create_turn(session_id: UUID, request: TurnRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    return _perform_turn(session, session_id, request)


@router.post("/sessions/{session_id}/close")
def close_session(session_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    _require_development()
    learning_session = session.get(LearningSession, session_id)
    student = _sandbox_student(session)
    if learning_session is None or learning_session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Sandbox session not found.")
    run = close_and_consolidate(session, learning_session=learning_session)
    return {"session_id": str(learning_session.id), "processing_run_id": str(run.id), "status": "CLOSED"}


@router.post("/reprocess")
def reprocess(session: Session = Depends(get_session)) -> dict[str, str]:
    student = _sandbox_student(session)
    run = consolidate_student_history(session, student_id=student.id)
    return {"processing_run_id": str(run.id), "status": run.status}


@router.get("/inspector")
def inspector(session: Session = Depends(get_session)) -> dict[str, object]:
    student = _sandbox_student(session)
    def serialize(rows: list[object]) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for row in rows:
            entry: dict[str, object] = {}
            for column in row.__table__.columns:
                attribute = "payload" if column.name == "metadata" and hasattr(row, "payload") else column.name
                value = getattr(row, attribute)
                entry[column.name] = str(value) if isinstance(value, UUID) else value
            output.append(entry)
        return output
    documents = session.execute(select(ContentDocument).where(ContentDocument.student_id == student.id)).scalars().all()
    sessions = session.execute(select(LearningSession).where(LearningSession.student_id == student.id)).scalars().all()
    session_ids = [value.id for value in sessions]
    events = session.execute(select(LearningEvent).where(LearningEvent.session_id.in_(session_ids))).scalars().all() if session_ids else []
    return {
        "student": {"id": str(student.id), "name": student.display_name},
        "documents": serialize(documents), "sessions": serialize(sessions),
        "messages": serialize(session.execute(select(LearningMessage).where(LearningMessage.session_id.in_(session_ids))).scalars().all()) if session_ids else [],
        "candidate_events": serialize(session.execute(select(CandidateEvent).where(CandidateEvent.session_id.in_(session_ids))).scalars().all()) if session_ids else [],
        "events": serialize(events),
        "evidence": serialize(session.execute(select(LearningEvidence).join(LearningEvent).where(LearningEvent.session_id.in_(session_ids))).scalars().all()) if session_ids else [],
        "current_state": serialize(session.execute(select(CurrentLearningState).where(CurrentLearningState.student_id == student.id)).scalars().all()),
        "patterns": serialize(session.execute(select(LearnerPattern).where(LearnerPattern.student_id == student.id)).scalars().all()),
        "cards": serialize(session.execute(select(LearnerIntelligenceCard).where(LearnerIntelligenceCard.student_id == student.id)).scalars().all()),
        "decision_views": serialize(session.execute(select(DecisionView).where(DecisionView.student_id == student.id)).scalars().all()),
    }
