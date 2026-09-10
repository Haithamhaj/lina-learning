"""Admission of a validated Tutor CanvasBrief into the existing run/job lifecycle."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.platform.db.models import (
    Job,
    LearningMessage,
    LearningSession,
    StudioCanvasSpecialistRun,
    StudioRuntime,
    StudioScene,
)
from services.platform.jobs import enqueue_job
from services.studio.canvas_brief import CanvasBriefContractError, parse_canvas_brief

AGENTIC_CANVAS_COMPOSE_JOB = "studio.agentic_canvas.compose.v1"
AGENTIC_CANVAS_CAPABILITY_IDENTITY = "agentic-canvas-v1"
AGENTIC_CANVAS_DEADLINE = timedelta(minutes=2)
AGENTIC_CANVAS_SCENE_SCHEMA_VERSION = "agentic-canvas-scene-v1"


def _canonical_digest(value: dict[str, object]) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def latest_admitted_agentic_message(
    session: Session,
    *,
    learning_session_id: UUID,
    lock: bool = False,
) -> LearningMessage | None:
    """Return the newest Tutor turn that actually requested Agentic Canvas."""

    statement = (
        select(LearningMessage)
        .where(
            LearningMessage.session_id == learning_session_id,
            LearningMessage.role == "tutor",
        )
        .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
    )
    if lock:
        statement = statement.with_for_update()
    return next(
        (
            candidate
            for candidate in session.scalars(statement)
            if isinstance(candidate.payload, dict)
            and isinstance(candidate.payload.get("agentic_canvas"), dict)
            and candidate.payload["agentic_canvas"].get("status") == "ADMITTED"
        ),
        None,
    )


def admit_agentic_canvas_brief(session: Session, *, student_id: UUID, learning_session_id: UUID, source_message_id: UUID, now: datetime | None = None) -> StudioCanvasSpecialistRun | None:
    """Atomically schedule one current, safety-admitted Tutor CanvasBrief.

    The additive Agentic path fences only unsettled compose work.  Accepted
    historical Scenes and legacy replay records remain untouched.
    """
    clock = now or datetime.now(UTC)
    learning_session = session.get(LearningSession, learning_session_id)
    if learning_session is None or learning_session.student_id != student_id:
        return None
    # Runtime -> Run is the canonical lock order shared by legacy admission,
    # settlement, and reconciliation. Lock the message only after Runtime.
    runtime = session.execute(select(StudioRuntime).where(StudioRuntime.student_id == student_id, StudioRuntime.learning_session_id == learning_session_id).with_for_update()).scalar_one_or_none()
    if runtime is None:
        return None
    message = session.execute(select(LearningMessage).where(LearningMessage.id == source_message_id, LearningMessage.session_id == learning_session_id, LearningMessage.role == "tutor").with_for_update()).scalar_one_or_none()
    if message is None:
        return None
    audit = message.payload.get("agentic_canvas") if isinstance(message.payload, dict) else None
    if not isinstance(audit, dict) or audit.get("status") != "ADMITTED":
        return None
    declared_digest, raw_brief = audit.get("brief_digest"), audit.get("brief")
    if not isinstance(declared_digest, str) or len(declared_digest) != 64:
        return None
    try:
        brief = parse_canvas_brief(raw_brief)
    except CanvasBriefContractError:
        return None
    if brief is None:
        return None
    serialized = brief.model_dump(mode="json")
    digest = _canonical_digest(serialized)
    if declared_digest != digest:
        return None
    # Only a later eligible Canvas brief supersedes this composition. Ordinary
    # Chat turns remain independent while Canvas work is in flight.
    newest = latest_admitted_agentic_message(
        session,
        learning_session_id=learning_session_id,
        lock=True,
    )
    if newest is None or newest.id != message.id:
        return None
    existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == message.id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY)).scalar_one_or_none()
    if existing is not None:
        return existing
    # Agentic and legacy compose jobs share Studio's Run boundary. A new
    # Agentic brief can supersede unfinished work, but never an accepted Scene.
    prior_runs = session.scalars(
        select(StudioCanvasSpecialistRun).where(
            StudioCanvasSpecialistRun.studio_runtime_id == runtime.id,
            StudioCanvasSpecialistRun.status.in_(("PENDING", "RUNNING", "COMPLETED")),
            StudioCanvasSpecialistRun.scene_id.is_(None),
            StudioCanvasSpecialistRun.source_message_id != message.id,
        ).with_for_update()
    )
    for prior in prior_runs:
        prior.status = "SUPERSEDED"
        prior.failure_metadata = {"code": "SUPERSEDED_BY_NEWER_AGENTIC_CANVAS_BRIEF", "successor_order_digest": digest}
        prior.completed_at = clock
        if prior.job_id is not None:
            prior_job = session.get(Job, prior.job_id, with_for_update=True)
            if prior_job is not None and prior_job.status == "PENDING":
                prior_job.status = "FAILED"
                prior_job.completed_at = clock
                prior_job.last_error = "Superseded by a newer admitted Agentic Canvas brief."
    active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == runtime.id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
    job = enqueue_job(session, job_type=AGENTIC_CANVAS_COMPOSE_JOB, payload={"run_kind": AGENTIC_CANVAS_CAPABILITY_IDENTITY, "source_message_id": str(message.id), "brief_digest": digest}, idempotency_key=f"agentic-canvas:{message.id}:{digest}", max_attempts=2)
    try:
        with session.begin_nested():
            run = StudioCanvasSpecialistRun(studio_runtime_id=runtime.id, student_id=student_id, learning_session_id=learning_session_id, source_message_id=message.id, scene_id=None, base_scene_id=None if active is None else active.id, base_scene_version=0 if active is None else active.scene_version, subject_key=brief.subject_key, capability_profile_version=AGENTIC_CANVAS_CAPABILITY_IDENTITY, status="PENDING", job_id=job.id, output_schema_version=AGENTIC_CANVAS_SCENE_SCHEMA_VERSION, deadline_at=clock + AGENTIC_CANVAS_DEADLINE, order_digest=digest)
            session.add(run)
            session.flush()
            return run
    except IntegrityError:
        existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == message.id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY)).scalar_one_or_none()
        if existing is None:
            raise
        return existing
