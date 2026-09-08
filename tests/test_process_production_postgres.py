"""CS-05 atomic Process Scene acceptance on the disposable PostgreSQL database."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.studio.canvas_specialist import admit_committed_visual_order
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.interactions import StudioInteractionTutorService
from services.studio.process_production_acceptance import ProcessAcceptanceFailure, accept_completed_process_run
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from services.studio.subjects import process_visual as awareness


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, studio_canvas_specialist_runs, studio_tutor_observations, studio_student_interactions, studio_events, studio_snapshots, studio_scenes, studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _seed() -> dict[str, object]:
    return {
        "title": "Old process", "subtitle": "The prior usable explanation.", "locale": "en", "topology": "sequence",
        "sourceLabel": "Tutor-approved Process explanation", "sourceUrl": "https://lina.local/process",
        "stages": [
            {"id": "old-start", "label": "Old start", "detail": "The old first step.", "art": "idea"},
            {"id": "old-end", "label": "Old end", "detail": "The old second step.", "art": "review"},
        ],
        "relations": [{"id": "old-next", "from": "old-start", "to": "old-end", "label": "then"}],
    }


def _pack() -> dict[str, object]:
    return {
        "version": "frozen-composition-pack-v1", "pattern": "PROCESS", "topology": "SEQUENCE", "locale": "en", "direction": "ltr",
        "capability_pack": {"identity": "process-capability-pack-v1", "process_stage_limit": [2, 8]},
        "semantic_alignment": {
            "required_semantics": [{"id": "F1"}, {"id": "F2"}],
            "required_relations": [{"id": "R1"}], "must_not_imply": [],
        },
        "admitted_order": {"objective": "Explain a two-stage process."},
        "grounding": {"origin": "ADMITTED_TUTOR_ORDER", "excerpts": []},
        "allowed_affordances": ["FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION"],
        "allowed_art_handles": ["drop", "filter"],
    }


def _proposal() -> dict[str, object]:
    return {
        "version": "canvas-specialist-process-proposal-v1", "pattern": "PROCESS", "topology": "SEQUENCE",
        "title": "Water filtration", "subtitle": "Water moves through each step.",
        "stages": [
            {"semantic_key": "collect", "label": "Collect", "detail": "Collect water.", "support_ids": ["F1"], "art_handle": "drop"},
            {"semantic_key": "filter", "label": "Filter", "detail": "Filter particles.", "support_ids": ["F2"], "art_handle": "filter"},
        ],
        "relations": [{"relation_key": "collect-to-filter", "source_semantic_key": "collect", "target_semantic_key": "filter", "label": "then", "support_ids": ["R1"]}],
        "text_equivalent": "Collect water, then filter it.", "focus_intent": None, "motion_intents": [],
        "interaction_affordances": ["FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION"],
    }


def _run(factory: sessionmaker[Session], *, with_active: bool = True) -> tuple[object, object, object, object]:
    with factory.begin() as session:
        user = m.User(identity_provider="cs05", external_subject=uuid4().hex)
        session.add(user); session.flush()
        student = m.Student(user_id=user.id, display_name="CS-05 fixture")
        session.add(student); session.flush()
        learning = m.LearningSession(student_id=student.id, subject="SCIENCE", status="OPEN")
        session.add(learning); session.flush()
        state = StudioStateService(session)
        runtime = state.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        old = state.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning.id, subject_key="SCIENCE", subject_profile_version=awareness.PROFILE_VERSION,
            concept_keys=("old-process",), activity_key=awareness.ACTIVITY_KEY, artifact_type="visual-explanation",
            renderer_key=awareness.RENDERER_KEY, renderer_version=awareness.RENDERER_VERSION, activity_contract_version=awareness.ACTIVITY_VERSION,
            payload_schema_version=awareness.SEED_VERSION, seed_payload=_seed(), accessibility_payload={}, locale="en", direction="ltr",
        ))
        if with_active:
            state.append_event(AppendStudioEventCommand(runtime_id=runtime.id, student_id=student.id, learning_session_id=learning.id,
            event_kind="studio.scene.activated", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
            payload_schema_version="studio-scene-activated-v1", payload={}, scene_id=old.id, base_scene_version=old.scene_version,
            idempotency_key="cs05-old-activate"))
        pack = _pack(); digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        message = m.LearningMessage(session_id=learning.id, role="tutor", content="Tutor order", payload={"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}})
        session.add(message); session.flush()
        run = admit_committed_visual_order(session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
        assert run is not None
        run.status, run.proposal_payload = "COMPLETED", _proposal()
        return student.id, learning.id, runtime.id, run.id


def test_atomic_replacement_is_replayable_and_idempotent(factory: sessionmaker[Session]) -> None:
    student_id, _, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        scene = accept_completed_process_run(session, run_id)
        assert scene is not None
        assert accept_completed_process_run(session, run_id).id == scene.id
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        active = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE"))
        old = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "SUPERSEDED"))
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert run is not None and run.scene_id == active.id and run.accepted_scene_version == active.scene_version
        assert old is not None and active.activity_key == "process_visual_production"
        assert replay["current_scene_id"] == active.id and replay["state_payload"]["scene_seed"] == active.seed_payload


def test_first_activation_without_prior_active_scene_is_authoritative(factory: sessionmaker[Session]) -> None:
    student_id, _, runtime_id, run_id = _run(factory, with_active=False)
    with factory.begin() as session:
        scene = accept_completed_process_run(session, run_id)
        assert scene is not None
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        active = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE"))
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert run is not None and active is not None and run.scene_id == active.id and run.accepted_scene_version == active.scene_version
        assert replay["current_scene_id"] == active.id


def test_rollback_keeps_prior_active_scene_usable(factory: sessionmaker[Session]) -> None:
    student_id, _, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        with pytest.raises(ProcessAcceptanceFailure):
            accept_completed_process_run(session, run_id, before_commit=lambda: (_ for _ in ()).throw(ProcessAcceptanceFailure("injected")))
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        active = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE"))
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert run is not None and run.scene_id is None and run.status == "COMPLETED"
        assert active is not None and active.activity_key == awareness.ACTIVITY_KEY
        assert replay["current_scene_id"] == active.id


def test_stale_result_is_rejected_without_replacing_active_scene(factory: sessionmaker[Session]) -> None:
    _, _, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        run.base_scene_version += 1
        assert accept_completed_process_run(session, run_id) is None
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        active = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE"))
        assert run is not None and run.status == "REJECTED" and run.failure_metadata == {"code": "ACTIVE_SCENE_CHANGED"}
        assert active is not None and active.activity_key == awareness.ACTIVITY_KEY


def test_relation_explanation_uses_one_runtime03_tutor_turn_with_exact_source(factory: sessionmaker[Session]) -> None:
    student_id, learning_id, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        scene = accept_completed_process_run(session, run_id)
        assert scene is not None
        event = StudioStateService(session).append_event(AppendStudioEventCommand(
            runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id, event_kind=None, actor=StudioActor.STUDENT,
            event_schema_version=None, payload_schema_version="process-visual-production-action-v1",
            payload={"target_id": "collect-to-filter"}, scene_id=scene.id, base_scene_version=scene.scene_version,
            action_key="REQUEST_EXPLANATION", idempotency_key="cs05-relation-explain",
        ))
        assert event.interaction is not None
        interaction_id = event.interaction.id

    class Provider:
        calls: list[dict[str, object]] = []

        def stream(self, route, payload):
            self.calls.append(payload)
            source = payload["studio_interaction_context"]["current_interaction"]
            if len(self.calls) == 1:
                assert source == {"action": "REQUEST_EXPLANATION", "target_id": "collect-to-filter", "target_kind": "relation", "from": "collect", "to": "filter", "meaning": "then"}
            else:
                assert source == {"action": "REQUEST_EXPLANATION", "target_id": "collect", "target_kind": "object", "label": "Collect", "detail": "Collect water."}
            output = {"text": "Collect comes before filter in this process.", "workspace_intent": None, "suggested_actions": [], "guided_check": None,
                "teaching_mode": None, "teaching_strategy": None, "teaching_method_id": None, "prior_method_relation": None,
                "candidate_metadata": None, "provisional_broad_subject": None, "segment_relation": None, "structured_segment_state": None}
            yield StreamDelta(output["text"])
            yield StreamComplete(ModelResult(output=output))

        def gateway(self, session):
            return ModelGateway(session, routes={m.ModelTask.TUTOR: ModelRoute("fixture", "primary-tutor")}, providers={"fixture": self})

    provider = Provider()
    service = StudioInteractionTutorService(bind=factory.kw["bind"], gateway_factory=provider.gateway)
    admission = service.admit(student_id=student_id, learning_session_id=learning_id, runtime_id=runtime_id, interaction_id=interaction_id)
    events = list(service.stream_admitted(admission=admission, student_id=student_id))
    result = next(item.result for item in events if isinstance(item, StreamComplete))
    turn = service.persist_canvas_turn(admission=admission, result=result, student_id=student_id)
    service.finalize_delivered_turn(admission=admission, turn=turn, student_id=student_id)

    with factory.begin() as session:
        current = session.get(m.StudioScene, scene.id)
        stage_event = StudioStateService(session).append_event(AppendStudioEventCommand(
            runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id, event_kind=None, actor=StudioActor.STUDENT,
            event_schema_version=None, payload_schema_version="process-visual-production-action-v1", payload={"target_id": "collect"},
            scene_id=current.id, base_scene_version=current.scene_version, action_key="REQUEST_EXPLANATION", idempotency_key="cs05-stage-explain"))
        stage_interaction_id = stage_event.interaction.id
    stage_admission = service.admit(student_id=student_id, learning_session_id=learning_id, runtime_id=runtime_id, interaction_id=stage_interaction_id)
    stage_events = list(service.stream_admitted(admission=stage_admission, student_id=student_id))
    stage_result = next(item.result for item in stage_events if isinstance(item, StreamComplete))
    stage_turn = service.persist_canvas_turn(admission=stage_admission, result=stage_result, student_id=student_id)
    service.finalize_delivered_turn(admission=stage_admission, turn=stage_turn, student_id=student_id)

    with factory() as session:
        interaction = session.get(m.StudioStudentInteraction, interaction_id)
        stage_interaction = session.get(m.StudioStudentInteraction, stage_interaction_id)
        assert len(provider.calls) == 2 and interaction is not None and interaction.status == "COMPLETED" and stage_interaction is not None and stage_interaction.status == "COMPLETED"
        assert session.scalar(select(m.LearningMessage).where(m.LearningMessage.session_id == learning_id, m.LearningMessage.role == "student")) is None


def test_focus_reveal_and_trace_are_record_only_and_replay_exactly(factory: sessionmaker[Session]) -> None:
    student_id, learning_id, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        scene = accept_completed_process_run(session, run_id)
        assert scene is not None
        state = StudioStateService(session)
        for action, target in (("FOCUS_OBJECT", "collect"), ("REVEAL_OBJECT_DETAIL", "filter"), ("TRACE_RELATION", "collect-to-filter")):
            scene = session.get(m.StudioScene, scene.id)
            state.append_event(AppendStudioEventCommand(runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id,
                event_kind=None, event_schema_version=None, actor=StudioActor.STUDENT, payload_schema_version="process-visual-production-action-v1",
                payload={"target_id": target}, scene_id=scene.id, base_scene_version=scene.scene_version, action_key=action,
                idempotency_key=f"cs05-record-only:{action}"))
    with factory() as session:
        assert session.scalar(select(m.AIExecution).where(m.AIExecution.task == "canvas_specialist")) is None
        assert session.scalar(select(m.StudioCanvasSpecialistRun).where(m.StudioCanvasSpecialistRun.id == run_id)).scene_id is not None
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        state = replay["state_payload"]["process_visual_production"]
        assert state["focused_stage_id"] == "collect" and state["active_explanation_stage_id"] == "filter"
        assert state["highlighted_relation_ids"] == ["collect-to-filter"]
        assert state["tracing_relation_id"] == "collect-to-filter"
