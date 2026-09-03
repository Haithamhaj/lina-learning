"""Atomic PostgreSQL persistence for the subject-agnostic Studio state stream."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Mapping
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    AIExecution,
    Job,
    LearningMessage,
    LearningSegment,
    LearningSession,
    StudioCanvasSpecialistRun,
    StudioEvent,
    StudioRuntime,
    StudioScene,
    StudioSnapshot,
    StudioStudentInteraction,
    StudioTutorObservation,
)
from services.studio.contracts import (
    AppendStudioEventCommand,
    CreateCanvasSpecialistRunCommand,
    CreateSceneCommand,
    CreateTutorObservationCommand,
    StudioEventResultStatus,
)
from services.studio.reducer import (
    CORE_EVENT_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    SnapshotProjection,
    UnknownStudioEvent,
    empty_snapshot,
    reduce_snapshot,
    registered_reducer,
)


MAX_EVENT_PAYLOAD_BYTES = 8_192
MAX_SCENE_PAYLOAD_BYTES = 16_384
MAX_ACCESSIBILITY_PAYLOAD_BYTES = 8_192
MAX_SNAPSHOT_PAYLOAD_BYTES = 16_384
MAX_FAILURE_METADATA_BYTES = 4_096
MAX_INTERACTION_PAYLOAD_BYTES = 4_096


class StudioStateError(ValueError):
    """Base error for a rejected Studio state command."""


class InvalidStudioLineage(StudioStateError):
    """A referenced object is outside the runtime's Student/session boundary."""


class StaleSceneVersion(StudioStateError):
    """A state-changing command is based on an older accepted Scene version."""


class IdempotencyConflict(StudioStateError):
    """An idempotency key was reused for a different semantic command."""


class StudioRuntimeClosed(StudioStateError):
    """A mutable command targeted a closed or archived runtime."""


class StudioStateService:
    """Application service that locks one runtime before allocating its event sequence."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_runtime(self, *, student_id: UUID, learning_session_id: UUID) -> StudioRuntime:
        """Return the sole runtime for a Student-owned LearningSession."""

        with self.session.begin_nested():
            learning_session = self.session.execute(
                select(LearningSession)
                .where(LearningSession.id == learning_session_id)
                .with_for_update()
            ).scalar_one_or_none()
            if learning_session is None or learning_session.student_id != student_id:
                raise InvalidStudioLineage("LearningSession does not belong to the supplied Student.")
            runtime = self.session.execute(
                select(StudioRuntime)
                .where(StudioRuntime.learning_session_id == learning_session_id)
                .with_for_update()
            ).scalar_one_or_none()
            if runtime is not None:
                if runtime.student_id != student_id:
                    raise InvalidStudioLineage("Studio runtime Student does not match its LearningSession.")
                return runtime
            runtime = StudioRuntime(student_id=student_id, learning_session_id=learning_session_id)
            self.session.add(runtime)
            self.session.flush()
            self.session.add(
                StudioSnapshot(
                    studio_runtime_id=runtime.id,
                    student_id=student_id,
                    snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
                    latest_event_sequence=0,
                    state_payload={},
                )
            )
            self.session.flush()
            return runtime

    def accept_scene(self, command: CreateSceneCommand) -> StudioScene:
        """Persist an accepted Scene and its first immutable lifecycle event atomically."""

        self._validate_scene_command(command)
        with self.session.begin_nested():
            runtime = self._runtime_locked(command.student_id, command.learning_session_id)
            self._require_open_runtime(runtime)
            self._validate_source_lineage(
                runtime,
                source_segment_id=command.source_segment_id,
                source_message_id=command.source_message_id,
            )
            scene = StudioScene(
                studio_runtime_id=runtime.id,
                student_id=runtime.student_id,
                learning_session_id=runtime.learning_session_id,
                source_segment_id=command.source_segment_id,
                source_message_id=command.source_message_id,
                subject_key=command.subject_key,
                concept_keys=list(command.concept_keys),
                activity_key=command.activity_key,
                artifact_type=command.artifact_type,
                renderer_key=command.renderer_key,
                renderer_version=command.renderer_version,
                activity_contract_version=command.activity_contract_version,
                payload_schema_version=command.payload_schema_version,
                seed_payload=dict(command.seed_payload),
                accessibility_payload=dict(command.accessibility_payload),
                locale=command.locale,
                direction=command.direction,
                source_asset_refs=list(command.source_asset_refs),
            )
            self.session.add(scene)
            self.session.flush()
            accepted_payload = {
                "scene_seed": dict(command.seed_payload),
                "accessibility_payload": dict(command.accessibility_payload),
                "concept_keys": list(command.concept_keys),
            }
            self._append_locked(
                runtime,
                AppendStudioEventCommand(
                    runtime_id=runtime.id,
                    student_id=runtime.student_id,
                    learning_session_id=runtime.learning_session_id,
                    event_kind="studio.scene.accepted",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=self._system_actor(),
                    payload_schema_version="studio-scene-accepted-v1",
                    payload=accepted_payload,
                    scene_id=scene.id,
                    base_scene_version=0,
                    subject_key=scene.subject_key,
                    activity_key=scene.activity_key,
                    source_message_id=scene.source_message_id,
                    source_segment_id=scene.source_segment_id,
                    idempotency_key=f"scene-accept:{scene.id}",
                ),
            )
            return scene

    def append_event(self, command: AppendStudioEventCommand) -> "AppendStudioEventResult":
        """Append one typed semantic event, snapshot projection, and optional interaction."""

        self._validate_append_command(command)
        with self.session.begin_nested():
            runtime = self._runtime_locked(command.student_id, command.learning_session_id, runtime_id=command.runtime_id)
            self._require_open_runtime(runtime)
            return self._append_locked(runtime, command)

    def _append_locked(
        self,
        runtime: StudioRuntime,
        command: AppendStudioEventCommand,
    ) -> "AppendStudioEventResult":
        """Append while the owning runtime sequence allocator is row-locked."""

        fingerprint = self._fingerprint(command)
        existing = self.session.execute(
            select(StudioEvent).where(
                StudioEvent.studio_runtime_id == runtime.id,
                StudioEvent.idempotency_key == command.idempotency_key,
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.command_fingerprint != fingerprint:
                raise IdempotencyConflict("Studio idempotency key was reused with a different command.")
            snapshot = self._snapshot_locked(runtime)
            interaction = self.session.execute(
                select(StudioStudentInteraction).where(StudioStudentInteraction.source_event_id == existing.id)
            ).scalar_one_or_none()
            scene = self.session.get(StudioScene, existing.scene_id) if existing.scene_id else None
            return AppendStudioEventResult(existing, snapshot, scene, interaction, replayed=True)

        # Validate reducer availability before assigning a sequence or mutating any row.
        registered_reducer(command.event_kind, command.event_schema_version)
        self._validate_source_lineage(
            runtime,
            source_segment_id=command.source_segment_id,
            source_message_id=command.source_message_id,
        )
        scene = self._scene_for_command(runtime, command)
        if command.causal_event_id is not None:
            causal = self.session.execute(
                select(StudioEvent).where(
                    StudioEvent.id == command.causal_event_id,
                    StudioEvent.studio_runtime_id == runtime.id,
                    StudioEvent.student_id == runtime.student_id,
                )
            ).scalar_one_or_none()
            if causal is None:
                raise InvalidStudioLineage("Causal Studio event is outside this runtime.")

        next_sequence = runtime.latest_event_sequence + 1
        resulting_scene_version = None if scene is None else scene.scene_version + 1
        event = StudioEvent(
            id=uuid4(),
            studio_runtime_id=runtime.id,
            student_id=runtime.student_id,
            learning_session_id=runtime.learning_session_id,
            segment_id=command.source_segment_id,
            scene_id=None if scene is None else scene.id,
            sequence=next_sequence,
            actor=command.actor.value,
            event_kind=command.event_kind,
            event_schema_version=command.event_schema_version,
            subject_key=command.subject_key if command.subject_key is not None else (scene.subject_key if scene else None),
            activity_key=command.activity_key if command.activity_key is not None else (scene.activity_key if scene else None),
            source_message_id=command.source_message_id,
            base_scene_version=command.base_scene_version,
            resulting_scene_version=resulting_scene_version,
            idempotency_key=command.idempotency_key,
            command_fingerprint=fingerprint,
            causal_event_id=command.causal_event_id,
            payload_schema_version=command.payload_schema_version,
            payload=dict(command.payload),
            result_status=self._result_status_value(command.result_status),
            occurred_at=command.occurred_at or datetime.now(UTC),
        )
        snapshot = self._snapshot_locked(runtime)
        projection = reduce_snapshot(self.snapshot_projection(snapshot), event.to_reducer_event())
        self._validate_json_capacity(projection["state_payload"], MAX_SNAPSHOT_PAYLOAD_BYTES, "Snapshot payload")
        self._apply_scene_lifecycle(scene, command)
        if scene is not None:
            scene.scene_version = resulting_scene_version  # type: ignore[assignment]
            scene.updated_at = datetime.now(UTC)
        runtime.latest_event_sequence = next_sequence
        runtime.updated_at = datetime.now(UTC)
        self._apply_snapshot(snapshot, projection)
        self.session.add(event)
        self.session.flush()
        interaction = None
        if command.create_student_interaction:
            interaction = StudioStudentInteraction(
                studio_runtime_id=runtime.id,
                student_id=runtime.student_id,
                learning_session_id=runtime.learning_session_id,
                source_event_id=event.id,
                interaction_kind=command.interaction_kind or "tutor-follow-up",
                context_payload={},
            )
            self.session.add(interaction)
            self.session.flush()
        return AppendStudioEventResult(event, snapshot, scene, interaction, replayed=False)

    def rebuild_snapshot(self, *, runtime_id: UUID, student_id: UUID) -> SnapshotProjection:
        """Replay accepted history from sequence zero without touching the stored projection."""

        runtime = self._runtime(runtime_id, student_id)
        projection = empty_snapshot()
        events = self.session.execute(
            select(StudioEvent)
            .where(StudioEvent.studio_runtime_id == runtime.id, StudioEvent.student_id == student_id)
            .order_by(StudioEvent.sequence)
        ).scalars()
        for event in events:
            projection = reduce_snapshot(projection, event.to_reducer_event())
        return projection

    def snapshot_projection(self, snapshot: StudioSnapshot) -> SnapshotProjection:
        return {
            "snapshot_schema_version": snapshot.snapshot_schema_version,
            "latest_event_sequence": snapshot.latest_event_sequence,
            "current_scene_id": snapshot.current_scene_id,
            "current_scene_version": snapshot.current_scene_version,
            "active_subject_key": snapshot.active_subject_key,
            "active_activity_key": snapshot.active_activity_key,
            "active_step_key": snapshot.active_step_key,
            "last_meaningful_student_event_id": snapshot.last_meaningful_student_event_id,
            "state_payload": dict(snapshot.state_payload),
        }

    def runtime_state(self, *, runtime_id: UUID, student_id: UUID) -> dict[str, object]:
        runtime = self._runtime(runtime_id, student_id)
        snapshot = self._snapshot(runtime)
        return {
            "latest_event_sequence": runtime.latest_event_sequence,
            "last_tutor_observation_sequence": runtime.last_tutor_observation_sequence,
            "snapshot": self.snapshot_projection(snapshot),
        }

    def close_runtime(self, *, runtime_id: UUID, student_id: UUID) -> StudioRuntime:
        with self.session.begin_nested():
            runtime = self._runtime_locked(student_id, None, runtime_id=runtime_id)
            runtime.status = "CLOSED"
            runtime.closed_at = datetime.now(UTC)
            return runtime

    def archive_runtime(self, *, runtime_id: UUID, student_id: UUID) -> StudioRuntime:
        with self.session.begin_nested():
            runtime = self._runtime_locked(student_id, None, runtime_id=runtime_id)
            if runtime.status != "CLOSED":
                raise StudioStateError("Only a closed Studio runtime may be archived.")
            runtime.status = "ARCHIVED"
            runtime.archived_at = datetime.now(UTC)
            return runtime

    def create_tutor_observation(self, command: CreateTutorObservationCommand) -> StudioTutorObservation:
        self._validate_json_capacity(command.failure_metadata, MAX_FAILURE_METADATA_BYTES, "Observation failure metadata")
        with self.session.begin_nested():
            runtime = self._runtime_locked(command.student_id, None, runtime_id=command.runtime_id)
            if (
                command.from_event_sequence <= 0
                or command.through_event_sequence < command.from_event_sequence
                or command.through_event_sequence > runtime.latest_event_sequence
            ):
                raise StudioStateError("Tutor observation range must be within committed Studio history.")
            if command.student_interaction_id is not None:
                interaction = self.session.execute(
                    select(StudioStudentInteraction).where(
                        StudioStudentInteraction.id == command.student_interaction_id,
                        StudioStudentInteraction.studio_runtime_id == runtime.id,
                        StudioStudentInteraction.student_id == runtime.student_id,
                    )
                ).scalar_one_or_none()
                if interaction is None:
                    raise InvalidStudioLineage("Tutor observation interaction is outside this runtime.")
            self._validate_ai_execution(command.ai_execution_id, runtime.student_id)
            observation = StudioTutorObservation(
                studio_runtime_id=runtime.id,
                student_id=runtime.student_id,
                from_event_sequence=command.from_event_sequence,
                through_event_sequence=command.through_event_sequence,
                student_interaction_id=command.student_interaction_id,
                ai_execution_id=command.ai_execution_id,
                failure_metadata=None if command.failure_metadata is None else dict(command.failure_metadata),
            )
            self.session.add(observation)
            self.session.flush()
            return observation

    def advance_tutor_observation_watermark(self, *, observation_id: UUID, student_id: UUID) -> None:
        """Reserve acknowledgement advancement for STUDIO-RUNTIME-01's atomic Tutor contract."""

        del observation_id, student_id
        raise ValueError("Tutor observation watermark advancement is not available in STUDIO-STATE-01.")

    def create_canvas_specialist_run(
        self,
        command: CreateCanvasSpecialistRunCommand,
    ) -> StudioCanvasSpecialistRun:
        self._validate_json_capacity(command.failure_metadata, MAX_FAILURE_METADATA_BYTES, "Specialist failure metadata")
        with self.session.begin_nested():
            runtime = self._runtime_locked(command.student_id, None, runtime_id=command.runtime_id)
            self._validate_source_lineage(runtime, source_segment_id=None, source_message_id=command.source_message_id)
            scene = None
            if command.scene_id is not None:
                scene = self.session.execute(
                    select(StudioScene).where(
                        StudioScene.id == command.scene_id,
                        StudioScene.studio_runtime_id == runtime.id,
                        StudioScene.student_id == runtime.student_id,
                    )
                ).scalar_one_or_none()
                if scene is None:
                    raise InvalidStudioLineage("Specialist Scene is outside this runtime.")
                if command.base_scene_version != scene.scene_version:
                    raise StaleSceneVersion("Specialist base Scene version is stale.")
            if command.job_id is not None and self.session.get(Job, command.job_id) is None:
                raise InvalidStudioLineage("Canvas Specialist Job reference does not exist.")
            self._validate_ai_execution(command.ai_execution_id, runtime.student_id)
            run = StudioCanvasSpecialistRun(
                studio_runtime_id=runtime.id,
                student_id=runtime.student_id,
                learning_session_id=runtime.learning_session_id,
                source_message_id=command.source_message_id,
                scene_id=command.scene_id,
                base_scene_version=command.base_scene_version,
                subject_key=command.subject_key,
                capability_profile_version=command.capability_profile_version,
                job_id=command.job_id,
                ai_execution_id=command.ai_execution_id,
                output_schema_version=command.output_schema_version,
                accepted_scene_version=command.accepted_scene_version,
                failure_metadata=None if command.failure_metadata is None else dict(command.failure_metadata),
                deadline_at=command.deadline_at,
            )
            self.session.add(run)
            self.session.flush()
            return run

    def _runtime_locked(
        self,
        student_id: UUID,
        learning_session_id: UUID | None,
        *,
        runtime_id: UUID | None = None,
    ) -> StudioRuntime:
        statement = select(StudioRuntime).where(StudioRuntime.student_id == student_id)
        if runtime_id is not None:
            statement = statement.where(StudioRuntime.id == runtime_id)
        if learning_session_id is not None:
            statement = statement.where(StudioRuntime.learning_session_id == learning_session_id)
        runtime = self.session.execute(statement.with_for_update()).scalar_one_or_none()
        if runtime is None:
            raise InvalidStudioLineage("Studio runtime is not owned by the supplied Student/session.")
        if learning_session_id is not None and runtime.learning_session_id != learning_session_id:
            raise InvalidStudioLineage("Studio runtime LearningSession does not match the command.")
        learning_session = self.session.get(LearningSession, runtime.learning_session_id)
        if learning_session is None or learning_session.student_id != runtime.student_id:
            raise InvalidStudioLineage("Studio runtime does not match the persisted LearningSession Student.")
        return runtime

    def _runtime(self, runtime_id: UUID, student_id: UUID) -> StudioRuntime:
        runtime = self.session.execute(
            select(StudioRuntime).where(StudioRuntime.id == runtime_id, StudioRuntime.student_id == student_id)
        ).scalar_one_or_none()
        if runtime is None:
            raise InvalidStudioLineage("Studio runtime is outside the supplied Student scope.")
        return runtime

    def _snapshot_locked(self, runtime: StudioRuntime) -> StudioSnapshot:
        snapshot = self.session.execute(
            select(StudioSnapshot)
            .where(StudioSnapshot.studio_runtime_id == runtime.id, StudioSnapshot.student_id == runtime.student_id)
            .with_for_update()
        ).scalar_one_or_none()
        if snapshot is None:
            raise StudioStateError("Studio runtime is missing its required materialized Snapshot.")
        return snapshot

    def _snapshot(self, runtime: StudioRuntime) -> StudioSnapshot:
        snapshot = self.session.execute(
            select(StudioSnapshot).where(
                StudioSnapshot.studio_runtime_id == runtime.id,
                StudioSnapshot.student_id == runtime.student_id,
            )
        ).scalar_one_or_none()
        if snapshot is None:
            raise StudioStateError("Studio runtime is missing its required materialized Snapshot.")
        return snapshot

    def _scene_for_command(self, runtime: StudioRuntime, command: AppendStudioEventCommand) -> StudioScene | None:
        if command.scene_id is None:
            if command.base_scene_version is not None:
                raise StaleSceneVersion("A Scene version was supplied without a Scene.")
            if command.create_student_interaction:
                raise StudioStateError("Tutor-triggering interactions require a source Scene event.")
            return None
        scene = self.session.execute(
            select(StudioScene).where(
                StudioScene.id == command.scene_id,
                StudioScene.studio_runtime_id == runtime.id,
                StudioScene.student_id == runtime.student_id,
            ).with_for_update()
        ).scalar_one_or_none()
        if scene is None:
            raise InvalidStudioLineage("Studio Scene is outside this runtime.")
        if command.base_scene_version is None or command.base_scene_version != scene.scene_version:
            raise StaleSceneVersion("Studio Scene version is stale.")
        return scene

    def _apply_scene_lifecycle(self, scene: StudioScene | None, command: AppendStudioEventCommand) -> None:
        if scene is None:
            return
        if command.event_kind == "studio.scene.accepted":
            if scene.status != "ACCEPTED" or command.base_scene_version != 0:
                raise StudioStateError("Only a new accepted Scene may receive the accepted lifecycle event.")
            return
        if command.event_kind == "studio.scene.activated":
            if scene.status != "ACCEPTED":
                raise StudioStateError("Only an accepted Scene may become active.")
            active = self.session.execute(
                select(StudioScene.id).where(
                    StudioScene.studio_runtime_id == scene.studio_runtime_id,
                    StudioScene.status == "ACTIVE",
                    StudioScene.id != scene.id,
                )
            ).scalar_one_or_none()
            if active is not None:
                raise ValueError("A Studio runtime already has an active Scene.")
            scene.status = "ACTIVE"
            return
        if command.event_kind == "studio.scene.status_changed":
            status = command.payload.get("status")
            if not isinstance(status, str):
                raise StudioStateError("Scene status change requires a valid status.")
            transitions = {
                "ACCEPTED": {"ACTIVE", "SUPERSEDED", "ARCHIVED"},
                "ACTIVE": {"SUPERSEDED", "ARCHIVED"},
                "SUPERSEDED": {"ARCHIVED"},
                "ARCHIVED": set(),
            }
            if status not in transitions.get(scene.status, set()):
                raise StudioStateError("Invalid Studio Scene status transition.")
            scene.status = status

    def _apply_snapshot(self, snapshot: StudioSnapshot, projection: SnapshotProjection) -> None:
        snapshot.snapshot_schema_version = str(projection["snapshot_schema_version"])
        snapshot.latest_event_sequence = int(projection["latest_event_sequence"])
        snapshot.current_scene_id = projection["current_scene_id"]  # type: ignore[assignment]
        snapshot.current_scene_version = projection["current_scene_version"]  # type: ignore[assignment]
        snapshot.active_subject_key = projection["active_subject_key"]  # type: ignore[assignment]
        snapshot.active_activity_key = projection["active_activity_key"]  # type: ignore[assignment]
        snapshot.active_step_key = projection["active_step_key"]  # type: ignore[assignment]
        snapshot.last_meaningful_student_event_id = projection["last_meaningful_student_event_id"]  # type: ignore[assignment]
        snapshot.state_payload = dict(projection["state_payload"])  # type: ignore[arg-type]
        snapshot.updated_at = datetime.now(UTC)

    def _validate_scene_command(self, command: CreateSceneCommand) -> None:
        for value, label, limit in (
            (command.subject_key, "Subject key", 64),
            (command.activity_key, "Activity key", 128),
            (command.artifact_type, "Artifact type", 64),
            (command.renderer_key, "Renderer key", 128),
            (command.renderer_version, "Renderer version", 64),
            (command.activity_contract_version, "Activity contract version", 64),
            (command.payload_schema_version, "Payload schema version", 64),
            (command.locale, "Locale", 16),
        ):
            self._bounded_text(value, label, limit)
        if command.direction not in {"ltr", "rtl", "auto"}:
            raise ValueError("Scene direction must be ltr, rtl, or auto.")
        if any(not key or len(key) > 128 for key in command.concept_keys):
            raise ValueError("Scene concept keys must be bounded non-empty strings.")
        if any(not ref or len(ref) > 512 for ref in command.source_asset_refs):
            raise ValueError("Scene source asset references must be bounded non-empty strings.")
        self._validate_json_capacity(command.seed_payload, MAX_SCENE_PAYLOAD_BYTES, "Scene payload")
        self._validate_json_capacity(command.accessibility_payload, MAX_ACCESSIBILITY_PAYLOAD_BYTES, "Accessibility payload")

    def _validate_append_command(self, command: AppendStudioEventCommand) -> None:
        self._bounded_text(command.event_kind, "Event kind", 128)
        self._bounded_text(command.event_schema_version, "Event schema version", 64)
        self._bounded_text(command.payload_schema_version, "Event payload schema version", 64)
        self._bounded_text(command.idempotency_key, "Event idempotency key", 255)
        self._result_status_value(command.result_status)
        if command.subject_key is not None:
            self._bounded_text(command.subject_key, "Event subject key", 64)
        if command.activity_key is not None:
            self._bounded_text(command.activity_key, "Event activity key", 128)
        if command.create_student_interaction and command.interaction_kind is None:
            raise ValueError("Tutor-triggering Studio events require an interaction kind.")
        if command.interaction_kind is not None:
            self._bounded_text(command.interaction_kind, "Interaction kind", 64)
        self._validate_json_capacity(command.payload, MAX_EVENT_PAYLOAD_BYTES, "Event payload")
        if command.event_kind == "studio.recorded":
            if command.payload or command.subject_key is not None or command.activity_key is not None:
                raise StudioStateError("Recorded events must not carry activity state before STUDIO-SUBJECT-01.")
        if command.event_kind == "studio.runtime.initialized" and command.payload:
            raise StudioStateError("Runtime initialization must not carry activity state.")

    def _validate_source_lineage(
        self,
        runtime: StudioRuntime,
        *,
        source_segment_id: UUID | None,
        source_message_id: UUID | None,
    ) -> None:
        if source_segment_id is not None:
            segment = self.session.get(LearningSegment, source_segment_id)
            if segment is None or segment.session_id != runtime.learning_session_id:
                raise InvalidStudioLineage("Source Segment is outside the Studio LearningSession.")
        if source_message_id is not None:
            message = self.session.get(LearningMessage, source_message_id)
            if message is None or message.session_id != runtime.learning_session_id:
                raise InvalidStudioLineage("Source Message is outside the Studio LearningSession.")

    def _validate_ai_execution(self, execution_id: UUID | None, student_id: UUID) -> None:
        if execution_id is None:
            return
        execution = self.session.get(AIExecution, execution_id)
        if execution is None or execution.student_id != student_id:
            raise InvalidStudioLineage("AI execution is outside the supplied Student scope.")

    @staticmethod
    def _require_open_runtime(runtime: StudioRuntime) -> None:
        if runtime.status != "OPEN":
            raise StudioRuntimeClosed("Studio runtime is not open for state mutation.")

    @staticmethod
    def _bounded_text(value: str, label: str, limit: int) -> None:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{label} must be a bounded non-empty string.")

    @classmethod
    def _validate_json_capacity(cls, value: object, limit: int, label: str) -> None:
        try:
            cls._validate_json_value(value)
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} must be JSON-shaped.") from error
        if len(encoded) > limit:
            raise ValueError(f"{label} exceeds its capacity limit; accepted state is never truncated.")

    @classmethod
    def _validate_json_value(cls, value: object) -> None:
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("JSON number must be finite.")
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings.")
                cls._validate_json_value(child)
            return
        if isinstance(value, (list, tuple)):
            for child in value:
                cls._validate_json_value(child)
            return
        raise ValueError("Value is not JSON-shaped.")

    @staticmethod
    def _system_actor():
        from services.studio.contracts import StudioActor

        return StudioActor.SYSTEM

    @staticmethod
    def _fingerprint(command: AppendStudioEventCommand) -> str:
        payload = {
            "runtime_id": str(command.runtime_id),
            "student_id": str(command.student_id),
            "learning_session_id": str(command.learning_session_id),
            "event_kind": command.event_kind,
            "event_schema_version": command.event_schema_version,
            "actor": command.actor.value,
            "payload_schema_version": command.payload_schema_version,
            "payload": command.payload,
            "result_status": StudioStateService._result_status_value(command.result_status),
            "scene_id": None if command.scene_id is None else str(command.scene_id),
            "base_scene_version": command.base_scene_version,
            "subject_key": command.subject_key,
            "activity_key": command.activity_key,
            "source_message_id": None if command.source_message_id is None else str(command.source_message_id),
            "source_segment_id": None if command.source_segment_id is None else str(command.source_segment_id),
            "causal_event_id": None if command.causal_event_id is None else str(command.causal_event_id),
            "create_student_interaction": command.create_student_interaction,
            "interaction_kind": command.interaction_kind,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _result_status_value(result_status: StudioEventResultStatus | str) -> str:
        try:
            return StudioEventResultStatus(result_status).value
        except ValueError as error:
            allowed = ", ".join(status.value for status in StudioEventResultStatus)
            raise StudioStateError(f"Studio event result status must be one of: {allowed}.") from error


class AppendStudioEventResult:
    """Committed (or idempotently replayed) result of one Studio append."""

    def __init__(
        self,
        event: StudioEvent,
        snapshot: StudioSnapshot,
        scene: StudioScene | None,
        interaction: StudioStudentInteraction | None,
        *,
        replayed: bool,
    ) -> None:
        self.event = event
        self.snapshot = snapshot
        self.scene = scene
        self.interaction = interaction
        self.replayed = replayed
