"""CS-04 Worker lifecycle proofs against the canonical disposable database."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ModelTask
from services.studio.canvas_specialist import CanvasSpecialistProcessProposal, admit_committed_visual_order
from services.studio.service import StudioStateService
from workers.job_worker import JobHandlerRegistry, run_once
from workers.studio_handlers import reconcile_canvas_specialist_runs, register_canvas_specialist_handlers


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, studio_canvas_specialist_runs, studio_runtimes, learning_messages, learning_sessions, students, users, ai_executions CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _admitted_run(
    session: Session,
    *,
    with_student_source: bool = False,
    production_runtime: bool = False,
) -> tuple[m.StudioCanvasSpecialistRun, m.Job]:
    user = m.User(identity_provider="cs04-worker", external_subject=uuid4().hex)
    session.add(user); session.flush()
    student = m.Student(user_id=user.id, display_name="Specialist fixture")
    session.add(student); session.flush()
    learning = m.LearningSession(student_id=student.id, subject="SCIENCE", status="OPEN")
    session.add(learning); session.flush()
    if production_runtime:
        StudioStateService(session).get_or_create_runtime(
            student_id=student.id, learning_session_id=learning.id
        )
        segment = m.LearningSegment(session_id=learning.id, sequence=1)
        session.add(segment); session.flush()
    else:
        session.add(m.StudioRuntime(student_id=student.id, learning_session_id=learning.id)); session.flush()
        segment = None
    pack = {
        "version": "frozen-composition-pack-v1",
        "pattern": "PROCESS",
        "topology": "SEQUENCE",
        "capability_pack": {"identity": "process-capability-pack-v1", "process_stage_limit": [2, 8]},
        "semantic_alignment": {"required_semantics": [{"id": "F1"}]},
        "admitted_order": {"objective": "Explain a two-stage process."},
        "grounding": {"origin": "ADMITTED_TUTOR_ORDER", "excerpts": []},
        "allowed_affordances": [],
    }
    if production_runtime:
        pack.update({"locale": "en", "direction": "ltr"})
    digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    source_message = None
    source_asset = None
    if with_student_source:
        source_message = m.LearningMessage(
            session_id=learning.id,
            segment_id=None if segment is None else segment.id,
            role="student",
            content="Please explain this source visually.",
            payload={},
        )
        session.add(source_message); session.flush()
        source_asset = m.StudentSourceAsset(
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=source_message.id,
            kind="IMAGE",
            original_filename="synthetic-source.png",
            content_type="image/png",
            size_bytes=123,
            checksum_sha256="b" * 64,
            storage_key=f"private/student-sources/{student.id}/{uuid4()}.png",
        )
        session.add(source_asset); session.flush()
        source_message.source_asset_id = source_asset.id
    parent = m.AIExecution(
        task="tutor", provider="fixture", model="gpt-5.6-luna", latency_ms=1,
        success=True, student_id=student.id, learning_session_id=learning.id,
        source_message_id=None if source_message is None else source_message.id,
        source_asset_id=None if source_asset is None else source_asset.id,
    )
    session.add(parent); session.flush()
    message = m.LearningMessage(session_id=learning.id, segment_id=None if segment is None else segment.id, role="tutor", content="Tutor", ai_execution_id=parent.id, payload={"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}})
    session.add(message); session.flush()
    run = admit_committed_visual_order(session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
    assert run is not None and run.job_id is not None
    job = session.get(m.Job, run.job_id)
    assert job is not None
    return run, job


def _valid_proposal() -> dict[str, object]:
    return {
        "version": "canvas-specialist-process-proposal-v1",
        "pattern": "PROCESS",
        "topology": "SEQUENCE",
        "title": "A two-stage process",
        "subtitle": None,
        "stages": [
            {"semantic_key": "start", "label": "Start", "detail": None, "support_ids": ["F1"], "art_handle": None},
            {"semantic_key": "finish", "label": "Finish", "detail": None, "support_ids": ["F1"], "art_handle": None},
        ],
        "relations": [{"relation_key": "next", "source_semantic_key": "start", "target_semantic_key": "finish", "label": None, "support_ids": ["F1"]}],
        "text_equivalent": "Start then finish.",
        "focus_intent": None,
        "motion_intents": [],
        "interaction_affordances": [],
    }


def test_transient_first_attempt_retries_same_run_then_settles_one_scene(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session, production_runtime=True)
        run_id, job_id = run.id, job.id
    clock = datetime.now(UTC) + timedelta(seconds=1)

    calls = 0
    inputs: list[str] = []

    class TransientThenSuccessfulProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            del route
            calls += 1
            inputs.append(str(payload["input"]))
            if calls == 1:
                raise TimeoutError("fixture provider timeout")
            return ModelResult(output=_valid_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry,
        session_factory=factory,
        gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": TransientThenSuccessfulProvider()}),
    )

    assert run_once(factory, registry, worker_id="cs04-worker", now=clock) == m.JobStatus.PENDING
    with factory() as session:
        job = session.get(m.Job, job_id)
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert job is not None and job.status == "PENDING" and job.attempt_count == 1
        assert job.max_attempts == 2 and job.run_after > clock
        assert run is not None and run.status == "PENDING"
        assert run.failure_metadata == {
            "code": "TRANSIENT_PROVIDER_FAILURE", "provider_attempt": 1,
        }
        retry_at = job.run_after

    assert run_once(
        factory, registry, worker_id="cs04-worker", now=retry_at
    ) == m.JobStatus.COMPLETED

    with factory() as session:
        job = session.get(m.Job, job_id)
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        executions = session.scalars(select(m.AIExecution).where(
            m.AIExecution.operation_id == run_id,
            m.AIExecution.task == ModelTask.CANVAS_SPECIALIST.value,
        ).order_by(m.AIExecution.created_at, m.AIExecution.id)).all()
        scenes = session.scalars(select(m.StudioScene).where(
            m.StudioScene.studio_runtime_id == run.studio_runtime_id
        )).all()
        assert job is not None and job.status == "COMPLETED"
        assert job.attempt_count == job.max_attempts == 2
        assert run is not None and run.status == "COMPLETED" and run.scene_id == scenes[0].id
        assert [execution.success for execution in executions] == [False, True]
        assert run.ai_execution_id == executions[-1].id
        assert len(scenes) == 1 and calls == 2
        assert len(inputs) == 2 and inputs[0] == inputs[1]
        assert run.failure_metadata is None


def test_invalid_generated_proposal_is_diagnostic_and_never_retried(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session, production_runtime=True)
        run_id, job_id = run.id, job.id
    calls = 0

    class InvalidProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            del route, payload
            calls += 1
            return ModelResult(output={})

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry,
        session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session,
            routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")},
            providers={"fixture": InvalidProvider()},
        ),
    )

    assert run_once(factory, registry, worker_id="invalid-proposal") == m.JobStatus.FAILED
    assert run_once(factory, registry, worker_id="invalid-proposal-retry") is None
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        job = session.get(m.Job, job_id)
        assert calls == 1
        assert job.status == "FAILED" and job.attempt_count == 1 and job.max_attempts == 2
        assert run.status == "FAILED" and run.scene_id is None and run.proposal_payload is None
        assert run.failure_metadata["code"] == "PROPOSAL_VALIDATION_FAILURE"
        assert run.failure_metadata["exception_type"] == "ValidationError"
        assert "Field required" in run.failure_metadata["validation_detail"]


def test_deadline_before_inference_is_terminal_without_provider_call(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
        run_id, job_id = run.id, job.id
    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output=_valid_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": Provider()}))
    assert run_once(factory, registry, worker_id="cs04-worker") == m.JobStatus.COMPLETED
    with factory() as session:
        assert session.get(m.StudioCanvasSpecialistRun, run_id).status == "FAILED"
        assert session.get(m.Job, job_id).status == "COMPLETED"
        assert calls == 0


def test_invalid_proposal_fails_after_one_call_without_repair_or_critic(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run_id, job_id = run.id, job.id
    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output={"not": "a proposal"})

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": Provider()}))
    assert run_once(factory, registry, worker_id="cs04-worker") == m.JobStatus.FAILED
    with factory() as session:
        assert session.get(m.StudioCanvasSpecialistRun, run_id).status == "FAILED"
        assert session.get(m.Job, job_id).status == "FAILED"
        assert calls == 1


def test_success_uses_only_frozen_input_outside_the_preflight_transaction(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run_id, job_id = run.id, job.id
        expected_input = json.dumps(
            session.get(m.LearningMessage, run.source_message_id).payload["workspace_visual"]["frozen_composition_pack"],
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    seen_inputs: list[str] = []

    class LockingProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            seen_inputs.append(str(payload["input"]))
            # This separate connection can lock the Run while inference is in
            # progress only when preflight has committed its row lock.
            with factory.begin() as session:
                assert session.execute(
                    select(m.StudioCanvasSpecialistRun)
                    .where(m.StudioCanvasSpecialistRun.id == run_id)
                    .with_for_update(nowait=True)
                ).scalar_one().id == run_id
            return ModelResult(output=_valid_proposal(), input_tokens=12, output_tokens=8, estimated_cost_usd=0.001)

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry,
        session_factory=factory,
        gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": LockingProvider()}),
    )

    assert run_once(factory, registry, worker_id="cs04-worker") == m.JobStatus.COMPLETED

    with factory() as session:
        job = session.get(m.Job, job_id)
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        execution = session.scalar(select(m.AIExecution).where(m.AIExecution.operation_id == run_id))
        assert seen_inputs == [expected_input]
        assert job is not None and job.status == "COMPLETED" and job.attempt_count == 1
        assert run is not None and run.status == "COMPLETED"
        assert run.proposal_payload == CanvasSpecialistProcessProposal.model_validate(_valid_proposal()).model_dump(mode="json")
        assert execution is not None and execution.success is True and run.ai_execution_id == execution.id


def test_source_derived_specialist_receives_only_semantic_pack_and_retains_outer_lineage(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        run, _job = _admitted_run(session, with_student_source=True)
        run_id = run.id

    seen_inputs: list[str] = []

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            seen_inputs.append(str(payload["input"]))
            return ModelResult(output=_valid_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry,
        session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session,
            routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")},
            providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="vision-02-source-semantics") == m.JobStatus.COMPLETED

    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        tutor_message = session.get(m.LearningMessage, run.source_message_id)
        tutor_execution = session.get(m.AIExecution, tutor_message.ai_execution_id)
        source_message = session.get(m.LearningMessage, tutor_execution.source_message_id)
        source_asset = session.get(m.StudentSourceAsset, tutor_execution.source_asset_id)
        assert source_message.source_asset_id == source_asset.id
        assert source_asset.source_message_id == source_message.id
        assert len(seen_inputs) == 1
        serialized = seen_inputs[0]
        for forbidden in (
            source_asset.storage_key,
            str(source_asset.id),
            str(source_message.id),
            "base64",
            "provider_file",
            "pixel",
            "bounding",
        ):
            assert forbidden not in serialized
        assert "Explain a two-stage process." in serialized


def test_expired_final_attempt_is_reconciled_without_a_second_generation(factory: sessionmaker[Session]) -> None:
    """A lost worker lease is an ambiguous terminal outcome, never a regeneration cue."""
    clock = datetime.now(UTC)
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run.status = "RUNNING"
        job.status = "RUNNING"
        job.attempt_count = job.max_attempts
        job.lease_expires_at = clock - timedelta(seconds=1)
        run_id, job_id = run.id, job.id

    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session, now=clock) == 1

    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        job = session.get(m.Job, job_id)
        assert run is not None and run.status == "FAILED"
        assert run.failure_metadata == {"code": "LEASE_EXPIRED_OUTCOME_UNKNOWN"}
        assert job is not None and job.status == "FAILED"
        assert session.scalar(select(m.AIExecution).where(m.AIExecution.task == ModelTask.CANVAS_SPECIALIST.value)) is None


def test_two_transient_failures_exhaust_bound_without_a_third_generation(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run_id, job_id = run.id, job.id
    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            del route, payload
            calls += 1
            raise ConnectionResetError("fixture reset")

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry,
        session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session,
            routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")},
            providers={"fixture": Provider()},
        ),
    )
    first_clock = datetime.now(UTC) + timedelta(seconds=1)
    assert run_once(factory, registry, worker_id="bounded-1", now=first_clock) == m.JobStatus.PENDING
    with factory() as session:
        retry_at = session.get(m.Job, job_id).run_after
    assert run_once(factory, registry, worker_id="bounded-2", now=retry_at) == m.JobStatus.FAILED
    assert run_once(factory, registry, worker_id="bounded-3", now=retry_at + timedelta(minutes=1)) is None

    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        job = session.get(m.Job, job_id)
        executions = session.scalars(select(m.AIExecution).where(
            m.AIExecution.operation_id == run_id,
            m.AIExecution.task == ModelTask.CANVAS_SPECIALIST.value,
        )).all()
        assert calls == len(executions) == 2
        assert job.status == "FAILED" and job.attempt_count == job.max_attempts == 2
        assert run.status == "FAILED"
        assert run.failure_metadata == {
            "code": "TRANSIENT_PROVIDER_FAILURE",
            "provider_attempt": 2,
            "retry_exhausted": True,
        }


def test_deterministic_frozen_pack_failure_has_zero_provider_attempts(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session)
        message = session.get(m.LearningMessage, run.source_message_id)
        payload = json.loads(json.dumps(message.payload))
        payload["workspace_visual"]["frozen_composition_pack"]["admitted_order"] = {
            "objective": "Tampered after admission."
        }
        message.payload = payload
        run_id, job_id = run.id, job.id
    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output=_valid_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session,
            routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")},
            providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="deterministic-preflight") == m.JobStatus.COMPLETED
    with factory() as session:
        assert calls == 0
        assert session.get(m.Job, job_id).attempt_count == 1
        failed = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert failed.status == "FAILED"
        assert failed.failure_metadata == {"code": "FROZEN_PACK_INVALID"}


def test_durable_proposal_reconciles_deferred_scene_without_regeneration(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    with factory.begin() as session:
        run, _job = _admitted_run(session, production_runtime=True)
        run_id = run.id
    calls = 0
    real_accept = __import__(
        "workers.studio_handlers", fromlist=["accept_completed_process_run"]
    ).accept_completed_process_run

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            del route, payload
            calls += 1
            return ModelResult(output=_valid_proposal())

    def deferred(*args, **kwargs):
        raise RuntimeError("fixture settlement interruption")

    monkeypatch.setattr("workers.studio_handlers.accept_completed_process_run", deferred)
    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session,
            routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")},
            providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="deferred-scene") == m.JobStatus.COMPLETED
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run.status == "COMPLETED" and run.scene_id is None
        assert run.proposal_payload == CanvasSpecialistProcessProposal.model_validate(_valid_proposal()).model_dump(mode="json")
        assert run.failure_metadata == {"code": "SCENE_SETTLEMENT_DEFERRED"}

    monkeypatch.setattr("workers.studio_handlers.accept_completed_process_run", real_accept)
    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session) == 0
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run.scene_id is not None
        assert session.query(m.StudioScene).filter_by(studio_runtime_id=run.studio_runtime_id).count() == 1
        assert calls == 1


def test_newer_admitted_order_supersedes_pending_work_before_provider_execution(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        older, older_job = _admitted_run(session)
        message = session.get(m.LearningMessage, older.source_message_id)
        assert message is not None
        pack = dict(message.payload["workspace_visual"]["frozen_composition_pack"])
        pack["admitted_order"] = {"objective": "Explain a newer process."}
        digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        newer_message = m.LearningMessage(
                session_id=older.learning_session_id, role="tutor", content="Newer Tutor", ai_execution_id=message.ai_execution_id,
                payload={"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}}, created_at=message.created_at + timedelta(microseconds=1),
        )
        session.add(newer_message); session.flush()
        newer = admit_committed_visual_order(
            session, student_id=older.student_id, learning_session_id=older.learning_session_id, source_message_id=newer_message.id,
        )
        assert newer is not None
        older_id, older_job_id, newer_job_id = older.id, older_job.id, newer.job_id

    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output=_valid_proposal(), input_tokens=1, output_tokens=1)

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": Provider()}),
    )
    assert run_once(factory, registry, worker_id="cs04-worker") == m.JobStatus.COMPLETED

    with factory() as session:
        old_run, old_job, new_job = session.get(m.StudioCanvasSpecialistRun, older_id), session.get(m.Job, older_job_id), session.get(m.Job, newer_job_id)
        assert old_run is not None and old_run.status == "SUPERSEDED" and old_run.proposal_payload is None
        assert old_job is not None and old_job.status == "FAILED"
        assert new_job is not None and new_job.status == "COMPLETED"
        assert calls == 1


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "SUPERSEDED", "REJECTED"])
def test_terminal_specialist_runs_never_reenter_provider(factory: sessionmaker[Session], status: str) -> None:
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run.status = status
        run_id, job_id = run.id, job.id

    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output=_valid_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": Provider()}),
    )
    assert run_once(factory, registry, worker_id="cs04-worker") == m.JobStatus.COMPLETED
    with factory() as session:
        assert session.get(m.StudioCanvasSpecialistRun, run_id).status == status
        assert session.get(m.Job, job_id).status == "COMPLETED"
        assert calls == 0


def test_completed_run_repairs_only_the_lost_queue_settlement_after_lease_expiry(factory: sessionmaker[Session]) -> None:
    """A post-handler crash closes queue bookkeeping from the durable proposal."""
    clock = datetime.now(UTC)
    with factory.begin() as session:
        run, job = _admitted_run(session)
        run.status = "COMPLETED"
        run.proposal_payload = _valid_proposal()
        run.proposal_digest = "a" * 64
        job.status = "RUNNING"
        job.attempt_count = 1
        job.lease_expires_at = clock - timedelta(seconds=1)
        run_id, job_id = run.id, job.id

    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session, now=clock) == 1

    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        job = session.get(m.Job, job_id)
        assert run is not None and run.status == "COMPLETED" and run.proposal_payload == _valid_proposal()
        assert job is not None and job.status == "COMPLETED"
        assert job.result == {"run_id": str(run_id), "run_status": "COMPLETED", "proposal_digest": "a" * 64}
