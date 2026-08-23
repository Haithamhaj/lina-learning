"""Authenticated Student-owned Math session endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.platform.auth import AuthenticatedPrincipal, UserRole, require_role
from services.platform.db.models import LearningMessage, LearningSession
from services.platform.db.session import get_session
from services.tutor.candidate_events import normalize_suggested_actions
from services.tutor.student_sessions import (
    append_student_message,
    open_or_resume_math_session,
    ordered_messages,
    owned_open_math_session,
    student_for_authenticated_subject,
)
from services.tutor.runtime import TutorModelStreamFailure, TutorTextDelta, TutorTurn, create_tutor_runtime


router = APIRouter(prefix="/api/v1/student", tags=["student"])


class StudentMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    suggested_action: bool = False


class StudentMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    suggested_actions: list[str] = Field(default_factory=list)

    @classmethod
    def from_model(cls, message: LearningMessage) -> "StudentMessageResponse":
        payload = message.payload if isinstance(message.payload, dict) else {}
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            suggested_actions=normalize_suggested_actions(payload.get("suggested_actions")) if message.role == "tutor" else [],
        )


class StudentSessionResponse(BaseModel):
    id: UUID
    subject: str
    status: str
    opened_at: datetime
    last_activity_at: datetime
    messages: list[StudentMessageResponse]


def _response(session: Session, learning_session: LearningSession) -> StudentSessionResponse:
    return StudentSessionResponse(
        id=learning_session.id,
        subject=learning_session.subject,
        status=learning_session.status,
        opened_at=learning_session.opened_at,
        last_activity_at=learning_session.last_activity_at,
        messages=[StudentMessageResponse.from_model(message) for message in ordered_messages(session, learning_session=learning_session)],
    )


def _student_for_principal(
    session: Session,
    principal: AuthenticatedPrincipal,
):
    try:
        return student_for_authenticated_subject(
            session,
            identity_provider="clerk",
            subject=principal.subject,
            email=principal.email,
        )
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student profile is unavailable.") from None


@router.post("/math/session", response_model=StudentSessionResponse)
def start_or_resume_math_session(
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> StudentSessionResponse:
    student = _student_for_principal(session, principal)
    return _response(session, open_or_resume_math_session(session, student_id=student.id))


@router.get("/math/session/{session_id}", response_model=StudentSessionResponse)
def get_math_session(
    session_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> StudentSessionResponse:
    student = _student_for_principal(session, principal)
    learning_session = owned_open_math_session(session, student_id=student.id, session_id=session_id)
    if learning_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open Math session not found.")
    return _response(session, learning_session)


@router.post("/math/session/{session_id}/messages", response_model=StudentMessageResponse)
def post_math_message(
    session_id: UUID,
    request: StudentMessageRequest,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> StudentMessageResponse:
    student = _student_for_principal(session, principal)
    learning_session = owned_open_math_session(
        session, student_id=student.id, session_id=session_id, lock=True
    )
    if learning_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open Math session not found.")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message content is required.")
    return StudentMessageResponse.from_model(
        append_student_message(session, learning_session=learning_session, content=content)
    )


@router.post("/math/session/{session_id}/turn/stream")
def stream_math_tutor_turn(
    session_id: UUID,
    request: StudentMessageRequest,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Forward provider-produced Tutor deltas over the authenticated Student SSE path."""

    student = _student_for_principal(session, principal)
    learning_session = owned_open_math_session(session, student_id=student.id, session_id=session_id)
    if learning_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open Math session not found.")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message content is required.")
    bind = session.get_bind()
    student_id = student.id

    def events() -> Iterator[str]:
        stream_session = Session(bind)
        turn_stream: Iterator[TutorTextDelta | TutorTurn] | None = None
        try:
            owned_session = owned_open_math_session(
                stream_session, student_id=student_id, session_id=session_id, lock=True
            )
            if owned_session is None:
                return
            runtime = create_tutor_runtime(stream_session)
            turn_stream = runtime.stream_turn(
                learning_session=owned_session,
                question=content,
                is_suggested_action=request.suggested_action,
            )
            for event in turn_stream:
                if isinstance(event, TutorTextDelta):
                    yield f"event: delta\ndata: {json.dumps({'text': event.text})}\n\n"
                elif isinstance(event, TutorTurn):
                    yield f"event: turn\ndata: {json.dumps({'text': event.text, 'suggested_actions': event.suggested_actions})}\n\n"
            stream_session.commit()
        except GeneratorExit:
            if turn_stream is not None:
                turn_stream.close()
            stream_session.commit()
            raise
        except TutorModelStreamFailure:
            stream_session.commit()
            raise
        except Exception:
            stream_session.rollback()
            raise
        finally:
            stream_session.close()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
