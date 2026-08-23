"""PostgreSQL contracts for REC-29 structural-first content indexing."""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.indexing import build_content_index, lexical_candidates, vector_candidates
from services.content.repository import create_content_document, create_processing_run, create_structural_items
from services.content.structural_contract import NormalizedStructuralItem
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.model_gateway.lineage import derived_objects_for_execution
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, ContentIndexRun, ContentSemanticProcessingRun, IndexedContentBlock, IndexedContentBlockSource, ModelTask, Student, User
from services.retrieval.service import CurrentFocus, RetrievalService


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE indexed_content_block_sources, indexed_content_blocks, content_index_runs, content_semantic_item_sources, content_semantic_items, content_semantic_processing_runs, document_structural_items, content_processing_runs, content_documents CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _gateway(session: Session, *, vector: list[float] | None = None) -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            return ModelResult(output={"embeddings": [vector or [0.01] * 1536 for _ in payload["input"]]})

    return ModelGateway(
        session,
        routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
        providers={"fixture": Provider()},
    )


def _item(
    key: str,
    *,
    text_value: str | None,
    caption: str | None = None,
    parent: str | None = None,
    reading_order: int = 0,
    depth: int = 0,
    page: int | None = 2,
    source_ref: str = "fixture#page=2",
    provenance: dict[str, object] | None = None,
    attributes: dict[str, object] | None = None,
) -> NormalizedStructuralItem:
    return NormalizedStructuralItem(
        item_key=key,
        parent_item_key=parent,
        sibling_order=reading_order,
        reading_order=reading_order,
        hierarchy_depth=depth,
        item_type="paragraph",
        text=text_value,
        caption_text=caption,
        caption_item_keys=(),
        heading_level=2 if depth else 1,
        page_number=page,
        source_ref=source_ref,
        provenance=provenance or {},
        attributes=attributes or {},
    )


def _setup_structural(
    session: Session,
    *,
    items: list[NormalizedStructuralItem] | None = None,
    processor_version: str = "v1",
):
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="fixture")
    session.add(student)
    session.flush()
    document = create_content_document(
        session,
        student_id=student.id,
        grade_level=5,
        subject="MATH",
        original_storage_key="fixture",
        original_checksum=uuid4().hex * 2,
        filename="fixture.pdf",
        content_type="application/pdf",
    )
    structural = create_processing_run(
        session,
        document_id=document.id,
        kind="STRUCTURAL",
        processor_version=processor_version,
    )
    structural.status = "COMPLETED"
    rows = create_structural_items(
        session,
        document_id=document.id,
        processing_run_id=structural.id,
        items=items or [
            _item("section", text_value=None, caption="Decimal multiplication"),
            _item(
                "section/example",
                parent="section",
                reading_order=1,
                depth=1,
                text_value="Place value explains how digits change when multiplying decimals by ten.",
                page=4,
                source_ref="fixture#page=4",
                provenance={"source": "docling", "region": "body"},
                attributes={"layout": "paragraph"},
            ),
        ],
    )
    return document, structural, rows


def test_structural_index_builds_retrieval_blocks_with_exact_provenance(factory) -> None:
    with factory.begin() as session:
        document, structural, rows = _setup_structural(session)
        run = build_content_index(session, document=document, structural_run=structural, gateway=_gateway(session))
        blocks = session.query(IndexedContentBlock).filter_by(index_run_id=run.id).order_by(IndexedContentBlock.block_key).all()
        source = session.query(IndexedContentBlockSource).join(IndexedContentBlock).filter(IndexedContentBlock.index_run_id == run.id, IndexedContentBlockSource.structural_item_id == rows[1].id).one()
        lexical = lexical_candidates(session, index_run_id=run.id, query="digits decimals", grade_level=5, subject="MATH")
        vector = vector_candidates(session, index_run_id=run.id, embedding=[0.01] * 1536, grade_level=5, subject="MATH")
        semantic_runs = session.query(ContentSemanticProcessingRun).filter_by(document_id=document.id).count()

    example = next(block for block in blocks if block.attributes["structural_item_key"] == "section/example")
    assert run.status == "COMPLETED"
    assert semantic_runs == 0
    assert example.semantic_item_id is None and example.semantic_type is None
    assert example.unit_key is None and example.lesson_key is None and example.concept_key is None
    assert example.block_key == "section/example:part-0"
    assert example.attributes == {
        "structural_item_key": "section/example",
        "parent_structural_item_id": str(rows[0].id),
        "sibling_order": 1,
        "reading_order": 1,
        "hierarchy_depth": 1,
        "item_type": "paragraph",
        "heading_level": 2,
        "page_number": 4,
        "source_ref": "fixture#page=4",
        "provenance": {"source": "docling", "region": "body"},
        "structural_attributes": {"layout": "paragraph"},
        "part_index": 0,
    }
    assert source.semantic_item_id is None and source.page_number == 4 and source.source_ref == "fixture#page=4" and source.source_order == 0
    assert any(block.id == example.id for block in lexical)
    assert any(block.id == example.id for block in vector)


def test_structural_index_execution_lineage_has_no_semantic_run(factory) -> None:
    with factory.begin() as session:
        document, structural, _ = _setup_structural(session)
        run = build_content_index(session, document=document, structural_run=structural, gateway=_gateway(session))
        execution = session.query(AIExecution).filter_by(content_index_run_id=run.id).one()
        derived = derived_objects_for_execution(session, execution=execution)

    assert execution.document_id == document.id
    assert execution.semantic_processing_run_id is None
    assert execution.content_index_run_id == run.id
    assert derived.semantic_item_ids == ()
    assert len(derived.indexed_block_ids) == 2


def test_structural_index_identity_is_idempotent_and_distinguishes_structural_runs(factory) -> None:
    with factory.begin() as session:
        document, first_structural, _ = _setup_structural(session)
        first = build_content_index(session, document=document, structural_run=first_structural, gateway=_gateway(session))
        same = build_content_index(session, document=document, structural_run=first_structural, gateway=_gateway(session))
        second_structural = create_processing_run(session, document_id=document.id, kind="STRUCTURAL", processor_version="v2")
        second_structural.status = "COMPLETED"
        create_structural_items(session, document_id=document.id, processing_run_id=second_structural.id, items=[_item("replacement", text_value="A different structural source has its own retrieval identity.")])
        second = build_content_index(session, document=document, structural_run=second_structural, gateway=_gateway(session))

    assert same.id == first.id and first.semantic_processing_run_id is None
    assert second.id != first.id and second.structural_processing_run_id == second_structural.id


def test_structural_index_failure_preserves_completed_index(factory) -> None:
    with factory.begin() as session:
        document, structural, _ = _setup_structural(session)
        completed = build_content_index(session, document=document, structural_run=structural, gateway=_gateway(session))
        failed = build_content_index(
            session,
            document=document,
            structural_run=structural,
            gateway=_gateway(session, vector=[0.1] * 8),
            settings_version="structural-v2",
        )
        retained = session.query(IndexedContentBlock).filter_by(index_run_id=completed.id).count()

    assert failed.status == "FAILED" and retained == 2 and document.status == "INDEX_READY"


def test_oversized_structural_item_is_refined_without_losing_provenance(factory) -> None:
    with factory.begin() as session:
        document, structural, rows = _setup_structural(session, items=[_item("oversized", text_value="x" * 4500)])
        run = build_content_index(session, document=document, structural_run=structural, gateway=_gateway(session))
        blocks = session.query(IndexedContentBlock).filter_by(index_run_id=run.id).order_by(IndexedContentBlock.block_key).all()
        sources = session.query(IndexedContentBlockSource).join(IndexedContentBlock).filter(IndexedContentBlock.index_run_id == run.id).all()

    assert [block.block_key for block in blocks] == ["oversized:part-0", "oversized:part-1", "oversized:part-2"]
    assert [len(block.text) for block in blocks] == [2000, 2000, 500]
    assert {source.structural_item_id for source in sources} == {rows[0].id}


def test_empty_structural_representation_fails_without_false_success(factory) -> None:
    with factory.begin() as session:
        document, structural, _ = _setup_structural(session, items=[_item("empty", text_value=None, caption=None)])
        run = build_content_index(session, document=document, structural_run=structural, gateway=_gateway(session))
        blocks = session.query(IndexedContentBlock).filter_by(index_run_id=run.id).count()
        executions = session.query(AIExecution).filter_by(content_index_run_id=run.id).count()

    assert run.status == "FAILED" and blocks == 0 and executions == 0
    assert document.status == "STRUCTURAL_READY"


@pytest.mark.parametrize(
    ("question", "source_ref"),
    [
        ("Show me a decimal example.", "structural#example"),
        ("Give me a decimal practice problem.", "structural#exercise"),
        ("Explain the decimal diagram.", "structural#figure"),
        ("What decimal formula is this equation using?", "structural#formula"),
    ],
)
def test_structural_retrieval_keeps_semantic_hint_questions_eligible(factory, question: str, source_ref: str) -> None:
    with factory.begin() as session:
        document, structural, _ = _setup_structural(
            session,
            items=[
                _item("example", text_value="A decimal example shows place value.", source_ref="structural#example"),
                _item("exercise", text_value="A decimal practice problem checks place value.", source_ref="structural#exercise"),
                _item("figure", text_value="A decimal diagram shows each place value.", source_ref="structural#figure"),
                _item("formula", text_value="A decimal formula and equation show place value.", source_ref="structural#formula"),
            ],
        )
        build_content_index(session, document=document, structural_run=structural, gateway=_gateway(session))
        blocks = RetrievalService(session, embedding_gateway=_gateway(session)).retrieve(
            student_id=document.student_id,
            question=question,
            focus=CurrentFocus(concept_key="stale-focus"),
            limit=4,
            character_budget=800,
        )

    assert any(block.source_ref == source_ref for block in blocks)
    assert all(block.semantic_type is None and block.matched for block in blocks)
