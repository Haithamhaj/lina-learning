"""PostgreSQL contract tests for TASK-011 structural processing."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.ingestion import ingest_source_document
from services.content.processing import process_structural_document
from services.content.structural_contract import NormalizedStructuralItem
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    ContentDocument,
    ContentProcessingRun,
    DocumentStructuralItem,
    Student,
    User,
)
from services.platform.storage import LocalObjectStorage


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for structural content tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE indexed_content_block_sources, indexed_content_blocks, content_index_runs, content_semantic_item_sources, content_semantic_items, content_semantic_processing_runs, document_structural_items, content_blocks, curriculum_nodes, "
                "content_processing_runs, content_documents CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student_id(session: Session) -> object:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Lina fixture")
    session.add(student)
    session.flush()
    return student.id


def _source_document(session: Session, storage: LocalObjectStorage) -> ContentDocument:
    return ingest_source_document(
        session,
        storage=storage,
        student_id=_student_id(session),
        grade_level=5,
        subject="MATH",
        filename="fixture.md",
        content_type="text/markdown",
        content=b"# Fixture",
    )


def _items() -> list[NormalizedStructuralItem]:
    return [
        NormalizedStructuralItem(
            item_key="#/body", parent_item_key=None, sibling_order=0, reading_order=0,
            hierarchy_depth=0, item_type="unspecified", text=None, caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=None,
            source_ref="fixture.md#item=0", provenance={"locations": []}, attributes={},
        ),
        NormalizedStructuralItem(
            item_key="#/texts/0", parent_item_key="#/body", sibling_order=0, reading_order=1,
            hierarchy_depth=1, item_type="title", text="Module 1", caption_text=None,
            caption_item_keys=(), heading_level=1, page_number=1,
            source_ref="fixture.md#page=1:item=1", provenance={"locations": [{"page_no": 1}]}, attributes={},
        ),
        NormalizedStructuralItem(
            item_key="#/groups/0", parent_item_key="#/body", sibling_order=1, reading_order=2,
            hierarchy_depth=1, item_type="list", text=None, caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=1,
            source_ref="fixture.md#page=1:item=2", provenance={"locations": [{"page_no": 1}]}, attributes={},
        ),
        NormalizedStructuralItem(
            item_key="#/texts/1", parent_item_key="#/groups/0", sibling_order=0, reading_order=3,
            hierarchy_depth=2, item_type="list_item", text="Count tenths.", caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=1,
            source_ref="fixture.md#page=1:item=3", provenance={"locations": [{"page_no": 1}]}, attributes={},
        ),
        NormalizedStructuralItem(
            item_key="#/tables/0", parent_item_key="#/body", sibling_order=2, reading_order=4,
            hierarchy_depth=1, item_type="table", text=None, caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=2,
            source_ref="fixture.md#page=2:item=4", provenance={"locations": [{"page_no": 2}]}, attributes={"structured_data": {"num_rows": 2}},
        ),
        NormalizedStructuralItem(
            item_key="#/pictures/0", parent_item_key="#/body", sibling_order=3, reading_order=5,
            hierarchy_depth=1, item_type="picture", text=None, caption_text="Place-value chart",
            caption_item_keys=("#/texts/2",), heading_level=None, page_number=2,
            source_ref="fixture.md#page=2:item=5", provenance={"locations": [{"page_no": 2}]}, attributes={},
        ),
        NormalizedStructuralItem(
            item_key="#/texts/3", parent_item_key="#/body", sibling_order=4, reading_order=6,
            hierarchy_depth=1, item_type="formula", text="10 × 4 = 40", caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=2,
            source_ref="fixture.md#page=2:item=6", provenance={"locations": [{"page_no": 2}]}, attributes={},
        ),
    ]


def test_processing_persists_tree_order_types_and_source_linkage(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if TASK-011 persists flattened retrieval blocks instead of a tree."""

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr("services.content.processing.extract_structural_items", lambda **_: _items())
    with postgres_session_factory.begin() as session:
        document = _source_document(session, storage)
        original_storage_key = document.original_storage_key
        original_checksum = document.original_checksum
        run = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v1")
        rows = session.query(DocumentStructuralItem).filter_by(processing_run_id=run.id).order_by(DocumentStructuralItem.reading_order).all()

    by_key = {row.item_key: row for row in rows}
    assert run.status == "COMPLETED"
    assert run.processor_name == "docling"
    assert run.library_version
    assert run.processor_settings_version == "docling-defaults-v1"
    assert run.processor_metadata == {"adapter_contract_version": "structural-v1"}
    assert len(rows) == 7
    assert by_key["#/texts/1"].parent_id == by_key["#/groups/0"].id
    assert [by_key["#/texts/0"].sibling_order, by_key["#/groups/0"].sibling_order] == [0, 1]
    assert by_key["#/tables/0"].item_type == "table"
    assert by_key["#/pictures/0"].caption_text == "Place-value chart"
    assert by_key["#/texts/3"].item_type == "formula"
    assert by_key["#/texts/1"].page_number == 1
    assert by_key["#/texts/1"].source_ref == "fixture.md#page=1:item=3"
    assert by_key["#/texts/1"].document_id == document.id
    assert by_key["#/texts/1"].processing_run_id == run.id


def test_same_processor_identity_is_idempotent_and_new_version_preserves_prior_tree(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if reprocessing overwrites a valid earlier structural derivation."""

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr("services.content.processing.extract_structural_items", lambda **_: _items())
    with postgres_session_factory.begin() as session:
        document = _source_document(session, storage)
        first = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v1")
        same = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v1")
        settings_changed = process_structural_document(
            session,
            storage=storage,
            document=document,
            processor_version="fixture-v1",
            settings_version="fixture-layout-v2",
        )
        second = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v2")
        first_rows = session.query(DocumentStructuralItem).filter_by(processing_run_id=first.id).count()
        second_rows = session.query(DocumentStructuralItem).filter_by(processing_run_id=second.id).count()

    assert same.id == first.id
    assert settings_changed.id != first.id
    assert second.id != first.id
    assert first_rows == 7
    assert second_rows == 7


def test_failed_new_version_records_failure_without_corrupting_prior_tree(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if a failed conversion deletes a completed run or its source readiness."""

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr("services.content.processing.extract_structural_items", lambda **_: _items())
    with postgres_session_factory.begin() as session:
        document = _source_document(session, storage)
        original_storage_key = document.original_storage_key
        original_checksum = document.original_checksum
        first = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v1")
        monkeypatch.setattr("services.content.processing.extract_structural_items", lambda **_: (_ for _ in ()).throw(ValueError("bad fixture")))
        failed = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v2")
        retained = session.query(DocumentStructuralItem).filter_by(processing_run_id=first.id).count()
        persisted_document = session.get(ContentDocument, document.id)

    assert failed.status == "FAILED"
    assert failed.failure_detail == "ValueError: bad fixture"
    assert retained == 7
    assert persisted_document is not None
    assert persisted_document.status == "STRUCTURAL_READY"
    assert persisted_document.original_storage_key == original_storage_key
    assert persisted_document.original_checksum == original_checksum


def test_failed_third_version_keeps_two_completed_structural_trees_ready(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if failure handling assumes only one prior completed run exists."""

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr("services.content.processing.extract_structural_items", lambda **_: _items())
    with postgres_session_factory.begin() as session:
        document = _source_document(session, storage)
        first = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v1")
        second = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v2")
        monkeypatch.setattr(
            "services.content.processing.extract_structural_items",
            lambda **_: (_ for _ in ()).throw(ValueError("third version failed")),
        )
        failed = process_structural_document(session, storage=storage, document=document, processor_version="fixture-v3")
        first_tree_size = session.query(DocumentStructuralItem).filter_by(processing_run_id=first.id).count()
        second_tree_size = session.query(DocumentStructuralItem).filter_by(processing_run_id=second.id).count()
        persisted_document = session.get(ContentDocument, document.id)

    assert failed.status == "FAILED"
    assert failed.failure_detail == "ValueError: third version failed"
    assert first_tree_size == 7
    assert second_tree_size == 7
    assert persisted_document is not None
    assert persisted_document.status == "STRUCTURAL_READY"
