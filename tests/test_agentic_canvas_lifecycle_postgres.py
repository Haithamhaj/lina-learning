"""Durable lifecycle tests for the additive Tutor-led Agentic Canvas path."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import SecretStr
from agents.exceptions import ModelBehaviorError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.platform.safety import SafetyAction, SafetyDecision
from services.platform.storage import LocalObjectStorage
from services.studio.custom_visual_builds import (
    CustomVisualBuildResolver,
    persist_custom_visual_build,
    promote_custom_visual_build,
)
from services.studio.full_power_canvas import CustomVisualPackageV1
from services.studio.agent.admission import (
    AGENTIC_CANVAS_CAPABILITY_IDENTITY,
    admit_agentic_canvas_brief,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV2
from services.studio.agent.orchestrator import CustomVisualCandidateMissingError
from services.tutor.context import TutorContextBuilder
from services.retrieval.service import RetrievalService
from services.tutor.runtime import TutorRuntime
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


class _JevExactReuseSettings(_TerraSettings):
    jev_canvas_reuse_mode = "active"
    jev_canvas_reuse_min_probability = 0.90
    jev_canvas_reuse_min_margin = 0.20
    jev_canvas_reuse_policy_version = "jev-canvas-exact-reuse-test-v1"


class _AllowPolicy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(SafetyAction.ALLOW, None, "BASELINE", 1, "TEST", "normal", None)


class _RawReplayProvider:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls = 0
        self.payloads: list[dict[str, object]] = []

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.calls += 1
        self.payloads.append(deepcopy(payload))
        yield StreamDelta(str(self.output["text"]))
        yield StreamComplete(ModelResult(output=deepcopy(self.output), input_tokens=101, output_tokens=202))


def _tutor_canvas_output(
    *,
    text: str,
    canvas_brief: dict[str, object] | None = None,
    canvas_change_intent: str | None = None,
) -> dict[str, object]:
    return {
        "text": text,
        "suggested_actions": [],
        "guided_check": None,
        "teaching_mode": None,
        "teaching_strategy": None,
        "teaching_method_id": None,
        "prior_method_relation": None,
        "candidate_metadata": None,
        "provisional_broad_subject": None,
        "segment_relation": None,
        "structured_segment_state": None,
        "workspace_intent": None,
        "workspace_visual_order": None,
        "canvas_visual_context_selection": None,
        "canvas_brief": canvas_brief,
        "canvas_change_intent": canvas_change_intent,
    }


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


def _install_empty_snapshot(
    session: Session,
    *,
    student: m.Student,
    learning: m.LearningSession,
) -> m.StudioSnapshot:
    runtime = session.scalar(
        select(m.StudioRuntime).where(m.StudioRuntime.learning_session_id == learning.id)
    )
    assert runtime is not None
    snapshot = m.StudioSnapshot(
        studio_runtime_id=runtime.id,
        student_id=student.id,
        snapshot_schema_version="studio-snapshot-v1",
        latest_event_sequence=runtime.latest_event_sequence,
        state_payload={},
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _registry(factory: sessionmaker[Session], compose, *, settings_factory=_Settings):
    registry = JobHandlerRegistry()
    register_agentic_canvas_handlers(
        registry,
        session_factory=factory,
        compose=compose,
        settings_factory=settings_factory,
    )
    return registry


def _stream_tutor_canvas_turn(
    session: Session,
    *,
    learning: m.LearningSession,
    output: dict[str, object],
    question: str,
) -> tuple[_RawReplayProvider, m.LearningMessage]:
    provider = _RawReplayProvider(output)
    runtime = TutorRuntime(
        session,
        context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
        safety_policy=_AllowPolicy(),
        gateway=ModelGateway(
            session,
            routes={m.ModelTask.TUTOR: ModelRoute("fixture-recovery", "fixture-recovery-output")},
            providers={"fixture-recovery": provider},
        ),
    )
    list(runtime.stream_turn(learning_session=learning, question=question))
    session.flush()
    message = session.scalars(
        select(m.LearningMessage)
        .where(m.LearningMessage.session_id == learning.id, m.LearningMessage.role == "tutor")
        .order_by(m.LearningMessage.created_at.desc(), m.LearningMessage.id.desc())
    ).first()
    assert message is not None
    return provider, message


def test_primary_tutor_failed_same_need_retry_flows_to_exactly_one_admitted_run(
    factory: sessionmaker[Session],
) -> None:
    """E26-A: real Tutor output binds RETRY to the failed Run and admission stays idempotent."""

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        failed = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert failed is not None and failed.job_id is not None
        failed.status = "FAILED"
        failed.completed_at = datetime.now(UTC)
        failed.failure_metadata = {"code": "AGENT_MODEL_BEHAVIOR_FAILURE"}
        failed_job = session.get(m.Job, failed.job_id)
        assert failed_job is not None
        failed_job.status = "FAILED"
        failed_job.completed_at = datetime.now(UTC)
        failed_job.last_error = "fixture failure"
        _install_empty_snapshot(session, student=student, learning=learning)
        student_id, learning_id, failed_id = student.id, learning.id, failed.id

    with factory.begin() as session:
        student = session.get(m.Student, student_id)
        learning = session.get(m.LearningSession, learning_id)
        failed = session.get(m.StudioCanvasSpecialistRun, failed_id)
        assert student is not None and learning is not None and failed is not None
        provider, retry_message = _stream_tutor_canvas_turn(
            session,
            learning=learning,
            question="The same decimal visual failed. Please try that visual again.",
            output=_tutor_canvas_output(
                text="The visual failed, so I am retrying the same visual now.",
                canvas_brief=_brief(),
                canvas_change_intent="RETRY",
            ),
        )

        encoded_input = str(provider.payloads[-1]["input"])
        assert str(failed.id) in encoded_input
        assert '"run_status": "FAILED"' in encoded_input
        assert '"failure_code": "AGENT_MODEL_BEHAVIOR_FAILURE"' in encoded_input
        assert retry_message.payload["canvas_change_intent"] == "RETRY"
        assert retry_message.payload["canvas_decision_base"] == {
            "version": "canvas-decision-base-v1",
            "expected_run_id": str(failed.id),
            "expected_run_status": "FAILED",
            "expected_scene_id": None,
            "expected_scene_version": None,
        }
        runs = list(session.scalars(
            select(m.StudioCanvasSpecialistRun)
            .where(m.StudioCanvasSpecialistRun.learning_session_id == learning.id)
            .order_by(m.StudioCanvasSpecialistRun.created_at, m.StudioCanvasSpecialistRun.id)
        ))
        retry = next(run for run in runs if run.source_message_id == retry_message.id)
        assert len(runs) == 2
        assert failed.status == "FAILED"
        assert retry.status == "PENDING"
        assert admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=retry_message.id
        ).id == retry.id
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 2


@pytest.mark.parametrize("inflight_status", ["PENDING", "RUNNING"])
def test_primary_tutor_inflight_visual_reports_status_without_duplicate_composition(
    factory: sessionmaker[Session], inflight_status: str,
) -> None:
    """E26-B: PENDING/RUNNING truth reaches Tutor output and creates no second Run."""

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        inflight = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert inflight is not None and inflight.job_id is not None
        inflight.status = inflight_status
        job = session.get(m.Job, inflight.job_id)
        assert job is not None
        job.status = inflight_status
        _install_empty_snapshot(session, student=student, learning=learning)
        student_id, learning_id, inflight_id = student.id, learning.id, inflight.id

    with factory.begin() as session:
        learning = session.get(m.LearningSession, learning_id)
        inflight = session.get(m.StudioCanvasSpecialistRun, inflight_id)
        assert learning is not None and inflight is not None
        provider, status_message = _stream_tutor_canvas_turn(
            session,
            learning=learning,
            question="Is the decimal visual ready yet?",
            output=_tutor_canvas_output(
                text="That visual is still being prepared; I will not start a duplicate.",
            ),
        )

        encoded_input = str(provider.payloads[-1]["input"])
        assert str(inflight.id) in encoded_input
        assert f'"run_status": "{inflight_status}"' in encoded_input
        assert status_message.payload["canvas_change_intent"] is None
        assert status_message.payload["canvas_decision_base"] is None
        assert status_message.payload["agentic_canvas"]["status"] == "NOT_REQUESTED"
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 1
        assert inflight.status == inflight_status


def test_primary_tutor_ready_but_client_missing_uses_reload_without_new_composition(
    factory: sessionmaker[Session],
) -> None:
    """E26-C: server-ready truth does not claim browser display or create another visual."""

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        completed = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert completed is not None and completed.job_id is not None
        scene, snapshot = _install_active_scene(session, student=student, learning=learning)
        completed.status = "COMPLETED"
        completed.scene_id = scene.id
        completed.completed_at = datetime.now(UTC)
        job = session.get(m.Job, completed.job_id)
        assert job is not None
        job.status = "COMPLETED"
        job.completed_at = datetime.now(UTC)
        learning_id, completed_id = learning.id, completed.id
        scene_id, scene_version, snapshot_id = scene.id, scene.scene_version, snapshot.id

    with factory.begin() as session:
        learning = session.get(m.LearningSession, learning_id)
        completed = session.get(m.StudioCanvasSpecialistRun, completed_id)
        scene = session.get(m.StudioScene, scene_id)
        snapshot = session.get(m.StudioSnapshot, snapshot_id)
        assert learning is not None and completed is not None and scene is not None and snapshot is not None
        provider, status_message = _stream_tutor_canvas_turn(
            session,
            learning=learning,
            question="The visual is not showing in my browser.",
            output=_tutor_canvas_output(
                text="The server reports the scene ready, but I cannot verify your browser display. Use Reload Workspace.",
            ),
        )

        encoded_input = str(provider.payloads[-1]["input"])
        assert '"scene_ready": true' in encoded_input
        assert str(scene.id) in encoded_input
        assert status_message.content.endswith("Use Reload Workspace.")
        assert status_message.payload["canvas_change_intent"] is None
        assert session.scalar(select(func.count(m.StudioCanvasSpecialistRun.id))) == 1
        assert snapshot.current_scene_id == scene.id
        assert snapshot.current_scene_version == scene_version


def test_primary_tutor_semantically_insufficient_scene_replacement_flows_to_admission(
    factory: sessionmaker[Session],
) -> None:
    """E26-D: real Tutor REPLACE_SCENE preserves the observed Scene lineage."""

    replacement_brief = _brief(objective="Show three equal groups of four counters.")
    replacement_brief.update({
        "student_request": "Replace the decimal line with equal groups.",
        "requested_representation": "Three equal groups of four counters.",
        "facts": ["There are three equal groups.", "Each group contains four counters."],
        "quantities": [
            {"id": "groups", "value": "3", "unit": "groups"},
            {"id": "per_group", "value": "4", "unit": "counters"},
        ],
        "desired_student_action": "Count the counters in each equal group.",
        "must_not_imply": [],
    })
    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        completed = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=original_message.id
        )
        assert completed is not None and completed.job_id is not None
        scene, snapshot = _install_active_scene(session, student=student, learning=learning)
        completed.status = "COMPLETED"
        completed.scene_id = scene.id
        completed.completed_at = datetime.now(UTC)
        job = session.get(m.Job, completed.job_id)
        assert job is not None
        job.status = "COMPLETED"
        job.completed_at = datetime.now(UTC)
        learning_id, completed_id = learning.id, completed.id
        scene_id, scene_version, snapshot_id = scene.id, scene.scene_version, snapshot.id

    with factory.begin() as session:
        learning = session.get(m.LearningSession, learning_id)
        completed = session.get(m.StudioCanvasSpecialistRun, completed_id)
        scene = session.get(m.StudioScene, scene_id)
        snapshot = session.get(m.StudioSnapshot, snapshot_id)
        assert learning is not None and completed is not None and scene is not None and snapshot is not None
        provider, replacement_message = _stream_tutor_canvas_turn(
            session,
            learning=learning,
            question="The number line cannot show the equal groups I need. Replace it with groups of counters.",
            output=_tutor_canvas_output(
                text="The current representation is not suitable for equal groups, so I am replacing it.",
                canvas_brief=replacement_brief,
                canvas_change_intent="REPLACE_SCENE",
            ),
        )

        encoded_input = str(provider.payloads[-1]["input"])
        assert '"scene_ready": true' in encoded_input
        assert replacement_message.payload["canvas_change_intent"] == "REPLACE_SCENE"
        assert replacement_message.payload["canvas_decision_base"] == {
            "version": "canvas-decision-base-v1",
            "expected_run_id": str(completed.id),
            "expected_run_status": "COMPLETED",
            "expected_scene_id": str(scene.id),
            "expected_scene_version": scene_version,
        }
        runs = list(session.scalars(
            select(m.StudioCanvasSpecialistRun)
            .where(m.StudioCanvasSpecialistRun.learning_session_id == learning.id)
            .order_by(m.StudioCanvasSpecialistRun.created_at, m.StudioCanvasSpecialistRun.id)
        ))
        replacement = next(run for run in runs if run.source_message_id == replacement_message.id)
        assert len(runs) == 2
        assert completed.status == "COMPLETED"
        assert replacement.status == "PENDING"
        assert replacement.base_scene_id == scene.id
        assert replacement.base_scene_version == scene_version
        assert snapshot.current_scene_id == scene.id
        assert snapshot.current_scene_version == scene_version


@pytest.mark.parametrize("schema_version", ["tutor_turn_v12", "tutor_turn_v13"])
def test_current_status_or_scene_step_cannot_admit_a_new_canvas_run(
    factory: sessionmaker[Session], schema_version: str,
) -> None:
    """A03: lifecycle intent is enforced at the durable admission boundary."""

    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        payload = dict(message.payload)
        payload["tutor_turn_schema_version"] = schema_version
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


def test_original_v02_raw_output_replays_unchanged_with_historical_fact_identity_and_one_causal_replacement(
    factory: sessionmaker[Session],
) -> None:
    """The saved failed Luna output succeeds through the local fixture path without rewriting its key."""

    fixture_path = Path(__file__).parent / "fixtures" / "tutor_canvas_ab_v02_meaningful_representation_change.json"
    raw_output = json.loads(fixture_path.read_text(encoding="utf-8"))
    original_output = deepcopy(raw_output)

    with factory.begin() as session:
        student, learning, original_message = _admitted_message(session)
        original_run = admit_agentic_canvas_brief(
            session,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=original_message.id,
        )
        assert original_run is not None and original_run.status == "PENDING"
        scene, _snapshot = _install_active_scene(session, student=student, learning=learning)

        now = datetime.now(UTC)
        session.add(m.PersonalFact(
            student_id=student.id,
            category="ACTIVITY",
            fact_key="activity.building_blocks",
            value="LIKES",
            display_statement="Enjoys building with blocks.",
            support_count=1,
            first_observed_at=now,
            last_observed_at=now,
        ))
        other_user = m.User(identity_provider="agentic-lifecycle", external_subject=uuid4().hex)
        session.add(other_user)
        session.flush()
        other_student = m.Student(user_id=other_user.id, display_name="Other learner")
        session.add(other_student)
        session.flush()
        session.add(m.PersonalFact(
            student_id=other_student.id,
            category="ACTIVITY",
            fact_key="activity:private_other_student",
            value="LIKES",
            display_statement="Other learner fact.",
            support_count=1,
            first_observed_at=now,
            last_observed_at=now,
        ))
        session.flush()
        student_id = student.id
        learning_id = learning.id
        original_run_id = original_run.id
        scene_id = scene.id
        scene_version = scene.scene_version

    with factory.begin() as session:
        student = session.get(m.Student, student_id)
        learning = session.get(m.LearningSession, learning_id)
        original_run = session.get(m.StudioCanvasSpecialistRun, original_run_id)
        scene = session.get(m.StudioScene, scene_id)
        assert student is not None and learning is not None
        assert original_run is not None and scene is not None
        provider = _RawReplayProvider(raw_output)
        runtime = TutorRuntime(
            session,
            context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
            safety_policy=_AllowPolicy(),
            gateway=ModelGateway(
                session,
                routes={m.ModelTask.TUTOR: ModelRoute("fixture-replay", "fixture-raw-luna-output")},
                providers={"fixture-replay": provider},
            ),
        )

        events = list(runtime.stream_turn(
            learning_session=learning,
            question="Switch from the number line to equal groups using blocks.",
        ))
        session.flush()

        assert provider.calls == 1
        assert raw_output == original_output
        assert events[-1].text == raw_output["text"]
        tutor_messages = list(session.scalars(
            select(m.LearningMessage)
            .where(m.LearningMessage.session_id == learning.id, m.LearningMessage.role == "tutor")
            .order_by(m.LearningMessage.created_at, m.LearningMessage.id)
        ))
        replay_message = tutor_messages[-1]
        assert replay_message.payload["agentic_canvas"]["status"] == "ADMITTED", json.dumps({
            "audit": replay_message.payload["agentic_canvas"],
            "base": replay_message.payload["canvas_decision_base"],
            "original": {"id": str(original_run.id), "status": original_run.status},
            "scene": {"id": str(scene.id), "version": scene.scene_version},
        }, ensure_ascii=False)
        assert replay_message.payload["agentic_canvas"]["visual_learner_context"]["selected_personal_facts"] == [{
            "fact_key": "activity.building_blocks",
            "category": "ACTIVITY",
            "display_statement": "Enjoys building with blocks.",
        }]
        assert replay_message.payload["canvas_change_intent"] == "REPLACE_PENDING"
        assert replay_message.payload["canvas_decision_base"] == {
            "version": "canvas-decision-base-v1",
            "expected_run_id": str(original_run.id),
            "expected_run_status": "PENDING",
            "expected_scene_id": str(scene.id),
            "expected_scene_version": scene.scene_version,
        }

        runs = list(session.scalars(
            select(m.StudioCanvasSpecialistRun)
            .where(m.StudioCanvasSpecialistRun.learning_session_id == learning.id)
            .order_by(m.StudioCanvasSpecialistRun.created_at, m.StudioCanvasSpecialistRun.id)
        ))
        replacement = next(run for run in runs if run.source_message_id == replay_message.id)
        assert len(runs) == 2
        assert original_run.status == "SUPERSEDED"
        assert replacement.status == "PENDING"
        assert replacement.base_scene_id == scene.id
        assert replacement.base_scene_version == scene.scene_version
        assert session.scalar(select(func.count(m.Job.id)).where(m.Job.job_type == "studio.agentic_canvas.compose.v1")) == 2

        replay_execution = session.get(m.AIExecution, replay_message.ai_execution_id)
        assert replay_execution is not None
        assert replay_execution.success is True
        assert replay_execution.provider == "fixture-replay"
        assert replay_execution.model == "fixture-raw-luna-output"
        assert replay_execution.source_message_id is not None


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


def test_active_jev_exact_reuse_bypasses_terra_only_for_executable_frozen_action(
    factory: sessionmaker[Session], tmp_path: Path
) -> None:
    from test_full_power_canvas import _manifest

    storage = LocalObjectStorage(tmp_path)
    with factory.begin() as session:
        student, first_learning, first_message = _admitted_message(session)
        first_run = admit_agentic_canvas_brief(
            session,
            student_id=student.id,
            learning_session_id=first_learning.id,
            source_message_id=first_message.id,
        )
        assert first_run is not None
        prior_scene, _ = _install_active_scene(
            session, student=student, learning=first_learning
        )
        package = CustomVisualPackageV1.model_validate(
            {
                "version": "custom-visual-package-v1",
                "runtime_kind": "custom-visual",
                "dependencies": ["native-svg-v1"],
                "source": (
                    "window.mount=(root,params,bridge)=>{root.textContent=params.label;}"
                    f"/* exact-reuse-test:{uuid4().hex} */"
                ),
                "manifest": _manifest(),
                "parameter_schema": {
                    "type": "object",
                    "properties": {"label": {"type": "string"}},
                },
            }
        )
        build = persist_custom_visual_build(
            session, storage=storage, run=first_run, package=package
        )
        session.flush()
        version = promote_custom_visual_build(
            session,
            resolver=CustomVisualBuildResolver(storage),
            build_id=build.id,
            student_id=student.id,
            runtime_id=first_run.studio_runtime_id,
            stable_slug=f"exact-reuse-{uuid4().hex}",
            semantic_purpose="Compare two exact fractions on a movable number line",
            parameter_schema=package.parameter_schema,
            promotion_reason="Verified reusable exact fraction comparison",
        )
        first_run.status = "CANCELLED"
        first_job = session.get(m.Job, first_run.job_id)
        assert first_job is not None
        first_job.status = m.JobStatus.COMPLETED.value
        first_job.result = {"fixture": "prior reusable source"}
        session.add(
            m.VisualArtifactInstance(
                artifact_version_id=version.id,
                studio_scene_id=prior_scene.id,
                student_id=student.id,
                bound_parameters={"label": "1/2"},
                semantic_manifest=package.manifest.model_dump(mode="json"),
                current_semantic_state={},
                locale="en",
                direction="ltr",
            )
        )

        later = m.LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(later)
        session.flush()
        runtime = m.StudioRuntime(student_id=student.id, learning_session_id=later.id)
        session.add(runtime)
        session.flush()
        _, _, message = _admitted_message(
            session,
            student=student,
            learning=later,
            objective="Compare two exact fractions on a movable number line.",
        )
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
            learning_session_id=later.id,
            source_message_id=message.id,
        )
        assert run is not None
        run_id = run.id

    class DecisionProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            options = payload["questions"]["reuse_action"]["criteria"]
            reuse = next(key for key in options if key != "NO_MATCH")
            return ModelResult(
                output={
                    "answers": {
                        "reuse_action": {
                            "choice": reuse,
                            "probabilities": {reuse: 0.98, "NO_MATCH": 0.02},
                        }
                    }
                },
                input_tokens=100,
                output_tokens=0,
                estimated_cost_usd=0.0000042,
            )

    async def compose(**_kwargs):
        raise AssertionError("Terra must not run for accepted exact reuse")

    registry = JobHandlerRegistry()
    register_agentic_canvas_handlers(
        registry,
        session_factory=factory,
        compose=compose,
        settings_factory=_JevExactReuseSettings,
        storage=storage,
        decision_gateway_factory=lambda session, **_kwargs: ModelGateway(
            session,
            routes={
                m.ModelTask.CANVAS_REUSE_SELECTION: ModelRoute("fixture-jev", "typesafe/jev-1.13")
            },
            providers={"fixture-jev": DecisionProvider()},
        ),
    )
    assert run_once(factory, registry, worker_id="jev-exact-reuse") == m.JobStatus.COMPLETED

    with factory() as session:
        completed = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert completed is not None and completed.scene_id is not None
        assert completed.agent_execution_metadata["jev_exact_reuse"]["bypassed_canvas_agent"] is True
        assert completed.agent_execution_metadata["reusable_selections"][0]["version_id"] == str(version.id)
        execution = session.get(m.AIExecution, completed.ai_execution_id)
        assert execution is not None
        assert execution.task == m.ModelTask.CANVAS_REUSE_SELECTION.value
        assert session.scalar(
            select(func.count(m.AIExecution.id)).where(
                m.AIExecution.operation_id == run_id,
                m.AIExecution.task == "canvas_agent_orchestration",
            )
        ) == 0
        instance = session.scalar(
            select(m.VisualArtifactInstance).where(
                m.VisualArtifactInstance.studio_scene_id == completed.scene_id
            )
        )
        assert instance is not None
        assert instance.artifact_version_id == version.id
        assert instance.bound_parameters == {"label": "1/2"}


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
