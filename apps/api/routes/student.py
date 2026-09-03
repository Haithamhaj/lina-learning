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
from services.platform.student_identity import resolve_student_for_authenticated_identity
from services.tutor.candidate_events import (
    PersistedGuidedLearningCheck,
    SuggestedAction,
    normalize_suggested_actions,
    persisted_guided_learning_check,
)
from services.tutor.student_sessions import (
    append_student_message,
    latest_tutor_guided_check_choice,
    latest_tutor_suggested_action,
    open_or_resume_math_session,
    ordered_messages,
    owned_open_math_session,
)
from services.tutor.runtime import TutorModelStreamFailure, TutorTextDelta, TutorTurn, create_tutor_runtime
from services.tutor.capacity import TutorContextCapacityExceeded


router = APIRouter(prefix="/api/v1/student", tags=["student"])


class StudentMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    suggested_action: bool = False
    guided_check_id: UUID | None = None


class StudentMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    guided_check: PersistedGuidedLearningCheck | None = None

    @classmethod
    def from_model(cls, message: LearningMessage) -> "StudentMessageResponse":
        payload = message.payload if isinstance(message.payload, dict) else {}
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            suggested_actions=normalize_suggested_actions(payload.get("suggested_actions")) if message.role == "tutor" else [],
            guided_check=persisted_guided_learning_check(payload.get("guided_check")) if message.role == "tutor" else None,
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
        return resolve_student_for_authenticated_identity(
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
    selected_action = None
    selected_guided_check = None
    if request.guided_check_id is not None:
        if request.suggested_action:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A guided check choice cannot also be a generic suggested action.",
            )
        selected_guided_check = latest_tutor_guided_check_choice(
            session,
            learning_session=learning_session,
            guided_check_id=request.guided_check_id,
            label=content,
        )
        if selected_guided_check is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Guided check choice is no longer available.")
    elif request.suggested_action:
        selected_action = latest_tutor_suggested_action(
            session,
            learning_session=learning_session,
            label=content,
        )
        if selected_action is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Suggested action is no longer available.")
    student_id = student.id
    selected_action_kind = selected_action.action.kind.value if selected_action is not None else None
    selected_action_source_tutor_message_id = (
        selected_action.source_tutor_message_id if selected_action is not None else None
    )
    guided_check_id = selected_guided_check.guided_check.id if selected_guided_check is not None else None
    guided_check_source_tutor_message_id = (
        selected_guided_check.source_tutor_message_id if selected_guided_check is not None else None
    )
    bind = session.get_bind()
    # The generator owns a separate transaction. Finish all authenticated
    # request-side work before it persists SafetyAudit rows for this Student.
    session.commit()

    def events() -> Iterator[str]:
        stream_session = Session(bind)
        turn_stream: Iterator[TutorTextDelta | TutorTurn] | None = None
        final_turn: TutorTurn | None = None
        committed = False
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
                suggested_action_kind=selected_action_kind,
                suggested_action_source_tutor_message_id=selected_action_source_tutor_message_id,
                guided_check_id=guided_check_id,
                guided_check_source_tutor_message_id=guided_check_source_tutor_message_id,
            )
            for event in turn_stream:
                if isinstance(event, TutorTextDelta):
                    yield f"event: delta\ndata: {json.dumps({'text': event.text})}\n\n"
                elif isinstance(event, TutorTurn):
                    final_turn = event
            stream_session.commit()
            committed = True
            if final_turn is not None:
                yield f"event: turn\ndata: {json.dumps({'text': final_turn.text, 'suggested_actions': [action.model_dump() for action in final_turn.suggested_actions], 'guided_check': final_turn.guided_check.model_dump(mode='json') if final_turn.guided_check is not None else None})}\n\n"
        except GeneratorExit:
            if turn_stream is not None:
                turn_stream.close()
            if not committed:
                stream_session.commit()
            raise
        except (TutorModelStreamFailure, TutorContextCapacityExceeded):
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
