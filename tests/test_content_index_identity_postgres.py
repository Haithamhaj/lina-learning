"""PostgreSQL contracts for semantic-optional content-index identities."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    ContentDocument,
    ContentIndexRun,
    ContentProcessingRun,
    ContentSemanticProcessingRun,
    Student,
    User,
)


BASE_REVISION = "9d92f905e25a"
IDENTITY = {
    "block_schema_version": "structural-blocks-v1",
    "embedding_route_version": "fixture:text-embedding-3-small",
    "embedding_dimensions": 1536,
    "settings_version": "fixture-settings-v1",
}


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for content-index identity tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE indexed_content_block_sources, indexed_content_blocks, "
                "content_index_runs, content_semantic_item_sources, content_semantic_items, "
                "content_semantic_processing_runs, document_structural_items, "
                "content_processing_runs, content_documents, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _source(session: Session) -> tuple[ContentDocument, ContentProcessingRun, ContentSemanticProcessingRun]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="fixture")
    session.add(student)
    session.flush()
    document = ContentDocument(
        student_id=student.id,
        grade_level=5,
        subject="MATH",
        original_storage_key="private/content/fixture.pdf",
        original_checksum=uuid4().hex * 2,
        filename="fixture.pdf",
        content_type="application/pdf",
    )
    session.add(document)
    session.flush()
    structural = _structural_run(session, document, version="structural-v1")
    semantic = ContentSemanticProcessingRun(
        document_id=document.id,
        structural_processing_run_id=structural.id,
        semantic_schema_version="semantic-v1",
        prompt_version="prompt-v1",
        model_route_version="fixture:semantic-model",
        provider="fixture",
        model="semantic-model",
        settings_version="semantic-settings-v1",
        status="COMPLETED",
    )
    session.add(semantic)
    session.flush()
    return document, structural, semantic


def _structural_run(
    session: Session,
    document: ContentDocument,
    *,
    version: str,
) -> ContentProcessingRun:
    run = ContentProcessingRun(
        document_id=document.id,
        kind="STRUCTURAL",
        processor_version=version,
        processor_settings_version="fixture-settings-v1",
        status="COMPLETED",
    )
    session.add(run)
    session.flush()
    return run


def _index_run(
    document: ContentDocument,
    structural: ContentProcessingRun,
    semantic: ContentSemanticProcessingRun | None,
) -> ContentIndexRun:
    return ContentIndexRun(
        document_id=document.id,
        structural_processing_run_id=structural.id,
        semantic_processing_run_id=semantic.id if semantic is not None else None,
        **IDENTITY,
    )


def test_completed_structural_run_can_have_a_structural_only_index_identity(
    factory: sessionmaker[Session],
) -> None:
    """Catches semantic processing remaining mandatory for an index identity."""

    with factory.begin() as session:
        document, structural, _ = _source(session)
        run = _index_run(document, structural, None)
        session.add(run)
        session.flush()

    assert run.structural_processing_run_id == structural.id
    assert run.semantic_processing_run_id is None


def test_identical_structural_only_index_identity_is_unique(
    factory: sessionmaker[Session],
) -> None:
    """Catches PostgreSQL NULL semantics allowing duplicate structural-only runs."""

    with factory.begin() as session:
        document, structural, _ = _source(session)
        session.add(_index_run(document, structural, None))
        session.flush()
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(_index_run(document, structural, None))
                session.flush()


def test_different_structural_runs_have_distinct_structural_only_index_identities(
    factory: sessionmaker[Session],
) -> None:
    """Catches structural-only identity collapsing distinct source derivations."""

    with factory.begin() as session:
        document, first_structural, _ = _source(session)
        second_structural = _structural_run(session, document, version="structural-v2")
        first = _index_run(document, first_structural, None)
        second = _index_run(document, second_structural, None)
        session.add_all([first, second])
        session.flush()

    assert first.id != second.id
    assert first.structural_processing_run_id != second.structural_processing_run_id


def test_semantic_backed_index_identity_remains_unique(
    factory: sessionmaker[Session],
) -> None:
    """Catches the new structural-only contract weakening semantic identity."""

    with factory.begin() as session:
        document, structural, semantic = _source(session)
        session.add(_index_run(document, structural, semantic))
        session.flush()
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(_index_run(document, structural, semantic))
                session.flush()


def test_index_identity_migration_preserves_semantic_history_and_drops_only_structural_derivations_on_downgrade(
    factory: sessionmaker[Session],
) -> None:
    """Catches destructive migration behavior or an unsafe NOT NULL downgrade."""

    observability_logger = logging.getLogger("services.platform.observability.metrics")
    logger_was_disabled = observability_logger.disabled
    config = Config("alembic.ini")
    try:
        command.downgrade(config, BASE_REVISION)
        with factory.begin() as session:
            document, structural, semantic = _source(session)
            historic_semantic_run = _index_run(document, structural, semantic)
            session.add(historic_semantic_run)
            session.flush()
            historic_semantic_run_id = historic_semantic_run.id

        command.upgrade(config, "head")

        with factory.begin() as session:
            historic = session.get(ContentIndexRun, historic_semantic_run_id)
            assert historic is not None
            assert historic.semantic_processing_run_id == semantic.id
            structural_only = _index_run(document, structural, None)
            session.add(structural_only)
            session.flush()
            structural_only_run_id = structural_only.id

        command.downgrade(config, BASE_REVISION)

        engine = factory.kw["bind"]
        assert engine is not None
        column = next(
            item
            for item in inspect(engine).get_columns("content_index_runs")
            if item["name"] == "semantic_processing_run_id"
        )
        with engine.connect() as connection:
            assert column["nullable"] is False
            assert connection.execute(
                text(
                    "SELECT count(*) FROM content_index_runs "
                    "WHERE semantic_processing_run_id IS NULL"
                )
            ).scalar_one() == 0

        with factory() as session:
            assert session.get(ContentIndexRun, historic_semantic_run_id) is not None
            assert session.get(ContentIndexRun, structural_only_run_id) is None
    finally:
        try:
            command.upgrade(config, "head")
        finally:
            observability_logger.disabled = logger_was_disabled
