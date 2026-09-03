"""Authenticated application boundary for Studio snapshot and operation protocol v1.

The public command intentionally contains only an Activity action request.  The
Scene's immutable capability contract derives every durable event detail.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningSession, StudioEvent, StudioRuntime, StudioScene, StudioSnapshot
from services.studio.contracts import AppendStudioEventCommand, StudioActor
from services.studio.service import (
    IdempotencyConflict,
    InvalidStudioLineage,
    StaleSceneVersion,
    StudioStateError,
    StudioStateService,
)
from services.studio.subjects.registry import SubjectCapabilityError, SubjectCapabilityRegistry


STUDIO_PROTOCOL_VERSION = "studio-protocol-v1"


class StudioProtocolError(ValueError):
    """Base error for a rejected external Studio protocol request."""


class StudioResourceNotFound(StudioProtocolError):
    """A Student-scoped Studio resource was not found."""


class StudioCursorConflict(StudioProtocolError):
    """Resume cursor values are invalid or inconsistent."""


class StudioOperationConflict(StudioProtocolError):
    """A mutable operation conflicts with accepted Studio history."""


class StudioOperationRequest(BaseModel):
    """Only browser-controlled action inputs; durable semantics are not public."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scene_id: UUID
    base_scene_version: int = Field(ge=0)
    action_key: str = Field(min_length=1, max_length=128)
    payload: dict[str, object]
    idempotency_key: str = Field(min_length=1, max_length=255)


def parse_resume_cursor(*, last_event_id: str | None, after_sequence: int | None) -> int | None:
    """Resolve equivalent cursor transport forms without silently choosing one."""

    header_cursor: int | None = None
    if last_event_id is not None:
        value = last_event_id.strip()
        if not value or not value.isdecimal():
            raise StudioCursorConflict("Last-Event-ID must be a non-negative integer sequence.")
        header_cursor = int(value)
    if after_sequence is not None and after_sequence < 0:
        raise StudioCursorConflict("after_sequence must be a non-negative integer sequence.")
    if header_cursor is not None and after_sequence is not None and header_cursor != after_sequence:
        raise StudioCursorConflict("Last-Event-ID and after_sequence disagree.")
    return header_cursor if header_cursor is not None else after_sequence


class StudioProtocolService:
    """Student-owned read/open/submit boundary; no Tutor or renderer authority."""

    def __init__(self, session: Session, *, subject_registry: SubjectCapabilityRegistry | None = None) -> None:
        self.session = session
        self.state = StudioStateService(session, subject_registry=subject_registry)
        self.subject_registry = self.state.subject_registry

    def open_runtime(self, *, student_id: UUID, learning_session_id: UUID) -> StudioRuntime:
        learning_session = self.session.execute(
            select(LearningSession).where(
                LearningSession.id == learning_session_id,
                LearningSession.student_id == student_id,
            )
        ).scalar_one_or_none()
        if learning_session is None:
            raise StudioResourceNotFound("Studio LearningSession was not found.")
        try:
            return self.state.get_or_create_runtime(student_id=student_id, learning_session_id=learning_session.id)
        except InvalidStudioLineage as error:
            raise StudioResourceNotFound("Studio LearningSession was not found.") from error

    def runtime(self, *, student_id: UUID, runtime_id: UUID) -> StudioRuntime:
        runtime = self.session.execute(
            select(StudioRuntime).where(StudioRuntime.id == runtime_id, StudioRuntime.student_id == student_id)
        ).scalar_one_or_none()
        if runtime is None:
            raise StudioResourceNotFound("Studio runtime was not found.")
        return runtime

    def snapshot(self, *, student_id: UUID, runtime_id: UUID) -> StudioSnapshot:
        runtime = self.runtime(student_id=student_id, runtime_id=runtime_id)
        snapshot = self.session.execute(
            select(StudioSnapshot).where(
                StudioSnapshot.studio_runtime_id == runtime.id,
                StudioSnapshot.student_id == student_id,
            )
        ).scalar_one_or_none()
        if snapshot is None:
            raise StudioProtocolError("Studio runtime is missing its required Snapshot.")
        return snapshot

    def events_after(self, *, student_id: UUID, runtime_id: UUID, after_sequence: int) -> list[StudioEvent]:
        runtime = self.runtime(student_id=student_id, runtime_id=runtime_id)
        if after_sequence > runtime.latest_event_sequence:
            raise StudioCursorConflict("Resume sequence is ahead of committed Studio history.")
        return list(
            self.session.execute(
                select(StudioEvent)
                .where(
                    StudioEvent.studio_runtime_id == runtime.id,
                    StudioEvent.student_id == student_id,
                    StudioEvent.sequence > after_sequence,
                )
                .order_by(StudioEvent.sequence)
            ).scalars()
        )

    def submit_operation(self, *, student_id: UUID, runtime_id: UUID, request: StudioOperationRequest):
        runtime = self.runtime(student_id=student_id, runtime_id=runtime_id)
        scene = self.session.execute(
            select(StudioScene).where(
                StudioScene.id == request.scene_id,
                StudioScene.studio_runtime_id == runtime.id,
                StudioScene.student_id == student_id,
            )
        ).scalar_one_or_none()
        if scene is None:
            raise StudioResourceNotFound("Studio Scene was not found.")
        try:
            action = self.subject_registry.resolve_action(
                scene.subject_key,
                scene.subject_profile_version,
                scene.activity_key,
                scene.activity_contract_version,
                request.action_key,
            )
        except SubjectCapabilityError as error:
            raise StudioProtocolError(str(error)) from error
        try:
            return self.state.append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime.id,
                    student_id=student_id,
                    learning_session_id=runtime.learning_session_id,
                    event_kind=None,
                    event_schema_version=None,
                    actor=StudioActor.STUDENT,
                    action_key=action.action_key,
                    payload_schema_version=action.payload_schema_version,
                    payload=request.payload,
                    idempotency_key=request.idempotency_key,
                    scene_id=scene.id,
                    base_scene_version=request.base_scene_version,
                )
            )
        except (IdempotencyConflict, StaleSceneVersion) as error:
            raise StudioOperationConflict(str(error)) from error
        except (StudioStateError, InvalidStudioLineage) as error:
            raise StudioProtocolError(str(error)) from error


def snapshot_frame(snapshot: StudioSnapshot) -> dict[str, object]:
    """Return the bounded client-safe snapshot representation for protocol v1."""

    return {
        "protocol_version": STUDIO_PROTOCOL_VERSION,
        "type": "STUDIO_SNAPSHOT",
        "latest_event_sequence": snapshot.latest_event_sequence,
        "snapshot_schema_version": snapshot.snapshot_schema_version,
        "current_scene_id": None if snapshot.current_scene_id is None else str(snapshot.current_scene_id),
        "current_scene_version": snapshot.current_scene_version,
        "active_subject_key": snapshot.active_subject_key,
        "active_activity_key": snapshot.active_activity_key,
        "active_step_key": snapshot.active_step_key,
        "state_payload": dict(snapshot.state_payload),
    }


def event_frame(event: StudioEvent) -> dict[str, object]:
    """Return a committed event frame; sequence remains the feed authority."""

    return {
        "protocol_version": STUDIO_PROTOCOL_VERSION,
        "type": "STUDIO_EVENT_COMMITTED",
        "sequence": event.sequence,
        "event": {
            "id": str(event.id),
            "sequence": event.sequence,
            "actor": event.actor,
            "event_kind": event.event_kind,
            "action_key": event.action_key,
            "event_schema_version": event.event_schema_version,
            "payload_schema_version": event.payload_schema_version,
            "scene_id": None if event.scene_id is None else str(event.scene_id),
            "base_scene_version": event.base_scene_version,
            "resulting_scene_version": event.resulting_scene_version,
            "payload": dict(event.payload),
            "result_status": event.result_status,
        },
    }
