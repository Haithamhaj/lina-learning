"""Run the TASK-012 semantic golden set against the local Eureka PDF structure.

The ignored PDF is never copied into Git. First run the TASK-011 structural
verifier with the same disposable database. This verifier then selects the
real module-cover and first place-value practice region (pages 1-2), calls the
configured Model Gateway semantic route, and validates only the bounded model
output against explicit educational and source/page expectations.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from services.content.repository import create_semantic_processing_run
from services.content.semantic_contract import (
    SEMANTIC_SCHEMA_VERSION,
    SemanticContractError,
    SemanticExtractionOutput,
    validate_semantic_output,
)
from services.content.semantics import SEMANTIC_PROMPT_VERSION, _extract_batch, _validate_semantic_coverage
from services.model_gateway.factory import create_curriculum_semantics_gateway
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ContentDocument, ContentProcessingRun, DocumentStructuralItem, ModelTask


DEFAULT_PDF_NAME = "EM_G5_M1_StudentWorkbook.pdf"
GOLDEN_PAGES = {1, 2}
MODULE_SOURCE_KEY = "#/texts/1"
INSTRUCTION_SOURCE_KEY = "#/texts/26"
EXAMPLE_SOURCE_KEY = "#/texts/27"
EXERCISE_SOURCE_KEYS = {"#/texts/36", "#/texts/37", "#/texts/38"}
FIGURE_SOURCE_KEYS = {"#/pictures/0", "#/pictures/1"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Disposable PostgreSQL database containing the verified TASK-011 run.")
    parser.add_argument("--filename", default=DEFAULT_PDF_NAME)
    parser.add_argument("--show-output", action="store_true", help="Print semantic labels and source keys for local diagnosis.")
    args = parser.parse_args()

    engine = create_engine(normalize_database_url(args.database_url))
    try:
        with Session(engine) as session:
            document, structural_run, items = _load_golden_region(session, filename=args.filename)
            gateway = create_curriculum_semantics_gateway(session)
            route = gateway.route_for(ModelTask.CURRICULUM_SEMANTICS)
            semantic_run = create_semantic_processing_run(
                session,
                document_id=document.id,
                structural_processing_run_id=structural_run.id,
                semantic_schema_version=SEMANTIC_SCHEMA_VERSION,
                prompt_version=SEMANTIC_PROMPT_VERSION,
                model_route_version=f"{route.provider}:{route.model}",
                provider=route.provider,
                model=route.model,
                settings_version="eureka-pages-1-2-verifier-v2",
                settings_metadata={"pages": sorted(GOLDEN_PAGES), "disposable": True},
            )
            parent_key_by_id = {item.id: item.item_key for item in items}
            output = _extract_batch(
                gateway,
                semantic_run=semantic_run,
                document=document,
                batch=items,
                batch_index=0,
                parent_key_by_id=parent_key_by_id,
                known_items=[],
            )
            if args.show_output:
                for item in output.items:
                    print(
                        f"{item.semantic_type} key={item.semantic_key!r} "
                        f"title={item.title!r} sources={item.structural_item_keys!r}"
                    )
            validate_semantic_output(
                output,
                available_structural_item_keys={item.item_key for item in items},
            )
            _validate_semantic_coverage(items, output.items)
            _assert_eureka_golden(output, items)
            session.rollback()
            print(
                "Eureka semantic golden: PASS "
                f"pages={sorted(GOLDEN_PAGES)} structural_items={len(items)} "
                f"semantic_types={dict(sorted(Counter(item.semantic_type for item in output.items).items()))}"
            )
    finally:
        engine.dispose()


def _load_golden_region(
    session: Session, *, filename: str
) -> tuple[ContentDocument, ContentProcessingRun, list[DocumentStructuralItem]]:
    document = session.execute(
        select(ContentDocument).where(ContentDocument.filename == filename).order_by(ContentDocument.created_at.desc())
    ).scalars().first()
    if document is None:
        raise SystemExit(
            "No Eureka source is present in this database. Run "
            "scripts/verify_eureka_structural_representation.py --database-url ... first."
        )
    structural_run = session.execute(
        select(ContentProcessingRun)
        .where(
            ContentProcessingRun.document_id == document.id,
            ContentProcessingRun.kind == "STRUCTURAL",
            ContentProcessingRun.status == "COMPLETED",
        )
        .order_by(ContentProcessingRun.completed_at.desc())
    ).scalars().first()
    if structural_run is None:
        raise SystemExit("The Eureka source has no completed TASK-011 structural run.")
    items = session.execute(
        select(DocumentStructuralItem)
        .where(
            DocumentStructuralItem.processing_run_id == structural_run.id,
            DocumentStructuralItem.page_number.in_(GOLDEN_PAGES),
        )
        .order_by(DocumentStructuralItem.reading_order, DocumentStructuralItem.item_key)
    ).scalars().all()
    if not items:
        raise SystemExit("The selected Eureka golden pages have no persisted structural items.")
    return document, structural_run, items


def _assert_eureka_golden(
    output: SemanticExtractionOutput, structural_items: list[DocumentStructuralItem]
) -> None:
    """Validate manually selected source facts, not counts or layout keywords."""

    source_by_key = {item.item_key: item for item in structural_items}
    for semantic_item in output.items:
        for structural_key in semantic_item.structural_item_keys:
            source = source_by_key[structural_key]
            if source.page_number not in GOLDEN_PAGES or not source.source_ref:
                raise SemanticContractError(
                    f"Semantic item {semantic_item.semantic_key!r} lacks valid Eureka page/source lineage."
                )

    _require_type_with_source(output, "UNIT", MODULE_SOURCE_KEY)
    lesson = _require_type_with_any_source(output, "LESSON", {item.item_key for item in structural_items if item.page_number == 2})
    concept = _require_type_with_any_source(output, "CONCEPT", {item.item_key for item in structural_items if item.page_number == 2})
    concept_words = f"{concept.title} {concept.description or ''}".casefold()
    if "place" not in concept_words or "value" not in concept_words:
        raise SemanticContractError("Eureka golden Concept must identify place value from the selected practice region.")
    _require_type_with_source(output, "OBJECTIVE", INSTRUCTION_SOURCE_KEY)
    _require_type_with_source(output, "EXAMPLE", EXAMPLE_SOURCE_KEY)
    _require_type_with_any_source(output, "EXERCISE", EXERCISE_SOURCE_KEYS)
    _require_type_with_any_source(output, "FIGURE", FIGURE_SOURCE_KEYS)
    if not lesson.title.strip():
        raise SemanticContractError("Eureka golden Lesson identity has no title.")


def _require_type_with_source(
    output: SemanticExtractionOutput, semantic_type: str, structural_key: str
):
    return _require_type_with_any_source(output, semantic_type, {structural_key})


def _require_type_with_any_source(
    output: SemanticExtractionOutput, semantic_type: str, structural_keys: set[str]
):
    for item in output.items:
        if item.semantic_type == semantic_type and structural_keys.intersection(item.structural_item_keys):
            return item
    raise SemanticContractError(
        f"Eureka golden is missing {semantic_type} linked to one of {sorted(structural_keys)!r}."
    )


if __name__ == "__main__":
    main()
