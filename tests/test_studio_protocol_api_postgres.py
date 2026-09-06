"""Authenticated API contracts for Studio protocol v1."""

from __future__ import annotations

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole
from services.platform.auth.clerk import get_current_principal
from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.models import (
    AIExecution,
    LearningMessage,
    LearningSession,
    StudioScene,
    StudioStudentInteraction,
    StudioTutorObservation,
    Student,
    User,
)
from services.platform.db.session import get_session
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.feed import StudioEventFeed
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from tests.test_studio_state_postgres import _studio_test_registry


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Studio protocol API contracts",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student_session(factory: sessionmaker[Session], *, subject: str) -> tuple[UUID, UUID]:
    with factory.begin() as session:
        user = User(identity_provider="clerk", external_subject=subject, role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id, display_name="Protocol Student")
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        return student.id, learning_session.id


def _client(factory: sessionmaker[Session], *, subject: str) -> TestClient:
    from apps.api.main import app

    def database_session():
        with factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject,
        role=UserRole.STUDENT,
        email=f"{subject}@example.test",
    )
    return TestClient(app)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


def test_open_and_snapshot_are_student_owned_and_do_not_create_a_scene(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Opening is idempotent runtime/snapshot initialization, never activity creation."""

    _student_id, learning_session_id = _student_session(postgres_session_factory, subject="studio-owner")
    client = _client(postgres_session_factory, subject="studio-owner")
    try:
        opened = client.post(f"/api/v1/student/studio/session/{learning_session_id}/open")
        assert opened.status_code == 200
        body = opened.json()
        runtime_id = body["runtime_id"]
        assert body["latest_event_sequence"] == 0

        snapshot = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
        assert snapshot.status_code == 200
        assert snapshot.json()["latest_event_sequence"] == 0

        other = _client(postgres_session_factory, subject=f"other-{uuid4().hex}")
        assert other.get(f"/api/v1/student/studio/{runtime_id}/snapshot").status_code == 404
    finally:
        _clear_overrides()


def test_snapshot_without_an_active_scene_exposes_a_null_scene_contract(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A client can distinguish real Chat-only state from a missing Workspace projection."""

    _student_id, learning_session_id = _student_session(
        postgres_session_factory,
        subject="studio-empty-scene-contract",
    )
    client = _client(postgres_session_factory, subject="studio-empty-scene-contract")
    try:
        opened = client.post(f"/api/v1/student/studio/session/{learning_session_id}/open")
        assert opened.status_code == 200

        snapshot = client.get(f"/api/v1/student/studio/{opened.json()['runtime_id']}/snapshot")

        assert snapshot.status_code == 200
        assert snapshot.json()["active_scene_contract"] is None
    finally:
        _clear_overrides()


def test_snapshot_exposes_the_exact_persisted_math_scene_contract(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """The public Workspace identity comes from the active persisted Scene, never inferred."""

    from services.studio.subjects.math_make_ten import (  # noqa: PLC0415 - test reads the accepted contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        ACCESSIBILITY_PAYLOAD,
        MATH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION,
        make_ten_scene_seed,
    )

    student_id, learning_session_id = _student_session(
        postgres_session_factory,
        subject="studio-math-scene-contract",
    )
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session)
        runtime = state.get_or_create_runtime(
            student_id=student_id,
            learning_session_id=learning_session_id,
        )
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id,
                learning_session_id=learning_session_id,
                subject_key="MATH",
                subject_profile_version=MATH_PROFILE_VERSION,
                concept_keys=("make-ten",),
                activity_key=ACTIVITY_KEY,
                artifact_type="interactive-activity",
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                activity_contract_version=ACTIVITY_VERSION,
                payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                seed_payload=make_ten_scene_seed(),
                accessibility_payload=ACCESSIBILITY_PAYLOAD,
                locale="en",
                direction="auto",
            )
        )
        state.append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id,
                student_id=student_id,
                learning_session_id=learning_session_id,
                event_kind="studio.scene.activated",
                event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM,
                payload_schema_version="studio-scene-activated-v1",
                payload={},
                scene_id=scene.id,
                base_scene_version=scene.scene_version,
                idempotency_key=f"activate:{scene.id}",
            )
        )
        expected_scene_id = str(scene.id)
        expected_scene_version = scene.scene_version
        runtime_id = runtime.id

    client = _client(postgres_session_factory, subject="studio-math-scene-contract")
    try:
        response = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")

        assert response.status_code == 200
        body = response.json()
        assert body["active_scene_contract"] == {
            "scene_id": expected_scene_id,
            "scene_version": expected_scene_version,
            "subject_key": "MATH",
            "subject_profile_version": MATH_PROFILE_VERSION,
            "activity_key": ACTIVITY_KEY,
            "activity_contract_version": ACTIVITY_VERSION,
            "renderer_key": RENDERER_KEY,
            "renderer_version": RENDERER_VERSION,
            "payload_schema_version": SCENE_PAYLOAD_SCHEMA_VERSION,
            "locale": "en",
            "direction": "auto",
        }
        assert body["active_scene_seed"] == make_ten_scene_seed()
        assert body["current_scene_id"] == expected_scene_id
        assert body["current_scene_version"] == expected_scene_version
    finally:
        _clear_overrides()


def test_snapshot_exposes_exact_persisted_science_and_english_scene_contracts(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Every accepted non-Math renderer receives its identity from its persisted Scene."""

    from services.studio.subjects.process_sequence import (  # noqa: PLC0415 - accepted contract fixtures
        ACCESSIBILITY_PAYLOAD as SCIENCE_ACCESSIBILITY,
        ACTIVITY_KEY as SCIENCE_ACTIVITY,
        ACTIVITY_VERSION as SCIENCE_ACTIVITY_VERSION,
        process_sequence_scene_seed,
        RENDERER_KEY as SCIENCE_RENDERER,
        RENDERER_VERSION as SCIENCE_RENDERER_VERSION,
        SCIENCE_PROFILE_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION as SCIENCE_PAYLOAD_SCHEMA,
    )
    from services.studio.subjects.sentence_ordering import (  # noqa: PLC0415 - accepted contract fixtures
        ACCESSIBILITY_PAYLOAD as ENGLISH_ACCESSIBILITY,
        ACTIVITY_KEY as ENGLISH_ACTIVITY,
        ACTIVITY_VERSION as ENGLISH_ACTIVITY_VERSION,
        ENGLISH_PROFILE_VERSION,
        RENDERER_KEY as ENGLISH_RENDERER,
        RENDERER_VERSION as ENGLISH_RENDERER_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION as ENGLISH_PAYLOAD_SCHEMA,
        sentence_ordering_scene_seed,
    )

    accepted = (
        {
            "student_subject": "studio-science-scene-contract",
            "subject_key": "SCIENCE",
            "profile": SCIENCE_PROFILE_VERSION,
            "activity": SCIENCE_ACTIVITY,
            "activity_version": SCIENCE_ACTIVITY_VERSION,
            "renderer": SCIENCE_RENDERER,
            "renderer_version": SCIENCE_RENDERER_VERSION,
            "payload_schema": SCIENCE_PAYLOAD_SCHEMA,
            "seed": process_sequence_scene_seed,
            "accessibility": SCIENCE_ACCESSIBILITY,
            "locale": "ar",
            "direction": "rtl",
        },
        {
            "student_subject": "studio-english-scene-contract",
            "subject_key": "ENGLISH",
            "profile": ENGLISH_PROFILE_VERSION,
            "activity": ENGLISH_ACTIVITY,
            "activity_version": ENGLISH_ACTIVITY_VERSION,
            "renderer": ENGLISH_RENDERER,
            "renderer_version": ENGLISH_RENDERER_VERSION,
            "payload_schema": ENGLISH_PAYLOAD_SCHEMA,
            "seed": sentence_ordering_scene_seed,
            "accessibility": ENGLISH_ACCESSIBILITY,
            "locale": "en",
            "direction": "ltr",
        },
    )
    required_keys = {
        "scene_id", "scene_version", "subject_key", "subject_profile_version",
        "activity_key", "activity_contract_version", "renderer_key", "renderer_version",
        "payload_schema_version", "locale", "direction",
    }

    for spec in accepted:
        student_id, learning_session_id = _student_session(
            postgres_session_factory,
            subject=str(spec["student_subject"]),
        )
        with postgres_session_factory.begin() as session:
            state = StudioStateService(session)
            runtime = state.get_or_create_runtime(
                student_id=student_id,
                learning_session_id=learning_session_id,
            )
            scene = state.accept_scene(
                CreateSceneCommand(
                    student_id=student_id,
                    learning_session_id=learning_session_id,
                    subject_key=str(spec["subject_key"]),
                    subject_profile_version=str(spec["profile"]),
                    concept_keys=(str(spec["activity"]),),
                    activity_key=str(spec["activity"]),
                    artifact_type="interactive-activity",
                    renderer_key=str(spec["renderer"]),
                    renderer_version=str(spec["renderer_version"]),
                    activity_contract_version=str(spec["activity_version"]),
                    payload_schema_version=str(spec["payload_schema"]),
                    seed_payload=spec["seed"](),
                    accessibility_payload=dict(spec["accessibility"]),
                    locale=str(spec["locale"]),
                    direction=str(spec["direction"]),
                )
            )
            state.append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime.id,
                    student_id=student_id,
                    learning_session_id=learning_session_id,
                    event_kind="studio.scene.activated",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-scene-activated-v1",
                    payload={},
                    scene_id=scene.id,
                    base_scene_version=scene.scene_version,
                    idempotency_key=f"activate:{scene.id}",
                )
            )
            runtime_id = runtime.id
            scene_id = str(scene.id)
            scene_version = scene.scene_version

        client = _client(postgres_session_factory, subject=str(spec["student_subject"]))
        try:
            response = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
            assert response.status_code == 200
            body = response.json()
            descriptor = body["active_scene_contract"]
        finally:
            _clear_overrides()

        assert set(descriptor) == required_keys
        assert descriptor == {
            "scene_id": scene_id,
            "scene_version": scene_version,
            "subject_key": spec["subject_key"],
            "subject_profile_version": spec["profile"],
            "activity_key": spec["activity"],
            "activity_contract_version": spec["activity_version"],
            "renderer_key": spec["renderer"],
            "renderer_version": spec["renderer_version"],
            "payload_schema_version": spec["payload_schema"],
            "locale": spec["locale"],
            "direction": spec["direction"],
        }
        assert body["active_scene_seed"] == spec["seed"]()
        assert not any("answer" in key.lower() or "valid" in key.lower() for key in body["active_scene_seed"])


def test_feed_snapshot_carries_the_same_active_scene_contract(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A catch-up Snapshot must not lose the exact Workspace identity seen by direct reads."""

    from services.studio.subjects.math_make_ten import (  # noqa: PLC0415 - test reads the accepted contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        ACCESSIBILITY_PAYLOAD,
        MATH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION,
        make_ten_scene_seed,
    )

    student_id, learning_session_id = _student_session(
        postgres_session_factory,
        subject="studio-feed-scene-contract",
    )
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session)
        runtime = state.get_or_create_runtime(
            student_id=student_id,
            learning_session_id=learning_session_id,
        )
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id,
                learning_session_id=learning_session_id,
                subject_key="MATH",
                subject_profile_version=MATH_PROFILE_VERSION,
                concept_keys=("make-ten",),
                activity_key=ACTIVITY_KEY,
                artifact_type="interactive-activity",
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                activity_contract_version=ACTIVITY_VERSION,
                payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                seed_payload=make_ten_scene_seed(),
                accessibility_payload=ACCESSIBILITY_PAYLOAD,
                locale="en",
                direction="auto",
            )
        )
        state.append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id,
                student_id=student_id,
                learning_session_id=learning_session_id,
                event_kind="studio.scene.activated",
                event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM,
                payload_schema_version="studio-scene-activated-v1",
                payload={},
                scene_id=scene.id,
                base_scene_version=scene.scene_version,
                idempotency_key=f"activate:{scene.id}",
            )
        )
        runtime_id = runtime.id
        expected_scene_id = str(scene.id)

    _latest, _events, frame = StudioEventFeed(
        session_factory=postgres_session_factory,
    )._snapshot_and_events(
        student_id=student_id,
        runtime_id=runtime_id,
        after_sequence=None,
    )

    assert frame["active_scene_contract"] is not None
    assert frame["active_scene_contract"]["scene_id"] == expected_scene_id
    assert frame["active_scene_contract"]["renderer_key"] == RENDERER_KEY
    assert frame["active_scene_contract"]["renderer_version"] == RENDERER_VERSION
    assert frame["active_scene_seed"] == make_ten_scene_seed()
    client = _client(postgres_session_factory, subject="studio-feed-scene-contract")
    try:
        direct = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
    finally:
        _clear_overrides()
    assert direct.status_code == 200
    assert direct.json()["active_scene_contract"] == frame["active_scene_contract"]
    assert direct.json()["active_scene_seed"] == frame["active_scene_seed"]


def test_accepted_but_inactive_scene_has_no_daily_workspace_projection(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A current accepted Scene is reconstruction state, not learner-visible Workspace state."""

    from services.studio.subjects.math_make_ten import (  # noqa: PLC0415 - accepted contract fixture
        ACCESSIBILITY_PAYLOAD,
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        MATH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION,
        make_ten_scene_seed,
    )

    student_id, learning_session_id = _student_session(
        postgres_session_factory,
        subject="studio-accepted-not-active",
    )
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session)
        runtime = state.get_or_create_runtime(student_id=student_id, learning_session_id=learning_session_id)
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id,
                learning_session_id=learning_session_id,
                subject_key="MATH",
                subject_profile_version=MATH_PROFILE_VERSION,
                concept_keys=("make-ten",),
                activity_key=ACTIVITY_KEY,
                artifact_type="interactive-activity",
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                activity_contract_version=ACTIVITY_VERSION,
                payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                seed_payload=make_ten_scene_seed(),
                accessibility_payload=ACCESSIBILITY_PAYLOAD,
                locale="en",
                direction="auto",
            )
        )
        runtime_id = runtime.id

    client = _client(postgres_session_factory, subject="studio-accepted-not-active")
    try:
        response = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")

        assert response.status_code == 200
        assert response.json()["current_scene_id"] == str(scene.id)
        assert response.json()["active_scene_contract"] is None
        assert response.json()["active_scene_seed"] is None

        with postgres_session_factory.begin() as session:
            persisted_scene = session.get(StudioScene, scene.id)
            assert persisted_scene is not None
            StudioStateService(session).append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime_id,
                    student_id=student_id,
                    learning_session_id=learning_session_id,
                    event_kind="studio.scene.activated",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-scene-activated-v1",
                    payload={},
                    scene_id=persisted_scene.id,
                    base_scene_version=persisted_scene.scene_version,
                    idempotency_key=f"activate:{persisted_scene.id}",
                )
            )

        activated = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
        assert activated.status_code == 200
        assert activated.json()["active_scene_contract"] is not None
        assert activated.json()["active_scene_seed"] == make_ten_scene_seed()

        with postgres_session_factory.begin() as session:
            persisted_scene = session.get(StudioScene, scene.id)
            assert persisted_scene is not None
            StudioStateService(session).append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime_id,
                    student_id=student_id,
                    learning_session_id=learning_session_id,
                    event_kind="studio.scene.status_changed",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-scene-status-changed-v1",
                    payload={"status": "SUPERSEDED"},
                    scene_id=persisted_scene.id,
                    base_scene_version=persisted_scene.scene_version,
                    idempotency_key=f"supersede:{persisted_scene.id}",
                )
            )

        superseded = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
    finally:
        _clear_overrides()

    assert superseded.status_code == 200
    assert superseded.json()["current_scene_id"] == str(scene.id)
    assert superseded.json()["active_scene_contract"] is None
    assert superseded.json()["active_scene_seed"] is None


def test_operation_derives_semantics_from_scene_contract_and_is_idempotent(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """The public body cannot choose event kind/schema/trigger semantics."""

    from apps.api.main import app
    from apps.api.routes.studio import get_studio_subject_registry

    student_id, learning_session_id = _student_session(postgres_session_factory, subject="studio-operation")
    registry = _studio_test_registry()
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session, subject_registry=registry)
        state.get_or_create_runtime(student_id=student_id, learning_session_id=learning_session_id)
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id,
                learning_session_id=learning_session_id,
                subject_key="MATH",
                subject_profile_version="fixture-v1",
                concept_keys=("fixture",),
                activity_key="generic-workspace",
                artifact_type="fixture",
                renderer_key="native-react-svg",
                renderer_version="1",
                activity_contract_version="activity-v1",
                payload_schema_version="scene-v1",
                seed_payload={"value": 1},
                accessibility_payload={"summary": "fixture"},
                locale="en",
                direction="ltr",
            )
        )
        scene_id, scene_version = scene.id, scene.scene_version

    app.dependency_overrides[get_studio_subject_registry] = lambda: registry
    client = _client(postgres_session_factory, subject="studio-operation")
    payload = {
        "scene_id": str(scene_id),
        "base_scene_version": scene_version,
        "action_key": "fixture.record",
        "payload": {"value": 2},
        "idempotency_key": "operation-record-1",
    }
    try:
        accepted = client.post(f"/api/v1/student/studio/session/{learning_session_id}/open")
        assert accepted.status_code == 200
        runtime_id = accepted.json()["runtime_id"]
        result = client.post(f"/api/v1/student/studio/{runtime_id}/operations", json=payload)
        assert result.status_code == 200
        assert result.json()["replayed"] is False
        assert result.json()["student_interaction_id"] is None
        assert result.json()["student_interaction_status"] is None

        replay = client.post(f"/api/v1/student/studio/{runtime_id}/operations", json=payload)
        assert replay.status_code == 200
        assert replay.json()["replayed"] is True

        conflicting = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={**payload, "payload": {"value": 3}},
        )
        assert conflicting.status_code == 409

        unknown_action = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                **payload,
                "base_scene_version": scene_version + 1,
                "action_key": "fixture.unknown",
                "idempotency_key": "operation-unknown",
            },
        )
        assert unknown_action.status_code == 422

        forbidden = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={**payload, "idempotency_key": "operation-forbidden", "event_kind": "caller.event"},
        )
        assert forbidden.status_code == 422
    finally:
        app.dependency_overrides.pop(get_studio_subject_registry, None)
        _clear_overrides()


def test_triggering_operation_returns_the_contract_created_pending_interaction(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """The browser discovers an interaction; it never selects the trigger policy."""

    from apps.api.main import app
    from apps.api.routes.studio import get_studio_subject_registry

    student_id, learning_session_id = _student_session(postgres_session_factory, subject="studio-triggering-operation")
    registry = _studio_test_registry()
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session, subject_registry=registry)
        runtime = state.get_or_create_runtime(student_id=student_id, learning_session_id=learning_session_id)
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id,
                learning_session_id=learning_session_id,
                subject_key="MATH",
                subject_profile_version="fixture-v1",
                concept_keys=("fixture",),
                activity_key="generic-workspace",
                artifact_type="fixture",
                renderer_key="native-react-svg",
                renderer_version="1",
                activity_contract_version="activity-v1",
                payload_schema_version="scene-v1",
                seed_payload={"value": 1},
                accessibility_payload={"summary": "fixture"},
                locale="en",
                direction="ltr",
            )
        )
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version

    app.dependency_overrides[get_studio_subject_registry] = lambda: registry
    client = _client(postgres_session_factory, subject="studio-triggering-operation")
    payload = {
        "scene_id": str(scene_id),
        "base_scene_version": scene_version,
        "action_key": "fixture.submit",
        "payload": {"value": 2},
        "idempotency_key": "operation-submit-1",
    }
    try:
        accepted = client.post(f"/api/v1/student/studio/{runtime_id}/operations", json=payload)
        assert accepted.status_code == 200
        body = accepted.json()
        assert body["student_interaction_id"]
        assert body["student_interaction_status"] == "PENDING"

        replay = client.post(f"/api/v1/student/studio/{runtime_id}/operations", json=payload)
        assert replay.status_code == 200
        assert replay.json()["replayed"] is True
        assert replay.json()["student_interaction_id"] == body["student_interaction_id"]
        assert replay.json()["student_interaction_status"] == "PENDING"
    finally:
        app.dependency_overrides.pop(get_studio_subject_registry, None)
        _clear_overrides()


def test_canvas_tutor_stream_claims_once_and_persists_no_fake_student_message(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public endpoint only starts a pre-created owned interaction once."""

    from apps.api.main import app
    from apps.api.routes import student as student_routes
    from apps.api.routes.studio import get_studio_subject_registry
    from services.platform.db.models import ModelTask

    class StreamingProvider:
        def __init__(self) -> None:
            self.calls = 0

        def stream(self, route: ModelRoute, payload: dict[str, object]):  # type: ignore[no-untyped-def]
            assert route.model == "fixture-tutor"
            assert "question" not in payload
            self.calls += 1
            yield StreamDelta("Canvas ")
            yield StreamComplete(ModelResult(output={"text": "Tutor reply", "workspace_intent": None}))

    student_id, learning_session_id = _student_session(postgres_session_factory, subject="studio-canvas-stream")
    registry = _studio_test_registry()
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session, subject_registry=registry)
        runtime = state.get_or_create_runtime(student_id=student_id, learning_session_id=learning_session_id)
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id, learning_session_id=learning_session_id,
                subject_key="MATH", subject_profile_version="fixture-v1", concept_keys=("fixture",),
                activity_key="generic-workspace", artifact_type="fixture", renderer_key="native-react-svg",
                renderer_version="1", activity_contract_version="activity-v1", payload_schema_version="scene-v1",
                seed_payload={"value": 1}, accessibility_payload={"summary": "fixture"}, locale="en", direction="ltr",
            )
        )
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version
    provider = StreamingProvider()
    monkeypatch.setattr(
        student_routes,
        "create_studio_interaction_tutor_gateway",
        lambda gateway_session: ModelGateway(
            gateway_session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
            providers={"fixture": provider},
        ),
    )
    app.dependency_overrides[get_studio_subject_registry] = lambda: registry
    client = _client(postgres_session_factory, subject="studio-canvas-stream")
    try:
        operation = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id), "base_scene_version": scene_version,
                "action_key": "fixture.submit", "payload": {"value": 2}, "idempotency_key": "canvas-stream-1",
            },
        )
        assert operation.status_code == 200
        interaction_id = operation.json()["student_interaction_id"]

        streamed = client.post(
            f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream"
        )
        assert streamed.status_code == 200
        assert "event: delta" in streamed.text
        assert "event: turn" in streamed.text
        assert "interaction_id" not in streamed.text
        assert provider.calls == 1

        replay = client.post(
            f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream"
        )
        assert replay.status_code == 409
        assert provider.calls == 1
        with postgres_session_factory.begin() as session:
            interaction = session.get(StudioStudentInteraction, UUID(interaction_id))
            assert interaction is not None and interaction.status == "COMPLETED"
            messages = session.query(LearningMessage).filter(LearningMessage.session_id == learning_session_id).all()
            assert len(messages) == 1 and messages[0].role == "tutor"
            assert messages[0].payload["turn_origin"] == "STUDIO_INTERACTION"
    finally:
        app.dependency_overrides.pop(get_studio_subject_registry, None)
        _clear_overrides()


def test_canvas_terminal_disconnect_cancels_running_interaction_but_preserves_tutor_truth(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a terminal SSE close stranding a persisted Canvas turn in RUNNING."""

    from apps.api.routes import student as student_routes
    from apps.api.routes.studio import get_studio_subject_registry
    from services.platform.db.models import ModelTask

    class StreamingProvider:
        def stream(self, route: ModelRoute, payload: dict[str, object]):  # type: ignore[no-untyped-def]
            del route, payload
            yield StreamDelta("Tutor ")
            yield StreamComplete(ModelResult(output={"text": "Persisted Canvas Tutor reply", "workspace_intent": None}))

    student_id, learning_session_id = _student_session(postgres_session_factory, subject="studio-disconnect")
    registry = _studio_test_registry()
    with postgres_session_factory.begin() as session:
        state = StudioStateService(session, subject_registry=registry)
        runtime = state.get_or_create_runtime(student_id=student_id, learning_session_id=learning_session_id)
        scene = state.accept_scene(
            CreateSceneCommand(
                student_id=student_id, learning_session_id=learning_session_id,
                subject_key="MATH", subject_profile_version="fixture-v1", concept_keys=("fixture",),
                activity_key="generic-workspace", artifact_type="fixture", renderer_key="native-react-svg",
                renderer_version="1", activity_contract_version="activity-v1", payload_schema_version="scene-v1",
                seed_payload={"value": 1}, accessibility_payload={"summary": "fixture"}, locale="en", direction="ltr",
            )
        )
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version
    monkeypatch.setattr(
        student_routes,
        "create_studio_interaction_tutor_gateway",
        lambda gateway_session: ModelGateway(
            gateway_session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
            providers={"fixture": StreamingProvider()},
        ),
    )
    client = _client(postgres_session_factory, subject="studio-disconnect")
    from apps.api.main import app

    app.dependency_overrides[get_studio_subject_registry] = lambda: registry
    try:
        operation = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id), "base_scene_version": scene_version,
                "action_key": "fixture.submit", "payload": {"value": 2}, "idempotency_key": "canvas-disconnect-1",
            },
        )
        interaction_id = UUID(operation.json()["student_interaction_id"])
        principal = AuthenticatedPrincipal(
            subject="studio-disconnect", role=UserRole.STUDENT, email="studio-disconnect@example.test"
        )
        with postgres_session_factory() as route_session:
            response = student_routes.stream_canvas_interaction_tutor_turn(
                runtime_id=runtime_id,
                interaction_id=interaction_id,
                principal=principal,
                subject_registry=registry,
                session=route_session,
            )

            async def consume_terminal_then_disconnect() -> None:
                iterator = response.body_iterator
                assert "event: delta" in str(await anext(iterator))
                assert "event: turn" in str(await anext(iterator))
                await iterator.aclose()

            asyncio.run(consume_terminal_then_disconnect())
        with postgres_session_factory.begin() as session:
            interaction = session.get(StudioStudentInteraction, interaction_id)
            observation = session.scalar(
                session.query(StudioTutorObservation).filter_by(student_interaction_id=interaction_id).statement
            )
            assert interaction is not None
            assert interaction.status == "CANCELLED"
            assert interaction.tutor_message_id is None
            assert session.query(LearningMessage).filter_by(session_id=learning_session_id, role="tutor").count() == 1
            assert session.query(AIExecution).filter_by(operation_id=interaction_id, success=True).count() == 1
            assert observation is not None and observation.status == "CANCELLED"
            runtime = session.get(type(runtime), runtime_id)
            assert runtime is not None and runtime.last_tutor_observation_sequence == 0
    finally:
        app.dependency_overrides.pop(get_studio_subject_registry, None)
        _clear_overrides()
