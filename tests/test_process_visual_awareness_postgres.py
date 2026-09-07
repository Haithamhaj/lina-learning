"""Actual accepted Process state through normal Tutor and Runtime-03, mock transport only."""

import json
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from services.platform.db import models as m
from services.studio.subjects import process_visual as v
from services.studio.contracts import (
    CreateSceneCommand,
    AppendStudioEventCommand,
    StudioActor,
)
from services.studio.service import StudioStateService, StudioStateError
from services.studio.tutor_context import select_studio_tutor_context
from services.studio.interactions import StudioInteractionTutorService
from services.model_gateway.gateway import (
    ModelGateway,
    ModelRoute,
    ModelResult,
    StreamComplete,
    StreamDelta,
)
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContextBuilder
from services.tutor.runtime import TutorRuntime
from test_studio_process_sequence_postgres import (
    postgres_session_factory as _postgres_session_factory,
    _student,
    _learning_session,
    _activate,
)
from test_process_visual_awareness import seed


postgres_session_factory = _postgres_session_factory


def setup(factory):
    with factory.begin() as s:
        student = _student(s, "visual-awareness-fixture")
        lesson = _learning_session(s, student)
        svc = StudioStateService(s)
        runtime = svc.get_or_create_runtime(
            student_id=student.id, learning_session_id=lesson.id
        )
        scene = svc.accept_scene(
            CreateSceneCommand(
                student.id,
                lesson.id,
                "SCIENCE",
                ("butterfly-life-cycle",),
                v.ACTIVITY_KEY,
                "semantic-process",
                v.RENDERER_KEY,
                v.RENDERER_VERSION,
                v.ACTIVITY_VERSION,
                v.SEED_VERSION,
                seed(),
                subject_profile_version=v.PROFILE_VERSION,
                locale="en",
                direction="ltr",
            )
        )
        _activate(
            svc,
            runtime_id=runtime.id,
            student=student,
            learning_session=lesson,
            scene=scene,
        )
        return student.id, lesson.id, runtime.id, scene.id


def action(factory, ids, key, target):
    student, lesson, runtime, scene_id = ids
    with factory.begin() as s:
        scene = s.get(m.StudioScene, scene_id)
        return StudioStateService(s).append_event(
            AppendStudioEventCommand(
                runtime,
                student,
                lesson,
                None,
                None,
                StudioActor.STUDENT,
                v.ACTION_VERSION,
                {"target_id": target},
                uuid4().hex,
                action_key=key,
                scene_id=scene_id,
                base_scene_version=scene.scene_version,
            )
        )


def counts(s):
    return tuple(
        s.scalar(select(func.count()).select_from(t))
        for t in (
            m.CandidateEvent,
            m.LearningEvent,
            m.LearningEvidence,
            m.PersonalFact,
            m.PersonalFactObservation,
            m.CurrentLearningState,
            m.LearnerPattern,
            m.StudioCanvasSpecialistRun,
        )
    )


class Capture:
    def __init__(self, canvas=False):
        self.calls = []
        self.canvas = canvas

    def stream(self, route, payload):
        self.calls.append(payload)
        assert "VISUAL_GUIDANCE_V1" in payload["instructions"]
        encoded = payload["input"]
        assert (
            "image_url" not in encoded
            and "<svg" not in encoded
            and "scene_seed" not in encoded
        )
        if self.canvas:
            current = payload["studio_interaction_context"]["current_interaction"]
            assert (
                current["action"] == "REQUEST_EXPLANATION"
                and current["target_id"] == "pupa"
            )
            assert current["label"] == "Chrysalis"
            visual = payload["studio_workspace_context"]["snapshot"]["visual_scene"]
            assert visual["state"]["focused_stage_id"] == "adult"
            assert "question" not in payload
        else:
            assert "Why does the chrysalis come after the caterpillar?" in encoded
            marker = "Studio Workspace Context (current authoritative Workspace state; unseen Events are meaningful Student actions since the last successful Tutor observation):\n"
            visual = json.JSONDecoder().raw_decode(encoded.split(marker)[1])[0][
                "snapshot"
            ]["visual_scene"]
            assert visual["state"]["focused_stage_id"] == "pupa"
        assert [o["id"] for o in visual["objects"]] == ["egg", "larva", "pupa", "adult"]
        assert visual["relations"][-1]["meaning"] == "Female lays eggs · new generation"
        relation = next(
            r for r in visual["relations"] if r["from"] == "larva" and r["to"] == "pupa"
        )
        detail = next(
            o["detail"] for o in visual["objects"] if o["id"] == relation["to"]
        )
        # Deterministic answer demonstrates semantic data availability, not model quality.
        answer = "Caterpillar → Chrysalis: " + relation["meaning"] + ". " + detail
        yield StreamDelta(answer)
        yield StreamComplete(
            ModelResult(
                output={
                    "text": answer,
                    "workspace_intent": None,
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
                }
            )
        )

    def gateway(self, s):
        return ModelGateway(
            s,
            routes={
                m.ModelTask.TUTOR: ModelRoute("fixture", "semantic-canvas-capture")
            },
            providers={"fixture": self},
        )


def test_normal_chat_uses_actual_accepted_scene_one_primary_call(
    postgres_session_factory,
):
    f = postgres_session_factory
    ids = setup(f)
    action(f, ids, "FOCUS_OBJECT", "pupa")
    provider = Capture()
    with f.begin() as s:
        before = counts(s)
    with f.begin() as s:
        runtime = TutorRuntime(
            s,
            context_builder=TutorContextBuilder(
                s, retrieval_service=RetrievalService(s)
            ),
            safety_policy=SafetyPolicyService(s),
            gateway=provider.gateway(s),
        )
        list(
            runtime.stream_turn(
                learning_session=s.get(m.LearningSession, ids[1]),
                question="Why does the chrysalis come after the caterpillar?",
            )
        )
    assert len(provider.calls) == 1
    with f() as s:
        assert counts(s) == before
        assert (
            s.scalar(
                select(func.count())
                .select_from(m.LearningMessage)
                .where(
                    m.LearningMessage.session_id == ids[1],
                    m.LearningMessage.role == "student",
                )
            )
            == 1
        )
        assert "develops inside" in s.scalar(
            select(m.LearningMessage.content).where(
                m.LearningMessage.session_id == ids[1],
                m.LearningMessage.role == "tutor",
            )
        )


def test_runtime03_exact_source_survives_later_record_only_focus(
    postgres_session_factory,
):
    f = postgres_session_factory
    ids = setup(f)
    action(f, ids, "FOCUS_OBJECT", "pupa")
    action(f, ids, "REQUEST_EXPLANATION", "pupa")
    with f() as s:
        interaction = s.scalar(
            select(m.StudioStudentInteraction).where(
                m.StudioStudentInteraction.studio_runtime_id == ids[2]
            )
        )
        interaction_id = interaction.id
        before = counts(s)
    action(f, ids, "FOCUS_OBJECT", "adult")
    provider = Capture(canvas=True)
    svc = StudioInteractionTutorService(
        bind=f.kw["bind"], gateway_factory=provider.gateway
    )
    admission = svc.admit(
        student_id=ids[0],
        learning_session_id=ids[1],
        runtime_id=ids[2],
        interaction_id=interaction_id,
    )
    events = list(svc.stream_admitted(admission=admission, student_id=ids[0]))
    result = next(e.result for e in events if isinstance(e, StreamComplete))
    turn = svc.persist_canvas_turn(
        admission=admission, result=result, student_id=ids[0]
    )
    svc.finalize_delivered_turn(admission=admission, turn=turn, student_id=ids[0])
    assert len(provider.calls) == 1
    payload = provider.calls[0]
    assert payload["studio_interaction_context"]["source"]["event"][
        "action_payload"
    ] == {"target_id": "pupa"}
    assert (
        payload["studio_interaction_context"]["source"]["event"]["scene_version"]
        < payload["studio_workspace_context"]["snapshot"]["current_scene_version"]
    )
    with f() as s:
        assert counts(s) == before
        assert list(
            s.scalars(
                select(m.LearningMessage.role).where(
                    m.LearningMessage.session_id == ids[1]
                )
            )
        ) == ["tutor"]
        assert s.get(m.StudioStudentInteraction, interaction_id).status == "COMPLETED"
        replay = StudioStateService(s).rebuild_snapshot(
            runtime_id=ids[2], student_id=ids[0]
        )
        assert replay["state_payload"][v.ACTIVITY_KEY]["focused_stage_id"] == "adult"


def test_selection_scope_version_and_malformed_seed(postgres_session_factory):
    f = postgres_session_factory
    ids = setup(f)
    bind = f.kw["bind"]
    assert (
        select_studio_tutor_context(
            bind=bind, student_id=uuid4(), learning_session_id=ids[1]
        )
        is None
    )
    selected = select_studio_tutor_context(
        bind=bind, student_id=ids[0], learning_session_id=ids[1]
    )
    assert selected.context.visual_scene
    with pytest.raises(StudioStateError):
        action(f, ids, "REQUEST_EXPLANATION", "unknown")
    with f.begin() as s:
        scene = s.get(m.StudioScene, ids[3])
        scene.seed_payload = {**scene.seed_payload, "css": "PRIVATE-PATH"}
    selected = select_studio_tutor_context(
        bind=bind, student_id=ids[0], learning_session_id=ids[1]
    )
    assert selected.context.visual_scene is None
    assert "PRIVATE-PATH" not in json.dumps(selected.context.as_model_payload())


def test_accepted_server_seed_is_rendered_by_actual_process_view(
    postgres_session_factory,
):
    import subprocess
    from pathlib import Path

    f = postgres_session_factory
    ids = setup(f)
    action(f, ids, "FOCUS_OBJECT", "pupa")
    with f() as session:
        state = StudioStateService(session).rebuild_snapshot(
            runtime_id=ids[2], student_id=ids[0]
        )["state_payload"]
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", str(root / "tests/process_visual_render_proof.cjs")],
        input=json.dumps({"seed": state["scene_seed"], "state": state[v.ACTIVITY_KEY]}),
        text=True,
        capture_output=True,
        check=True,
        cwd=root,
    )
    proof = json.loads(result.stdout)
    assert proof["focus"] == "pupa" and len(proof["objects"]) == 4


def test_selection_omits_absent_and_mismatched_version(postgres_session_factory):
    f = postgres_session_factory
    ids = setup(f)
    bind = f.kw["bind"]
    assert (
        select_studio_tutor_context(
            bind=bind, student_id=ids[0], learning_session_id=uuid4()
        )
        is None
    )
    with f.begin() as session:
        session.get(m.StudioScene, ids[3]).scene_version += 1
    selected = select_studio_tutor_context(
        bind=bind, student_id=ids[0], learning_session_id=ids[1]
    )
    assert selected.context.visual_scene is None
