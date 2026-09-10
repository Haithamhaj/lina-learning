"""Worker handler for the additive Tutor-led Agentic Canvas run type."""
from __future__ import annotations

import asyncio
import errno
import logging
from datetime import UTC, datetime
from time import perf_counter
from urllib.error import HTTPError, URLError

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from agents.tracing import gen_trace_id
from agents.exceptions import ModelBehaviorError

from services.platform.config.settings import Settings
from services.platform.db.models import (
    AIExecution,
    Job,
    LearningMessage,
    StudioCanvasSpecialistRun,
    StudioRuntime,
    StudioScene,
    StudioSnapshot,
)
from services.platform.jobs import NonRetryableJobError
from services.platform.storage import ObjectStorage
from services.studio.agent.admission import (
    AGENTIC_CANVAS_CAPABILITY_IDENTITY,
    AGENTIC_CANVAS_COMPOSE_JOB,
    AGENTIC_CANVAS_SCENE_SCHEMA_VERSION,
    _canonical_digest,
    latest_admitted_agentic_message,
)
from services.studio.agent.orchestrator import (
    AgenticCanvasCompositionResult,
    HostedGeneratedImage,
    compose_canvas_scene_with_trace,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV1
from services.studio.canvas_brief import (
    CanvasBriefContractError,
    CanvasBriefV1,
    parse_canvas_brief,
)
from services.studio.generated_assets import (
    GeneratedAssetValidationError,
    adopt_generated_image,
    resolve_generated_image_handles,
)
from services.studio.process_production_acceptance import accept_completed_canvas_run

_logger = logging.getLogger(__name__)


def register_agentic_canvas_handlers(
    registry,
    *,
    session_factory: sessionmaker[Session],
    compose=compose_canvas_scene_with_trace,
    settings_factory=Settings,
    storage: ObjectStorage | None = None,
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
            composition = asyncio.run(compose(
                brief=execution.brief,
                api_key=settings.model_api_key.get_secret_value(),
                model=settings.model_name,
                base_url=settings.model_base_url,
                sdk_trace_id=execution.sdk_trace_id,
            ))
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
        if isinstance(composition, AgenticCanvasCompositionResult):
            if composition.sdk_trace_id != execution.sdk_trace_id or composition.model != settings.model_name:
                _fail(session_factory, execution.run_id, "AGENT_TRACE_INVALID")
                raise NonRetryableJobError("AGENT_TRACE_INVALID")
            scene = composition.scene
            generated_images = composition.generated_images
            agent_trace = composition.execution_metadata()
        else:
            # Deterministic fixtures may retain the historical Scene-only seam.
            scene = composition
            generated_images = ()
            agent_trace = {"selected_tools": [], "tool_call_count": 0}
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
        durable_result: dict[str, object]
        try:
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
                post_brief = _matching_audited_brief(audit, run)
                active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == run.studio_runtime_id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
                newest = latest_admitted_agentic_message(
                    session,
                    learning_session_id=run.learning_session_id,
                )
                if (run.status != "RUNNING" or (run.deadline_at is not None and run.deadline_at <= datetime.now(UTC))
                        or post_brief is None
                        or (active is None and (run.base_scene_id is not None or run.base_scene_version != 0))
                        or (active is not None and (active.id != run.base_scene_id or active.scene_version != run.base_scene_version))
                        or newest is None or newest.id != execution.message_id):
                    run.status, run.failure_metadata, run.completed_at = "REJECTED", {"code": "STALE_AGENTIC_CANVAS_RESULT"}, datetime.now(UTC)
                    return {"run_id": str(run.id), "run_status": run.status}
                if generated_images and storage is None:
                    raise GeneratedAssetValidationError("Hosted images require configured owned object storage.")
                scene = _adopt_hosted_images(
                    session,
                    storage=storage,
                    run=run,
                    brief=execution.brief,
                    scene=scene,
                    generated_images=generated_images,
                ) if generated_images else scene
                latency_ms = round((perf_counter() - started) * 1000)
                usage = composition.usage if isinstance(composition, AgenticCanvasCompositionResult) else {}
                cached_input_tokens = int(usage.get("cached_input_tokens", 0)) if usage else None
                aggregate_input_tokens = int(usage.get("input_tokens", 0)) if usage else None
                ai_execution = AIExecution(
                    task="canvas_agent_orchestration",
                    provider="openai-agents-sdk",
                    model=settings.model_name,
                    input_tokens=(
                        max(aggregate_input_tokens - (cached_input_tokens or 0), 0)
                        if aggregate_input_tokens is not None
                        else None
                    ),
                    cached_input_tokens=cached_input_tokens,
                    cache_write_tokens=None,
                    output_tokens=int(usage.get("output_tokens", 0)) if usage else None,
                    latency_ms=latency_ms,
                    estimated_cost_usd=None,
                    success=True,
                    failure_code=None,
                    operation_id=run.id,
                    operation_type="agentic_canvas_compose",
                    parent_execution_id=execution.parent_execution_id,
                    student_id=execution.student_id,
                    learning_session_id=execution.session_id,
                    source_message_id=execution.message_id,
                    source_candidate_event_ids=[],
                )
                session.add(ai_execution)
                session.flush()
                proposal = scene.model_dump(mode="json")
                proposal_digest = _canonical_digest(proposal)
                if isinstance(composition, AgenticCanvasCompositionResult):
                    agent_trace = {
                        key: value
                        for key, value in agent_trace.items()
                        if key != "sdk_trace_id"
                    }
                    agent_trace.update({"latency_ms": latency_ms, "proposal_digest": proposal_digest})
                    run.agent_execution_metadata = agent_trace
                run.proposal_payload, run.proposal_digest, run.ai_execution_id, run.status, run.completed_at, run.failure_metadata = proposal, proposal_digest, ai_execution.id, "COMPLETED", datetime.now(UTC), None
                has_snapshot = session.execute(
                    select(StudioSnapshot.id).where(
                        StudioSnapshot.studio_runtime_id == run.studio_runtime_id
                    )
                ).scalar_one_or_none() is not None
                durable_result = {
                    "run_id": str(run.id),
                    "run_status": run.status,
                    "scene_contract": scene.version,
                    "proposal_digest": proposal_digest,
                    "scene_id": None,
                    "agent_trace": agent_trace,
                }
        except GeneratedAssetValidationError as error:
            _fail(
                session_factory,
                execution.run_id,
                "GENERATED_ASSET_INVALID",
                metadata={"code": "GENERATED_ASSET_INVALID", "exception_type": type(error).__name__},
            )
            raise NonRetryableJobError("GENERATED_ASSET_INVALID") from error
        # The provider result is durable before this short deterministic
        # settlement transaction. Reconciliation remains crash-window repair.
        if has_snapshot:
            try:
                with session_factory.begin() as acceptance_session:
                    accepted = accept_completed_canvas_run(acceptance_session, execution.run_id)
                    if accepted is not None:
                        durable_result["scene_id"] = str(accepted.id)
            except Exception:
                _logger.exception(
                    "Agentic Canvas Scene settlement deferred for run %s",
                    execution.run_id,
                )
                _mark_scene_settlement_deferred(session_factory, execution.run_id)
        with session_factory() as session:
            settled_run = session.get(StudioCanvasSpecialistRun, execution.run_id)
            if settled_run is None:
                raise ValueError("AGENTIC_CANVAS_RUN_MISSING")
            durable_result["run_status"] = settled_run.status
            durable_result["scene_id"] = (
                str(settled_run.scene_id) if settled_run.scene_id is not None else None
            )
        return durable_result
    registry.register(AGENTIC_CANVAS_COMPOSE_JOB, handle)


def _adopt_hosted_images(
    session: Session,
    *,
    storage: ObjectStorage,
    run: StudioCanvasSpecialistRun,
    brief: CanvasBriefV1,
    scene: AgenticCanvasSceneV1,
    generated_images: tuple[HostedGeneratedImage, ...],
) -> AgenticCanvasSceneV1:
    """Adopt ephemeral SDK bytes and expose only owned asset IDs to the Scene."""

    if len(generated_images) != 1 or len(scene.blocks) >= 12:
        raise GeneratedAssetValidationError("Generated image output cannot fit the bounded Canvas scene.")
    block_id = "generated-image"
    if any(block.block_id == block_id for block in scene.blocks):
        raise GeneratedAssetValidationError("Generated image block identity conflicts with the composed scene.")
    output = generated_images[0]
    resolution = adopt_generated_image(
        session,
        storage=storage,
        run=run,
        temporary_handle=output.temporary_handle,
        content=output.content,
        content_type=output.content_type,
    )
    draft = scene.model_dump(mode="json")
    draft["blocks"].append({
        "block_id": block_id,
        "type": "IMAGE",
        "meaning": brief.requested_representation,
        "title": "Generated visual",
        "accessibility": {
            "text_equivalent": brief.requested_representation,
            "aria_label": None,
        },
        "allowed_actions": ["FOCUS"],
        "elements": [],
        "temporary_image_handle": output.temporary_handle,
    })
    resolved = resolve_generated_image_handles(draft, resolutions=[resolution])
    return AgenticCanvasSceneV1.model_validate(resolved)


class _AgenticExecutionEnvelope:
    def __init__(self, *, run_id, student_id, session_id, message_id, parent_execution_id, brief, provider_attempt: int, provider_max_attempts: int, sdk_trace_id: str) -> None:
        self.run_id = run_id
        self.student_id = student_id
        self.session_id = session_id
        self.message_id = message_id
        self.parent_execution_id = parent_execution_id
        self.brief = brief
        self.provider_attempt = provider_attempt
        self.provider_max_attempts = provider_max_attempts
        self.sdk_trace_id = sdk_trace_id


def _preflight(factory: sessionmaker[Session], job: Job) -> _AgenticExecutionEnvelope | None:
    terminal_error: str | None = None
    envelope: _AgenticExecutionEnvelope | None = None
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
            terminal_error = "RUN_STATUS_INVALID"
        elif run.deadline_at is not None and run.deadline_at <= datetime.now(UTC):
            _fail_in_session(run, "DEADLINE_EXCEEDED")
            terminal_error = "DEADLINE_EXCEEDED"
        else:
            payload = claimed.payload if isinstance(claimed.payload, dict) else {}
            if payload.get("run_kind") != AGENTIC_CANVAS_CAPABILITY_IDENTITY or payload.get("source_message_id") != str(run.source_message_id) or payload.get("brief_digest") != run.order_digest or run.output_schema_version != AGENTIC_CANVAS_SCENE_SCHEMA_VERSION:
                _fail_in_session(run, "CANVAS_BRIEF_LINEAGE_INVALID")
                terminal_error = "CANVAS_BRIEF_LINEAGE_INVALID"
            else:
                message = session.get(LearningMessage, run.source_message_id)
                audit = message.payload.get("agentic_canvas") if message is not None and isinstance(message.payload, dict) else None
                brief = _matching_audited_brief(audit, run)
                if (message is None or message.role != "tutor" or message.session_id != run.learning_session_id
                        or brief is None):
                    _fail_in_session(run, "CANVAS_BRIEF_LINEAGE_INVALID")
                    terminal_error = "CANVAS_BRIEF_LINEAGE_INVALID"
                else:
                    newest = latest_admitted_agentic_message(
                        session,
                        learning_session_id=run.learning_session_id,
                    )
                    active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == run.studio_runtime_id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
                    if newest is None or newest.id != message.id or (active is None and (run.base_scene_id is not None or run.base_scene_version != 0)) or (active is not None and (active.id != run.base_scene_id or active.scene_version != run.base_scene_version)):
                        run.status, run.failure_metadata, run.completed_at = "REJECTED", {"code": "STALE_AGENTIC_CANVAS_REQUEST"}, datetime.now(UTC)
                        terminal_error = "STALE_AGENTIC_CANVAS_REQUEST"
                    else:
                        run.status, run.started_at = "RUNNING", run.started_at or datetime.now(UTC)
                        run.sdk_trace_id = run.sdk_trace_id or gen_trace_id()
                        envelope = _AgenticExecutionEnvelope(run_id=run.id, student_id=run.student_id, session_id=run.learning_session_id, message_id=message.id, parent_execution_id=message.ai_execution_id, brief=brief, provider_attempt=claimed.attempt_count, provider_max_attempts=claimed.max_attempts, sdk_trace_id=run.sdk_trace_id)
    # Raising inside ``factory.begin()`` rolls back the terminal Run state.
    # Commit that authoritative state first, then fail the queue Job.
    if terminal_error is not None:
        raise NonRetryableJobError(terminal_error)
    return envelope


def _fail_in_session(run: StudioCanvasSpecialistRun, code: str) -> None:
    run.status, run.failure_metadata, run.completed_at = "FAILED", {"code": code}, datetime.now(UTC)


def _matching_audited_brief(audit: object, run: StudioCanvasSpecialistRun):
    """Return only the exact canonical Tutor brief admitted for this Run."""
    if not isinstance(audit, dict) or audit.get("status") != "ADMITTED":
        return None
    try:
        brief = parse_canvas_brief(audit.get("brief"))
    except CanvasBriefContractError:
        return None
    if (
        brief is None
        or brief.subject_key != run.subject_key
        or audit.get("brief_digest") != run.order_digest
        or _canonical_digest(brief.model_dump(mode="json")) != run.order_digest
    ):
        return None
    return brief


def _runtime_then_run_locked(session: Session, run_id):
    """Read the Runtime id unlocked, then acquire the shared Runtime -> Run fence."""
    unguarded_run = session.get(StudioCanvasSpecialistRun, run_id)
    if unguarded_run is None:
        return None
    runtime = session.execute(
        select(StudioRuntime)
        .where(StudioRuntime.id == unguarded_run.studio_runtime_id)
        .with_for_update()
    ).scalar_one_or_none()
    if runtime is None:
        return None
    return session.execute(
        select(StudioCanvasSpecialistRun)
        .where(StudioCanvasSpecialistRun.id == run_id)
        .with_for_update()
    ).scalar_one_or_none()


def _record_retryable_failure(factory: sessionmaker[Session], run_id, metadata: dict[str, object]) -> None:
    with factory.begin() as session:
        run = _runtime_then_run_locked(session, run_id)
        if run is not None and run.status not in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
            run.status, run.failure_metadata, run.completed_at = "PENDING", metadata, None


def _mark_scene_settlement_deferred(factory: sessionmaker[Session], run_id) -> None:
    """Expose a retryable settlement gap without changing provider truth."""

    with factory.begin() as session:
        run = _runtime_then_run_locked(session, run_id)
        if run is not None and run.status == "COMPLETED" and run.scene_id is None:
            run.failure_metadata = {"code": "SCENE_SETTLEMENT_DEFERRED"}


def _fail(factory: sessionmaker[Session], run_id, code: str, *, metadata: dict[str, object] | None = None) -> None:
    with factory.begin() as session:
        run = _runtime_then_run_locked(session, run_id)
        if run is not None and run.status not in {"COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"}:
            run.status, run.failure_metadata, run.completed_at = "FAILED", metadata or {"code": code}, datetime.now(UTC)


def _classify_agent_failure(error: Exception) -> tuple[str, bool]:
    if isinstance(error, ModelBehaviorError):
        # The provider completed but one model turn produced malformed tool or
        # final-output arguments. A fresh bounded attempt can recover without
        # weakening any application validation.
        return "AGENT_MODEL_BEHAVIOR_FAILURE", True
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
