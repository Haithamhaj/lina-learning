"""Worker handler for the additive Tutor-led Agentic Canvas run type."""
from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.platform.config.settings import Settings
from services.platform.db.models import AIExecution, Job, LearningMessage, StudioCanvasSpecialistRun
from services.platform.jobs import NonRetryableJobError
from services.studio.agent.admission import AGENTIC_CANVAS_CAPABILITY_IDENTITY, AGENTIC_CANVAS_COMPOSE_JOB
from services.studio.agent.orchestrator import compose_canvas_scene
from services.studio.canvas_brief import parse_canvas_brief


def register_agentic_canvas_handlers(registry, *, session_factory: sessionmaker[Session]) -> None:
    def handle(job: Job) -> dict[str, object]:
        with session_factory.begin() as session:
            run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.job_id == job.id).with_for_update()).scalar_one_or_none()
            if run is None or run.capability_profile_version != AGENTIC_CANVAS_CAPABILITY_IDENTITY or run.status != "PENDING":
                return {"run_status": "SKIPPED"}
            message = session.get(LearningMessage, run.source_message_id)
            audit = message.payload.get("agentic_canvas") if message is not None and isinstance(message.payload, dict) else None
            if not isinstance(audit, dict) or audit.get("status") != "ADMITTED" or audit.get("brief_digest") != run.order_digest:
                run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "CANVAS_BRIEF_LINEAGE_INVALID"}, datetime.now(UTC)
                raise NonRetryableJobError("CANVAS_BRIEF_LINEAGE_INVALID")
            brief = parse_canvas_brief(audit.get("brief"))
            if brief is None or brief.subject_key != run.subject_key:
                run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "CANVAS_BRIEF_INVALID"}, datetime.now(UTC)
                raise NonRetryableJobError("CANVAS_BRIEF_INVALID")
            run.status, run.started_at = "RUNNING", datetime.now(UTC)
            run_id, student_id, session_id, message_id, parent_execution_id = run.id, run.student_id, run.learning_session_id, message.id, message.ai_execution_id
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            _fail(session_factory, run_id, "OPENAI_API_KEY_MISSING")
            raise NonRetryableJobError("OPENAI_API_KEY_MISSING")
        settings, started = Settings(), perf_counter()
        try:
            scene = asyncio.run(compose_canvas_scene(brief=brief, api_key=key, model=settings.model_name, base_url=settings.model_base_url))
        except Exception as error:
            _fail(session_factory, run_id, type(error).__name__)
            raise
        with session_factory.begin() as session:
            run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one()
            execution = AIExecution(task="canvas_agent", provider="openai", model=settings.model_name, input_tokens=None, cached_input_tokens=None, cache_write_tokens=None, output_tokens=None, latency_ms=round((perf_counter() - started) * 1000), estimated_cost_usd=None, success=True, failure_code=None, operation_id=run.id, operation_type="agentic_canvas_compose", parent_execution_id=parent_execution_id, student_id=student_id, learning_session_id=session_id, source_message_id=message_id, source_candidate_event_ids=[])
            session.add(execution)
            session.flush()
            run.proposal_payload, run.proposal_digest, run.ai_execution_id, run.status, run.completed_at, run.failure_metadata = scene.model_dump(mode="json"), run.order_digest, execution.id, "COMPLETED", datetime.now(UTC), None
            return {"run_id": str(run.id), "run_status": run.status, "scene_contract": scene.version}
    registry.register(AGENTIC_CANVAS_COMPOSE_JOB, handle)


def _fail(factory: sessionmaker[Session], run_id, code: str) -> None:
    with factory.begin() as session:
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one_or_none()
        if run is not None:
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": code}, datetime.now(UTC)
