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
from apps.api.routes.studio import get_studio_subject_registry
from services.platform.db.models import LearningMessage, LearningSession
from services.platform.db.session import get_session
from services.platform.student_identity import resolve_student_for_authenticated_identity
from services.studio.tutor_context import acknowledge_studio_tutor_observation
from services.studio.interactions import (
    StudioInteractionAccessDenied,
    StudioInteractionSourceError,
    StudioInteractionStateError,
    StudioInteractionTutorService,
)
from services.studio.protocol import StudioProtocolService, StudioResourceNotFound
from services.studio.subjects.registry import SubjectCapabilityRegistry
from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import StreamComplete, StreamDelta, StreamParentBoundaryDecision
from services.platform.safety import SafetyAction
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
from services.tutor.parent_boundaries import parse_parent_boundary_decision
from services.tutor.capacity import TutorContextCapacityExceeded


router = APIRouter(prefix="/api/v1/student", tags=["student"])


def create_studio_interaction_tutor_gateway(session: Session):
    """Small test seam for the existing provider-neutral Tutor gateway."""

    return create_tutor_gateway(session)


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
                before_model_stream=stream_session.commit,
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
                if final_turn.studio_observation_id is not None:
                    acknowledge_studio_tutor_observation(
                        bind=bind,
                        student_id=student_id,
                        observation_id=final_turn.studio_observation_id,
                        ai_execution_id=final_turn.studio_ai_execution_id,
                        source_message_id=final_turn.studio_source_message_id,
                    )
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


@router.post("/studio/{runtime_id}/interactions/{interaction_id}/turn/stream")
def stream_canvas_interaction_tutor_turn(
    runtime_id: UUID,
    interaction_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    subject_registry: SubjectCapabilityRegistry = Depends(get_studio_subject_registry),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """Stream one already-contract-created Canvas interaction for its owner only."""

    student = _student_for_principal(session, principal)
    student_id = student.id
    bind = session.get_bind()
    service = StudioInteractionTutorService(
        bind=bind,
        gateway_factory=create_studio_interaction_tutor_gateway,
        subject_registry=subject_registry,
    )
    try:
        runtime = StudioProtocolService(session).runtime(student_id=student_id, runtime_id=runtime_id)
        admission = service.admit(
            student_id=student_id,
            learning_session_id=runtime.learning_session_id,
            runtime_id=runtime.id,
            interaction_id=interaction_id,
        )
        session.commit()
    except StudioResourceNotFound:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio interaction was not found.") from None
    except StudioInteractionAccessDenied:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio interaction was not found.") from None
    except StudioInteractionStateError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
    except StudioInteractionSourceError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None

    def events() -> Iterator[str]:
        buffered: list[str] = []
        parent_resolution = None
        terminal = None
        turn = None
        try:
            for event in service.stream_admitted(admission=admission, student_id=student_id):
                if isinstance(event, StreamDelta):
                    if parent_resolution is None:
                        buffered.append(event.text)
                    elif parent_resolution.action is not SafetyAction.REDIRECT_TO_PARENT:
                        yield f"event: delta\ndata: {json.dumps({'text': event.text})}\n\n"
                elif isinstance(event, StreamParentBoundaryDecision):
                    with Session(bind) as policy_session:
                        parent_resolution = create_tutor_runtime(policy_session)._resolve_parent_boundary(  # noqa: SLF001 - shared policy seam
                            student_id=student_id,
                            decision=parse_parent_boundary_decision(event.payload),
                        )
                    if parent_resolution.action is not SafetyAction.REDIRECT_TO_PARENT:
                        for text in buffered:
                            yield f"event: delta\ndata: {json.dumps({'text': text})}\n\n"
                    buffered.clear()
                elif isinstance(event, StreamComplete):
                    terminal = event.result
            if terminal is None:
                raise RuntimeError("Canvas Tutor stream ended without a terminal result.")
            if parent_resolution is None:
                with Session(bind) as policy_session:
                    parent_resolution = create_tutor_runtime(policy_session)._resolve_parent_boundary(  # noqa: SLF001 - shared policy seam
                        student_id=student_id,
                        decision=parse_parent_boundary_decision(terminal.output.get("parent_boundary")),
                    )
            redirect = parent_resolution.action is SafetyAction.REDIRECT_TO_PARENT
            turn = service.persist_canvas_turn(
                admission=admission,
                result=terminal,
                student_id=student_id,
                parent_boundary={"action": parent_resolution.action.value, "reason_code": parent_resolution.reason_code},
                override_text=("Please ask a trusted grown-up for help with this topic." if redirect else None),
            )
            if not redirect:
                for text in buffered:
                    yield f"event: delta\ndata: {json.dumps({'text': text})}\n\n"
            yield (
                "event: turn\ndata: "
                + json.dumps({
                    "text": turn.text,
                    "suggested_actions": [action.model_dump() for action in turn.suggested_actions],
                    "guided_check": None if turn.guided_check is None else turn.guided_check.model_dump(mode="json"),
                })
                + "\n\n"
            )
            # This is the existing server-side terminal SSE lifecycle, not a
            # claim that the browser received the frame.
            service.finalize_delivered_turn(admission=admission, turn=turn, student_id=student_id)
        except GeneratorExit:
            # A terminal frame may already have been constructed while the
            # server-side stream is interrupted.  Preserve its durable Tutor
            # message and execution, but cancel the still-RUNNING interaction
            # rather than leaving an unclaimable lifecycle orphan.
            service.abandon_admitted_turn(admission=admission, student_id=student_id, status="CANCELLED")
            raise
        except Exception:
            service.abandon_admitted_turn(admission=admission, student_id=student_id, status="FAILED")
            raise

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
