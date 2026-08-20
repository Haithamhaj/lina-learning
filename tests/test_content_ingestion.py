"""Fixture upload and Docling adapter tests without a real school book."""

from pathlib import Path
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.ingestion import ingest_source_document
from services.content.docling_adapter import StructuralItem, extract_structural_markdown
from services.content.processing import process_markdown_document, process_structural_document
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ContentBlock, ContentDocument, Student, User
from services.platform.jobs import enqueue_job
from services.platform.storage import LocalObjectStorage
from workers.content_handlers import STRUCTURAL_PROCESSING_JOB, register_content_handlers
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for content ingestion tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE content_blocks, curriculum_nodes, content_processing_runs, content_documents CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def make_student(session: Session) -> object:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Lina fixture")
    session.add(student)
    session.flush()
    return student.id


def test_fixture_upload_preserves_original_and_rejects_duplicate_checksum(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    source = b"# Equivalent Fractions\n\n1/2 = 2/4"
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        first = ingest_source_document(
            session,
            storage=storage,
            student_id=student_id,
            grade_level=5,
            subject="MATH",
            filename="fractions.md",
            content_type="text/markdown",
            content=source,
        )
        duplicate = ingest_source_document(
            session,
            storage=storage,
            student_id=student_id,
            grade_level=5,
            subject="MATH",
            filename="renamed-fractions.md",
            content_type="text/markdown",
            content=source,
        )

    assert storage.get(first.original_storage_key).content.startswith(b"# Equivalent")
    assert duplicate.id == first.id
    with postgres_session_factory() as session:
        assert session.get(ContentDocument, first.id).original_checksum == storage.head(first.original_storage_key).checksum_sha256
        assert session.query(ContentDocument).count() == 1


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        ("notes.txt", "text/plain", b"not a supported source", "Only Markdown"),
        ("book.pdf", "application/pdf", b"not a PDF", "PDF source must"),
        ("book.md", "application/pdf", b"%PDF-1.7\n", "filename must"),
    ],
)
def test_upload_rejects_invalid_or_mismatched_source_files(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    filename: str,
    content_type: str,
    content: bytes,
    message: str,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        with pytest.raises(ValueError, match=message):
            ingest_source_document(
                session,
                storage=storage,
                student_id=make_student(session),
                grade_level=5,
                subject="MATH",
                filename=filename,
                content_type=content_type,
                content=content,
            )


def test_docling_normalizes_a_markdown_fixture_with_source_text() -> None:
    markdown = extract_structural_markdown(
        "# Equivalent Fractions\n\nOne half is equal to two fourths."
    )

    assert "Equivalent Fractions" in markdown
    assert "two fourths" in markdown


def test_processing_persists_a_versioned_source_linked_structural_block(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        run = process_markdown_document(session, storage=storage, document=document)

    assert run.status == "COMPLETED"
    assert run.processor_version.startswith("docling-")


def test_structural_processing_is_idempotent_and_preserves_item_provenance(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr(
        "services.content.processing.extract_structural_items",
        lambda **_: [
            StructuralItem(
                text="Use place value to multiply by 10.",
                item_type="list_item",
                page_number=2,
                source_ref="book.pdf#page=2:item=4",
                attributes={"label": "list_item", "has_figure": False},
            )
        ],
    )
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="book.pdf", content_type="application/pdf",
            content=b"%PDF-1.7\nfixture",
        )
        first = process_structural_document(session, storage=storage, document=document)
        second = process_structural_document(session, storage=storage, document=document)
        blocks = session.query(ContentBlock).filter_by(processing_run_id=first.id).all()

    assert first.id == second.id
    assert first.status == "COMPLETED"
    assert len(blocks) == 1
    assert blocks[0].page_number == 2
    assert blocks[0].source_ref == "book.pdf#page=2:item=4"
    assert blocks[0].attributes["label"] == "list_item"


def test_structural_processing_can_run_through_the_durable_worker(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id)},
            idempotency_key=f"structural:{document.id}:docling-2.121.0",
        )

    registry = JobHandlerRegistry()
    register_content_handlers(
        registry,
        session_factory=postgres_session_factory,
        storage=storage,
    )
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == "COMPLETED"

    with postgres_session_factory() as session:
        assert session.query(ContentBlock).filter_by(document_id=document.id).count() > 0


def test_parent_upload_endpoint_requires_parent_role(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from apps.api.main import app
    from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
    from services.platform.db.session import get_session

    with postgres_session_factory.begin() as session:
        student_id = make_student(session)

    app.dependency_overrides[get_session] = lambda: postgres_session_factory()
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject="student-fixture", role=UserRole.STUDENT
    )
    try:
        response = TestClient(app).post(
            "/api/v1/content/documents",
            json={
                "student_id": str(student_id), "grade_level": 5, "subject": "MATH",
                "filename": "fractions.md", "content_type": "text/markdown",
                "content_base64": "IyBGcmFjdGlvbnM=",
            },
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)
