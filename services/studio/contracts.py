"""Typed, bounded commands for the Studio state application service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping
from uuid import UUID


class StudioActor(str, Enum):
    STUDENT = "STUDENT"
    TUTOR = "TUTOR"
    SYSTEM = "SYSTEM"
    CANVAS_SPECIALIST = "CANVAS_SPECIALIST"


class StudioEventResultStatus(str, Enum):
    """Durable Studio events record only accepted state transitions in this foundation."""

    ACCEPTED = "ACCEPTED"


STUDIO_EVENT_RESULT_STATUS_VALUES = tuple(status.value for status in StudioEventResultStatus)


@dataclass(frozen=True)
class CreateSceneCommand:
    student_id: UUID
    learning_session_id: UUID
    subject_key: str
    concept_keys: tuple[str, ...]
    activity_key: str
    artifact_type: str
    renderer_key: str
    renderer_version: str
    activity_contract_version: str
    payload_schema_version: str
    seed_payload: Mapping[str, object]
    subject_profile_version: str = "subject-profile-v1"
    accessibility_payload: Mapping[str, object] = field(default_factory=dict)
    locale: str = "en"
    direction: str = "auto"
    source_asset_refs: tuple[str, ...] = ()
    source_segment_id: UUID | None = None
    source_message_id: UUID | None = None


@dataclass(frozen=True)
class AppendStudioEventCommand:
    runtime_id: UUID
    student_id: UUID
    learning_session_id: UUID
    event_kind: str | None
    event_schema_version: str | None
    actor: StudioActor
    payload_schema_version: str
    payload: Mapping[str, object]
    idempotency_key: str
    action_key: str | None = None
    result_status: StudioEventResultStatus | str = StudioEventResultStatus.ACCEPTED
    scene_id: UUID | None = None
    base_scene_version: int | None = None
    subject_key: str | None = None
    activity_key: str | None = None
    source_message_id: UUID | None = None
    source_segment_id: UUID | None = None
    causal_event_id: UUID | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True)
class CreateTutorObservationCommand:
    runtime_id: UUID
    student_id: UUID
    from_event_sequence: int
    through_event_sequence: int
    student_interaction_id: UUID | None = None
    ai_execution_id: UUID | None = None
    failure_metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class CreateCanvasSpecialistRunCommand:
    runtime_id: UUID
    student_id: UUID
    source_message_id: UUID
    scene_id: UUID | None
    base_scene_version: int
    subject_key: str
    capability_profile_version: str
    output_schema_version: str
    job_id: UUID | None = None
    ai_execution_id: UUID | None = None
    accepted_scene_version: int | None = None
    failure_metadata: Mapping[str, object] | None = None
    deadline_at: datetime | None = None
