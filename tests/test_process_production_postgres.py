"""CS-05 atomic Process Scene acceptance on the disposable PostgreSQL database."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db import models as m
from services.platform.db.models import ModelTask
from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.model_gateway.factory import create_canvas_specialist_gateway
from services.studio.canvas_specialist import admit_committed_visual_order
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.interactions import StudioInteractionTutorService
from services.studio.process_production_acceptance import ProcessAcceptanceFailure, accept_completed_process_run
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from services.studio.subjects import process_visual as awareness
from workers.studio_handlers import _settle
from workers.job_worker import JobHandlerRegistry, run_once
from workers.studio_handlers import reconcile_canvas_specialist_runs, register_canvas_specialist_handlers


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


def _v2_pack() -> dict[str, object]:
    pack = _pack()
    pack.update(version="frozen-composition-pack-v2", capability_pack={"identity": "process-capability-pack-v2", "process_stage_limit": [2, 8]}, allowed_motion_intents=["REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"])
    return pack


def _v2_proposal(*, invalid: bool = False) -> dict[str, object]:
    proposal = _proposal()
    proposal.update(version="canvas-specialist-process-proposal-v2", motion_intents=["TRACE_CYCLE"] if invalid else ["REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"])
    return proposal


def _v2_cycle_pack() -> dict[str, object]:
    pack = _v2_pack()
    pack.update(
        topology="CYCLE",
        admitted_order={"objective": "Explain the water cycle: evaporation, condensation, collection, and the return to evaporation."},
        allowed_motion_intents=["REVEAL_IN_ORDER", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"],
    )
    return pack


def _v2_cycle_proposal() -> dict[str, object]:
    return {
        "version": "canvas-specialist-process-proposal-v2", "pattern": "PROCESS", "topology": "CYCLE",
        "title": "The water cycle", "subtitle": "Water returns to where it started.",
        "stages": [
            {"semantic_key": "evaporate", "label": "Evaporate", "detail": "Water rises as vapor.", "support_ids": ["F1"], "art_handle": "drop"},
            {"semantic_key": "condense", "label": "Condense", "detail": "Vapor forms clouds.", "support_ids": ["F2"], "art_handle": "filter"},
            {"semantic_key": "collect", "label": "Collect", "detail": "Water returns to Earth.", "support_ids": ["F1"], "art_handle": "drop"},
        ],
        "relations": [
            {"relation_key": "evaporate-to-condense", "source_semantic_key": "evaporate", "target_semantic_key": "condense", "label": "then", "support_ids": ["R1"]},
            {"relation_key": "condense-to-collect", "source_semantic_key": "condense", "target_semantic_key": "collect", "label": "then", "support_ids": ["R1"]},
            {"relation_key": "collect-to-evaporate", "source_semantic_key": "collect", "target_semantic_key": "evaporate", "label": "returns", "support_ids": ["R1"]},
        ],
        "text_equivalent": "Water evaporates, condenses, collects, and returns to evaporation.",
        "focus_intent": None,
        "motion_intents": ["REVEAL_IN_ORDER", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"],
        "interaction_affordances": ["FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION"],
    }


def _v2_pending_run(factory: sessionmaker[Session]) -> tuple[object, object, object, object, object]:
    student_id, learning_id, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); assert run is not None
        source = session.get(m.LearningMessage, run.source_message_id); assert source is not None
        pack = _v2_pack(); digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        source.payload = {"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}}
        run.capability_profile_version, run.output_schema_version, run.order_digest, run.status, run.proposal_payload = "process-capability-pack-v2", "canvas-specialist-process-proposal-v2", digest, "PENDING", None
        job = session.get(m.Job, run.job_id); assert job is not None
        job.payload = {**job.payload, "order_digest": digest, "capability_identity": "process-capability-pack-v2"}
        return student_id, learning_id, runtime_id, run_id, job.id


def test_v2_worker_persists_motion_scene_and_fresh_rebuild(factory: sessionmaker[Session]) -> None:
    student_id, _, runtime_id, run_id, _ = _v2_pending_run(factory); calls = 0
    class Provider:
        def execute(self, route, payload):
            nonlocal calls; calls += 1; return ModelResult(output=_v2_proposal())
    registry = JobHandlerRegistry(); register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "v2")}, providers={"fixture": Provider()}))
    assert run_once(factory, registry, worker_id="v2-valid") == m.JobStatus.COMPLETED
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); scene = session.get(m.StudioScene, run.scene_id)
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert calls == 1 and run.proposal_payload == _v2_proposal() and scene.seed_payload["motion_intents"] == _v2_proposal()["motion_intents"] and replay["state_payload"]["scene_seed"]["motion_intents"] == _v2_proposal()["motion_intents"]


def test_v2_cycle_worker_settles_into_snapshot_and_replays_semantic_operations(factory: sessionmaker[Session]) -> None:
    """CS-04 Worker and CS-05 acceptance preserve one real V2 cycle end to end."""
    student_id, learning_id, runtime_id, run_id, job_id = _v2_pending_run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); assert run is not None
        source = session.get(m.LearningMessage, run.source_message_id); assert source is not None
        pack = _v2_cycle_pack(); digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        source.payload = {"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}}
        run.order_digest = digest
        job = session.get(m.Job, job_id); assert job is not None
        job.payload = {**job.payload, "order_digest": digest}

    calls = 0

    class Provider:
        def execute(self, route, payload):
            nonlocal calls
            calls += 1
            return ModelResult(output=_v2_cycle_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry,
        session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session,
            routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "v2")},
            providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="v2-cycle") == m.JobStatus.COMPLETED

    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); assert run is not None and run.scene_id is not None
        scene = session.get(m.StudioScene, run.scene_id); assert scene is not None
        state = StudioStateService(session)
        state.append_event(AppendStudioEventCommand(
            runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id,
            event_kind=None, event_schema_version=None, actor=StudioActor.STUDENT,
            payload_schema_version="process-visual-production-action-v1", payload={"target_id": "evaporate"},
            scene_id=scene.id, base_scene_version=scene.scene_version, action_key="FOCUS_OBJECT",
            idempotency_key="cs04-cs05-cycle-focus",
        ))
        scene = session.get(m.StudioScene, scene.id); assert scene is not None
        state.append_event(AppendStudioEventCommand(
            runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id,
            event_kind=None, event_schema_version=None, actor=StudioActor.STUDENT,
            payload_schema_version="process-visual-production-action-v1", payload={"target_id": "collect-to-evaporate"},
            scene_id=scene.id, base_scene_version=scene.scene_version, action_key="TRACE_RELATION",
            idempotency_key="cs04-cs05-cycle-trace",
        ))

    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); job = session.get(m.Job, job_id)
        assert run is not None and run.scene_id is not None and run.status == "COMPLETED"
        scene = session.get(m.StudioScene, run.scene_id); assert scene is not None
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        process_state = replay["state_payload"]["process_visual_production"]
        assert calls == 1 and job is not None and job.max_attempts == 2 and job.attempt_count == 1
        assert scene.status == "ACTIVE" and scene.seed_payload["topology"] == "cycle"
        assert scene.seed_payload["motion_intents"] == _v2_cycle_proposal()["motion_intents"]
        assert "TRACE_CYCLE" in scene.seed_payload["motion_intents"] and "TRACE_SEQUENCE" not in scene.seed_payload["motion_intents"]
        assert {relation["id"] for relation in scene.seed_payload["relations"]} >= {"collect-to-evaporate"}
        assert replay["current_scene_id"] == scene.id and replay["state_payload"]["scene_seed"] == scene.seed_payload
        assert process_state["focused_stage_id"] == "evaporate" and process_state["tracing_relation_id"] == "collect-to-evaporate"
        assert session.scalar(select(m.CandidateEvent).where(m.CandidateEvent.session_id == learning_id)) is None
        assert session.scalar(select(m.PersonalFact).where(m.PersonalFact.student_id == student_id)) is None
        assert session.scalar(select(m.LearnerIntelligenceCard).where(m.LearnerIntelligenceCard.student_id == student_id)) is None


@pytest.mark.skipif(os.getenv("LIVE_CANVAS_SPECIALIST_PROOF") != "1", reason="explicit live proof only")
@pytest.mark.parametrize(("topology", "proposal"), [("SEQUENCE", _v2_proposal), ("CYCLE", _v2_cycle_proposal)])
def test_live_luna_v2_worker_path(factory: sessionmaker[Session], topology: str, proposal) -> None:
    student_id, _, runtime_id, run_id, job_id = _v2_pending_run(factory)
    if topology == "CYCLE":
        with factory.begin() as session:
            run = session.get(m.StudioCanvasSpecialistRun, run_id); source = session.get(m.LearningMessage, run.source_message_id)
            assert run is not None and source is not None
            pack = _v2_cycle_pack(); digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            source.payload = {"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}}
            run.order_digest = digest
            job = session.get(m.Job, job_id); assert job is not None
            job.payload = {**job.payload, "order_digest": digest}
    registry = JobHandlerRegistry(); register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=create_canvas_specialist_gateway)
    assert run_once(factory, registry, worker_id=f"live-{topology.lower()}") == m.JobStatus.COMPLETED
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); job = session.get(m.Job, job_id)
        assert run is not None and job is not None and run.status == "COMPLETED" and run.scene_id is not None
        scene = session.get(m.StudioScene, run.scene_id); execution = session.get(m.AIExecution, run.ai_execution_id)
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        allowed_motion = {"REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"} if topology == "SEQUENCE" else {"REVEAL_IN_ORDER", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"}
        assert scene is not None and scene.seed_payload["topology"] == topology.lower() and set(scene.seed_payload["motion_intents"]).issubset(allowed_motion)
        assert job.max_attempts == 2 and job.attempt_count == 1 and execution is not None and execution.provider == "openai" and execution.success and replay["current_scene_id"] == scene.id


def test_v2_invalid_motion_is_terminal_without_regeneration(factory: sessionmaker[Session]) -> None:
    _, _, runtime_id, run_id, _ = _v2_pending_run(factory); calls = 0
    class Provider:
        def execute(self, route, payload):
            nonlocal calls; calls += 1; return ModelResult(output=_v2_proposal(invalid=True))
    registry = JobHandlerRegistry(); register_canvas_specialist_handlers(registry, session_factory=factory, gateway_factory=lambda session: ModelGateway(session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "v2")}, providers={"fixture": Provider()}))
    assert run_once(factory, registry, worker_id="v2-invalid") == m.JobStatus.FAILED
    assert run_once(factory, registry, worker_id="v2-invalid-again") is None
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id); active = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE"))
        assert calls == 1 and run.status == "FAILED" and run.scene_id is None and active is not None and active.activity_key == awareness.ACTIVITY_KEY


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
        run.status, run.proposal_payload, run.completed_at = "COMPLETED", _proposal(), datetime.now(UTC)
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


def test_aud01_settle_reports_deterministic_scene_rejection_not_stale_completed_status(
    factory: sessionmaker[Session],
) -> None:
    """A committed proposal's job result reflects the later deterministic Run truth."""
    _, _, _, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None
        run.status = "RUNNING"
        run.proposal_payload = None
        run.base_scene_version += 1

    result = _settle(factory, run_id, _proposal(), None)

    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.status == "REJECTED"
        assert result["run_status"] == "REJECTED"
        assert result["scene_id"] is None


def test_aud01_completed_within_generation_deadline_can_settle_after_restart(
    factory: sessionmaker[Session],
) -> None:
    """Acceptance judges the durable completion instant, never reconciliation wall time."""
    from datetime import UTC, datetime, timedelta

    _, _, _, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None
        run.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
        run.completed_at = run.deadline_at - timedelta(seconds=1)

        scene = accept_completed_process_run(session, run_id)
        assert scene is not None


def test_aud01_scene_rejection_keeps_successful_compose_job_truthful(
    factory: sessionmaker[Session],
) -> None:
    """A deterministic CS-05 rejection is not a false provider failure."""
    _, _, _, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.job_id is not None
        run.status, run.proposal_payload, run.base_scene_version = "PENDING", None, run.base_scene_version + 1
        job_id = run.job_id
    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output=_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="aud01-rejected") == m.JobStatus.COMPLETED
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert calls == 1
        assert run is not None and run.status == "REJECTED" and isinstance(run.proposal_payload, dict)
        assert job is not None and job.status == "COMPLETED"
        assert job.result is not None and job.result["run_status"] == "REJECTED"


def test_aud01_transient_settlement_defers_without_regeneration_then_reconciles(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed deterministic effect is retryable from the committed proposal only."""
    _, _, _, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.job_id is not None
        run.status, run.proposal_payload = "PENDING", None
        job_id = run.job_id
    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            return ModelResult(output=_proposal())

    def injected_failure(session: Session, run_id: object):
        raise ProcessAcceptanceFailure("injected transient settlement failure")

    monkeypatch.setattr("workers.studio_handlers.accept_completed_process_run", injected_failure)
    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="aud01-deferred") == m.JobStatus.COMPLETED
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert calls == 1
        assert run is not None and run.status == "COMPLETED" and isinstance(run.proposal_payload, dict)
        assert run.scene_id is None and run.failure_metadata == {"code": "SCENE_SETTLEMENT_DEFERRED"}
        assert job is not None and job.status == "COMPLETED"

    monkeypatch.setattr("workers.studio_handlers.accept_completed_process_run", accept_completed_process_run)
    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session) == 0
    with factory() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert calls == 1
        assert run is not None and run.status == "COMPLETED" and run.scene_id is not None


def test_aud01_corrupt_durable_proposal_is_rejected_and_never_reconciled(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only infrastructure failures defer; proposal-to-seed invalidity is terminal."""
    _, _, runtime_id, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.job_id is not None
        job = session.get(m.Job, run.job_id)
        assert job is not None
        run.proposal_payload = {"corrupt": "durable proposal"}
        job.status = "COMPLETED"
        job_id = job.id

        assert accept_completed_process_run(session, run_id) is None

    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        active = session.scalar(select(m.StudioScene).where(m.StudioScene.studio_runtime_id == runtime_id, m.StudioScene.status == "ACTIVE"))
        assert run is not None and run.status == "REJECTED" and run.scene_id is None
        assert run.failure_metadata == {"code": "PROPOSAL_TO_SCENE_INVALID"}
        assert run.proposal_payload == {"corrupt": "durable proposal"}
        assert job is not None and job.status == "COMPLETED"
        assert active is not None and active.activity_key == awareness.ACTIVITY_KEY

    attempts = 0
    def settlement_must_not_run(session: Session, run_id: object):
        nonlocal attempts
        attempts += 1
        raise AssertionError("REJECTED runs must not re-enter settlement")

    monkeypatch.setattr("workers.studio_handlers.accept_completed_process_run", settlement_must_not_run)
    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session) == 0
    assert attempts == 0


def test_aud01_reconciliation_repairs_false_failed_job_after_durable_proposal(
    factory: sessionmaker[Session],
) -> None:
    """A crash after proposal commit cannot leave accepted Scene truth paired with Job FAILED."""
    _, _, _, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.job_id is not None
        job = session.get(m.Job, run.job_id)
        assert job is not None
        job.status, job.last_error = "FAILED", "old settlement exception"
        job_id = job.id

    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session) == 1
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert run is not None and run.status == "COMPLETED" and run.scene_id is not None
        assert job is not None and job.status == "COMPLETED" and job.last_error is None
        assert job.result is not None and job.result["run_status"] == "COMPLETED"


def test_aud01_reconciliation_and_newer_admission_terminate_without_lock_inversion(
    factory: sessionmaker[Session],
) -> None:
    """PostgreSQL proves reconciliation no longer holds Run while acquiring Runtime."""
    student_id, learning_id, _, old_run_id = _run(factory)
    with factory.begin() as session:
        old = session.get(m.StudioCanvasSpecialistRun, old_run_id)
        assert old is not None
        source = session.get(m.LearningMessage, old.source_message_id)
        assert source is not None
        pack = dict(source.payload["workspace_visual"]["frozen_composition_pack"])
        pack["admitted_order"] = {"objective": "Explain the newer process."}
        digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        message = m.LearningMessage(
            session_id=learning_id, role="tutor", content="Newer Tutor order",
            payload={"workspace_visual": {"status": "ADMITTED", "order_digest": digest, "frozen_composition_pack": pack}},
            created_at=source.created_at + timedelta(microseconds=1),
        )
        session.add(message); session.flush()
        newer_message_id = message.id
    gate = Barrier(2)

    def reconcile() -> int:
        gate.wait(timeout=2)
        with factory.begin() as session:
            session.execute(text("SET LOCAL lock_timeout = '1000ms'"))
            return reconcile_canvas_specialist_runs(session)

    def admit_newer() -> object:
        with factory.begin() as session:
            gate.wait(timeout=2)
            return admit_committed_visual_order(
                session, student_id=student_id, learning_session_id=learning_id, source_message_id=newer_message_id,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        reconciled = pool.submit(reconcile)
        newer = pool.submit(admit_newer)
        assert reconciled.result(timeout=5) >= 0
        new_run = newer.result(timeout=5)
    assert new_run is not None
    with factory() as session:
        old = session.get(m.StudioCanvasSpecialistRun, old_run_id)
        newest = session.get(m.StudioCanvasSpecialistRun, new_run.id)
        assert old is not None and old.status in {"REJECTED", "SUPERSEDED"} and old.scene_id is None
        assert newest is not None and newest.source_message_id == newer_message_id and newest.status == "PENDING"


def test_aud01_genuinely_late_provider_result_is_terminal_without_scene_or_regeneration(
    factory: sessionmaker[Session],
) -> None:
    """The protected post-provider deadline check still rejects a late model result."""
    _, _, _, run_id = _run(factory)
    with factory.begin() as session:
        run = session.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.job_id is not None
        run.status, run.proposal_payload = "PENDING", None
        job_id = run.job_id
    calls = 0

    class LateProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            calls += 1
            with factory.begin() as session:
                run = session.get(m.StudioCanvasSpecialistRun, run_id)
                assert run is not None
                run.deadline_at = datetime.now(UTC) - timedelta(seconds=1)
            return ModelResult(output=_proposal())

    registry = JobHandlerRegistry()
    register_canvas_specialist_handlers(
        registry, session_factory=factory,
        gateway_factory=lambda session: ModelGateway(
            session, routes={ModelTask.CANVAS_SPECIALIST: ModelRoute("fixture", "gpt-5.6-luna")}, providers={"fixture": LateProvider()},
        ),
    )
    assert run_once(factory, registry, worker_id="aud01-late") == m.JobStatus.COMPLETED
    assert run_once(factory, registry, worker_id="aud01-late-again") is None
    with factory() as session:
        run, job = session.get(m.StudioCanvasSpecialistRun, run_id), session.get(m.Job, job_id)
        assert calls == 1
        assert run is not None and run.status == "FAILED" and run.scene_id is None and run.proposal_payload is None
        assert job is not None and job.status == "COMPLETED"


def test_aud01_unusable_completed_run_cannot_poison_other_reconciliation_work(
    factory: sessionmaker[Session],
) -> None:
    """One deterministic rejection leaves the same poll usable for another eligible completion."""
    _, _, _, bad_run_id = _run(factory)
    _, _, _, good_run_id = _run(factory)
    clock = datetime.now(UTC)
    with factory.begin() as session:
        bad = session.get(m.StudioCanvasSpecialistRun, bad_run_id)
        good = session.get(m.StudioCanvasSpecialistRun, good_run_id)
        assert bad is not None and good is not None and good.job_id is not None
        bad.base_scene_version += 1
        good_job = session.get(m.Job, good.job_id)
        assert good_job is not None
        good_job.status, good_job.attempt_count, good_job.lease_expires_at = "RUNNING", 1, clock - timedelta(seconds=1)
        good_job_id = good_job.id

    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session, now=clock) == 1
    with factory() as session:
        bad, good, good_job = session.get(m.StudioCanvasSpecialistRun, bad_run_id), session.get(m.StudioCanvasSpecialistRun, good_run_id), session.get(m.Job, good_job_id)
        assert bad is not None and bad.status == "REJECTED" and bad.scene_id is None
        assert good is not None and good.status == "COMPLETED" and good.scene_id is not None
        assert good_job is not None and good_job.status == "COMPLETED"


def test_aud01_rejected_corrupt_run_is_skipped_while_another_completion_settles(
    factory: sessionmaker[Session],
) -> None:
    """A prior terminal proposal rejection cannot poison later polling work."""
    _, _, _, rejected_run_id = _run(factory)
    _, _, _, eligible_run_id = _run(factory)
    clock = datetime.now(UTC)
    with factory.begin() as session:
        rejected = session.get(m.StudioCanvasSpecialistRun, rejected_run_id)
        eligible = session.get(m.StudioCanvasSpecialistRun, eligible_run_id)
        assert rejected is not None and eligible is not None and eligible.job_id is not None
        rejected.proposal_payload = {"corrupt": "poisoned durable proposal"}
        assert accept_completed_process_run(session, rejected_run_id) is None
        assert rejected.status == "REJECTED"
        eligible_job = session.get(m.Job, eligible.job_id)
        assert eligible_job is not None
        eligible_job.status, eligible_job.attempt_count, eligible_job.lease_expires_at = "RUNNING", 1, clock - timedelta(seconds=1)
        eligible_job_id = eligible_job.id

    with factory.begin() as session:
        assert reconcile_canvas_specialist_runs(session, now=clock) == 1
    with factory() as session:
        rejected = session.get(m.StudioCanvasSpecialistRun, rejected_run_id)
        eligible = session.get(m.StudioCanvasSpecialistRun, eligible_run_id)
        eligible_job = session.get(m.Job, eligible_job_id)
        assert rejected is not None and rejected.status == "REJECTED" and rejected.scene_id is None
        assert eligible is not None and eligible.status == "COMPLETED" and eligible.scene_id is not None
        assert eligible_job is not None and eligible_job.status == "COMPLETED"


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
