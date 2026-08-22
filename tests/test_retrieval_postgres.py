"""PostgreSQL contracts for TASK-014 hierarchical hybrid retrieval."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.indexing import build_content_index
from services.content.repository import (
    create_content_document,
    create_processing_run,
    create_semantic_items,
    create_semantic_processing_run,
    create_structural_items,
)
from services.content.semantic_contract import SemanticExtractionItem
from services.content.structural_contract import NormalizedStructuralItem
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.model_gateway.lineage import executions_for_student
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, ModelTask, Student, User
from services.retrieval.service import (
    CurrentFocus,
    RetrievalService,
    reciprocal_rank_fusion,
)


def test_task014_retrieval_has_no_python_all_block_path() -> None:
    source = Path("services/retrieval/service.py").read_text()
    assert "from services.platform.db.models import ContentBlock" not in source
    assert "scalars().all()" not in source


def test_rank_fusion_deduplicates_and_prefers_agreement() -> None:
    assert reciprocal_rank_fusion(
        ["lexical-only", "both"], ["both", "vector-only"], offset=10
    ) == [
        "both",
        "lexical-only",
        "vector-only",
    ]


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL required"
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE indexed_content_block_sources, indexed_content_blocks, content_index_runs, "
                "content_semantic_item_sources, content_semantic_items, content_semantic_processing_runs, "
                "document_structural_items, content_processing_runs, content_documents CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _gateway(session: Session) -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            embeddings = []
            for value in payload["input"]:
                content = str(value).casefold()
                if "uniqueone" in content:
                    embeddings.append([1.0] + [0.0] * 1535)
                elif "relatedpart" in content:
                    embeddings.append([0.9, 0.1] + [0.0] * 1534)
                elif "decimal" in content:
                    embeddings.append([0.0, 1.0] + [0.0] * 1534)
                elif "meters" in content:
                    embeddings.append([0.0, 0.0, 1.0] + [0.0] * 1533)
                else:
                    embeddings.append([0.1, 0.1] + [0.0] * 1534)
            return ModelResult(output={"embeddings": embeddings})

    return ModelGateway(
        session,
        routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
        providers={"fixture": Provider()},
    )


def _seed(session: Session):
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
    structural_run = create_processing_run(
        session, document_id=document.id, kind="STRUCTURAL", processor_version="v1"
    )
    structural_run.status = "COMPLETED"
    structural = create_structural_items(
        session,
        document_id=document.id,
        processing_run_id=structural_run.id,
        items=[
            NormalizedStructuralItem(
                "one",
                None,
                0,
                0,
                0,
                "text",
                "Place value explains decimal digits.",
                None,
                (),
                1,
                2,
                "fixture#page=2",
                {},
                {},
            ),
            NormalizedStructuralItem(
                "two",
                None,
                1,
                1,
                0,
                "text",
                "uniqueone practice exercise " + "x" * 1450,
                None,
                (),
                1,
                3,
                "fixture#page=3",
                {},
                {},
            ),
            NormalizedStructuralItem(
                "three",
                None,
                2,
                2,
                0,
                "text",
                "relatedpart exercise continuation " + "y" * 1450,
                None,
                (),
                1,
                4,
                "fixture#page=4",
                {},
                {},
            ),
            NormalizedStructuralItem(
                "four",
                None,
                3,
                3,
                0,
                "text",
                "Convert meters to centimeters by multiplying by 100.",
                None,
                (),
                1,
                18,
                "fixture#page=18",
                {},
                {},
            ),
        ],
    )
    semantic_run = create_semantic_processing_run(
        session,
        document_id=document.id,
        structural_processing_run_id=structural_run.id,
        semantic_schema_version="v1",
        prompt_version="v1",
        model_route_version="fixture",
        provider="fixture",
        model="fixture",
        settings_version="v1",
        settings_metadata={},
    )
    semantic_run.status = "COMPLETED"
    create_semantic_items(
        session,
        document_id=document.id,
        semantic_processing_run_id=semantic_run.id,
        structural_items_by_key={item.item_key: item for item in structural},
        items=[
            SemanticExtractionItem(
                semantic_key="unit-1",
                semantic_type="UNIT",
                title="Module 1",
                description=None,
                normalized_concept_key=None,
                parent_semantic_key=None,
                structural_item_keys=["one"],
                sibling_order=0,
                metadata={},
            ),
            SemanticExtractionItem(
                semantic_key="lesson-1",
                semantic_type="LESSON",
                title="Place Value",
                description=None,
                normalized_concept_key=None,
                parent_semantic_key="unit-1",
                structural_item_keys=["one"],
                sibling_order=0,
                metadata={},
            ),
            SemanticExtractionItem(
                semantic_key="place-value",
                semantic_type="CONCEPT",
                title="Place Value",
                description="Decimal place value",
                normalized_concept_key="place-value",
                parent_semantic_key="lesson-1",
                structural_item_keys=["one"],
                sibling_order=0,
                metadata={},
            ),
            SemanticExtractionItem(
                semantic_key="example-1",
                semantic_type="EXAMPLE",
                title="Worked Example",
                description=None,
                normalized_concept_key="place-value",
                parent_semantic_key="place-value",
                structural_item_keys=["one"],
                sibling_order=0,
                metadata={},
            ),
            SemanticExtractionItem(
                semantic_key="exercise-1",
                semantic_type="EXERCISE",
                title="Practice",
                description=None,
                normalized_concept_key="place-value",
                parent_semantic_key="place-value",
                structural_item_keys=["two", "three"],
                sibling_order=0,
                metadata={},
            ),
            SemanticExtractionItem(
                semantic_key="lesson-2",
                semantic_type="LESSON",
                title="Metric conversions",
                description=None,
                normalized_concept_key=None,
                parent_semantic_key=None,
                structural_item_keys=["four"],
                sibling_order=1,
                metadata={},
            ),
            SemanticExtractionItem(
                semantic_key="metric-conversions",
                semantic_type="CONCEPT",
                title="Metric conversions",
                description="Meters and centimeters",
                normalized_concept_key="metric-conversions",
                parent_semantic_key="lesson-2",
                structural_item_keys=["four"],
                sibling_order=0,
                metadata={},
            ),
        ],
    )
    index_run = build_content_index(
        session, document=document, semantic_run=semantic_run, gateway=_gateway(session)
    )
    return student, index_run


def test_retrieval_filters_focus_fuses_expands_and_preserves_exact_provenance(
    factory,
) -> None:
    with factory.begin() as session:
        student, index_run = _seed(session)
        result = RetrievalService(
            session, embedding_gateway=_gateway(session)
        ).retrieve_with_debug(
            student_id=student.id,
            question="uniqueone practice",
            grade_level=5,
            subject="MATH",
            focus=CurrentFocus(
                unit_key="unit-1", lesson_key="lesson-1", concept_key="place-value"
            ),
            candidate_limit=1,
            block_limit=4,
            character_budget=4000,
        )
        execution = session.query(AIExecution).filter_by(operation_type="runtime_retrieval_embedding").one()
        assert execution.student_id == student.id
        assert executions_for_student(session, student_id=student.id) == [execution]
        assert execution.content_index_run_id is None
        assert execution.semantic_processing_run_id is None

    assert result.index_run_id == index_run.id
    assert result.debug.lexical_block_ids and result.debug.vector_block_ids
    assert [block.source_refs for block in result.blocks] == [
        ("fixture#page=3",),
        ("fixture#page=4",),
    ]
    assert all(block.concept_key == "place-value" for block in result.blocks)
    assert sum(len(block.text) for block in result.blocks) <= 4000


def test_retrieval_enforces_grade_subject_and_context_budget(factory) -> None:
    with factory.begin() as session:
        student, _ = _seed(session)
        service = RetrievalService(session, embedding_gateway=_gateway(session))
        matching = service.retrieve(
            student_id=student.id, question="decimal place value", character_budget=80
        )
        wrong_subject = service.retrieve(
            student_id=student.id, question="decimal place value", subject="SCIENCE"
        )

    assert matching and sum(len(block.text) for block in matching) <= 80
    assert wrong_subject == []


def test_retrieval_uses_explicit_semantic_content_type_request(factory) -> None:
    with factory.begin() as session:
        student, _ = _seed(session)
        blocks = RetrievalService(
            session, embedding_gateway=_gateway(session)
        ).retrieve(
            student_id=student.id,
            question="Show me an example.",
            focus=CurrentFocus(concept_key="place-value"),
        )

    assert blocks and {block.semantic_type for block in blocks} == {"EXAMPLE"}


def test_explicit_question_overrides_stale_current_focus_when_lexically_targeted(
    factory,
) -> None:
    with factory.begin() as session:
        student, _ = _seed(session)
        blocks = RetrievalService(
            session, embedding_gateway=_gateway(session)
        ).retrieve(
            student_id=student.id,
            question="How many centimeters are in 3 meters?",
            focus=CurrentFocus(lesson_key="lesson-1", concept_key="place-value"),
        )

    assert blocks and blocks[0].source_ref == "fixture#page=18"


def test_outside_focus_relevance_outranks_overlapping_stale_focus(factory) -> None:
    with factory.begin() as session:
        student, _ = _seed(session)
        blocks = RetrievalService(
            session, embedding_gateway=_gateway(session)
        ).retrieve(
            student_id=student.id,
            question="What value converts 3 meters to centimeters?",
            focus=CurrentFocus(lesson_key="lesson-1", concept_key="place-value"),
            limit=1,
        )

    assert blocks[0].source_ref == "fixture#page=18"
