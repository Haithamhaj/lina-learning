"""Typed, model-facing Studio Workspace context for the existing Tutor call."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from services.platform.db.models import (
    StudioEvent,
    StudioRuntime,
    StudioScene,
    StudioSnapshot,
    StudioStudentInteraction,
    StudioTutorObservation,
)
from services.studio.service import StudioStateService, TUTOR_OBSERVATION_FAILURE_CODES
from services.studio.subjects import production_subject_registry
from services.studio.subjects.registry import SubjectCapabilityError


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
class StudioTutorSceneCapability:
    """Exact persisted active-Scene identity plus compact allowed semantics."""

    scene_id: UUID
    subject_key: str
    subject_profile_version: str
    activity_key: str
    activity_version: str
    renderer_key: str
    renderer_version: str
    allowed_action_keys: tuple[str, ...]
    source_references: tuple[str, ...]
    source_message_id: UUID | None = None
    capability_status: str = "RESOLVED"

    def as_model_payload(self) -> dict[str, object]:
        return {
            "scene_id": str(self.scene_id),
            "subject_key": self.subject_key,
            "subject_profile_version": self.subject_profile_version,
            "activity_key": self.activity_key,
            "activity_version": self.activity_version,
            "allowed_action_keys": list(self.allowed_action_keys),
            "source_references": list(self.source_references),
            "capability_status": self.capability_status,
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
    current_scene_capability: StudioTutorSceneCapability | None = None

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
                "current_scene_capability": (
                    None if self.current_scene_capability is None else self.current_scene_capability.as_model_payload()
                ),
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
    student_interaction_id: UUID | None = None,
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
            if student_interaction_id is not None:
                interaction = selection_session.execute(
                    select(StudioStudentInteraction).where(
                        StudioStudentInteraction.id == student_interaction_id,
                        StudioStudentInteraction.studio_runtime_id == runtime.id,
                        StudioStudentInteraction.student_id == student_id,
                        StudioStudentInteraction.learning_session_id == learning_session_id,
                    )
                ).scalar_one_or_none()
                if interaction is None:
                    raise RuntimeError("Studio Tutor observation interaction is outside the locked Runtime.")
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
            scene_capability = _selected_scene_capability(
                selection_session=selection_session,
                runtime_id=runtime.id,
                student_id=student_id,
                scene_id=snapshot.current_scene_id,
            )
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
                    student_interaction_id=student_interaction_id,
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
                    current_scene_capability=scene_capability,
                ),
                previous_watermark=previous_watermark,
            )
    finally:
        selection_session.close()


def _selected_scene_capability(
    *,
    selection_session: Session,
    runtime_id: UUID,
    student_id: UUID,
    scene_id: UUID | None,
) -> StudioTutorSceneCapability | None:
    if scene_id is None:
        return None
    scene = selection_session.execute(
        select(StudioScene).where(
            StudioScene.id == scene_id,
            StudioScene.studio_runtime_id == runtime_id,
            StudioScene.student_id == student_id,
        )
    ).scalar_one_or_none()
    if scene is None:
        raise RuntimeError("Studio Snapshot references an unavailable current Scene.")
    status = "RESOLVED"
    action_keys: tuple[str, ...] = ()
    try:
        registry = production_subject_registry()
        activity = registry.resolve_activity(
            scene.subject_key, scene.subject_profile_version, scene.activity_key, scene.activity_contract_version
        )
        renderer = registry.resolve_renderer(
            scene.subject_key, scene.subject_profile_version, scene.renderer_key, scene.renderer_version
        )
        if activity.renderer_key != renderer.renderer_key or activity.renderer_version != renderer.renderer_version:
            raise SubjectCapabilityError("Scene Activity and Renderer relation is unsupported.")
        action_keys = tuple(action.action_key for action in activity.actions)
    except SubjectCapabilityError:
        status = "UNSUPPORTED_HISTORICAL_CAPABILITY"
    return StudioTutorSceneCapability(
        scene_id=scene.id,
        subject_key=scene.subject_key,
        subject_profile_version=scene.subject_profile_version,
        activity_key=scene.activity_key,
        activity_version=scene.activity_contract_version,
        renderer_key=scene.renderer_key,
        renderer_version=scene.renderer_version,
        allowed_action_keys=action_keys,
        source_references=tuple(scene.source_asset_refs),
        source_message_id=scene.source_message_id,
        capability_status=status,
    )


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
