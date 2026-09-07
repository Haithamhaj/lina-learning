"""Canvas Specialist domain handler; queue mechanics stay in the generic worker."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.factory import create_canvas_specialist_gateway
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import AIExecution, Job, JobStatus, LearningMessage, LearningSession, ModelTask, StudioCanvasSpecialistRun, StudioRuntime, StudioSnapshot
from services.studio.canvas_specialist import CANVAS_SPECIALIST_COMPOSE_JOB, CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION, PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY, CanvasSpecialistProcessProposal, validate_proposal_against_frozen_pack
from services.studio.process_production_acceptance import accept_completed_process_run

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


def register_canvas_specialist_handlers(registry: "JobHandlerRegistry", *, session_factory: sessionmaker[Session], gateway_factory: Callable[[Session], ModelGateway] = create_canvas_specialist_gateway) -> None:
    def handle(job: Job) -> dict[str, object]:
        payload = job.payload if isinstance(job.payload, dict) else {}
        execution = _preflight(session_factory, job, payload)
        if execution is None:
            return {"run_status": "SKIPPED"}
        # Fresh session: no Phase-A database transaction/lock exists during execute.
        with session_factory() as provider_session:
            request = {"instructions": _instructions(), "input": execution.input, "response_schema": {"name": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION, "schema": CanvasSpecialistProcessProposal.model_json_schema()}, "max_output_tokens": 1800}
            try:
                result = gateway_factory(provider_session).execute(ModelTask.CANVAS_SPECIALIST, request, lineage=AIExecutionLineage(operation="canvas_specialist_compose", operation_id=execution.run_id, student_id=execution.student_id, learning_session_id=execution.session_id, source_message_id=execution.message_id, parent_execution_id=execution.parent_execution_id))
                provider_session.commit()
            except Exception:
                provider_session.commit()
                failed_execution_id = provider_session.scalar(
                    select(AIExecution.id).where(
                        AIExecution.operation_id == execution.run_id,
                        AIExecution.task == ModelTask.CANVAS_SPECIALIST.value,
                    )
                )
                _fail(session_factory, execution.run_id, "PROVIDER_FAILURE", failed_execution_id)
                raise
        try:
            validated = CanvasSpecialistProcessProposal.model_validate(result.output)
            validate_proposal_against_frozen_pack(validated, execution.pack)
            proposal = validated.model_dump(mode="json")
        except Exception:
            _fail(session_factory, execution.run_id, "PROPOSAL_INVALID", result.execution_id)
            raise ValueError("Canvas Specialist proposal is invalid")
        return _settle(session_factory, execution.run_id, proposal, result.execution_id)
    registry.register(CANVAS_SPECIALIST_COMPOSE_JOB, handle)


@dataclass(frozen=True)
class SpecialistExecutionEnvelope:
    run_id: UUID; student_id: UUID; session_id: UUID; message_id: UUID; parent_execution_id: UUID | None; order_digest: str; capability_identity: str; proposal_schema_version: str; input: str; pack: dict[str, object]


def _preflight(factory: sessionmaker[Session], job: Job, payload: dict[str, object]) -> SpecialistExecutionEnvelope | None:
    with factory.begin() as session:
        claimed = session.get(Job, job.id)
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.job_id == job.id).with_for_update()).scalar_one_or_none()
        if claimed is None or claimed.job_type != CANVAS_SPECIALIST_COMPOSE_JOB or claimed.max_attempts != 1: raise ValueError("SPECIALIST_JOB_INVALID")
        if run is None or run.status in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}: return None
        if run.deadline_at and run.deadline_at <= datetime.now(UTC):
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "DEADLINE_EXCEEDED"}, datetime.now(UTC); return None
        if payload.get("order_digest") != run.order_digest or payload.get("capability_identity") != PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY:
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "LINEAGE_INVALID"}, datetime.now(UTC); return None
        run.status, run.started_at = "RUNNING", run.started_at or datetime.now(UTC)
        message = session.get(LearningMessage, run.source_message_id)
        learning_session = session.get(LearningSession, run.learning_session_id); runtime = session.get(StudioRuntime, run.studio_runtime_id)
        if message is None or message.role != "tutor" or message.session_id != run.learning_session_id or learning_session is None or learning_session.student_id != run.student_id or runtime is None or runtime.student_id != run.student_id or runtime.learning_session_id != run.learning_session_id: raise ValueError("SPECIALIST_LINEAGE_INVALID")
        visual = message.payload.get("workspace_visual") if message is not None and isinstance(message.payload, dict) else None
        pack = visual.get("frozen_composition_pack") if isinstance(visual, dict) else None
        if not isinstance(pack, dict) or visual.get("status") != "ADMITTED" or visual.get("order_digest") != run.order_digest or sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() != run.order_digest:
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "FROZEN_PACK_INVALID"}, datetime.now(UTC); return None
        return SpecialistExecutionEnvelope(run.id, run.student_id, run.learning_session_id, run.source_message_id, message.ai_execution_id, run.order_digest, PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY, run.output_schema_version, json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")), pack)


def _settle(factory: sessionmaker[Session], run_id: UUID, proposal: dict[str, object], execution_id: UUID | None) -> dict[str, object]:
    durable_result: dict[str, object]
    with factory.begin() as session:
        unguarded_run = session.get(StudioCanvasSpecialistRun, run_id)
        if unguarded_run is None:
            raise ValueError("SPECIALIST_RUN_MISSING")
        # Canonical order shared with admission and acceptance: Runtime -> Run.
        session.execute(select(StudioRuntime).where(StudioRuntime.id == unguarded_run.studio_runtime_id).with_for_update()).scalar_one()
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one()
        if run.status in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
            if run.ai_execution_id is None and execution_id is not None:
                run.ai_execution_id = execution_id
            return {"run_id": str(run.id), "run_status": run.status}
        if run.deadline_at and run.deadline_at <= datetime.now(UTC):
            run.status = "FAILED"
            run.failure_metadata = {"code": "DEADLINE_EXCEEDED_AFTER_PROVIDER"}
            run.completed_at = datetime.now(UTC)
            run.ai_execution_id = execution_id
            return {"run_id": str(run.id), "run_status": run.status}
        run.proposal_payload, run.proposal_digest, run.ai_execution_id, run.status, run.completed_at = proposal, sha256(json.dumps(proposal, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(), execution_id, "COMPLETED", datetime.now(UTC)
        # CS-04 fixtures and corrupt historical runtimes can legitimately lack the
        # Studio projection.  Keep the durable proposal; production acceptance
        # fails closed until the existing lifecycle has an authoritative Snapshot.
        has_snapshot = session.execute(select(StudioSnapshot.id).where(StudioSnapshot.studio_runtime_id == run.studio_runtime_id)).scalar_one_or_none() is not None
        durable_result = {"run_id": str(run.id), "run_status": run.status, "proposal_digest": run.proposal_digest, "scene_id": None}
    # Proposal durability is the boundary: acceptance is a separate short
    # deterministic transaction and may fail without erasing provider success.
    if has_snapshot:
        with factory.begin() as acceptance_session:
            scene = accept_completed_process_run(acceptance_session, run_id)
            if scene is not None:
                durable_result["scene_id"] = str(scene.id)
    return durable_result


def _fail(factory: sessionmaker[Session], run_id: UUID, code: str, execution_id: UUID | None = None) -> None:
    with factory.begin() as session:
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one_or_none()
        if run is not None and run.status not in {"COMPLETED", "SUPERSEDED", "CANCELLED", "REJECTED"}:
            run.status, run.failure_metadata, run.completed_at, run.ai_execution_id = "FAILED", {"code": code}, datetime.now(UTC), execution_id


def reconcile_canvas_specialist_runs(session: Session, *, now: datetime | None = None) -> int:
    """Close queue/handler crash windows without ever creating another model call.

    A completed durable proposal can repair a lost queue completion only after the
    worker lease expires. A run without a durable proposal after its sole attempt
    becomes an explicit terminal outcome rather than becoming claimable again.
    """
    clock = now or datetime.now(UTC)
    changed = 0
    runs = session.scalars(
        select(StudioCanvasSpecialistRun)
        .where(StudioCanvasSpecialistRun.status.in_(("PENDING", "RUNNING", "COMPLETED")))
        .with_for_update(skip_locked=True)
    )
    for run in runs:
        job = session.get(Job, run.job_id, with_for_update=True) if run.job_id is not None else None
        if run.status == "COMPLETED":
            if job is not None and job.status == JobStatus.RUNNING.value and job.lease_expires_at is not None and job.lease_expires_at <= clock:
                job.status = JobStatus.COMPLETED.value
                job.result = {"run_id": str(run.id), "run_status": run.status, "proposal_digest": run.proposal_digest}
                job.completed_at = clock
                job.lease_token = None
                job.lease_expires_at = None
                job.last_error = None
                changed += 1
            continue
        if job is None:
            code = "JOB_ORPHANED"
        elif job.status == JobStatus.FAILED.value:
            code = "JOB_TERMINAL_FAILURE"
        elif job.status == JobStatus.RUNNING.value and job.attempt_count >= job.max_attempts and job.lease_expires_at is not None and job.lease_expires_at <= clock:
            code = "LEASE_EXPIRED_OUTCOME_UNKNOWN"
        else:
            continue
        run.status = "FAILED"
        run.failure_metadata = {"code": code}
        run.completed_at = clock
        if job is not None and job.status == JobStatus.RUNNING.value:
            job.status = JobStatus.FAILED.value
            job.completed_at = clock
            job.lease_token = None
            job.lease_expires_at = None
            job.last_error = "Canvas Specialist final attempt reached a terminal outcome without a proposal."
        changed += 1
    return changed


def _instructions() -> str:
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    return (root / "runtime/canvas-specialist/SKILL.md").read_text() + "\n\n" + (root / "runtime/canvas-specialist/process-capability-pack-v1.md").read_text()
