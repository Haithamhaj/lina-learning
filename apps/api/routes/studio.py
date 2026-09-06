"""Authenticated Student Studio protocol v1 endpoints.

This router deliberately has no Tutor, renderer, or curriculum authority.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.platform.auth import AuthenticatedPrincipal, UserRole, require_role
from services.platform.db.session import get_session
from services.platform.student_identity import resolve_student_for_authenticated_identity
from services.studio.feed import StudioEventFeed
from services.studio.protocol import (
    StudioCursorConflict,
    StudioOperationRequest,
    StudioOperationConflict,
    StudioProtocolError,
    StudioProtocolService,
    StudioResourceNotFound,
    parse_resume_cursor,
    snapshot_frame,
)
from services.studio.subjects import production_subject_registry
from services.studio.subjects.registry import SubjectCapabilityRegistry


router = APIRouter(prefix="/api/v1/student/studio", tags=["student-studio"])


class StudioRuntimeOpenResponse(BaseModel):
    runtime_id: UUID
    learning_session_id: UUID
    status: str
    latest_event_sequence: int


class StudioOperationResponse(BaseModel):
    event_id: UUID
    sequence: int
    replayed: bool
    student_interaction_id: UUID | None
    student_interaction_status: str | None


def _student_id(session: Session, principal: AuthenticatedPrincipal) -> UUID:
    try:
        return resolve_student_for_authenticated_identity(
            session,
            identity_provider="clerk",
            subject=principal.subject,
            email=principal.email,
        ).id
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student profile is unavailable.") from None


def _not_found(error: StudioResourceNotFound) -> HTTPException:
    # Same public response for cross-Student and unknown identifiers.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio resource not found.")


def get_studio_subject_registry() -> SubjectCapabilityRegistry:
    """Production registry injection seam; fixture activities remain test-only."""

    return production_subject_registry()


@router.post("/session/{learning_session_id}/open", response_model=StudioRuntimeOpenResponse)
def open_studio_runtime(
    learning_session_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> StudioRuntimeOpenResponse:
    student_id = _student_id(session, principal)
    protocol = StudioProtocolService(session)
    try:
        runtime = protocol.open_runtime(student_id=student_id, learning_session_id=learning_session_id)
        snapshot = protocol.snapshot(student_id=student_id, runtime_id=runtime.id)
        response = StudioRuntimeOpenResponse(
            runtime_id=runtime.id,
            learning_session_id=runtime.learning_session_id,
            status=runtime.status,
            latest_event_sequence=snapshot.latest_event_sequence,
        )
        # The open result is returned only after durable runtime/snapshot state.
        session.commit()
        return response
    except StudioResourceNotFound as error:
        session.rollback()
        raise _not_found(error) from None


@router.get("/{runtime_id}/snapshot")
def get_studio_snapshot(
    runtime_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    student_id = _student_id(session, principal)
    try:
        projection = StudioProtocolService(session).snapshot_projection(
            student_id=student_id,
            runtime_id=runtime_id,
        )
        return snapshot_frame(
            projection.snapshot,
            active_scene_contract=projection.active_scene_contract,
            active_scene_seed=projection.active_scene_seed,
        )
    except StudioResourceNotFound as error:
        raise _not_found(error) from None


@router.post("/{runtime_id}/operations", response_model=StudioOperationResponse)
def submit_studio_operation(
    runtime_id: UUID,
    request: StudioOperationRequest,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    subject_registry: SubjectCapabilityRegistry = Depends(get_studio_subject_registry),
    session: Session = Depends(get_session),
) -> StudioOperationResponse:
    student_id = _student_id(session, principal)
    try:
        result = StudioProtocolService(session, subject_registry=subject_registry).submit_operation(
            student_id=student_id,
            runtime_id=runtime_id,
            request=request,
        )
        response = StudioOperationResponse(
            event_id=result.event.id,
            sequence=result.event.sequence,
            replayed=result.replayed,
            student_interaction_id=None if result.interaction is None else result.interaction.id,
            student_interaction_status=None if result.interaction is None else result.interaction.status,
        )
        # Do not claim acceptance before Event/Snapshot/interaction commit.
        session.commit()
        return response
    except StudioResourceNotFound as error:
        session.rollback()
        raise _not_found(error) from None
    except StudioOperationConflict as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
    except StudioProtocolError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None


@router.get("/{runtime_id}/events/stream")
def stream_studio_events(
    runtime_id: UUID,
    after_sequence: int | None = None,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.STUDENT)),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    try:
        cursor = parse_resume_cursor(last_event_id=last_event_id, after_sequence=after_sequence)
    except StudioCursorConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
    student_id = _student_id(session, principal)
    try:
        protocol = StudioProtocolService(session)
        runtime = protocol.runtime(student_id=student_id, runtime_id=runtime_id)
        if cursor is not None and cursor > runtime.latest_event_sequence:
            raise StudioCursorConflict("Resume sequence is ahead of committed Studio history.")
        # Finish request auth/ownership work before the long-lived generator.
        session.commit()
    except StudioResourceNotFound as error:
        session.rollback()
        raise _not_found(error) from None
    except StudioCursorConflict as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None

    return StreamingResponse(
        StudioEventFeed().stream(student_id=student_id, runtime_id=runtime_id, after_sequence=cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
