"""Admission of a validated Tutor CanvasBrief into the existing run/job lifecycle."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import Job, LearningMessage, LearningSession, StudioCanvasSpecialistRun, StudioRuntime, StudioScene
from services.platform.jobs import enqueue_job

AGENTIC_CANVAS_COMPOSE_JOB = "studio.agentic_canvas.compose.v1"
AGENTIC_CANVAS_CAPABILITY_IDENTITY = "agentic-canvas-v1"
AGENTIC_CANVAS_DEADLINE = timedelta(minutes=2)


def admit_agentic_canvas_brief(session: Session, *, student_id: UUID, learning_session_id: UUID, source_message_id: UUID) -> StudioCanvasSpecialistRun | None:
    """Schedule only a committed, safety-admitted Tutor CanvasBrief."""
    message = session.execute(select(LearningMessage).where(LearningMessage.id == source_message_id, LearningMessage.session_id == learning_session_id, LearningMessage.role == "tutor").with_for_update()).scalar_one_or_none()
    learning_session = session.get(LearningSession, learning_session_id)
    runtime = session.execute(select(StudioRuntime).where(StudioRuntime.student_id == student_id, StudioRuntime.learning_session_id == learning_session_id).with_for_update()).scalar_one_or_none()
    if message is None or learning_session is None or learning_session.student_id != student_id or runtime is None:
        return None
    audit = message.payload.get("agentic_canvas") if isinstance(message.payload, dict) else None
    if not isinstance(audit, dict) or audit.get("status") != "ADMITTED":
        return None
    digest, brief = audit.get("brief_digest"), audit.get("brief")
    if not isinstance(digest, str) or len(digest) != 64 or not isinstance(brief, dict) or not isinstance(brief.get("subject_key"), str):
        return None
    existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == message.id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY)).scalar_one_or_none()
    if existing is not None:
        return existing
    active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == runtime.id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
    job = enqueue_job(session, job_type=AGENTIC_CANVAS_COMPOSE_JOB, payload={"run_kind": AGENTIC_CANVAS_CAPABILITY_IDENTITY, "source_message_id": str(message.id), "brief_digest": digest}, idempotency_key=f"agentic-canvas:{message.id}:{digest}", max_attempts=2)
    run = StudioCanvasSpecialistRun(studio_runtime_id=runtime.id, student_id=student_id, learning_session_id=learning_session_id, source_message_id=message.id, scene_id=None, base_scene_id=None if active is None else active.id, base_scene_version=0 if active is None else active.scene_version, subject_key=brief["subject_key"], capability_profile_version=AGENTIC_CANVAS_CAPABILITY_IDENTITY, status="PENDING", job_id=job.id, output_schema_version="agentic-canvas-scene-v1", deadline_at=datetime.now(UTC) + AGENTIC_CANVAS_DEADLINE, order_digest=digest)
    session.add(run)
    session.flush()
    return run
