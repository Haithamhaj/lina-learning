"""Authenticated API contracts for Studio protocol v1."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole
from services.platform.auth.clerk import get_current_principal
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningSession, Student, User
from services.platform.db.session import get_session
from services.studio.contracts import CreateSceneCommand
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
