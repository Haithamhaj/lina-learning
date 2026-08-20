"""Fixture upload and Docling adapter tests without a real school book."""

from pathlib import Path
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.ingestion import ingest_source_document
from services.content.docling_adapter import extract_structural_markdown
from services.content.processing import process_markdown_document
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ContentDocument, Student, User
from services.platform.storage import LocalObjectStorage


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
    with postgres_session_factory.begin() as session:
        first = ingest_source_document(
            session,
            storage=storage,
            student_id=make_student(session),
            grade_level=5,
            subject="MATH",
            filename="fractions.md",
            content_type="text/markdown",
            content=b"# Equivalent Fractions\n\n1/2 = 2/4",
        )

    assert storage.get(first.original_storage_key).content.startswith(b"# Equivalent")
    with postgres_session_factory() as session:
        assert session.get(ContentDocument, first.id).original_checksum == storage.head(first.original_storage_key).checksum_sha256


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
