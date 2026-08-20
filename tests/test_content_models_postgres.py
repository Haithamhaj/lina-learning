"""PostgreSQL tests for versioned content provenance foundation."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content import create_content_block, create_content_document, create_processing_run
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ContentBlock, ContentDocument, ContentProcessingRun, Student, User


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for content model tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE content_blocks, curriculum_nodes, "
                "content_processing_runs, content_documents"
            )
        )
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


def test_original_document_and_derived_content_are_versioned_and_traceable(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        document = create_content_document(
            session,
            student_id=student_id,
            grade_level=5,
            subject="MATH",
            original_storage_key="books/fixture.md",
            original_checksum="a" * 64,
            filename="fixture.md",
            content_type="text/markdown",
        )
        run = create_processing_run(
            session,
            document_id=document.id,
            kind="STRUCTURAL",
            processor_version="docling-fixture-v1",
        )
        block = create_content_block(
            session,
            document_id=document.id,
            processing_run_id=run.id,
            text="Equivalent fractions have the same value.",
            block_type="EXPLANATION",
            page_number=1,
            source_ref="fixture.md#equivalent-fractions",
        )

    with postgres_session_factory() as session:
        persisted_block = session.get(ContentBlock, block.id)
        assert persisted_block is not None
        assert session.get(ContentDocument, persisted_block.document_id).original_storage_key == "books/fixture.md"
        assert session.get(ContentProcessingRun, persisted_block.processing_run_id).processor_version == "docling-fixture-v1"
