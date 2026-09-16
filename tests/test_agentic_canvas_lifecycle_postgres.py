"""Durable lifecycle tests for the additive Tutor-led Agentic Canvas path."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import SecretStr
from agents.exceptions import ModelBehaviorError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.studio.agent.admission import (
    AGENTIC_CANVAS_CAPABILITY_IDENTITY,
    admit_agentic_canvas_brief,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV2
from services.studio.agent.orchestrator import CustomVisualCandidateMissingError
from workers.agentic_canvas_handlers import register_agentic_canvas_handlers
from workers.agentic_canvas_handlers import _classify_agent_failure
from workers.job_worker import JobHandlerRegistry, run_once

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required"
)


def test_agent_model_behavior_failure_is_retryable_within_the_bounded_job_attempts() -> None:
    """Catches making one transient malformed Agent turn terminal on its first attempt."""

    assert _classify_agent_failure(ModelBehaviorError("malformed tool arguments")) == (
        "AGENT_MODEL_BEHAVIOR_FAILURE",
        True,
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
    canvas_model_name = None
    model_base_url = None


class _TerraSettings(_Settings):
    model_name = "gpt-5.6-luna"
    canvas_model_name = "gpt-5.6-terra"


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


def _scene() -> AgenticCanvasSceneV2:
    return AgenticCanvasSceneV2.model_validate(
        {
            "version": "agentic-canvas-scene-v2",
            "objective": "Compare two decimals on a number line.",
            "subject_key": "MATH",
            "presentation": {"layout": "FOCUS", "palette": "COOL", "motion": "NONE", "placements": [{"block_id": "decimal-line", "role": "PRIMARY", "order": 0, "span": "FULL"}], "reveal_order": []},
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
        payload={"agentic_canvas": {"status": "ADMITTED", "brief": brief, "brief_digest": digest, "visual_learner_context": {"version": "visual-learner-context-v1", "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []}}},
        created_at=datetime.now(UTC),
    )
    session.add(message)
    session.flush()
    return student, learning, message


def _set_v12_canvas_change(
    message: m.LearningMessage,
    *,
    intent: str,
    expected_run: m.StudioCanvasSpecialistRun | None = None,
    expected_scene_id: object | None = None,
    expected_scene_version: int | None = None,
) -> None:
    payload = dict(message.payload)
    payload["tutor_turn_schema_version"] = "tutor_turn_v12"
    payload["canvas_change_intent"] = intent
    payload["canvas_decision_base"] = {
        "version": "canvas-decision-base-v1",
        "expected_run_id": None if expected_run is None else str(expected_run.id),
        "expected_run_status": None if expected_run is None else expected_run.status,
        "expected_scene_id": None if expected_scene_id is None else str(expected_scene_id),
        "expected_scene_version": expected_scene_version,
    }
    message.payload = payload


def _install_active_scene(
    session: Session,
    *,
    student: m.Student,
    learning: m.LearningSession,
) -> tuple[m.StudioScene, m.StudioSnapshot]:
    runtime = session.scalar(
        select(m.StudioRuntime).where(m.StudioRuntime.learning_session_id == learning.id)
    )
    assert runtime is not None
    scene = m.StudioScene(
        studio_runtime_id=runtime.id,
        student_id=student.id,
        learning_session_id=learning.id,
        subject_key="MATH",
        subject_profile_version="fixture-v1",
        concept_keys=["decimals"],
        activity_key="fixture-scene",
        artifact_type="interactive-workspace",
        renderer_key="native-react-svg",
        renderer_version="1",
        activity_contract_version="activity-v1",
        payload_schema_version="scene-v1",
        scene_version=1,
        status="ACTIVE",
        seed_payload={"label": "Current scene"},
        accessibility_payload={"summary": "Current scene"},
        locale="en",
        direction="ltr",
        source_asset_refs=[],
    )
    session.add(scene)
    session.flush()
    snapshot = m.StudioSnapshot(
        studio_runtime_id=runtime.id,
        student_id=student.id,
        snapshot_schema_version="studio-snapshot-v1",
        latest_event_sequence=0,
        current_scene_id=scene.id,
        current_scene_version=scene.scene_version,
        active_subject_key="MATH",
        active_activity_key="fixture-scene",
        state_payload={},
    )
    session.add(snapshot)
    session.flush()
    return scene, snapshot


def _registry(factory: sessionmaker[Session], compose, *, settings_factory=_Settings):
    registry = JobHandlerRegistry()
    register_agentic_canvas_handlers(
        registry,
        session_factory=factory,
        compose=compose,
        settings_factory=settings_factory,
    )
    return registry


def test_v12_status_or_scene_step_cannot_admit_a_new_canvas_run(
    factory: sessionmaker[Session],
) -> None:
    """A03: lifecycle intent is enforced at the durable admission boundary."""

    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        payload = dict(message.payload)
        payload["tutor_turn_schema_version"] = "tutor_turn_v12"
        payload["canvas_change_intent"] = None
        message.payload = payload

        assert admit_agentic_canvas_brief(
            session,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=message.id,
        ) is None
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 0

        payload["canvas_change_intent"] = "CREATE"
        payload["canvas_decision_base"] = {
            "version": "canvas-decision-base-v1",
            "expected_run_id": None,
            "expected_run_status": None,
            "expected_scene_id": None,
            "expected_scene_version": None,
        }
        message.payload = payload
        assert admit_agentic_canvas_brief(
            session,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=message.id,
        ) is not None


def test_stale_replace_pending_is_rejected_when_expected_run_completes(
    factory: sessionmaker[Session],
) -> None:
    """A: a late REPLACE_PENDING cannot replace a run that settled during inference."""

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        original = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert original is not None
        _, _, late_message = _admitted_message(
            session, student=student, learning=learning, objective="A late replacement."
        )
        _set_v12_canvas_change(late_message, intent="REPLACE_PENDING", expected_run=original)
        original.status = "COMPLETED"
        original.completed_at = datetime.now(UTC)

        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=late_message.id
        ) is None
        assert late_message.payload["agentic_canvas"]["reason_code"] == "STALE_BASE"
        assert original.status == "COMPLETED"
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 1


def test_stale_expected_run_cannot_supersede_a_newer_run(
    factory: sessionmaker[Session],
) -> None:
    """B: an old Tutor decision cannot supersede a successor admitted after selection."""

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        original = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert original is not None
        _, _, stale_message = _admitted_message(
            session, student=student, learning=learning, objective="Stale change."
        )
        _set_v12_canvas_change(stale_message, intent="REPLACE_PENDING", expected_run=original)
        _, _, successor_message = _admitted_message(
            session, student=student, learning=learning, objective="Newest change."
        )
        successor = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=successor_message.id
        )
        assert successor is not None

        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=stale_message.id
        ) is None
        assert stale_message.payload["agentic_canvas"]["reason_code"] == "STALE_BASE"
        assert successor.status == "PENDING"
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 2


def test_stale_replace_scene_is_rejected_after_scene_version_advances(
    factory: sessionmaker[Session],
) -> None:
    """C: REPLACE_SCENE is bound to the exact Scene identity and version observed."""

    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        scene, snapshot = _install_active_scene(session, student=student, learning=learning)
        _set_v12_canvas_change(
            message,
            intent="REPLACE_SCENE",
            expected_scene_id=scene.id,
            expected_scene_version=1,
        )
        scene.scene_version = 2
        snapshot.current_scene_version = 2

        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        ) is None
        assert message.payload["agentic_canvas"]["reason_code"] == "STALE_BASE"
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 0


def test_stale_retry_is_rejected_after_a_successor_appears(
    factory: sessionmaker[Session],
) -> None:
    """D: RETRY stays bound to the failed run and cannot cross a newer successor."""

    with factory.begin() as session:
        student, learning, failed_message = _admitted_message(session)
        failed = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=failed_message.id
        )
        assert failed is not None
        failed.status = "FAILED"
        _, _, retry_message = _admitted_message(
            session, student=student, learning=learning, objective="Retry the failed visual."
        )
        _set_v12_canvas_change(retry_message, intent="RETRY", expected_run=failed)
        _, _, successor_message = _admitted_message(
            session, student=student, learning=learning, objective="A newer visual."
        )
        successor = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=successor_message.id
        )
        assert successor is not None

        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=retry_message.id
        ) is None
        assert retry_message.payload["agentic_canvas"]["reason_code"] == "STALE_BASE"
        assert successor.status == "PENDING"


def test_stale_create_is_rejected_when_canvas_appears_before_admission(
    factory: sessionmaker[Session],
) -> None:
    """E: CREATE is valid only for the same empty Canvas state seen before inference."""

    with factory.begin() as session:
        student, learning, stale_create = _admitted_message(session)
        _set_v12_canvas_change(stale_create, intent="CREATE")
        _, _, newer_message = _admitted_message(
            session, student=student, learning=learning, objective="A newer visual appeared."
        )
        newer = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=newer_message.id
        )
        assert newer is not None

        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=stale_create.id
        ) is None
        assert stale_create.payload["agentic_canvas"]["reason_code"] == "STALE_BASE"
        assert newer.status == "PENDING"
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 1


def test_v12_create_admits_against_an_unchanged_empty_canvas_base(
    factory: sessionmaker[Session],
) -> None:
    """F: a current empty base still permits one genuine CREATE."""

    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        _set_v12_canvas_change(message, intent="CREATE")

        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )

        assert run is not None and run.status == "PENDING"


def test_v12_replace_pending_admits_against_the_same_inflight_run(
    factory: sessionmaker[Session],
) -> None:
    """F: the exact current in-flight run remains replaceable."""

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        original = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert original is not None
        _, _, replacement_message = _admitted_message(
            session, student=student, learning=learning, objective="A genuine changed visual."
        )
        _set_v12_canvas_change(replacement_message, intent="REPLACE_PENDING", expected_run=original)

        replacement = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=replacement_message.id
        )

        assert replacement is not None and replacement.status == "PENDING"
        assert original.status == "SUPERSEDED"


def test_v12_replace_scene_admits_with_exact_scene_lineage(
    factory: sessionmaker[Session],
) -> None:
    """F: unchanged Scene identity/version is preserved as replacement lineage."""

    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        scene, _snapshot = _install_active_scene(session, student=student, learning=learning)
        _set_v12_canvas_change(
            message,
            intent="REPLACE_SCENE",
            expected_scene_id=scene.id,
            expected_scene_version=scene.scene_version,
        )

        replacement = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )

        assert replacement is not None
        assert replacement.base_scene_id == scene.id
        assert replacement.base_scene_version == scene.scene_version


def test_v12_retry_admits_against_the_same_failed_run_without_a_successor(
    factory: sessionmaker[Session],
) -> None:
    """F: RETRY remains available for the exact current terminal failed run."""

    with factory.begin() as session:
        student, learning, failed_message = _admitted_message(session)
        failed = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=failed_message.id
        )
        assert failed is not None
        failed.status = "FAILED"
        _, _, retry_message = _admitted_message(
            session, student=student, learning=learning, objective="Retry the same visual."
        )
        _set_v12_canvas_change(retry_message, intent="RETRY", expected_run=failed)

        retry = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=retry_message.id
        )

        assert retry is not None and retry.status == "PENDING"
        assert failed.status == "FAILED"


def test_dedicated_canvas_model_is_used_for_composition_and_successful_execution(
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
            session,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=message.id,
        )
        assert run is not None
        run_id = run.id

    async def compose(**kwargs):
        from services.studio.agent.orchestrator import AgenticCanvasCompositionResult

        assert kwargs["model"] == "gpt-5.6-terra"
        return AgenticCanvasCompositionResult(
            scene=_scene(),
            selected_tools=(),
            tool_call_count=0,
            sdk_trace_id=kwargs["sdk_trace_id"],
            model="gpt-5.6-terra",
            usage={
                "requests": 1,
                "input_tokens": 10,
                "cached_input_tokens": 0,
                "output_tokens": 2,
                "total_tokens": 12,
            },
        )

    assert run_once(
        factory,
        _registry(factory, compose, settings_factory=_TerraSettings),
        worker_id="agentic-terra-success",
    ) == m.JobStatus.COMPLETED
    with factory() as session:
        completed = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert completed is not None and completed.status == "COMPLETED"
        assert completed.agent_execution_metadata["model"] == "gpt-5.6-terra"
        execution = session.get(m.AIExecution, completed.ai_execution_id)
        assert execution is not None
        assert execution.model == "gpt-5.6-terra"
        assert execution.estimated_cost_usd is None


def test_dedicated_canvas_model_is_recorded_for_failed_composition(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(
            session,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=message.id,
        )
        assert run is not None
        run_id = run.id

    async def compose(**kwargs):
        assert kwargs["model"] == "gpt-5.6-terra"
        raise CustomVisualCandidateMissingError(tool_failures=[], model_turns=[])

    assert run_once(
        factory,
        _registry(factory, compose, settings_factory=_TerraSettings),
        worker_id="agentic-terra-failure",
    ) == m.JobStatus.FAILED
    with factory() as session:
        failed = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert failed is not None and failed.failure_metadata["model"] == "gpt-5.6-terra"
        execution = session.scalar(select(m.AIExecution).where(m.AIExecution.operation_id == run_id))
        assert execution is not None
        assert execution.model == "gpt-5.6-terra"
        assert not execution.success


def test_dedicated_canvas_model_is_required_in_agent_trace_validation(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(
            session,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=message.id,
        )
        assert run is not None
        run_id = run.id

    async def compose(**kwargs):
        from services.studio.agent.orchestrator import AgenticCanvasCompositionResult

        return AgenticCanvasCompositionResult(
            scene=_scene(),
            selected_tools=(),
            tool_call_count=0,
            sdk_trace_id=kwargs["sdk_trace_id"],
            model="gpt-5.6-luna",
        )

    assert run_once(
        factory,
        _registry(factory, compose, settings_factory=_TerraSettings),
        worker_id="agentic-terra-trace",
    ) == m.JobStatus.FAILED
    with factory() as session:
        failed = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert failed is not None and failed.failure_metadata == {"code": "AGENT_TRACE_INVALID"}


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
        assert run.failure_metadata["code"] == "TRANSIENT_PROVIDER_FAILURE"
        assert run.failure_metadata["provider_attempt"] == 1
        assert run.failure_metadata["latency_ms"] >= 0
        assert run.failure_metadata["model"] == "test-agentic-model"
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
                "scene_contract": "agentic-canvas-scene-v2",
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
        assert kwargs["model"] == "test-agentic-model"
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
        assert {key: value for key, value in completed.agent_execution_metadata.items() if key not in {"preflight_ms", "persistence_ms", "settlement_ms", "worker_total_ms", "estimated_token_cost_usd"}} == {
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
