"""PostgreSQL contract tests for the authenticated Student Math session path."""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, LearningMessage, LearningSession, Student, User
from services.platform.db.session import get_session
from services.platform.config import Settings


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Student session tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE learning_messages, learning_sessions, students, users CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student(session: Session, subject: str) -> Student:
    user = User(
        identity_provider="clerk",
        external_subject=subject,
        email=f"{subject}@example.test",
        role="STUDENT",
    )
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=subject)
    session.add(student)
    session.flush()
    return student


def _client(
    postgres_session_factory: sessionmaker[Session],
    *,
    subject: str,
) -> TestClient:
    from apps.api.main import app

    def database_session():
        with postgres_session_factory.begin() as session:
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


def test_authenticated_student_starts_and_resumes_one_open_math_session(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")

    client = _client(postgres_session_factory, subject="student-one")
    try:
        first = client.post("/api/v1/student/math/session")
        second = client.post("/api/v1/student/math/session")
    finally:
        _clear_overrides()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["subject"] == "MATH"
    assert first.json()["status"] == "OPEN"
    with postgres_session_factory() as session:
        assert session.query(LearningSession).filter_by(student_id=student.id).count() == 1


def test_first_authenticated_student_visit_creates_only_their_owned_profile(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    client = _client(postgres_session_factory, subject="first-student")
    try:
        response = client.post("/api/v1/student/math/session")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    with postgres_session_factory() as session:
        user = session.query(User).filter_by(
            identity_provider="clerk", external_subject="first-student"
        ).one()
        student = session.query(Student).filter_by(user_id=user.id).one()
        assert session.get(LearningSession, UUID(response.json()["id"])).student_id == student.id


def test_authenticated_student_messages_are_persisted_in_order_and_restored_after_refresh(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        _student(session, "student-one")

    client = _client(postgres_session_factory, subject="student-one")
    try:
        created = client.post("/api/v1/student/math/session")
        session_id = created.json()["id"]
        first = client.post(f"/api/v1/student/math/session/{session_id}/messages", json={"content": "I tried 4 × 25."})
        second = client.post(f"/api/v1/student/math/session/{session_id}/messages", json={"content": "Can I check my answer?"})
        refreshed = client.post("/api/v1/student/math/session")
    finally:
        _clear_overrides()

    assert first.status_code == 200
    assert second.status_code == 200
    assert refreshed.json()["id"] == session_id
    assert [message["content"] for message in refreshed.json()["messages"]] == [
        "I tried 4 × 25.",
        "Can I check my answer?",
    ]
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).order_by(LearningMessage.created_at, LearningMessage.id).all()
        assert [message.content for message in messages] == ["I tried 4 × 25.", "Can I check my answer?"]


def test_student_cannot_read_or_write_another_students_math_session(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        owner = _student(session, "student-owner")
        _student(session, "student-other")
        learning_session = LearningSession(student_id=owner.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    client = _client(postgres_session_factory, subject="student-other")
    try:
        read = client.get(f"/api/v1/student/math/session/{session_id}")
        write = client.post(
            f"/api/v1/student/math/session/{session_id}/messages",
            json={"content": "This must not be accepted."},
        )
    finally:
        _clear_overrides()

    assert read.status_code == 404
    assert write.status_code == 404
    with postgres_session_factory() as session:
        assert session.query(LearningMessage).filter_by(session_id=session_id).count() == 0


def test_student_session_path_has_no_automatic_close_side_effect(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        _student(session, "student-one")

    client = _client(postgres_session_factory, subject="student-one")
    try:
        created = client.post("/api/v1/student/math/session")
        session_id = UUID(created.json()["id"])
        client.post(
            f"/api/v1/student/math/session/{session_id}/messages",
            json={"content": "I am continuing after a short break."},
        )
    finally:
        _clear_overrides()

    with postgres_session_factory() as session:
        persisted = session.get(LearningSession, session_id)
        assert persisted is not None
        assert persisted.status == "OPEN"
        assert persisted.closed_at is None


def test_authenticated_student_tutor_turn_uses_the_real_sse_path_and_persists_response(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with postgres_session_factory.begin() as session:
        _student(session, "student-one")
        executions_before = session.query(AIExecution).filter_by(task="tutor").count()

    client = _client(postgres_session_factory, subject="student-one")
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(
        tutor_runtime,
        "get_settings",
        lambda: Settings(_env_file=None, model_provider="mock"),
    )
    try:
        created = client.post("/api/v1/student/math/session")
        session_id = created.json()["id"]
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Explain equivalent fractions."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in response.text
    assert "event: turn" in response.text
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=UUID(session_id)).order_by(LearningMessage.created_at, LearningMessage.id).all()
        assert [message.role for message in messages] == ["student", "tutor"]
        assert messages[-1].payload["source_refs"] == []
        assert session.query(AIExecution).filter_by(task="tutor").count() == executions_before + 1


def test_parent_redirect_stream_never_calls_the_tutor_model(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with postgres_session_factory.begin() as session:
        _student(session, "student-one")
        executions_before = session.query(AIExecution).filter_by(task="tutor").count()

    client = _client(postgres_session_factory, subject="student-one")
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
    try:
        session_id = client.post("/api/v1/student/math/session").json()["id"]
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Can you explain prayer?"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: delta" not in response.text
    assert "event: turn" in response.text
    with postgres_session_factory() as session:
        assert session.query(AIExecution).filter_by(task="tutor").count() == executions_before
