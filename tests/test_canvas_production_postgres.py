"""Production Canvas composition, persistence, reload, and Tutor continuation."""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.model_gateway.factory import create_canvas_specialist_gateway
from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.studio.canvas_specialist import admit_committed_visual_order
from services.studio.contracts import AppendStudioEventCommand, StudioActor
from services.studio.interactions import StudioInteractionTutorAdmission, StudioInteractionTutorService
from services.studio.service import StudioStateService
from services.studio.subjects import production_subject_registry
from services.studio.visual_order import admit_visual_order
from workers.job_worker import JobHandlerRegistry, run_once
from workers.studio_handlers import register_canvas_specialist_handlers


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, ai_executions, studio_canvas_specialist_runs, studio_tutor_observations, studio_student_interactions, studio_events, studio_snapshots, studio_scenes, studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _order(pattern: str) -> dict[str, object]:
    goals = {"SPATIAL_MANIPULATION": "PLACE_OBJECT", "MATH_VISUALIZATION": "CONSTRUCT_POINT", "MATH_INPUT": "AUTHOR_EXPRESSION"}
    return {
        "version": "workspace-visual-order-v2", "operation": "COMPOSE", "pattern": pattern, "topology": None,
        "interaction_goal": goals[pattern], "objective": f"Grade 5 objective for {pattern}",
        "required_semantics": ["The named learning object", "The exact target meaning"],
        "required_relations": ["The object relates to the target"], "must_not_imply": [],
        "source_references": [], "personal_fact_keys": [], "locale": "en", "direction": "ltr", "use_display_name": False,
    }


PROPOSALS = {
    "SPATIAL_MANIPULATION": {
        "version": "canvas-specialist-spatial-proposal-v1", "pattern": "SPATIAL_MANIPULATION",
        "title": "Classify three quarters", "prompt": "Place 3/4 inside Less than 1.",
        "objects": [{"semantic_key": "three-quarters", "label": "3/4", "support_ids": ["F1"]}],
        "targets": [{"semantic_key": "less-than-one", "label": "Less than 1", "relation": "INSIDE", "support_ids": ["F2", "R1"]}],
        "initial_placements": [{"object_semantic_key": "three-quarters", "target_semantic_key": None}],
        "interaction_affordances": ["PLACE_OBJECT"], "text_equivalent": "Three quarters is less than one.",
    },
    "MATH_VISUALIZATION": {
        "version": "canvas-specialist-math-visualization-proposal-v1", "pattern": "MATH_VISUALIZATION",
        "title": "Plot point P", "prompt": "Move P to (2, 3).",
        "point": {"semantic_key": "point-p", "label": "P", "initial_x": 0, "initial_y": 0, "support_ids": ["F1"]},
        "target": {"x": 2, "y": 3, "support_ids": ["F2", "R1"]},
        "x_range": {"minimum": -4, "maximum": 4}, "y_range": {"minimum": -4, "maximum": 4},
        "interaction_affordances": ["PLACE_POINT", "SUBMIT_CONSTRUCTION"], "text_equivalent": "Point P belongs at (2, 3).",
    },
    "MATH_INPUT": {
        "version": "canvas-specialist-math-input-proposal-v1", "pattern": "MATH_INPUT",
        "title": "Write a fraction sum", "prompt": "Enter three quarters plus one quarter.",
        "initial_latex": "", "expected_form": "LATEX", "expression_max_length": 120,
        "support_ids": ["F1", "F2", "R1"], "interaction_affordances": ["SUBMIT_EXPRESSION"],
        "text_equivalent": "Enter the fraction sum and submit it.",
    },
}


def _pending(factory: sessionmaker[Session], pattern: str):
    admitted = admit_visual_order(_order(pattern), authorized_source_references={}, visual_personalization_catalog={}, core_profile={"grade_level": "5"})
    with factory.begin() as session:
        user = m.User(identity_provider="canvas-final", external_subject=uuid4().hex); session.add(user); session.flush()
        student = m.Student(user_id=user.id, display_name="Lina Test"); session.add(student); session.flush()
        learning = m.LearningSession(student_id=student.id, subject="MATH", status="OPEN"); session.add(learning); session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        message = m.LearningMessage(session_id=learning.id, role="tutor", content="Let us use Canvas.", payload={"workspace_visual": {"status": "ADMITTED", "order_digest": admitted.order_digest, "frozen_composition_pack": admitted.frozen_composition_pack}})
        session.add(message); session.flush()
        run = admit_committed_visual_order(session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
        assert run is not None
        return student.id, learning.id, runtime.id, run.id


def _compose(factory: sessionmaker[Session], pattern: str):
    ids = _pending(factory, pattern)

    class Specialist:
        calls = 0

        def execute(self, route, payload):
            self.calls += 1
            assert route.model == "canvas-fixture"
            return ModelResult(output=PROPOSALS[pattern])

    specialist = Specialist()
    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(session, routes={m.ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "canvas-fixture")}, providers={"fixture": specialist}))
    assert run_once(factory, registry, worker_id=f"compose-{pattern.lower()}") == m.JobStatus.COMPLETED
    return (*ids, specialist.calls)


def _admit_existing(factory: sessionmaker[Session], student_id, learning_id, pattern: str):
    admitted = admit_visual_order(_order(pattern), authorized_source_references={}, visual_personalization_catalog={}, core_profile={"grade_level": "5"})
    with factory.begin() as session:
        message = m.LearningMessage(session_id=learning_id, role="tutor", content="Compose a replacement.", payload={"workspace_visual": {"status": "ADMITTED", "order_digest": admitted.order_digest, "frozen_composition_pack": admitted.frozen_composition_pack}})
        session.add(message); session.flush()
        run = admit_committed_visual_order(session, student_id=student_id, learning_session_id=learning_id, source_message_id=message.id)
        assert run is not None
        return run.id


@pytest.mark.parametrize("pattern", tuple(PROPOSALS))
def test_specialist_scene_event_snapshot_reload_and_same_tutor_continuation(factory: sessionmaker[Session], pattern: str):
    student_id, learning_id, runtime_id, run_id, specialist_calls = _compose(factory, pattern)
    assert specialist_calls == 1
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); assert run is not None and run.scene_id is not None
        scene = session.get(m.StudioScene, run.scene_id); assert scene is not None and scene.status == "ACTIVE"
        service = StudioStateService(session)
        if pattern == "SPATIAL_MANIPULATION":
            actions = [("PLACE_OBJECT", {"object_id": "three-quarters", "target_id": "less-than-one"})]
        elif pattern == "MATH_VISUALIZATION":
            actions = [("PLACE_POINT", {"point_id": "point-p", "x": 2, "y": 3}), ("SUBMIT_CONSTRUCTION", {"point_id": "point-p", "x": 2, "y": 3})]
        else:
            actions = [("SUBMIT_EXPRESSION", {"format": "latex", "value": r"\frac{3}{4}+\frac{1}{4}"})]
        interaction_id = None
        registry = production_subject_registry()
        for index, (action_key, payload) in enumerate(actions):
            action_contract = registry.resolve_action(scene.subject_key, scene.subject_profile_version, scene.activity_key, scene.activity_contract_version, action_key)
            result = service.append_event(AppendStudioEventCommand(
                runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id,
                event_kind=None, event_schema_version=None, actor=StudioActor.STUDENT,
                payload_schema_version=action_contract.payload_schema_version, payload=payload,
                scene_id=scene.id, base_scene_version=scene.scene_version,
                action_key=action_key, idempotency_key=f"{pattern}-{index}",
            ))
            assert result.scene is not None
            scene = result.scene
            interaction_id = result.interaction.id if result.interaction is not None else interaction_id
        stored = service.runtime_state(runtime_id=runtime_id, student_id=student_id)["snapshot"]
        rebuilt = service.rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert stored == rebuilt
        assert interaction_id is not None

    with factory() as reloaded:
        reloaded_snapshot = StudioStateService(reloaded).runtime_state(runtime_id=runtime_id, student_id=student_id)["snapshot"]
        assert reloaded_snapshot == stored

    class Tutor:
        calls = 0

        def execute(self, route, payload):
            self.calls += 1
            assert payload["studio_interaction_context"]["source"]["event"]["activity_key"] == stored["active_activity_key"]
            return ModelResult(output={"text": f"Tutor continuation for {pattern}", "workspace_intent": None})

    tutor = Tutor()
    continuation = StudioInteractionTutorService(bind=factory.kw["bind"], gateway_factory=lambda session: ModelGateway(session, routes={m.ModelTask.TUTOR: ModelRoute("fixture", "primary-tutor-fixture")}, providers={"fixture": tutor}))
    result = continuation.execute(student_id=student_id, learning_session_id=learning_id, runtime_id=runtime_id, interaction_id=interaction_id)
    admission = StudioInteractionTutorAdmission(context=result.context, observation_id=None, workspace_context=None)
    turn = continuation.persist_canvas_turn(admission=admission, result=result.result, student_id=student_id)
    continuation.finalize_delivered_turn(admission=admission, turn=turn, student_id=student_id)
    with factory() as session:
        interaction = session.get(m.StudioStudentInteraction, interaction_id)
        message = session.get(m.LearningMessage, turn.message_id)
        assert tutor.calls == 1 and interaction is not None and interaction.status == "COMPLETED"
        assert message is not None and message.payload["turn_origin"] == "STUDIO_INTERACTION"
        assert message.content == f"Tutor continuation for {pattern}"


@pytest.mark.parametrize("pattern", tuple(PROPOSALS))
def test_invalid_replacement_never_creates_a_scene_and_prior_scene_survives(factory: sessionmaker[Session], pattern: str):
    student_id, learning_id, runtime_id, _, _ = _compose(factory, pattern)
    with factory() as session:
        prior = session.execute(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE")).scalar_one()
        prior_id = prior.id
    run_id = _admit_existing(factory, student_id, learning_id, pattern)

    class InvalidSpecialist:
        calls = 0
        def execute(self, route, payload):
            self.calls += 1
            return ModelResult(output={**PROPOSALS[pattern], "renderer": "forbidden"})

    provider = InvalidSpecialist()
    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(session, routes={m.ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "invalid-fixture")}, providers={"fixture": provider}))
    assert run_once(factory, registry, worker_id=f"invalid-{pattern.lower()}") == m.JobStatus.FAILED
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        active = session.execute(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE")).scalar_one()
        assert provider.calls == 1 and run is not None and run.status == "FAILED" and run.scene_id is None
        assert active.id == prior_id


@pytest.mark.parametrize("pattern", tuple(PROPOSALS))
def test_reused_or_chat_only_scene_creates_zero_specialist_generations(factory: sessionmaker[Session], pattern: str):
    student_id, learning_id, _, _, _ = _compose(factory, pattern)
    with factory.begin() as session:
        for status in ("REUSED", "NOT_REQUESTED"):
            message = m.LearningMessage(session_id=learning_id, role="tutor", content=status, payload={"workspace_visual": {"status": status}})
            session.add(message); session.flush()
            assert admit_committed_visual_order(session, student_id=student_id, learning_session_id=learning_id, source_message_id=message.id) is None
        assert session.query(m.StudioCanvasSpecialistRun).count() == 1


@pytest.mark.parametrize("pattern", tuple(PROPOSALS))
def test_stale_specialist_result_cannot_replace_changed_active_scene(factory: sessionmaker[Session], pattern: str):
    student_id, learning_id, runtime_id, _, _ = _compose(factory, pattern)
    run_id = _admit_existing(factory, student_id, learning_id, pattern)
    with factory.begin() as session:
        scene = session.execute(select(m.StudioScene).where(
            m.StudioScene.studio_runtime_id == runtime_id,
            m.StudioScene.status == "ACTIVE",
        )).scalar_one()
        if pattern == "SPATIAL_MANIPULATION":
            action_key, payload = "PLACE_OBJECT", {"object_id": "three-quarters", "target_id": "less-than-one"}
        elif pattern == "MATH_VISUALIZATION":
            action_key, payload = "PLACE_POINT", {"point_id": "point-p", "x": 1, "y": 1}
        else:
            action_key, payload = "SUBMIT_EXPRESSION", {"format": "latex", "value": "1+1"}
        contract = production_subject_registry().resolve_action(
            scene.subject_key, scene.subject_profile_version, scene.activity_key,
            scene.activity_contract_version, action_key,
        )
        changed = StudioStateService(session).append_event(AppendStudioEventCommand(
            runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id,
            event_kind=None, event_schema_version=None, actor=StudioActor.STUDENT,
            payload_schema_version=contract.payload_schema_version, payload=payload,
            scene_id=scene.id, base_scene_version=scene.scene_version, action_key=action_key,
            idempotency_key=f"stale-change-{pattern}",
        )).scene
        assert changed is not None
        changed_version = changed.scene_version

    class Specialist:
        def execute(self, route, payload):
            return ModelResult(output=PROPOSALS[pattern])

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(
        session, routes={m.ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "stale-fixture")},
        providers={"fixture": Specialist()},
    ))
    assert run_once(factory, registry, worker_id=f"stale-{pattern.lower()}") == m.JobStatus.COMPLETED
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        active = session.execute(select(m.StudioScene).where(
            m.StudioScene.studio_runtime_id == runtime_id,
            m.StudioScene.status == "ACTIVE",
        )).scalar_one()
        assert run is not None and run.status == "REJECTED" and run.scene_id is None
        assert run.failure_metadata == {"code": "ACTIVE_SCENE_CHANGED"}
        assert active.scene_version == changed_version


@pytest.mark.skipif(os.getenv("LIVE_CANVAS_PRODUCTION_PROOF") != "1", reason="explicit live proof only")
@pytest.mark.parametrize("pattern", tuple(PROPOSALS))
def test_live_luna_non_process_worker_path(factory: sessionmaker[Session], pattern: str):
    student_id, _, runtime_id, run_id = _pending(factory, pattern)
    outputs: list[dict[str, object]] = []

    def recording_gateway(session: Session):
        gateway = create_canvas_specialist_gateway(session)

        class RecordingGateway:
            def execute(self, *args, **kwargs):
                result = gateway.execute(*args, **kwargs)
                outputs.append(result.output)
                return result

        return RecordingGateway()

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=recording_gateway)
    status = run_once(factory, registry, worker_id=f"live-{pattern.lower()}")
    assert status == m.JobStatus.COMPLETED, outputs
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.status == "COMPLETED" and run.scene_id is not None
        scene = session.get(m.StudioScene, run.scene_id)
        execution = session.get(m.AIExecution, run.ai_execution_id)
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert scene is not None and scene.seed_payload["pattern"] == pattern
        assert execution is not None and execution.provider == "openai" and execution.success
        assert replay["current_scene_id"] == scene.id
