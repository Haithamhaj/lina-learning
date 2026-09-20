"""Admission of a validated Tutor CanvasBrief into the existing run/job lifecycle."""
from __future__ import annotations

import json
from collections.abc import Mapping
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
    StudioSnapshot,
)
from services.platform.jobs import enqueue_job
from services.studio.canvas_brief import CanvasBriefContractError, parse_canvas_brief
from services.tutor.candidate_events import (
    TUTOR_TURN_SCHEMA_VERSIONS_WITH_CANVAS_CHANGE_INTENT,
)

AGENTIC_CANVAS_COMPOSE_JOB = "studio.agentic_canvas.compose.v1"
AGENTIC_CANVAS_CAPABILITY_IDENTITY = "agentic-canvas-v1"
# A bounded CREATE may legitimately use registry inspection, exact truth tools,
# package construction, and a final plan.  Keep the deadline finite but long
# enough for one such provider turn to settle.
AGENTIC_CANVAS_DEADLINE = timedelta(minutes=5)
AGENTIC_CANVAS_SCENE_SCHEMA_VERSION = "agentic-canvas-scene-v3"
_CANVAS_CHANGE_INTENTS = frozenset({"CREATE", "REPLACE_PENDING", "REPLACE_SCENE", "RETRY"})
CANVAS_DECISION_BASE_VERSION = "canvas-decision-base-v1"
_FAILED_RUN_STATUSES = frozenset({"FAILED", "REJECTED", "CANCELLED"})


def _canonical_digest(value: dict[str, object]) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def capture_canvas_decision_base(studio_context: object | None) -> dict[str, object] | None:
    """Freeze the minimal server-owned Canvas truth selected before inference."""

    if studio_context is None:
        return None
    composition = getattr(studio_context, "canvas_composition", None)
    composition = composition if isinstance(composition, Mapping) else {}
    run_id = composition.get("run_id")
    run_status = composition.get("run_status")
    scene_id = getattr(studio_context, "current_scene_id", None)
    return {
        "version": CANVAS_DECISION_BASE_VERSION,
        "expected_run_id": str(run_id) if run_id is not None else None,
        "expected_run_status": run_status if isinstance(run_status, str) else None,
        "expected_scene_id": str(scene_id) if scene_id is not None else None,
        "expected_scene_version": getattr(studio_context, "current_scene_version", None),
    }


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _reject_stale_base(message: LearningMessage) -> None:
    payload = dict(message.payload) if isinstance(message.payload, dict) else {}
    audit = dict(payload.get("agentic_canvas")) if isinstance(payload.get("agentic_canvas"), dict) else {}
    audit["status"] = "REJECTED"
    audit["reason_code"] = "STALE_BASE"
    payload["agentic_canvas"] = audit
    message.payload = payload


def _decision_base_is_current(
    session: Session,
    *,
    runtime: StudioRuntime,
    intent: str,
    base: object,
) -> bool:
    if not isinstance(base, dict) or base.get("version") != CANVAS_DECISION_BASE_VERSION:
        return False
    expected_run_id = _uuid_or_none(base.get("expected_run_id"))
    expected_run_status = base.get("expected_run_status")
    expected_scene_id = _uuid_or_none(base.get("expected_scene_id"))
    expected_scene_version = base.get("expected_scene_version")
    if base.get("expected_run_id") is not None and expected_run_id is None:
        return False
    if base.get("expected_scene_id") is not None and expected_scene_id is None:
        return False
    if expected_run_status is not None and not isinstance(expected_run_status, str):
        return False
    if expected_scene_version is not None and not isinstance(expected_scene_version, int):
        return False

    current_runs = session.execute(
        select(StudioCanvasSpecialistRun)
        .where(
            StudioCanvasSpecialistRun.studio_runtime_id == runtime.id,
            StudioCanvasSpecialistRun.student_id == runtime.student_id,
        )
        .order_by(StudioCanvasSpecialistRun.created_at.desc())
        .limit(2)
        .with_for_update()
    ).scalars().all()
    if len(current_runs) > 1 and current_runs[0].created_at == current_runs[1].created_at:
        # A timestamp tie has no chronological meaning. Reject safely instead
        # of treating UUID ordering as lifecycle authority.
        return False
    current_run = current_runs[0] if current_runs else None
    snapshot = session.execute(
        select(StudioSnapshot)
        .where(
            StudioSnapshot.studio_runtime_id == runtime.id,
            StudioSnapshot.student_id == runtime.student_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    current_run_id = None if current_run is None else current_run.id
    current_run_status = None if current_run is None else current_run.status
    current_scene_id = None if snapshot is None else snapshot.current_scene_id
    current_scene_version = None if snapshot is None else snapshot.current_scene_version

    if current_run_id != expected_run_id:
        return False
    if current_scene_id != expected_scene_id or current_scene_version != expected_scene_version:
        return False
    if intent == "CREATE":
        return expected_run_id is None and expected_run_status is None and expected_scene_id is None
    if intent == "REPLACE_PENDING":
        return (
            expected_run_id is not None
            and expected_run_status in {"PENDING", "RUNNING"}
            and current_run_status in {"PENDING", "RUNNING"}
        )
    if intent == "REPLACE_SCENE":
        return (
            expected_scene_id is not None
            and expected_scene_version is not None
            and current_run_status == expected_run_status
        )
    if intent == "RETRY":
        return (
            expected_run_id is not None
            and expected_run_status in _FAILED_RUN_STATUSES
            and current_run_status == expected_run_status
        )
    return False


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
    # v12+ makes the intended lifecycle transition explicit.  The admission
    # boundary enforces it too, so a caller cannot turn a status/Scene step
    # into composition merely by calling this service.  Older persisted Tutor
    # turns remain readable and replayable under their historical contract.
    if (
        message.payload.get("tutor_turn_schema_version")
        in TUTOR_TURN_SCHEMA_VERSIONS_WITH_CANVAS_CHANGE_INTENT
        and message.payload.get("canvas_change_intent") not in _CANVAS_CHANGE_INTENTS
    ):
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
    # An exact accepted source/digest replay is idempotent even though the
    # admitted Run is now the latest lifecycle state. It creates no new work.
    existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == message.id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY)).scalar_one_or_none()
    if existing is not None:
        return existing
    if (
        message.payload.get("tutor_turn_schema_version")
        in TUTOR_TURN_SCHEMA_VERSIONS_WITH_CANVAS_CHANGE_INTENT
    ):
        intent = message.payload.get("canvas_change_intent")
        if not isinstance(intent, str) or not _decision_base_is_current(
            session,
            runtime=runtime,
            intent=intent,
            base=message.payload.get("canvas_decision_base"),
        ):
            _reject_stale_base(message)
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
            run = StudioCanvasSpecialistRun(studio_runtime_id=runtime.id, student_id=student_id, learning_session_id=learning_session_id, source_message_id=message.id, scene_id=None, base_scene_id=None if active is None else active.id, base_scene_version=0 if active is None else active.scene_version, subject_key=brief.subject_key, capability_profile_version=AGENTIC_CANVAS_CAPABILITY_IDENTITY, status="PENDING", job_id=job.id, output_schema_version=AGENTIC_CANVAS_SCENE_SCHEMA_VERSION, deadline_at=clock + AGENTIC_CANVAS_DEADLINE, order_digest=digest, created_at=clock)
            session.add(run)
            session.flush()
            return run
    except IntegrityError:
        existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == message.id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY)).scalar_one_or_none()
        if existing is None:
            raise
        return existing
