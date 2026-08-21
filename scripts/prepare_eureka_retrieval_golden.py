"""Build a disposable real-Eureka TASK-014 semantic/indexed golden region."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from services.content.indexing import build_content_index
from services.content.repository import (
    create_semantic_items,
    create_semantic_processing_run,
)
from services.content.semantic_contract import validate_semantic_output
from services.content.semantics import _extract_batch, _validate_semantic_coverage
from services.model_gateway.factory import (
    create_curriculum_semantics_gateway,
    create_embedding_gateway,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    ContentDocument,
    ContentProcessingRun,
    ContentSemanticProcessingRun,
    DocumentStructuralItem,
    ModelTask,
)


GOLDEN_PAGES = {1, 2}
SEMANTIC_SETTINGS_VERSION = "task014-eureka-golden-v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        required=True,
        help="Disposable PostgreSQL database containing a TASK-011 Eureka run.",
    )
    parser.add_argument("--filename", default="EM_G5_M1_StudentWorkbook.pdf")
    args = parser.parse_args()
    engine = create_engine(normalize_database_url(args.database_url))
    try:
        with Session(engine) as session:
            document, structural_run, items = _load_region(session, args.filename)
            semantic_run = _semantic_run(session, document, structural_run, items)
            index_run = build_content_index(
                session,
                document=document,
                semantic_run=semantic_run,
                gateway=create_embedding_gateway(session),
            )
            session.commit()
            print(
                f"Eureka retrieval golden fixture: semantic_run={semantic_run.id} index_run={index_run.id} blocks={session.query(DocumentStructuralItem).filter(DocumentStructuralItem.processing_run_id == structural_run.id, DocumentStructuralItem.page_number.in_(GOLDEN_PAGES)).count()}"
            )
    finally:
        engine.dispose()


def _load_region(
    session: Session, filename: str
) -> tuple[ContentDocument, ContentProcessingRun, list[DocumentStructuralItem]]:
    document = (
        session.execute(
            select(ContentDocument)
            .where(ContentDocument.filename == filename)
            .order_by(ContentDocument.created_at.desc())
        )
        .scalars()
        .first()
    )
    if document is None:
        raise SystemExit(
            "No Eureka document is present. Run scripts/setup_eureka_demo.py first."
        )
    structural_run = (
        session.execute(
            select(ContentProcessingRun)
            .where(
                ContentProcessingRun.document_id == document.id,
                ContentProcessingRun.kind == "STRUCTURAL",
                ContentProcessingRun.status == "COMPLETED",
            )
            .order_by(ContentProcessingRun.completed_at.desc())
        )
        .scalars()
        .first()
    )
    if structural_run is None:
        raise SystemExit("No completed Eureka structural run is present.")
    items = (
        session.execute(
            select(DocumentStructuralItem)
            .where(
                DocumentStructuralItem.processing_run_id == structural_run.id,
                DocumentStructuralItem.page_number.in_(GOLDEN_PAGES),
            )
            .order_by(
                DocumentStructuralItem.reading_order, DocumentStructuralItem.item_key
            )
        )
        .scalars()
        .all()
    )
    if not items:
        raise SystemExit("Eureka structural run has no golden-region items.")
    return document, structural_run, items


def _semantic_run(
    session: Session,
    document: ContentDocument,
    structural_run: ContentProcessingRun,
    items: list[DocumentStructuralItem],
) -> ContentSemanticProcessingRun:
    existing = session.execute(
        select(ContentSemanticProcessingRun).where(
            ContentSemanticProcessingRun.document_id == document.id,
            ContentSemanticProcessingRun.structural_processing_run_id
            == structural_run.id,
            ContentSemanticProcessingRun.settings_version == SEMANTIC_SETTINGS_VERSION,
            ContentSemanticProcessingRun.status == "COMPLETED",
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    gateway = create_curriculum_semantics_gateway(session)
    output = _extract_batch(
        gateway,
        document=document,
        batch=items,
        batch_index=0,
        parent_key_by_id={item.id: item.item_key for item in items},
        known_items=[],
    )
    validate_semantic_output(
        output, available_structural_item_keys={item.item_key for item in items}
    )
    _validate_semantic_coverage(items, output.items)
    route = gateway.route_for(ModelTask.CURRICULUM_SEMANTICS)
    run = create_semantic_processing_run(
        session,
        document_id=document.id,
        structural_processing_run_id=structural_run.id,
        semantic_schema_version="educational-semantics-v1",
        prompt_version="task014-eureka-golden-v1",
        model_route_version=f"{route.provider}:{route.model}",
        provider=route.provider,
        model=route.model,
        settings_version=SEMANTIC_SETTINGS_VERSION,
        settings_metadata={"pages": sorted(GOLDEN_PAGES)},
    )
    create_semantic_items(
        session,
        document_id=document.id,
        semantic_processing_run_id=run.id,
        items=output.items,
        structural_items_by_key={item.item_key: item for item in items},
    )
    run.status = "COMPLETED"
    return run


if __name__ == "__main__":
    main()
