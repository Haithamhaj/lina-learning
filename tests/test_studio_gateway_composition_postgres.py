"""Real application Gateway composition and Canvas continuation regressions."""

from __future__ import annotations

import importlib
import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole
from services.platform.auth.clerk import get_current_principal
from services.platform.config import Settings, reset_settings_cache
from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.platform.db.session import get_session
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Disposable PostgreSQL required")


@pytest.fixture
def application(monkeypatch):
    from apps.api.main import app

    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("MODEL_NAME", "mock")
    reset_settings_cache()
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_student_interactions, studio_events, studio_snapshots, studio_scenes, studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"))
    factory = sessionmaker(engine)
    def database_session():
        with factory.begin() as session:
            yield session
    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(subject="gateway-canvas", role=UserRole.STUDENT)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, factory
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)
        engine.dispose()
        reset_settings_cache()


def prepare_submission(client, factory, subject):
    module_name, seed_name = {
        "MATH": ("math_make_ten", "make_ten_scene_seed"),
        "SCIENCE": ("process_sequence", "process_sequence_scene_seed"),
        "ENGLISH": ("sentence_ordering", "sentence_ordering_scene_seed"),
        "ARABIC": ("arabic_sentence_ordering", "arabic_sentence_ordering_scene_seed"),
    }[subject]
    activity = importlib.import_module("services.studio.subjects." + module_name)
    seed = getattr(activity, seed_name)()
    with factory.begin() as session:
        user = m.User(identity_provider="clerk", external_subject="gateway-canvas", role="STUDENT")
        session.add(user)
        session.flush()
        student = m.Student(user_id=user.id, display_name="Gateway fixture")
        session.add(student)
        session.flush()
        learning_session = m.LearningSession(student_id=student.id)
        session.add(learning_session)
        session.flush()
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning_session.id,
            subject_key=subject, subject_profile_version="subject-profile-v2",
            concept_keys=(activity.ACTIVITY_KEY,), activity_key=activity.ACTIVITY_KEY,
            artifact_type="interactive-activity", renderer_key=activity.RENDERER_KEY,
            renderer_version=activity.RENDERER_VERSION, activity_contract_version=activity.ACTIVITY_VERSION,
            payload_schema_version=activity.SCENE_PAYLOAD_SCHEMA_VERSION, seed_payload=seed,
            accessibility_payload=activity.ACCESSIBILITY_PAYLOAD, locale="ar", direction="rtl",
        ))
        service.append_event(AppendStudioEventCommand(
            runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
            event_kind="studio.scene.activated", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
            actor=StudioActor.SYSTEM, payload_schema_version="studio-scene-activated-v1", payload={},
            scene_id=scene.id, base_scene_version=scene.scene_version, idempotency_key="activate",
        ))
        runtime_id, session_id, scene_id = runtime.id, learning_session.id, scene.id
    if subject == "MATH":
        payload = {"ten_frame_item_ids": seed["groups"]["ten-frame"]["item_ids"], "ones_group_item_ids": seed["groups"]["ones-group"]["item_ids"]}
    else:
        key = "stage_ids" if subject == "SCIENCE" else "token_ids"
        payload = {key: seed[key]}
    operation = dict(scene_id=str(scene_id), base_scene_version=2, action_key="SUBMIT_CONFIGURATION", payload=payload, idempotency_key="fresh-submit")
    response = client.post(f"/api/v1/student/studio/{runtime_id}/operations", json=operation)
    assert response.status_code == 200
    assert response.json()["student_interaction_status"] == "PENDING"
    return runtime_id, session_id, UUID(response.json()["student_interaction_id"]), operation


def protected_counts(session):
    models = (m.CandidateEvent, m.LearningEvent, m.LearningEvidence, m.CurrentLearningState, m.LearnerPattern, m.LearnerIntelligenceCard, m.PersonalFact, m.PersonalFactObservation, m.PersonalFactExtractionRun, m.StudioCanvasSpecialistRun)
    return [session.scalar(select(func.count()).select_from(model)) for model in models]


@pytest.mark.parametrize("subject", ["MATH", "SCIENCE", "ENGLISH", "ARABIC"])
def test_real_application_mock_gateway_completes_canvas_without_chat_question(application, monkeypatch, subject):
    """Neither Gateway factory nor Gateway is replaced: construction and execution are real."""
    from services.tutor.runtime import LocalTutorProvider

    client, factory = application
    runtime_id, session_id, interaction_id, operation = prepare_submission(client, factory, subject)
    with factory() as session:
        before = protected_counts(session)
    calls = []
    original = LocalTutorProvider.execute
    def observe(self, route, payload):
        assert "question" not in payload
        assert isinstance(payload["studio_interaction_context"], dict)
        assert isinstance(payload["studio_workspace_context"], dict)
        calls.append((route.provider, route.model))
        return original(self, route, payload)
    monkeypatch.setattr(LocalTutorProvider, "execute", observe)
    path = f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream"
    response = client.post(path)
    assert response.status_code == 200
    assert "event: turn" in response.text
    assert "event: delta" in response.text
    assert calls == [("local-demo", "mock")]
    with factory() as session:
        interaction = session.get(m.StudioStudentInteraction, interaction_id)
        event = session.get(m.StudioEvent, interaction.source_event_id)
        execution = session.get(m.AIExecution, interaction.ai_execution_id)
        messages = list(session.scalars(select(m.LearningMessage).where(m.LearningMessage.session_id == session_id)))
        observation = session.scalar(select(m.StudioTutorObservation).where(m.StudioTutorObservation.student_interaction_id == interaction_id))
        assert interaction.status == "COMPLETED" and event.action_key == "SUBMIT_CONFIGURATION"
        assert len(messages) == 1 and messages[0].role == "tutor"
        message = messages[0]
        assert message.id == interaction.tutor_message_id
        assert message.ai_execution_id == execution.id == observation.ai_execution_id
        assert message.payload["turn_origin"] == "STUDIO_INTERACTION"
        assert message.payload["student_interaction_id"] == str(interaction_id)
        assert execution.task == "tutor" and execution.success
        assert execution.provider == "local-demo" and execution.model == "mock"
        assert execution.operation_id == interaction_id and execution.learning_session_id == session_id
        assert observation.status == "COMMITTED" and observation.through_event_sequence == 3
        assert session.get(m.StudioRuntime, runtime_id).last_tutor_observation_sequence == 3
        assert protected_counts(session) == before
    assert client.post(path).status_code == 409
    replay = client.post(f"/api/v1/student/studio/{runtime_id}/operations", json=operation)
    assert replay.status_code == 200 and replay.json()["replayed"]
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(m.StudioStudentInteraction)) == 1
        assert session.scalar(select(func.count()).select_from(m.AIExecution).where(m.AIExecution.learning_session_id == session_id)) == 1
        assert session.scalar(select(func.count()).select_from(m.LearningMessage).where(m.LearningMessage.session_id == session_id)) == 1


@pytest.mark.parametrize("failure", ["construction", "provider"])
def test_real_application_gateway_failure_is_terminal_without_false_ack(application, monkeypatch, failure):
    from services.model_gateway import factory as gateway_factory
    from services.tutor.runtime import LocalTutorProvider

    client, factory = application
    runtime_id, session_id, interaction_id, _operation = prepare_submission(client, factory, "MATH")
    if failure == "construction":
        missing = Settings(_env_file=None, model_provider="mock").model_copy(update={"model_provider": "openai", "model_api_key": None})
        monkeypatch.setattr(gateway_factory, "get_settings", lambda: missing)
    else:
        def unavailable(self, route, payload):
            raise RuntimeError("Controlled provider failure")
        monkeypatch.setattr(LocalTutorProvider, "execute", unavailable)
    response = client.post(f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream")
    assert "event: turn" not in response.text
    with factory() as session:
        interaction = session.get(m.StudioStudentInteraction, interaction_id)
        observation = session.scalar(select(m.StudioTutorObservation).where(m.StudioTutorObservation.student_interaction_id == interaction_id))
        assert interaction.status == observation.status == "FAILED"
        assert interaction.tutor_message_id is None
        assert session.get(m.StudioRuntime, runtime_id).last_tutor_observation_sequence == 0
        assert session.scalar(select(func.count()).select_from(m.LearningMessage).where(m.LearningMessage.session_id == session_id)) == 0
        executions = list(session.scalars(select(m.AIExecution).where(m.AIExecution.learning_session_id == session_id)))
        assert len(executions) == (0 if failure == "construction" else 1)
        assert all(not execution.success for execution in executions)


def test_canvas_factory_retains_real_provider_routing_without_live_calls(application, monkeypatch):
    from apps.api.routes.student import create_studio_interaction_tutor_gateway
    from services.model_gateway import factory as gateway_factory
    from services.model_gateway.gateway import ModelResult, StreamComplete, StreamDelta
    from services.model_gateway.openai_provider import OpenAIResponsesProvider
    from services.tutor.runtime import LocalTutorProvider

    _client, factory = application
    settings = Settings(_env_file=None, model_provider="openai", model_name="real-route-fixture", model_api_key="test-only-not-a-credential")
    monkeypatch.setattr(gateway_factory, "get_settings", lambda: settings)
    def real_transport_stub(self, route, payload):
        assert route.provider == "openai"
        yield StreamDelta("Real transport fixture.")
        yield StreamComplete(ModelResult(output={"text": "Real transport fixture.", "workspace_intent": None}))
    def never_local(*args, **kwargs):
        raise AssertionError("Real configuration fell back to the local provider")
    monkeypatch.setattr(OpenAIResponsesProvider, "stream", real_transport_stub)
    monkeypatch.setattr(LocalTutorProvider, "execute", never_local)
    with factory.begin() as session:
        events = list(create_studio_interaction_tutor_gateway(session).stream(m.ModelTask.TUTOR, {"input": "fixture"}))
        assert events[-1].result.output["text"] == "Real transport fixture."
    with factory() as session:
        execution = session.scalar(select(m.AIExecution).where(m.AIExecution.model == "real-route-fixture"))
        assert execution.provider == "openai" and execution.success


def test_local_provider_preserves_chat_and_never_echoes_canvas_internal_context():
    from services.tutor.runtime import LocalTutorProvider
    from services.model_gateway.gateway import ModelRoute

    provider = LocalTutorProvider()
    route = ModelRoute("local-demo", "mock")
    chat = provider.execute(route, {"question": "Compare 9 and 6"})
    assert chat.output["text"] == "Let’s work on this step by step. Compare 9 and 6"
    canvas = provider.execute(route, {
        "studio_interaction_context": {"private_probe": "INTERNAL-CONTEXT-NOT-LEARNER-TEXT"},
        "studio_workspace_context": {"private_probe": "INTERNAL-WORKSPACE-NOT-LEARNER-TEXT"},
    })
    assert canvas.output["text"] == "Development Tutor: your saved Workspace submission was received."
    assert canvas.output["workspace_intent"] is None
    with pytest.raises((KeyError, ValueError)):
        provider.execute(route, {"studio_interaction_context": None})


@pytest.mark.parametrize("lane", ["daily", "math"])
def test_real_application_local_chat_composition_remains_usable(application, lane):
    client, factory = application
    _runtime_id, session_id, _interaction_id, _operation = prepare_submission(client, factory, "MATH")
    response = client.post(f"/api/v1/student/{lane}/session/{session_id}/turn/stream", json={"content": "Compare 9 and 6"})
    assert response.status_code == 200 and "event: turn" in response.text
    with factory() as session:
        messages = list(session.scalars(select(m.LearningMessage).where(m.LearningMessage.session_id == session_id).order_by(m.LearningMessage.created_at)))
        assert [(message.role, message.content) for message in messages] == [
            ("student", "Compare 9 and 6"),
            ("tutor", "Let’s work on this step by step. Compare 9 and 6"),
        ]
        execution = session.scalar(select(m.AIExecution).where(m.AIExecution.learning_session_id == session_id))
        assert execution.provider == "local-demo" and execution.success
