"""Canvas Specialist domain handler; queue mechanics stay in the generic worker."""
from __future__ import annotations

import errno
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.factory import create_canvas_specialist_gateway
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    AIExecution,
    Job,
    JobStatus,
    LearningMessage,
    LearningSession,
    ModelTask,
    StudioCanvasSpecialistRun,
    StudioRuntime,
    StudioSnapshot,
)
from services.platform.jobs import NonRetryableJobError
from services.studio.agent.admission import AGENTIC_CANVAS_CAPABILITY_IDENTITY
from services.studio.canvas_specialist import (
    CANVAS_SPECIALIST_COMPOSE_JOB,
    frozen_pack_identity_is_valid,
    proposal_contract,
    validate_proposal_against_frozen_pack,
)
from services.studio.process_production_acceptance import (
    accept_completed_canvas_run,
    accept_completed_process_run,
)

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


_logger = logging.getLogger(__name__)

def register_canvas_specialist_handlers(registry: JobHandlerRegistry, *, session_factory: sessionmaker[Session], gateway_factory: Callable[[Session], ModelGateway] = create_canvas_specialist_gateway) -> None:
    def handle(job: Job) -> dict[str, object]:
        payload = job.payload if isinstance(job.payload, dict) else {}
        execution = _preflight(session_factory, job, payload)
        if execution is None:
            return {"run_status": "SKIPPED"}
        # Fresh session: no Phase-A database transaction/lock exists during execute.
        with session_factory() as provider_session:
            contract = proposal_contract(execution.capability_identity, execution.proposal_schema_version)
            request = {"instructions": _instructions(execution.capability_identity), "input": execution.input, "response_schema": {"name": execution.proposal_schema_version, "schema": contract.model_json_schema()}, "max_output_tokens": 1800}
            try:
                result = gateway_factory(provider_session).execute(ModelTask.CANVAS_SPECIALIST, request, lineage=AIExecutionLineage(operation="canvas_specialist_compose", operation_id=execution.run_id, student_id=execution.student_id, learning_session_id=execution.session_id, source_message_id=execution.message_id, parent_execution_id=execution.parent_execution_id))
                provider_session.commit()
            except Exception as error:
                provider_session.commit()
                failed_execution_id = provider_session.scalar(
                    select(AIExecution.id).where(
                        AIExecution.operation_id == execution.run_id,
                        AIExecution.task == ModelTask.CANVAS_SPECIALIST.value,
                    ).order_by(AIExecution.created_at.desc(), AIExecution.id.desc())
                )
                code, retryable, metadata = _classify_provider_failure(error)
                failure_metadata = {
                    "code": code,
                    "provider_attempt": execution.provider_attempt,
                    **metadata,
                }
                if retryable and execution.provider_attempt < execution.provider_max_attempts:
                    _record_retryable_failure(
                        session_factory,
                        execution.run_id,
                        failure_metadata,
                        failed_execution_id,
                    )
                    raise
                if retryable:
                    failure_metadata["retry_exhausted"] = True
                _fail(
                    session_factory,
                    execution.run_id,
                    code,
                    failed_execution_id,
                    metadata=failure_metadata,
                )
                raise NonRetryableJobError(code) from error
        try:
            validated = proposal_contract(execution.capability_identity, execution.proposal_schema_version).model_validate(result.output)
            validate_proposal_against_frozen_pack(validated, execution.pack)
            proposal = validated.model_dump(mode="json")
        except Exception as error:
            _fail(
                session_factory,
                execution.run_id,
                "PROPOSAL_VALIDATION_FAILURE",
                result.execution_id,
                metadata={
                    "code": "PROPOSAL_VALIDATION_FAILURE",
                    "exception_type": type(error).__name__,
                    "validation_detail": str(error)[:1000],
                },
            )
            raise NonRetryableJobError("Canvas Specialist proposal is invalid")
        return _settle(session_factory, execution.run_id, proposal, result.execution_id)
    registry.register(CANVAS_SPECIALIST_COMPOSE_JOB, handle)


@dataclass(frozen=True)
class SpecialistExecutionEnvelope:
    run_id: UUID; student_id: UUID; session_id: UUID; message_id: UUID; parent_execution_id: UUID | None; order_digest: str; capability_identity: str; proposal_schema_version: str; input: str; pack: dict[str, object]; provider_attempt: int; provider_max_attempts: int


def _preflight(factory: sessionmaker[Session], job: Job, payload: dict[str, object]) -> SpecialistExecutionEnvelope | None:
    with factory.begin() as session:
        claimed = session.get(Job, job.id)
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.job_id == job.id).with_for_update()).scalar_one_or_none()
        if claimed is None or claimed.job_type != CANVAS_SPECIALIST_COMPOSE_JOB or claimed.max_attempts != 2: raise ValueError("SPECIALIST_JOB_INVALID")
        if run is None or run.status in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}: return None
        if run.deadline_at and run.deadline_at <= datetime.now(UTC):
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "DEADLINE_EXCEEDED"}, datetime.now(UTC); return None
        if payload.get("order_digest") != run.order_digest or payload.get("capability_identity") != run.capability_profile_version:
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "LINEAGE_INVALID"}, datetime.now(UTC); return None
        run.status, run.started_at = "RUNNING", run.started_at or datetime.now(UTC)
        message = session.get(LearningMessage, run.source_message_id)
        learning_session = session.get(LearningSession, run.learning_session_id); runtime = session.get(StudioRuntime, run.studio_runtime_id)
        if message is None or message.role != "tutor" or message.session_id != run.learning_session_id or learning_session is None or learning_session.student_id != run.student_id or runtime is None or runtime.student_id != run.student_id or runtime.learning_session_id != run.learning_session_id: raise ValueError("SPECIALIST_LINEAGE_INVALID")
        visual = message.payload.get("workspace_visual") if message is not None and isinstance(message.payload, dict) else None
        pack = visual.get("frozen_composition_pack") if isinstance(visual, dict) else None
        if not isinstance(pack, dict) or visual.get("status") != "ADMITTED" or visual.get("order_digest") != run.order_digest or sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() != run.order_digest:
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "FROZEN_PACK_INVALID"}, datetime.now(UTC); return None
        try:
            proposal_contract(run.capability_profile_version, run.output_schema_version)
        except ValueError:
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "CAPABILITY_IDENTITY_INVALID"}, datetime.now(UTC); return None
        if not isinstance(pack.get("capability_pack"), dict) or pack["capability_pack"].get("identity") != run.capability_profile_version or not frozen_pack_identity_is_valid(pack, run.capability_profile_version):
            run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": "CAPABILITY_IDENTITY_INVALID"}, datetime.now(UTC); return None
        return SpecialistExecutionEnvelope(run.id, run.student_id, run.learning_session_id, run.source_message_id, message.ai_execution_id, run.order_digest, run.capability_profile_version, run.output_schema_version, json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")), pack, claimed.attempt_count, claimed.max_attempts)


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
        run.proposal_payload, run.proposal_digest, run.ai_execution_id, run.status, run.completed_at, run.failure_metadata = proposal, sha256(json.dumps(proposal, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(), execution_id, "COMPLETED", datetime.now(UTC), None
        # CS-04 fixtures and corrupt historical runtimes can legitimately lack the
        # Studio projection.  Keep the durable proposal; production acceptance
        # fails closed until the existing lifecycle has an authoritative Snapshot.
        has_snapshot = session.execute(select(StudioSnapshot.id).where(StudioSnapshot.studio_runtime_id == run.studio_runtime_id)).scalar_one_or_none() is not None
        durable_result = {"run_id": str(run.id), "run_status": run.status, "proposal_digest": run.proposal_digest, "scene_id": None}
    # Proposal durability is the boundary: acceptance is a separate short
    # deterministic transaction and may fail without erasing provider success.
    if has_snapshot:
        try:
            with factory.begin() as acceptance_session:
                scene = accept_completed_process_run(acceptance_session, run_id)
                if scene is not None:
                    durable_result["scene_id"] = str(scene.id)
        except Exception:
            # The provider result is already durable.  Scene settlement is a
            # separate deterministic effect and must never convert that result
            # into a false compose/provider failure.
            _logger.exception("Canvas Specialist Scene settlement deferred for run %s", run_id)
            _mark_scene_settlement_deferred(factory, run_id)
    with factory() as session:
        run = session.get(StudioCanvasSpecialistRun, run_id)
        if run is None:
            raise ValueError("SPECIALIST_RUN_MISSING")
        durable_result["run_status"] = run.status
        durable_result["scene_id"] = str(run.scene_id) if run.scene_id is not None else None
    return durable_result


def _mark_scene_settlement_deferred(factory: sessionmaker[Session], run_id: UUID) -> None:
    """Keep a retryable settlement failure visible without changing compose truth."""
    with factory.begin() as session:
        unguarded_run = session.get(StudioCanvasSpecialistRun, run_id)
        if unguarded_run is None:
            return
        session.execute(
            select(StudioRuntime)
            .where(StudioRuntime.id == unguarded_run.studio_runtime_id)
            .with_for_update()
        ).scalar_one()
        run = session.execute(
            select(StudioCanvasSpecialistRun)
            .where(StudioCanvasSpecialistRun.id == run_id)
            .with_for_update()
        ).scalar_one()
        if run.status == "COMPLETED" and run.scene_id is None:
            run.failure_metadata = {"code": "SCENE_SETTLEMENT_DEFERRED"}


def _record_retryable_failure(
    factory: sessionmaker[Session],
    run_id: UUID,
    metadata: dict[str, object],
    execution_id: UUID | None,
) -> None:
    with factory.begin() as session:
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one_or_none()
        if run is not None and run.status not in {"COMPLETED", "SUPERSEDED", "CANCELLED", "REJECTED"}:
            run.status = "PENDING"
            run.failure_metadata = metadata
            run.ai_execution_id = execution_id
            run.completed_at = None


def _fail(factory: sessionmaker[Session], run_id: UUID, code: str, execution_id: UUID | None = None, *, metadata: dict[str, object] | None = None) -> None:
    with factory.begin() as session:
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one_or_none()
        if run is not None and run.status not in {"COMPLETED", "SUPERSEDED", "CANCELLED", "REJECTED"}:
            run.status, run.failure_metadata, run.completed_at, run.ai_execution_id = "FAILED", metadata or {"code": code}, datetime.now(UTC), execution_id


def _classify_provider_failure(error: Exception) -> tuple[str, bool, dict[str, object]]:
    if isinstance(error, HTTPError):
        status = int(error.code)
        if status == 429:
            return "RATE_LIMIT", True, {"http_status": status}
        if 500 <= status <= 599:
            return "PROVIDER_SERVICE_FAILURE", True, {"http_status": status}
        return "OTHER", False, {"http_status": status}
    if isinstance(error, (TimeoutError, ConnectionError, URLError)):
        return "TRANSIENT_PROVIDER_FAILURE", True, {}
    if isinstance(error, OSError) and error.errno in {
        errno.ECONNABORTED, errno.ECONNRESET, errno.ETIMEDOUT, errno.EPIPE,
    }:
        return "TRANSIENT_PROVIDER_FAILURE", True, {"errno": int(error.errno)}
    return "OTHER", False, {"exception_type": type(error).__name__}


def reconcile_canvas_specialist_runs(session: Session, *, now: datetime | None = None) -> int:
    """Close queue/handler crash windows without ever creating another model call.

    A completed durable proposal can repair a lost queue completion only after the
    worker lease expires. A run without a durable proposal after its bounded final
    attempt becomes an explicit terminal outcome rather than claimable again.
    """
    clock = now or datetime.now(UTC)
    changed = 0
    # Do not bulk-lock Runs here: Scene acceptance/admission use Runtime ->
    # Run.  Candidate IDs are intentionally unlocked; each candidate is then
    # re-read under that same canonical order.
    run_ids = session.scalars(
        select(StudioCanvasSpecialistRun.id)
        .where(StudioCanvasSpecialistRun.status.in_(("PENDING", "RUNNING", "COMPLETED")))
    ).all()
    for run_id in run_ids:
        unguarded_run = session.get(StudioCanvasSpecialistRun, run_id)
        if unguarded_run is None:
            continue
        runtime = session.execute(
            select(StudioRuntime)
            .where(StudioRuntime.id == unguarded_run.studio_runtime_id)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if runtime is None:
            continue
        run = session.execute(
            select(StudioCanvasSpecialistRun)
            .where(StudioCanvasSpecialistRun.id == run_id)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if run is None:
            continue
        job = session.get(Job, run.job_id, with_for_update=True) if run.job_id is not None else None
        if run.status == "COMPLETED":
            has_snapshot = session.execute(select(StudioSnapshot.id).where(StudioSnapshot.studio_runtime_id == run.studio_runtime_id)).scalar_one_or_none() is not None
            if run.scene_id is None and isinstance(run.proposal_payload, dict) and has_snapshot:
                if run.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY:
                    try:
                        accept_completed_canvas_run(session, run.id)
                    except Exception:
                        _logger.exception("Agentic Canvas reconciliation deferred Scene settlement for run %s", run.id)
                        run.failure_metadata = {"code": "SCENE_SETTLEMENT_DEFERRED"}
                        continue
                else:
                    try:
                        accept_completed_process_run(session, run.id)
                    except Exception:
                        _logger.exception("Canvas Specialist reconciliation deferred Scene settlement for run %s", run.id)
                        run.failure_metadata = {"code": "SCENE_SETTLEMENT_DEFERRED"}
                        continue
            if job is not None and (
                job.status == JobStatus.FAILED.value
                or (job.status == JobStatus.RUNNING.value and job.lease_expires_at is not None and job.lease_expires_at <= clock)
            ):
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


def _instructions(capability_identity: str = "process-capability-pack-v1") -> str:
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    directory = root / "runtime/canvas-specialist"
    base = (directory / "SKILL.md").read_text()
    if capability_identity == "process-capability-pack-v2":
        return base + "\n\n" + (directory / "SKILL-v2.md").read_text() + "\n\n" + (directory / "process-capability-pack-v2.md").read_text()
    if capability_identity.startswith("canvas-"):
        return base + "\n\n" + (directory / "canvas-production-capability-pack-v1.md").read_text()
    return base + "\n\n" + (directory / "process-capability-pack-v1.md").read_text()
