"""PostgreSQL persistence and versioning contracts for TASK-012 semantics."""

from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.repository import (
    create_content_document,
    create_processing_run,
    create_structural_items,
)
from services.content.semantic_contract import SEMANTIC_SCHEMA_VERSION
from services.content.semantics import extract_educational_semantics
from services.content.structural_contract import NormalizedStructuralItem
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StaticModelProvider
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    ContentDocument,
    ContentSemanticItem,
    ContentSemanticItemSource,
    ContentSemanticProcessingRun,
    ModelTask,
    Student,
    User,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for semantic content tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE indexed_content_block_sources, indexed_content_blocks, content_index_runs, content_semantic_item_sources, content_semantic_items, "
                "content_semantic_processing_runs, document_structural_items, "
                "content_blocks, curriculum_nodes, content_processing_runs, content_documents CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _document_and_structural_run(session: Session) -> tuple[ContentDocument, object]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Semantic fixture learner")
    session.add(student)
    session.flush()
    document = create_content_document(
        session,
        student_id=student.id,
        grade_level=5,
        subject="MATH",
        original_storage_key="books/semantic-fixture.pdf",
        original_checksum=uuid4().hex * 2,
        filename="semantic-fixture.pdf",
        content_type="application/pdf",
    )
    structural_run = create_processing_run(
        session,
        document_id=document.id,
        kind="STRUCTURAL",
        processor_name="docling",
        processor_version="fixture-docling-v1",
        processor_settings_version="fixture-layout-v1",
    )
    structural_run.status = "COMPLETED"
    create_structural_items(
        session,
        document_id=document.id,
        processing_run_id=structural_run.id,
        items=[
            _structural("root", None, 0, "unspecified", None, 1),
            _structural("unit", "root", 1, "title", "Course section", 1),
            _structural("lesson-1", "root", 2, "section_header", "First daily section", 2),
            _structural("concept-1", "lesson-1", 3, "text", "Place value content", 2),
            _structural("objective", "lesson-1", 4, "text", "Learning goal", 2),
            _structural("definition", "lesson-1", 5, "text", "Explanation", 2),
            _structural("example", "lesson-1", 6, "text", "Worked steps", 2),
            _structural("exercise", "lesson-1", 7, "list_item", "Practice item", 2),
            _structural("vocabulary", "lesson-1", 8, "text", "Important term", 2),
            _structural("figure", "lesson-1", 9, "picture", None, 2),
            _structural("table", "lesson-1", 10, "table", None, 2),
            _structural("formula", "lesson-1", 11, "formula", "a = b", 2),
            _structural("lesson-2", "root", 12, "section_header", "Second daily section", 3),
            _structural("concept-2", "lesson-2", 13, "text", "Decimal content", 3),
        ],
    )
    document.status = "STRUCTURAL_READY"
    return document, structural_run


def _structural(
    key: str, parent: str | None, order: int, item_type: str, item_text: str | None, page: int
) -> NormalizedStructuralItem:
    return NormalizedStructuralItem(
        item_key=key,
        parent_item_key=parent,
        sibling_order=order,
        reading_order=order,
        hierarchy_depth=0 if parent is None else 1,
        item_type=item_type,
        text=item_text,
        caption_text="A visual" if item_type == "picture" else None,
        caption_item_keys=(),
        heading_level=1 if item_type in {"title", "section_header"} else None,
        page_number=page,
        source_ref=f"fixture.pdf#page={page}:item={key}",
        provenance={"locations": [{"page_no": page}]},
        attributes={},
    )


def _item(key: str, kind: str, source: list[str], parent: str | None = None) -> dict[str, object]:
    return {
        "semantic_key": key,
        "semantic_type": kind,
        "title": key.replace("-", " ").title(),
        "description": f"Fixture {kind.lower()}.",
        "normalized_concept_key": key if kind == "CONCEPT" else None,
        "parent_semantic_key": parent,
        "structural_item_keys": source,
        "sibling_order": 0,
        "metadata": {"fixture": True},
    }


def _semantic_response() -> ModelResult:
    payload = {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "items": [
            _item("unit-1", "UNIT", ["root", "unit"]),
            _item("lesson-1", "LESSON", ["lesson-1"], "unit-1"),
            _item("place-value", "CONCEPT", ["concept-1"], "lesson-1"),
            _item("place-value-objective", "OBJECTIVE", ["objective"], "place-value"),
            _item("place-value-definition", "DEFINITION", ["definition"], "place-value"),
            _item("place-value-example", "EXAMPLE", ["example"], "place-value"),
            _item("place-value-exercise", "EXERCISE", ["exercise"], "lesson-1"),
            _item("place-value-vocabulary", "VOCABULARY", ["vocabulary"], "place-value"),
            _item("place-value-figure", "FIGURE", ["figure"], "lesson-1"),
            _item("place-value-table", "TABLE", ["table"], "lesson-1"),
            _item("place-value-formula", "FORMULA", ["formula"], "lesson-1"),
            _item("lesson-2", "LESSON", ["lesson-2"], "unit-1"),
            _item("decimal-concept", "CONCEPT", ["concept-2"], "lesson-2"),
        ],
        "unclassified_structural_item_keys": [],
    }
    return ModelResult(output={"text": json.dumps(payload)})


def _gateway(session: Session, result: ModelResult | None = None) -> ModelGateway:
    return ModelGateway(
        session,
        routes={ModelTask.CURRICULUM_SEMANTICS: ModelRoute("fixture", "semantic-fixture-v1")},
        providers={"fixture": StaticModelProvider(result or _semantic_response())},
    )


def test_semantic_extraction_persists_educational_tree_and_exact_structural_lineage(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        document, structural_run = _document_and_structural_run(session)
        semantic_run = extract_educational_semantics(
            session,
            document=document,
            structural_run=structural_run,
            gateway=_gateway(session),
        )
        items = session.query(ContentSemanticItem).filter_by(semantic_processing_run_id=semantic_run.id).all()
        sources = session.query(ContentSemanticItemSource).all()

    by_key = {item.semantic_key: item for item in items}
    assert semantic_run.status == "COMPLETED"
    assert {item.semantic_type for item in items} == {
        "UNIT", "LESSON", "CONCEPT", "OBJECTIVE", "DEFINITION", "EXAMPLE",
        "EXERCISE", "VOCABULARY", "FIGURE", "TABLE", "FORMULA",
    }
    assert by_key["lesson-1"].parent_id == by_key["unit-1"].id
    assert by_key["place-value"].parent_id == by_key["lesson-1"].id
    assert by_key["place-value-objective"].parent_id == by_key["place-value"].id
    assert {source.structural_item_key for source in sources} >= {"objective", "example", "exercise", "figure", "table", "formula"}
    assert {source.page_number for source in sources} == {1, 2, 3}
    assert all(source.source_ref.startswith("fixture.pdf#page=") for source in sources)


def test_semantic_identity_is_idempotent_and_new_identity_preserves_prior_derivation(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        document, structural_run = _document_and_structural_run(session)
        first = extract_educational_semantics(session, document=document, structural_run=structural_run, gateway=_gateway(session))
        same = extract_educational_semantics(session, document=document, structural_run=structural_run, gateway=_gateway(session))
        second = extract_educational_semantics(
            session,
            document=document,
            structural_run=structural_run,
            gateway=_gateway(session),
            prompt_version="grade5-math-semantics-prompt-v2",
        )
        first_count = session.query(ContentSemanticItem).filter_by(semantic_processing_run_id=first.id).count()
        second_count = session.query(ContentSemanticItem).filter_by(semantic_processing_run_id=second.id).count()

    assert same.id == first.id
    assert second.id != first.id
    assert first_count == second_count == 13


def test_failed_new_semantic_identity_preserves_prior_semantics_and_structural_readiness(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        document, structural_run = _document_and_structural_run(session)
        first = extract_educational_semantics(session, document=document, structural_run=structural_run, gateway=_gateway(session))
        malformed = ModelResult(output={"text": "{}"})
        failed = extract_educational_semantics(
            session,
            document=document,
            structural_run=structural_run,
            gateway=_gateway(session, malformed),
            prompt_version="grade5-math-semantics-prompt-v2",
        )
        retained = session.query(ContentSemanticItem).filter_by(semantic_processing_run_id=first.id).count()
        persisted_document = session.get(ContentDocument, document.id)

    assert failed.status == "FAILED"
    assert retained == 13
    assert persisted_document is not None
    assert persisted_document.status == "SEMANTIC_READY"


def test_bounded_batches_pass_only_compact_prior_semantic_context(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    first_batch = {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "items": [
            _item("unit-1", "UNIT", ["root", "unit"]),
            _item("lesson-1", "LESSON", ["lesson-1"], "unit-1"),
            _item("place-value", "CONCEPT", ["concept-1"], "lesson-1"),
            _item("place-value-objective", "OBJECTIVE", ["objective"], "place-value"),
            _item("place-value-definition", "DEFINITION", ["definition"], "place-value"),
            _item("place-value-example", "EXAMPLE", ["example"], "place-value"),
        ],
        "unclassified_structural_item_keys": [],
    }
    second_batch = {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "items": [
            _item("place-value-exercise", "EXERCISE", ["exercise"], "lesson-1"),
            _item("place-value-vocabulary", "VOCABULARY", ["vocabulary"], "place-value"),
            _item("place-value-figure", "FIGURE", ["figure"], "lesson-1"),
            _item("place-value-table", "TABLE", ["table"], "lesson-1"),
            _item("place-value-formula", "FORMULA", ["formula"], "lesson-1"),
            _item("lesson-2", "LESSON", ["lesson-2"], "unit-1"),
            _item("decimal-concept", "CONCEPT", ["concept-2"], "lesson-2"),
        ],
        "unclassified_structural_item_keys": [],
    }

    class SequenceProvider:
        def __init__(self) -> None:
            self.payloads: list[dict[str, object]] = []
            self.responses = [first_batch, second_batch]

        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            self.payloads.append(payload)
            return ModelResult(output={"text": json.dumps(self.responses.pop(0))})

    with postgres_session_factory.begin() as session:
        document, structural_run = _document_and_structural_run(session)
        provider = SequenceProvider()
        gateway = ModelGateway(
            session,
            routes={ModelTask.CURRICULUM_SEMANTICS: ModelRoute("fixture", "semantic-fixture-v1")},
            providers={"fixture": provider},
        )
        run = extract_educational_semantics(
            session,
            document=document,
            structural_run=structural_run,
            gateway=gateway,
            max_structural_items_per_batch=7,
        )

    first_input = json.loads(provider.payloads[0]["input"])
    second_input = json.loads(provider.payloads[1]["input"])
    assert run.status == "COMPLETED"
    assert len(first_input["batch"]["structural_items"]) == 7
    assert len(second_input["batch"]["structural_items"]) == 7
    assert first_input["known_semantic_context"] == []
    assert {item["semantic_key"] for item in second_input["known_semantic_context"]} == {
        "unit-1", "lesson-1", "place-value"
    }
    assert second_input["batch"]["structural_items"][0]["parent_item_key"] == "lesson-1"


def test_catastrophic_missing_unit_lesson_coverage_is_recorded_as_failed_run(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    payload = {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "items": [_item("unclassified-example", "EXAMPLE", ["root"])],
        "unclassified_structural_item_keys": [
            "unit", "lesson-1", "concept-1", "objective", "definition", "example",
            "exercise", "vocabulary", "figure", "table", "formula", "lesson-2", "concept-2",
        ],
    }
    with postgres_session_factory.begin() as session:
        document, structural_run = _document_and_structural_run(session)
        failed = extract_educational_semantics(
            session,
            document=document,
            structural_run=structural_run,
            gateway=_gateway(session, ModelResult(output={"text": json.dumps(payload)})),
        )
        persisted_document = session.get(ContentDocument, document.id)

    assert failed.status == "FAILED"
    assert "Unit/Lesson coverage" in failed.failure_detail
    assert persisted_document is not None
    assert persisted_document.status == "STRUCTURAL_READY"
