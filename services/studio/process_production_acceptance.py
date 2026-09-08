"""Short, deterministic CS-05 settlement from a completed Specialist Run."""
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, StudioCanvasSpecialistRun, StudioRuntime, StudioScene
from services.studio.canvas_specialist import (CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
    PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY)
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from services.studio.subjects.process_production import (ACTIVITY_KEY, ACTIVITY_VERSION, PROFILE_VERSION,
    RENDERER_KEY, RENDERER_VERSION, SCENE_PAYLOAD_SCHEMA_VERSION, proposal_to_scene_seed)

class ProcessAcceptanceFailure(RuntimeError):
    pass


def accept_completed_process_run(session: Session, run_id, *, before_commit=None) -> StudioScene | None:
    """Accept one valid current completion. This makes no model call and is idempotent."""
    with session.begin_nested():
        unguarded_run = session.get(StudioCanvasSpecialistRun, run_id)
        if unguarded_run is None:
            return None
        # Match admission's Runtime -> Run lock order to avoid a new admission
        # deadlocking a settling completion.
        session.execute(select(StudioRuntime).where(StudioRuntime.id == unguarded_run.studio_runtime_id).with_for_update()).scalar_one()
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one()
        if run.scene_id is not None:
            return session.get(StudioScene, run.scene_id)
        # The generation deadline governs provider/proposal completion.  A
        # proposal already committed within that deadline remains settleable
        # after a worker crash or later reconciliation.
        completed_after_deadline = (
            run.deadline_at is not None
            and (run.completed_at is None or run.completed_at >= run.deadline_at)
        )
        if run.status != "COMPLETED" or not isinstance(run.proposal_payload, dict) or completed_after_deadline:
            if run.status == "COMPLETED":
                run.status, run.failure_metadata = "REJECTED", {"code": "STALE_OR_INCOMPLETE_ACCEPTANCE"}
            return None
        message = session.execute(select(LearningMessage).where(LearningMessage.id == run.source_message_id, LearningMessage.session_id == run.learning_session_id, LearningMessage.role == "tutor")).scalar_one_or_none()
        visual = message.payload.get("workspace_visual") if message is not None and isinstance(message.payload, dict) else None
        pack = visual.get("frozen_composition_pack") if isinstance(visual, dict) else None
        if not isinstance(pack, dict) or visual.get("status") != "ADMITTED" or visual.get("order_digest") != run.order_digest or sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() != run.order_digest:
            run.status, run.failure_metadata = "REJECTED", {"code": "CAUSAL_ORDER_STALE"}; return None
        if (run.subject_key != "PROCESS" or run.capability_profile_version != PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY
                or run.output_schema_version != CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION
                or not isinstance(pack.get("capability_pack"), dict)
                or pack["capability_pack"].get("identity") != PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY):
            run.status, run.failure_metadata = "REJECTED", {"code": "CAPABILITY_IDENTITY_INVALID"}; return None
        admitted_messages = session.scalars(
            select(LearningMessage).where(LearningMessage.session_id == run.learning_session_id, LearningMessage.role == "tutor")
            .order_by(LearningMessage.created_at.desc(), LearningMessage.id.asc())
        )
        newest = next((candidate for candidate in admitted_messages if isinstance(candidate.payload, dict)
                       and isinstance(candidate.payload.get("workspace_visual"), dict)
                       and candidate.payload["workspace_visual"].get("status") == "ADMITTED"), None)
        if newest is None or newest.id != message.id:
            run.status, run.failure_metadata = "REJECTED", {"code": "SUPERSEDED_BY_NEWER_ADMITTED_ORDER"}; return None
        active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == run.studio_runtime_id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
        if active is not None and (active.id != run.base_scene_id or active.scene_version != run.base_scene_version):
            # A result composed against a different active version cannot be safely rebased.
            run.status, run.failure_metadata = "REJECTED", {"code": "ACTIVE_SCENE_CHANGED"}; return None
        if active is None and (run.base_scene_id is not None or run.base_scene_version != 0):
            run.status, run.failure_metadata = "REJECTED", {"code": "ACTIVE_SCENE_MISSING"}; return None
        locale = pack.get("locale")
        direction = pack.get("direction")
        if not isinstance(locale, str) or not isinstance(direction, str):
            run.status, run.failure_metadata = "REJECTED", {"code": "FROZEN_LOCALE_DIRECTION_INVALID"}; return None
        seed = proposal_to_scene_seed(run.proposal_payload, pack, locale="ar" if locale.startswith("ar") else "en", direction=direction)
        state = StudioStateService(session)
        scene = state.accept_scene(CreateSceneCommand(student_id=run.student_id, learning_session_id=run.learning_session_id,
            subject_key="SCIENCE", subject_profile_version=PROFILE_VERSION, concept_keys=tuple(stage["id"] for stage in seed["stages"]),
            activity_key=ACTIVITY_KEY, artifact_type="visual-explanation", renderer_key=RENDERER_KEY, renderer_version=RENDERER_VERSION,
            activity_contract_version=ACTIVITY_VERSION, payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION, seed_payload=seed,
            accessibility_payload={"contract": "process-visual-production-v1"}, locale=locale, direction=direction,
            source_message_id=message.id, source_segment_id=message.segment_id))
        if active is not None:
            state.append_event(AppendStudioEventCommand(runtime_id=run.studio_runtime_id, student_id=run.student_id, learning_session_id=run.learning_session_id,
                event_kind="studio.scene.status_changed", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
                payload_schema_version="studio-scene-status-v1", payload={"status": "SUPERSEDED"}, scene_id=active.id,
                base_scene_version=active.scene_version, source_message_id=message.id, source_segment_id=message.segment_id,
                idempotency_key=f"process-production-supersede:{run.id}"))
        state.append_event(AppendStudioEventCommand(runtime_id=run.studio_runtime_id, student_id=run.student_id, learning_session_id=run.learning_session_id,
            event_kind="studio.scene.activated", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
            payload_schema_version="studio-scene-activated-v1", payload={}, scene_id=scene.id, base_scene_version=scene.scene_version,
            source_message_id=message.id, source_segment_id=message.segment_id, idempotency_key=f"process-production-activate:{run.id}"))
        run.scene_id, run.accepted_scene_version = scene.id, scene.scene_version
        if before_commit is not None:
            before_commit()
        return scene
