"""Durable lifecycle tests for the additive Tutor-led Agentic Canvas path."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.studio.agent.admission import (
    AGENTIC_CANVAS_CAPABILITY_IDENTITY,
    admit_agentic_canvas_brief,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV1
from workers.agentic_canvas_handlers import register_agentic_canvas_handlers
from workers.job_worker import JobHandlerRegistry, run_once

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required"
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE jobs, studio_canvas_specialist_runs, studio_scenes, "
                "studio_runtimes, learning_messages, learning_sessions, students, "
                "users, ai_executions CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


class _Settings:
    model_api_key = SecretStr("test-agentic-key")
    model_name = "test-agentic-model"
    model_base_url = None


def _brief(*, objective: str = "Compare two decimals on a number line.") -> dict[str, object]:
    return {
        "version": "canvas-brief-v1",
        "subject_key": "MATH",
        "objective": objective,
        "student_request": "Help me see which decimal is greater.",
        "requested_representation": "A number line.",
        "facts": ["0.6 is six tenths.", "0.45 is forty-five hundredths."],
        "relations": [],
        "quantities": [
            {"id": "first", "value": "0.6", "unit": None},
            {"id": "second", "value": "0.45", "unit": None},
        ],
        "desired_student_action": "Place each decimal and compare their positions.",
        "must_not_imply": ["Do not say that more digits always means a larger decimal."],
        "source_references": [],
        "locale": "en",
        "direction": "ltr",
    }


def _scene() -> AgenticCanvasSceneV1:
    return AgenticCanvasSceneV1.model_validate(
        {
            "version": "agentic-canvas-scene-v1",
            "objective": "Compare two decimals on a number line.",
            "subject_key": "MATH",
            "blocks": [
                {
                    "block_id": "decimal-line",
                    "type": "MATH_BOARD",
                    "meaning": "A number line compares the two decimal positions.",
                    "title": "Decimal positions",
                    "accessibility": {
                        "text_equivalent": "A number line containing zero point four five and zero point six.",
                        "aria_label": "Decimal comparison number line",
                    },
                    "allowed_actions": ["SELECT"],
                    "elements": [
                        {"id": "first", "label": "0.6", "current_value": "0.6"},
                        {"id": "second", "label": "0.45", "current_value": "0.45"},
                    ],
                    "board_kind": "NUMBER_LINE",
                    "axis_min": "0",
                    "axis_max": "1",
                }
            ],
        }
    )


def _admitted_message(
    session: Session,
    *,
    student: m.Student | None = None,
    learning: m.LearningSession | None = None,
    objective: str = "Compare two decimals on a number line.",
) -> tuple[m.Student, m.LearningSession, m.LearningMessage]:
    if student is None:
        user = m.User(identity_provider="agentic-lifecycle", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = m.Student(user_id=user.id, display_name="Agentic fixture")
        session.add(student)
        session.flush()
        learning = m.LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning)
        session.flush()
        session.add(m.StudioRuntime(student_id=student.id, learning_session_id=learning.id))
        session.flush()
    assert learning is not None
    brief = _brief(objective=objective)
    digest = sha256(
        json.dumps(brief, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    parent = m.AIExecution(
        task="tutor", provider="fixture", model="test-agentic-model", latency_ms=1, success=True,
        student_id=student.id, learning_session_id=learning.id,
    )
    session.add(parent)
    session.flush()
    message = m.LearningMessage(
        session_id=learning.id,
        role="tutor",
        content="Tutor response",
        ai_execution_id=parent.id,
        payload={"agentic_canvas": {"status": "ADMITTED", "brief": brief, "brief_digest": digest}},
        created_at=datetime.now(UTC),
    )
    session.add(message)
    session.flush()
    return student, learning, message


def _registry(factory: sessionmaker[Session], compose):
    registry = JobHandlerRegistry()
    register_agentic_canvas_handlers(
        registry,
        session_factory=factory,
        compose=compose,
        settings_factory=_Settings,
    )
    return registry


def test_agentic_admission_is_digest_checked_and_idempotent(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        first = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        second = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert first is not None and second is not None and first.id == second.id
        assert first.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(m.Job)) == 1
        assert session.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 1

    with factory.begin() as session:
        student, learning, bad = _admitted_message(session, objective="Explain a different idea.")
        payload = dict(bad.payload)
        payload["agentic_canvas"] = dict(payload["agentic_canvas"])
        payload["agentic_canvas"]["brief_digest"] = "0" * 64
        bad.payload = payload
        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=bad.id
        ) is None


def test_newer_agentic_admission_supersedes_old_run_before_provider_execution(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, older_message = _admitted_message(session)
        older = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=older_message.id
        )
        assert older is not None
        _, _, newer_message = _admitted_message(
            session, student=student, learning=learning, objective="Explain a newer decimal comparison."
        )
        newer = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=newer_message.id
        )
        assert newer is not None
        old_id, new_id, old_job_id, new_job_id = older.id, newer.id, older.job_id, newer.job_id

    calls = 0

    async def compose(**kwargs):
        nonlocal calls
        calls += 1
        return _scene()

    assert run_once(factory, _registry(factory, compose), worker_id="agentic-supersession") == m.JobStatus.COMPLETED
    with factory() as session:
        old = session.get(m.StudioCanvasSpecialistRun, old_id)
        new = session.get(m.StudioCanvasSpecialistRun, new_id)
        old_job, new_job = session.get(m.Job, old_job_id), session.get(m.Job, new_job_id)
        assert old is not None and old.status == "SUPERSEDED" and old.proposal_payload is None
        assert old_job is not None and old_job.status == "FAILED"
        assert new is not None and new.status == "COMPLETED"
        assert new_job is not None and new_job.status == "COMPLETED"
        assert calls == 1


def test_remote_run_holds_no_runtime_lock_and_late_result_keeps_superseded_status(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        old = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert old is not None
        old_id = old.id

    async def compose(**kwargs):
        # The preflight transaction must be committed before a remote Agent call.
        with factory.begin() as session:
            runtime = session.scalar(
                select(m.StudioRuntime)
                .where(m.StudioRuntime.id == old.studio_runtime_id)
                .with_for_update(nowait=True)
            )
            assert runtime is not None
            _, _, successor_message = _admitted_message(
                session, student=student, learning=learning, objective="Explain a newer comparison."
            )
            successor = admit_agentic_canvas_brief(
                session,
                student_id=student.id,
                learning_session_id=learning.id,
                source_message_id=successor_message.id,
            )
            assert successor is not None
        return _scene()

    assert run_once(factory, _registry(factory, compose), worker_id="agentic-no-lock") == m.JobStatus.COMPLETED
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, old_id)
        assert run is not None and run.status == "SUPERSEDED" and run.proposal_payload is None


def test_transient_provider_failure_retries_same_run_and_persists_canonical_digest(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert run is not None and run.job_id is not None
        run_id, job_id = run.id, run.job_id

    calls = 0

    async def compose(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("transient agent timeout")
        return _scene()

    registry = _registry(factory, compose)
    clock = datetime.now(UTC) + timedelta(seconds=1)
    assert run_once(factory, registry, worker_id="agentic-retry", now=clock) == m.JobStatus.PENDING
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert run is not None and run.status == "PENDING"
        assert run.failure_metadata == {"code": "TRANSIENT_PROVIDER_FAILURE", "provider_attempt": 1}
        assert job is not None and job.status == "PENDING"
        retry_at = job.run_after

    assert run_once(factory, registry, worker_id="agentic-retry", now=retry_at) == m.JobStatus.COMPLETED
    canonical = _scene().model_dump(mode="json")
    expected_digest = sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert calls == 2
        assert run is not None and run.status == "COMPLETED" and run.proposal_digest == expected_digest
        assert job is not None and job.status == "COMPLETED"
        assert job.result == {
            "run_id": str(run_id),
            "run_status": "COMPLETED",
            "scene_contract": "agentic-canvas-scene-v1",
            "proposal_digest": expected_digest,
            "scene_id": None,
            "agent_trace": {"selected_tools": [], "tool_call_count": 0},
        }


def test_deadline_is_terminal_without_calling_agent(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert run is not None and run.job_id is not None
        run.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
        run_id, job_id = run.id, run.job_id

    calls = 0

    async def compose(**kwargs):
        nonlocal calls
        calls += 1
        return _scene()

    assert run_once(factory, _registry(factory, compose), worker_id="agentic-deadline") == m.JobStatus.FAILED
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert calls == 0
        assert run is not None and run.status == "FAILED" and run.failure_metadata == {"code": "DEADLINE_EXCEEDED"}
        assert job is not None and job.status == "FAILED"


def test_worker_immediately_settles_completed_agentic_scene_through_existing_studio_state(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        runtime = session.scalar(
            select(m.StudioRuntime).where(m.StudioRuntime.learning_session_id == learning.id)
        )
        assert runtime is not None
        session.add(
            m.StudioSnapshot(
                studio_runtime_id=runtime.id,
                student_id=student.id,
                snapshot_schema_version="studio-snapshot-v1",
                latest_event_sequence=0,
                state_payload={},
            )
        )
        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert run is not None
        run_id = run.id

    async def compose(**kwargs):
        from services.studio.agent.orchestrator import (
            AgenticCanvasCompositionResult,
            AgentToolCallTrace,
        )

        assert kwargs["sdk_trace_id"].startswith("trace_")
        return AgenticCanvasCompositionResult(
            scene=_scene(),
            selected_tools=("code_interpreter", "create_math_board"),
            tool_call_count=2,
            sdk_trace_id=kwargs["sdk_trace_id"],
            model="test-agentic-model",
            usage={
                "requests": 2,
                "input_tokens": 100,
                "cached_input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 120,
            },
            tool_calls=(
                AgentToolCallTrace(
                    name="code_interpreter",
                    call_id="ci-call-1",
                    status="completed",
                    input_digest="1" * 64,
                    output_digest="2" * 64,
                ),
                AgentToolCallTrace(
                    name="create_math_board",
                    call_id="math-call-1",
                    status="completed",
                    input_digest="3" * 64,
                    output_digest="4" * 64,
                    produced_block_ids=("decimal-line",),
                ),
            ),
        )

    registry = _registry(factory, compose)
    assert run_once(factory, registry, worker_id="agentic-reconcile-success") == m.JobStatus.COMPLETED

    with factory() as session:
        completed = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert completed is not None
        assert completed.status == "COMPLETED"
        assert completed.proposal_payload == _scene().model_dump(mode="json")
        assert completed.failure_metadata is None
        assert completed.sdk_trace_id.startswith("trace_")
        assert completed.agent_execution_metadata == {
            "model": "test-agentic-model",
            "usage": {
                "requests": 2,
                "input_tokens": 100,
                "cached_input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 120,
            },
            "latency_ms": completed.agent_execution_metadata["latency_ms"],
            "selected_tools": ["code_interpreter", "create_math_board"],
            "tool_call_count": 2,
            "tool_calls": [
                {
                    "name": "code_interpreter",
                    "call_id": "ci-call-1",
                    "status": "completed",
                    "input_digest": "1" * 64,
                    "output_digest": "2" * 64,
                    "produced_block_ids": [],
                },
                {
                    "name": "create_math_board",
                    "call_id": "math-call-1",
                    "status": "completed",
                    "input_digest": "3" * 64,
                    "output_digest": "4" * 64,
                    "produced_block_ids": ["decimal-line"],
                },
            ],
            "proposal_digest": completed.proposal_digest,
        }
        assert completed.scene_id is not None
        scene = session.get(m.StudioScene, completed.scene_id)
        assert scene is not None and scene.status == "ACTIVE"
        assert scene.subject_key == "CANVAS"
        snapshot = session.scalar(
            select(m.StudioSnapshot).where(m.StudioSnapshot.studio_runtime_id == completed.studio_runtime_id)
        )
        assert snapshot is not None
        assert snapshot.current_scene_id == scene.id
        assert snapshot.active_activity_key == "agentic_canvas"
        job = session.get(m.Job, completed.job_id)
        assert job is not None
        assert job.result["run_id"] == str(completed.id)
        assert job.result["scene_id"] == str(scene.id)
        assert job.result["agent_trace"] == completed.agent_execution_metadata


def test_post_provider_brief_mutation_is_rejected_before_scene_commit(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert run is not None
        run_id = run.id

    async def compose(**kwargs):
        # Simulate a compromised/mutable persistence path after preflight. The
        # stale declared digest must not be trusted at settlement.
        with factory.begin() as session:
            current = session.get(m.LearningMessage, message.id)
            assert current is not None
            payload = dict(current.payload)
            audit = dict(payload["agentic_canvas"])
            altered = dict(audit["brief"])
            altered["objective"] = "A changed objective must not receive this Agent result."
            audit["brief"] = altered
            payload["agentic_canvas"] = audit
            current.payload = payload
        return _scene()

    assert run_once(factory, _registry(factory, compose), worker_id="agentic-late-mutation") == m.JobStatus.COMPLETED
    with factory() as session:
        rejected = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert rejected is not None
        assert rejected.status == "REJECTED"
        assert rejected.failure_metadata == {"code": "STALE_AGENTIC_CANVAS_RESULT"}
        assert rejected.proposal_payload is None and rejected.proposal_digest is None


def test_retry_recovery_preserves_supersession_that_happens_during_provider_failure(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert run is not None
        run_id = run.id

    async def compose(**kwargs):
        # A newer admission acquires Runtime -> Run before the retry helper.
        # The helper must see and preserve the terminal supersession state.
        with factory.begin() as session:
            _, _, successor_message = _admitted_message(
                session, student=student, learning=learning, objective="A newer Agentic brief."
            )
            successor = admit_agentic_canvas_brief(
                session,
                student_id=student.id,
                learning_session_id=learning.id,
                source_message_id=successor_message.id,
            )
            assert successor is not None
        raise TimeoutError("provider timed out after supersession")

    assert run_once(factory, _registry(factory, compose), worker_id="agentic-retry-superseded") == m.JobStatus.PENDING
    with factory() as session:
        superseded = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert superseded is not None
        assert superseded.status == "SUPERSEDED"
        assert superseded.proposal_payload is None
