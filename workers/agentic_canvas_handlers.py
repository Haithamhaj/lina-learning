"""Worker handler for the additive Tutor-led Agentic Canvas run type."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import errno
from time import perf_counter
from urllib.error import HTTPError, URLError

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.platform.config.settings import Settings
from services.platform.db.models import AIExecution, Job, LearningMessage, StudioCanvasSpecialistRun, StudioRuntime, StudioScene
from services.platform.jobs import NonRetryableJobError
from services.studio.agent.admission import AGENTIC_CANVAS_CAPABILITY_IDENTITY, AGENTIC_CANVAS_COMPOSE_JOB, AGENTIC_CANVAS_SCENE_SCHEMA_VERSION, _canonical_digest
from services.studio.agent.orchestrator import compose_canvas_scene
from services.studio.agentic_canvas import AgenticCanvasSceneV1
from services.studio.canvas_brief import parse_canvas_brief


def register_agentic_canvas_handlers(
    registry,
    *,
    session_factory: sessionmaker[Session],
    compose=compose_canvas_scene,
    settings_factory=Settings,
) -> None:
    def handle(job: Job) -> dict[str, object]:
        execution = _preflight(session_factory, job)
        if execution is None:
            return {"run_status": "SKIPPED"}
        settings = settings_factory()
        if settings.model_api_key is None:
            _fail(session_factory, execution.run_id, "MODEL_API_KEY_MISSING")
            raise NonRetryableJobError("MODEL_API_KEY_MISSING")
        started = perf_counter()
        try:
            # Phase A committed before the remote Agent call. No Runtime/Run
            # lock or transaction remains open while the provider is running.
            scene = asyncio.run(compose(brief=execution.brief, api_key=settings.model_api_key.get_secret_value(), model=settings.model_name, base_url=settings.model_base_url))
        except Exception as error:
            code, retryable = _classify_agent_failure(error)
            metadata = {"code": code, "provider_attempt": execution.provider_attempt}
            if retryable and execution.provider_attempt < execution.provider_max_attempts:
                _record_retryable_failure(session_factory, execution.run_id, metadata)
                raise
            if retryable:
                metadata["retry_exhausted"] = True
            _fail(session_factory, execution.run_id, code, metadata=metadata)
            raise NonRetryableJobError(code) from error
        try:
            scene = AgenticCanvasSceneV1.model_validate(scene)
        except Exception as error:
            _fail(
                session_factory,
                execution.run_id,
                "AGENTIC_SCENE_INVALID",
                metadata={"code": "AGENTIC_SCENE_INVALID", "exception_type": type(error).__name__},
            )
            raise NonRetryableJobError("AGENTIC_SCENE_INVALID") from error
        with session_factory.begin() as session:
            unguarded_run = session.get(StudioCanvasSpecialistRun, execution.run_id)
            if unguarded_run is None:
                raise ValueError("AGENTIC_CANVAS_RUN_MISSING")
            # Canonical order shared with admission and legacy settlement.
            session.execute(select(StudioRuntime).where(StudioRuntime.id == unguarded_run.studio_runtime_id).with_for_update()).scalar_one()
            run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == execution.run_id).with_for_update()).scalar_one()
            if run.status in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
                return {"run_id": str(run.id), "run_status": run.status}
            message = session.get(LearningMessage, execution.message_id)
            audit = message.payload.get("agentic_canvas") if message is not None and isinstance(message.payload, dict) else None
            active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == run.studio_runtime_id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
            newest = session.scalars(select(LearningMessage).where(LearningMessage.session_id == run.learning_session_id, LearningMessage.role == "tutor").order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())).first()
            if (run.status != "RUNNING" or (run.deadline_at is not None and run.deadline_at <= datetime.now(UTC))
                    or not isinstance(audit, dict) or audit.get("status") != "ADMITTED" or audit.get("brief_digest") != run.order_digest
                    or (active is None and (run.base_scene_id is not None or run.base_scene_version != 0))
                    or (active is not None and (active.id != run.base_scene_id or active.scene_version != run.base_scene_version))
                    or newest is None or newest.id != execution.message_id):
                run.status, run.failure_metadata, run.completed_at = "REJECTED", {"code": "STALE_AGENTIC_CANVAS_RESULT"}, datetime.now(UTC)
                return {"run_id": str(run.id), "run_status": run.status}
            ai_execution = AIExecution(task="canvas_agent", provider="openai", model=settings.model_name, input_tokens=None, cached_input_tokens=None, cache_write_tokens=None, output_tokens=None, latency_ms=round((perf_counter() - started) * 1000), estimated_cost_usd=None, success=True, failure_code=None, operation_id=run.id, operation_type="agentic_canvas_compose", parent_execution_id=execution.parent_execution_id, student_id=execution.student_id, learning_session_id=execution.session_id, source_message_id=execution.message_id, source_candidate_event_ids=[])
            session.add(ai_execution)
            session.flush()
            proposal = scene.model_dump(mode="json")
            proposal_digest = _canonical_digest(proposal)
            run.proposal_payload, run.proposal_digest, run.ai_execution_id, run.status, run.completed_at, run.failure_metadata = proposal, proposal_digest, ai_execution.id, "COMPLETED", datetime.now(UTC), None
            return {"run_id": str(run.id), "run_status": run.status, "scene_contract": scene.version, "proposal_digest": proposal_digest}
    registry.register(AGENTIC_CANVAS_COMPOSE_JOB, handle)


class _AgenticExecutionEnvelope:
    def __init__(self, *, run_id, student_id, session_id, message_id, parent_execution_id, brief, provider_attempt: int, provider_max_attempts: int) -> None:
        self.run_id = run_id
        self.student_id = student_id
        self.session_id = session_id
        self.message_id = message_id
        self.parent_execution_id = parent_execution_id
        self.brief = brief
        self.provider_attempt = provider_attempt
        self.provider_max_attempts = provider_max_attempts


def _preflight(factory: sessionmaker[Session], job: Job) -> _AgenticExecutionEnvelope | None:
    with factory.begin() as session:
        claimed = session.get(Job, job.id)
        unguarded_run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.job_id == job.id)).scalar_one_or_none()
        if claimed is None or claimed.job_type != AGENTIC_CANVAS_COMPOSE_JOB or claimed.max_attempts != 2:
            raise ValueError("AGENTIC_CANVAS_JOB_INVALID")
        if unguarded_run is None or unguarded_run.capability_profile_version != AGENTIC_CANVAS_CAPABILITY_IDENTITY:
            return None
        session.execute(select(StudioRuntime).where(StudioRuntime.id == unguarded_run.studio_runtime_id).with_for_update()).scalar_one()
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == unguarded_run.id).with_for_update()).scalar_one()
        if run.status in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
            return None
        if run.status not in {"PENDING", "RUNNING"}:
            _fail_in_session(run, "RUN_STATUS_INVALID")
            raise NonRetryableJobError("RUN_STATUS_INVALID")
        if run.deadline_at is not None and run.deadline_at <= datetime.now(UTC):
            _fail_in_session(run, "DEADLINE_EXCEEDED")
            raise NonRetryableJobError("DEADLINE_EXCEEDED")
        payload = claimed.payload if isinstance(claimed.payload, dict) else {}
        if payload.get("run_kind") != AGENTIC_CANVAS_CAPABILITY_IDENTITY or payload.get("source_message_id") != str(run.source_message_id) or payload.get("brief_digest") != run.order_digest or run.output_schema_version != AGENTIC_CANVAS_SCENE_SCHEMA_VERSION:
            _fail_in_session(run, "CANVAS_BRIEF_LINEAGE_INVALID")
            raise NonRetryableJobError("CANVAS_BRIEF_LINEAGE_INVALID")
        message = session.get(LearningMessage, run.source_message_id)
        audit = message.payload.get("agentic_canvas") if message is not None and isinstance(message.payload, dict) else None
        try:
            brief = parse_canvas_brief(audit.get("brief") if isinstance(audit, dict) else None)
        except Exception:
            brief = None
        if (message is None or message.role != "tutor" or message.session_id != run.learning_session_id
                or not isinstance(audit, dict) or audit.get("status") != "ADMITTED"
                or brief is None or brief.subject_key != run.subject_key
                or audit.get("brief_digest") != run.order_digest
                or _canonical_digest(brief.model_dump(mode="json")) != run.order_digest):
            _fail_in_session(run, "CANVAS_BRIEF_LINEAGE_INVALID")
            raise NonRetryableJobError("CANVAS_BRIEF_LINEAGE_INVALID")
        newest = session.scalars(select(LearningMessage).where(LearningMessage.session_id == run.learning_session_id, LearningMessage.role == "tutor").order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())).first()
        active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == run.studio_runtime_id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
        if newest is None or newest.id != message.id or (active is None and (run.base_scene_id is not None or run.base_scene_version != 0)) or (active is not None and (active.id != run.base_scene_id or active.scene_version != run.base_scene_version)):
            run.status, run.failure_metadata, run.completed_at = "REJECTED", {"code": "STALE_AGENTIC_CANVAS_REQUEST"}, datetime.now(UTC)
            raise NonRetryableJobError("STALE_AGENTIC_CANVAS_REQUEST")
        run.status, run.started_at = "RUNNING", run.started_at or datetime.now(UTC)
        return _AgenticExecutionEnvelope(run_id=run.id, student_id=run.student_id, session_id=run.learning_session_id, message_id=message.id, parent_execution_id=message.ai_execution_id, brief=brief, provider_attempt=claimed.attempt_count, provider_max_attempts=claimed.max_attempts)


def _fail_in_session(run: StudioCanvasSpecialistRun, code: str) -> None:
    run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": code}, datetime.now(UTC)


def _record_retryable_failure(factory: sessionmaker[Session], run_id, metadata: dict[str, object]) -> None:
    with factory.begin() as session:
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one_or_none()
        if run is not None and run.status not in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
            run.status, run.failure_metadata, run.completed_at = "PENDING", metadata, None


def _fail(factory: sessionmaker[Session], run_id, code: str, *, metadata: dict[str, object] | None = None) -> None:
    with factory.begin() as session:
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one_or_none()
        if run is not None and run.status not in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
            run.status, run.failure_metadata, run.completed_at = "FAILED", metadata or {"code": code}, datetime.now(UTC)


def _classify_agent_failure(error: Exception) -> tuple[str, bool]:
    if isinstance(error, HTTPError):
        if error.code == 429:
            return "RATE_LIMIT", True
        if 500 <= error.code <= 599:
            return "PROVIDER_SERVICE_FAILURE", True
        return "AGENT_PROVIDER_FAILURE", False
    if isinstance(error, (TimeoutError, ConnectionError, URLError)):
        return "TRANSIENT_PROVIDER_FAILURE", True
    if isinstance(error, OSError) and error.errno in {errno.ECONNABORTED, errno.ECONNRESET, errno.ETIMEDOUT, errno.EPIPE}:
        return "TRANSIENT_PROVIDER_FAILURE", True
    return type(error).__name__, False
