"""Typed, model-facing Studio Workspace context for the existing Tutor call."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from services.platform.db.models import StudioEvent, StudioRuntime, StudioSnapshot, StudioTutorObservation
from services.studio.service import StudioStateService, TUTOR_OBSERVATION_FAILURE_CODES


STUDIO_TUTOR_CONTEXT_SCHEMA_VERSION = "studio-tutor-context-v1"
OBSERVATION_FAILURE_CODES = TUTOR_OBSERVATION_FAILURE_CODES


@dataclass(frozen=True)
class StudioTutorEventContext:
    """One committed semantic Studio event, reduced to Tutor-useful fields."""

    sequence: int
    actor: str
    event_kind: str
    action_key: str | None
    subject_key: str | None
    activity_key: str | None
    base_scene_version: int | None
    resulting_scene_version: int | None
    payload_schema_version: str
    payload: Mapping[str, object]

    def as_model_payload(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "actor": self.actor,
            "event_kind": self.event_kind,
            "action_key": self.action_key,
            "subject_key": self.subject_key,
            "activity_key": self.activity_key,
            "base_scene_version": self.base_scene_version,
            "resulting_scene_version": self.resulting_scene_version,
            "payload_schema_version": self.payload_schema_version,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class StudioTutorWorkspaceContext:
    """Current Snapshot plus the exact unseen Event range selected for one turn."""

    runtime_id: UUID
    snapshot_schema_version: str
    through_sequence: int
    snapshot_sequence: int
    current_scene_id: UUID | None
    current_scene_version: int | None
    active_subject_key: str | None
    active_activity_key: str | None
    state_payload: Mapping[str, object]
    unseen_events: tuple[StudioTutorEventContext, ...]
    observation_id: UUID | None

    def as_model_payload(self) -> dict[str, object]:
        return {
            "schema_version": STUDIO_TUTOR_CONTEXT_SCHEMA_VERSION,
            "through_sequence": self.through_sequence,
            "snapshot": {
                "schema_version": self.snapshot_schema_version,
                "sequence": self.snapshot_sequence,
                "current_scene_id": None if self.current_scene_id is None else str(self.current_scene_id),
                "current_scene_version": self.current_scene_version,
                "active_subject_key": self.active_subject_key,
                "active_activity_key": self.active_activity_key,
                "state": dict(self.state_payload),
            },
            "unseen_events": [event.as_model_payload() for event in self.unseen_events],
        }


@dataclass(frozen=True)
class StudioTutorContextSelection:
    """One committed, exact selection boundary for a normal Chat Tutor turn."""

    context: StudioTutorWorkspaceContext
    previous_watermark: int


def select_studio_tutor_context(
    *,
    bind: Engine | Connection,
    student_id: UUID,
    learning_session_id: UUID,
) -> StudioTutorContextSelection | None:
    """Capture Snapshot and unseen Events under a brief Runtime lock, then release it."""

    selection_session = Session(bind)
    try:
        with selection_session.begin():
            runtime = selection_session.execute(
                select(StudioRuntime)
                .where(
                    StudioRuntime.student_id == student_id,
                    StudioRuntime.learning_session_id == learning_session_id,
                )
                .with_for_update()
            ).scalar_one_or_none()
            if runtime is None:
                return None
            snapshot = selection_session.execute(
                select(StudioSnapshot).where(
                    StudioSnapshot.studio_runtime_id == runtime.id,
                    StudioSnapshot.student_id == student_id,
                )
            ).scalar_one_or_none()
            if snapshot is None or snapshot.latest_event_sequence != runtime.latest_event_sequence:
                raise RuntimeError("Studio Snapshot is inconsistent with the locked Runtime sequence.")
            previous_watermark = runtime.last_tutor_observation_sequence
            through_sequence = runtime.latest_event_sequence
            events = tuple(
                StudioTutorEventContext(
                    sequence=event.sequence,
                    actor=event.actor,
                    event_kind=event.event_kind,
                    action_key=event.action_key,
                    subject_key=event.subject_key,
                    activity_key=event.activity_key,
                    base_scene_version=event.base_scene_version,
                    resulting_scene_version=event.resulting_scene_version,
                    payload_schema_version=event.payload_schema_version,
                    payload=dict(event.payload),
                )
                for event in selection_session.execute(
                    select(StudioEvent)
                    .where(
                        StudioEvent.studio_runtime_id == runtime.id,
                        StudioEvent.student_id == student_id,
                        StudioEvent.sequence > previous_watermark,
                        StudioEvent.sequence <= through_sequence,
                    )
                    .order_by(StudioEvent.sequence)
                ).scalars()
            )
            observation_id: UUID | None = None
            if events:
                StudioStateService(selection_session).supersede_selected_tutor_observations(
                    runtime_id=runtime.id,
                    student_id=student_id,
                    through_event_sequence=through_sequence,
                )
                observation = StudioTutorObservation(
                    studio_runtime_id=runtime.id,
                    student_id=student_id,
                    from_event_sequence=previous_watermark + 1,
                    through_event_sequence=through_sequence,
                    status="SELECTED",
                )
                selection_session.add(observation)
                selection_session.flush()
                observation_id = observation.id
            return StudioTutorContextSelection(
                context=StudioTutorWorkspaceContext(
                    runtime_id=runtime.id,
                    snapshot_schema_version=snapshot.snapshot_schema_version,
                    through_sequence=through_sequence,
                    snapshot_sequence=snapshot.latest_event_sequence,
                    current_scene_id=snapshot.current_scene_id,
                    current_scene_version=snapshot.current_scene_version,
                    active_subject_key=snapshot.active_subject_key,
                    active_activity_key=snapshot.active_activity_key,
                    state_payload=dict(snapshot.state_payload),
                    unseen_events=events,
                    observation_id=observation_id,
                ),
                previous_watermark=previous_watermark,
            )
    finally:
        selection_session.close()


def acknowledge_studio_tutor_observation(
    *,
    bind: Engine | Connection,
    student_id: UUID,
    observation_id: UUID,
    ai_execution_id: UUID,
    source_message_id: UUID,
) -> None:
    """Commit one selected observation and advance only its captured watermark."""

    acknowledgement_session = Session(bind)
    try:
        with acknowledgement_session.begin():
            StudioStateService(acknowledgement_session).advance_tutor_observation_watermark(
                observation_id=observation_id,
                student_id=student_id,
                ai_execution_id=ai_execution_id,
                source_message_id=source_message_id,
            )
    finally:
        acknowledgement_session.close()


def mark_studio_tutor_observation_failed(
    *,
    bind: Engine | Connection,
    student_id: UUID,
    observation_id: UUID,
    failure_code: str,
) -> None:
    """Record a bounded pre-acknowledgement failure without consuming Events."""

    if failure_code not in OBSERVATION_FAILURE_CODES:
        raise ValueError("Studio observation failure code is unsupported.")
    transition_session = Session(bind)
    try:
        with transition_session.begin():
            StudioStateService(transition_session).fail_tutor_observation(
                observation_id=observation_id,
                student_id=student_id,
                failure_code=failure_code,
            )
    finally:
        transition_session.close()


def cancel_studio_tutor_observation(
    *,
    bind: Engine | Connection,
    student_id: UUID,
    observation_id: UUID,
) -> None:
    """Record that an incomplete Tutor stream did not acknowledge selected Events."""

    transition_session = Session(bind)
    try:
        with transition_session.begin():
            StudioStateService(transition_session).cancel_tutor_observation(
                observation_id=observation_id,
                student_id=student_id,
            )
    finally:
        transition_session.close()
