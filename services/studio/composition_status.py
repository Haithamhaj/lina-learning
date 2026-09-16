"""Read-only, Student-owned projection of current Canvas composition work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    Job,
    LearningMessage,
    StudioCanvasSpecialistRun,
    StudioRuntime,
    StudioScene,
    StudioSnapshot,
)


VIEW_VERSION = "canvas-composition-view-v1"
_SAFE_FAILURE_CODES = {
    "CANCELLED_BY_APPLICATION",
    "SUPERSEDED_BY_NEWER_AGENTIC_CANVAS_BRIEF",
    "AGENT_MODEL_BEHAVIOR_FAILURE",
    "CUSTOM_VISUAL_CANDIDATE_MISSING",
}


@dataclass(frozen=True)
class CanvasCompositionView:
    version: str
    observed_at: datetime
    runtime_id: UUID
    run_id: UUID | None
    run_created_at: datetime | None
    source_message_id: UUID | None
    run_status: str
    job_status: str | None
    objective: str | None
    scene_id: UUID | None
    scene_ready: bool
    active_scene_id: UUID | None
    active_scene_version: int | None
    deadline_at: datetime | None
    failure_code: str | None

    def as_api_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "observed_at": self.observed_at,
            "runtime_id": self.runtime_id,
            "run_id": self.run_id,
            "run_created_at": self.run_created_at,
            "source_message_id": self.source_message_id,
            "run_status": self.run_status,
            "job_status": self.job_status,
            "objective": self.objective,
            "scene_id": self.scene_id,
            "scene_ready": self.scene_ready,
            "active_scene_id": self.active_scene_id,
            "active_scene_version": self.active_scene_version,
            "deadline_at": self.deadline_at,
            "failure_code": self.failure_code,
        }


def _objective(message: LearningMessage | None) -> str | None:
    if message is None or not isinstance(message.payload, dict):
        return None
    audit = message.payload.get("agentic_canvas")
    if not isinstance(audit, dict) or not isinstance(audit.get("brief"), dict):
        return None
    objective = audit["brief"].get("objective")
    return objective[:300] if isinstance(objective, str) else None


def _safe_failure_code(run: StudioCanvasSpecialistRun | None) -> str | None:
    if run is None or not isinstance(run.failure_metadata, dict):
        return None
    code = run.failure_metadata.get("code")
    return code if isinstance(code, str) and code in _SAFE_FAILURE_CODES else None


def load_canvas_composition_view(
    session: Session,
    *,
    student_id: UUID,
    runtime_id: UUID,
) -> CanvasCompositionView | None:
    """Project durable run, job and Scene state without mutating any resource."""

    runtime = session.execute(
        select(StudioRuntime).where(
            StudioRuntime.id == runtime_id,
            StudioRuntime.student_id == student_id,
        )
    ).scalar_one_or_none()
    if runtime is None:
        return None

    run = session.execute(
        select(StudioCanvasSpecialistRun)
        .where(
            StudioCanvasSpecialistRun.studio_runtime_id == runtime.id,
            StudioCanvasSpecialistRun.student_id == student_id,
        )
        .order_by(StudioCanvasSpecialistRun.created_at.desc(), StudioCanvasSpecialistRun.id.desc())
    ).scalars().first()
    snapshot = session.execute(
        select(StudioSnapshot).where(
            StudioSnapshot.studio_runtime_id == runtime.id,
            StudioSnapshot.student_id == student_id,
        )
    ).scalar_one_or_none()

    message = session.get(LearningMessage, run.source_message_id) if run is not None else None
    job = session.get(Job, run.job_id) if run is not None and run.job_id is not None else None
    scene = session.execute(
        select(StudioScene).where(
            StudioScene.id == run.scene_id,
            StudioScene.studio_runtime_id == runtime.id,
            StudioScene.student_id == student_id,
        )
    ).scalar_one_or_none() if run is not None and run.scene_id is not None else None

    return CanvasCompositionView(
        version=VIEW_VERSION,
        observed_at=datetime.now(UTC),
        runtime_id=runtime.id,
        run_id=None if run is None else run.id,
        run_created_at=None if run is None else run.created_at,
        source_message_id=None if run is None else run.source_message_id,
        run_status="IDLE" if run is None else run.status,
        job_status=None if job is None else job.status,
        objective=_objective(message),
        scene_id=None if scene is None else scene.id,
        scene_ready=scene is not None and scene.status in {"ACCEPTED", "ACTIVE"},
        active_scene_id=None if snapshot is None else snapshot.current_scene_id,
        active_scene_version=None if snapshot is None else snapshot.current_scene_version,
        deadline_at=None if run is None else run.deadline_at,
        failure_code=_safe_failure_code(run),
    )
