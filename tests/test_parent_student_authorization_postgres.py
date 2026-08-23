"""Isolated PostgreSQL contracts for explicit Parent-to-Student access."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.auth.parent_student import (
    ParentStudentAccessDenied,
    grant_parent_student_access,
    require_parent_student_access,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    LearningMessage,
    LearningSession,
    ParentStudentRelationship,
    Student,
    User,
)
from services.platform.db.session import get_session


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Parent/Student authorization tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    """Provide a schema isolated from development data and other test modules."""

    database_url = normalize_database_url(os.environ["DATABASE_URL"])
    schema = f"parent_student_auth_{uuid4().hex}"
    admin_engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(
        database_url,
        connect_args={"options": f"-csearch_path={schema},public"},
    )
    for table in (
        User.__table__,
        Student.__table__,
        ParentStudentRelationship.__table__,
        LearningSession.__table__,
        LearningMessage.__table__,
    ):
        table.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def _parent(session: Session, subject: str) -> User:
    user = User(
        identity_provider="clerk",
        external_subject=subject,
        email=f"{subject}@example.test",
        role="PARENT_ADMIN",
    )
    session.add(user)
    session.flush()
    return user


def _student(session: Session, subject: str, name: str) -> Student:
    user = User(
        identity_provider="clerk",
        external_subject=subject,
        email=f"{subject}@example.test",
        role="STUDENT",
    )
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=name)
    session.add(student)
    session.flush()
    return student


def _parent_principal(subject: str) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(subject=subject, role=UserRole.PARENT_ADMIN)


def _client(
    postgres_session_factory: sessionmaker[Session],
    principal: AuthenticatedPrincipal,
) -> TestClient:
    from apps.api.main import app

    def database_session():
        with postgres_session_factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: principal
    return TestClient(app)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


def test_verified_parent_with_explicit_link_can_read_only_linked_student(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        lina = _student(session, "lina", "Lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=lina.id)
        linked_id = lina.id

    client = _client(postgres_session_factory, _parent_principal("parent-a"))
    try:
        response = client.get(f"/api/v1/parent/students/{linked_id}/summary")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json() == {"id": str(linked_id), "display_name": "Lina"}


def test_parent_without_an_explicit_link_receives_non_enumerating_denial(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        _parent(session, "parent-a")
        lina = _student(session, "lina", "Lina")
        lina_id = lina.id

    client = _client(postgres_session_factory, _parent_principal("parent-a"))
    try:
        response = client.get(f"/api/v1/parent/students/{lina_id}/summary")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found."


def test_parent_a_cannot_use_browser_student_id_to_access_student_b(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        parent_a = _parent(session, "parent-a")
        lina = _student(session, "lina", "Lina")
        student_b = _student(session, "student-b", "Student B")
        grant_parent_student_access(session, parent_user_id=parent_a.id, student_id=lina.id)
        student_b_id = student_b.id

    client = _client(postgres_session_factory, _parent_principal("parent-a"))
    try:
        response = client.get(f"/api/v1/parent/students/{student_b_id}/summary")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found."


def test_second_parent_is_isolated_from_lina(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        parent_a = _parent(session, "parent-a")
        parent_b = _parent(session, "parent-b")
        lina = _student(session, "lina", "Lina")
        student_b = _student(session, "student-b", "Student B")
        grant_parent_student_access(session, parent_user_id=parent_a.id, student_id=lina.id)
        grant_parent_student_access(session, parent_user_id=parent_b.id, student_id=student_b.id)
        lina_id = lina.id
        student_b_id = student_b.id

    client = _client(postgres_session_factory, _parent_principal("parent-b"))
    try:
        linked = client.get(f"/api/v1/parent/students/{student_b_id}/summary")
        response = client.get(f"/api/v1/parent/students/{lina_id}/summary")
    finally:
        _clear_overrides()

    assert linked.status_code == 200
    assert linked.json() == {"id": str(student_b_id), "display_name": "Student B"}
    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found."


def test_student_principal_cannot_use_parent_access_helper(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        lina = _student(session, "lina", "Lina")
        with pytest.raises(ParentStudentAccessDenied):
            require_parent_student_access(
                session,
                principal=AuthenticatedPrincipal(subject="lina", role=UserRole.STUDENT),
                student_id=lina.id,
            )


def test_non_parent_application_user_is_denied_even_with_a_parent_claim(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        lina = _student(session, "lina", "Lina")
        not_parent = User(
            identity_provider="clerk",
            external_subject="not-parent",
            role="STUDENT",
        )
        session.add(not_parent)
        session.flush()
        with pytest.raises(ParentStudentAccessDenied):
            require_parent_student_access(
                session,
                principal=_parent_principal("not-parent"),
                student_id=lina.id,
            )


def test_duplicate_parent_student_link_is_prevented_by_the_database(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        lina = _student(session, "lina", "Lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=lina.id)
        session.add(
            ParentStudentRelationship(parent_user_id=parent.id, student_id=lina.id)
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_unknown_student_has_the_same_non_enumerating_denial_as_an_unlinked_student(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        _parent(session, "parent-a")

    client = _client(postgres_session_factory, _parent_principal("parent-a"))
    try:
        response = client.get(f"/api/v1/parent/students/{uuid4()}/summary")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found."


def test_student_math_entry_derives_student_from_principal_and_opens_math_with_zero_content(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    client = _client(
        postgres_session_factory,
        AuthenticatedPrincipal(subject="lina", role=UserRole.STUDENT),
    )
    try:
        response = client.post("/api/v1/student/math/session")
        parent_lookup = client.get(f"/api/v1/parent/students/{uuid4()}/summary")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["subject"] == "MATH"
    assert response.json()["status"] == "OPEN"
    assert parent_lookup.status_code == 403
    with postgres_session_factory() as session:
        student = session.query(Student).join(User).filter(User.external_subject == "lina").one()
        assert student.user_id
