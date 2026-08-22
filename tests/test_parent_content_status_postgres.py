"""PostgreSQL contracts for Parent-authorized, current-lineage content status."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.auth.parent_student import grant_parent_student_access
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    ContentDocument,
    ContentIndexRun,
    ContentProcessingRun,
    ContentSemanticProcessingRun,
    ParentStudentRelationship,
    Student,
    User,
)
from services.platform.db.session import get_session


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Parent content-status tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    database_url = normalize_database_url(os.environ["DATABASE_URL"])
    schema = f"parent_content_status_{uuid4().hex}"
    admin_engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema},public"})
    for table in (
        User.__table__, Student.__table__, ParentStudentRelationship.__table__,
        ContentDocument.__table__, ContentProcessingRun.__table__,
        ContentSemanticProcessingRun.__table__, ContentIndexRun.__table__,
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
    parent = User(identity_provider="clerk", external_subject=subject, role="PARENT_ADMIN")
    session.add(parent)
    session.flush()
    return parent


def _student(session: Session, subject: str) -> Student:
    user = User(identity_provider="clerk", external_subject=subject, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=subject.title())
    session.add(student)
    session.flush()
    return student


def _document(session: Session, student: Student, *, filename: str = "math.pdf", grade: int = 5, subject: str = "MATH") -> ContentDocument:
    document = ContentDocument(
        student_id=student.id,
        grade_level=grade,
        subject=subject,
        original_storage_key="private/content/source.pdf",
        original_checksum=uuid4().hex * 2,
        filename=filename,
        content_type="application/pdf",
    )
    session.add(document)
    session.flush()
    return document


def _structural(session: Session, document: ContentDocument, *, status: str = "COMPLETED", created_at: datetime | None = None) -> ContentProcessingRun:
    run = ContentProcessingRun(
        document_id=document.id,
        kind="STRUCTURAL",
        processor_version=uuid4().hex,
        processor_settings_version="fixture",
        status=status,
        created_at=created_at or datetime.now(UTC),
        completed_at=datetime.now(UTC) if status == "COMPLETED" else None,
        failure_detail="private structural exception" if status == "FAILED" else None,
    )
    session.add(run)
    session.flush()
    return run


def _semantic(session: Session, document: ContentDocument, structural: ContentProcessingRun, *, status: str = "COMPLETED", created_at: datetime | None = None) -> ContentSemanticProcessingRun:
    run = ContentSemanticProcessingRun(
        document_id=document.id,
        structural_processing_run_id=structural.id,
        semantic_schema_version=uuid4().hex,
        prompt_version=uuid4().hex,
        model_route_version="fixture:model",
        provider="fixture",
        model="fixture",
        settings_version="fixture",
        status=status,
        created_at=created_at or datetime.now(UTC),
        completed_at=datetime.now(UTC) if status == "COMPLETED" else None,
        failure_detail="private semantic provider error" if status == "FAILED" else None,
    )
    session.add(run)
    session.flush()
    return run


def _index(session: Session, document: ContentDocument, structural: ContentProcessingRun, semantic: ContentSemanticProcessingRun, *, status: str = "COMPLETED") -> ContentIndexRun:
    run = ContentIndexRun(
        document_id=document.id,
        structural_processing_run_id=structural.id,
        semantic_processing_run_id=semantic.id,
        block_schema_version=uuid4().hex,
        embedding_route_version="fixture:embedding",
        embedding_dimensions=1536,
        settings_version="fixture",
        status=status,
        completed_at=datetime.now(UTC) if status == "COMPLETED" else None,
        failure_detail="private embedding failure" if status == "FAILED" else None,
    )
    session.add(run)
    session.flush()
    return run


def _client(factory: sessionmaker[Session], principal: AuthenticatedPrincipal) -> TestClient:
    from apps.api.main import app

    def database_session():
        with factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: principal
    return TestClient(app)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


def _get(client: TestClient, student_id: UUID):
    return client.get(f"/api/v1/parent/students/{student_id}/content-status")


def test_linked_parent_receives_compact_ready_document_status(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        student = _student(session, "lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=student.id)
        document = _document(session, student)
        structural = _structural(session, document)
        semantic = _semantic(session, document, structural)
        _index(session, document, structural, semantic)
        student_id = student.id

    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="parent-a", role=UserRole.PARENT_ADMIN))
    try:
        response = _get(client, student_id)
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["student_id"] == str(student_id)
    assert body["documents"] == [{
        "id": str(document.id), "filename": "math.pdf", "grade_level": 5,
        "subject": "MATH", "upload_status": "UPLOADED", "status": "READY",
        "stages": {"structural": "READY", "semantic": "READY", "index": "READY"},
        "failure": None,
    }]


def test_parent_content_status_denies_unlinked_and_unknown_students_identically(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        _parent(session, "parent-a")
        student = _student(session, "lina")
        _document(session, student)
        student_id = student.id
    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="parent-a", role=UserRole.PARENT_ADMIN))
    try:
        unlinked = _get(client, student_id)
        unknown = _get(client, uuid4())
    finally:
        _clear_overrides()
    assert (unlinked.status_code, unlinked.json()) == (unknown.status_code, unknown.json()) == (404, {"detail": "Student not found."})


def test_student_principal_cannot_call_parent_content_status(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "lina")
    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="lina", role=UserRole.STUDENT))
    try:
        response = _get(client, student.id)
    finally:
        _clear_overrides()
    assert response.status_code == 403


def test_empty_content_is_a_valid_empty_list(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        student = _student(session, "lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=student.id)
    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="parent-a", role=UserRole.PARENT_ADMIN))
    try:
        response = _get(client, student.id)
    finally:
        _clear_overrides()
    assert response.status_code == 200
    assert response.json()["documents"] == []


@pytest.mark.parametrize(
    ("structural_status", "semantic_status", "index_status", "expected_status", "stages", "failure_stage"),
    [
        (None, None, None, "UPLOADED", {"structural": "PENDING", "semantic": "PENDING", "index": "PENDING"}, None),
        ("COMPLETED", None, None, "PROCESSING", {"structural": "READY", "semantic": "PENDING", "index": "PENDING"}, None),
        ("COMPLETED", "COMPLETED", None, "PROCESSING", {"structural": "READY", "semantic": "READY", "index": "PENDING"}, None),
        ("FAILED", None, None, "FAILED", {"structural": "FAILED", "semantic": "PENDING", "index": "PENDING"}, "structural"),
        ("COMPLETED", "FAILED", None, "FAILED", {"structural": "READY", "semantic": "FAILED", "index": "PENDING"}, "semantic"),
        ("COMPLETED", "COMPLETED", "FAILED", "FAILED", {"structural": "READY", "semantic": "READY", "index": "FAILED"}, "index"),
    ],
)
def test_readiness_derives_current_pipeline_stage(postgres_session_factory: sessionmaker[Session], structural_status: str | None, semantic_status: str | None, index_status: str | None, expected_status: str, stages: dict[str, str], failure_stage: str | None) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        student = _student(session, "lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=student.id)
        document = _document(session, student)
        structural = _structural(session, document, status=structural_status) if structural_status else None
        semantic = _semantic(session, document, structural, status=semantic_status) if semantic_status and structural else None
        if index_status and structural and semantic:
            _index(session, document, structural, semantic, status=index_status)
    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="parent-a", role=UserRole.PARENT_ADMIN))
    try:
        response = _get(client, student.id)
    finally:
        _clear_overrides()
    item = response.json()["documents"][0]
    assert item["status"] == expected_status
    assert item["stages"] == stages
    assert (item["failure"] or {}).get("stage") == failure_stage
    assert "private" not in str(item)


def test_newer_semantic_success_supersedes_historical_failure_and_old_index_cannot_make_it_ready(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        student = _student(session, "lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=student.id)
        document = _document(session, student)
        structural = _structural(session, document)
        older = _semantic(session, document, structural, status="FAILED", created_at=datetime.now(UTC) - timedelta(minutes=2))
        current = _semantic(session, document, structural, status="COMPLETED", created_at=datetime.now(UTC) - timedelta(minutes=1))
        _index(session, document, structural, older, status="COMPLETED")
    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="parent-a", role=UserRole.PARENT_ADMIN))
    try:
        response = _get(client, student.id)
    finally:
        _clear_overrides()
    item = response.json()["documents"][0]
    assert item["status"] == "PROCESSING"
    assert item["stages"] == {"structural": "READY", "semantic": "READY", "index": "PENDING"}
    assert item["failure"] is None
    assert current.id != older.id


def test_status_read_is_ordered_and_creates_no_processing_rows(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        parent = _parent(session, "parent-a")
        student = _student(session, "lina")
        grant_parent_student_access(session, parent_user_id=parent.id, student_id=student.id)
        _document(session, student, filename="zeta.pdf", grade=6, subject="SCIENCE")
        _document(session, student, filename="beta.pdf", grade=5, subject="MATH")
        _document(session, student, filename="alpha.pdf", grade=5, subject="MATH")
        student_id = student.id
    client = _client(postgres_session_factory, AuthenticatedPrincipal(subject="parent-a", role=UserRole.PARENT_ADMIN))
    try:
        response = _get(client, student_id)
    finally:
        _clear_overrides()
    assert [item["filename"] for item in response.json()["documents"]] == ["alpha.pdf", "beta.pdf", "zeta.pdf"]
    with postgres_session_factory() as session:
        assert session.query(ContentProcessingRun).count() == 0
        assert session.query(ContentSemanticProcessingRun).count() == 0
        assert session.query(ContentIndexRun).count() == 0
