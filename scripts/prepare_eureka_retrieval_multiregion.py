"""Build a disposable four-region Eureka semantic/index fixture for TASK-014."""

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
from services.content.semantic_contract import (
    SemanticExtractionItem,
    validate_semantic_output,
)
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


REGION_PAGES = (2, 18, 30, 42)
MAX_ITEMS_PER_REGION = 40
SETTINGS_VERSION = "task014-eureka-multiregion-v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--filename", default="EM_G5_M1_StudentWorkbook.pdf")
    args = parser.parse_args()
    engine = create_engine(normalize_database_url(args.database_url))
    try:
        with Session(engine) as session:
            document, structural_run = _document_and_run(session, args.filename)
            semantic_run = _semantic_run(session, document, structural_run)
            index_run = build_content_index(
                session,
                document=document,
                semantic_run=semantic_run,
                gateway=create_embedding_gateway(session),
            )
            session.commit()
            print(
                f"Eureka multi-region fixture: pages={REGION_PAGES} semantic_run={semantic_run.id} index_run={index_run.id}"
            )
    finally:
        engine.dispose()


def _document_and_run(
    session: Session, filename: str
) -> tuple[ContentDocument, ContentProcessingRun]:
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
        raise SystemExit("No Eureka document is present.")
    run = (
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
    if run is None:
        raise SystemExit("No completed Eureka structural run is present.")
    return document, run


def _semantic_run(
    session: Session,
    document: ContentDocument,
    structural_run: ContentProcessingRun,
) -> ContentSemanticProcessingRun:
    existing = session.execute(
        select(ContentSemanticProcessingRun).where(
            ContentSemanticProcessingRun.document_id == document.id,
            ContentSemanticProcessingRun.structural_processing_run_id
            == structural_run.id,
            ContentSemanticProcessingRun.settings_version == SETTINGS_VERSION,
            ContentSemanticProcessingRun.status == "COMPLETED",
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    gateway = create_curriculum_semantics_gateway(session)
    route = gateway.route_for(ModelTask.CURRICULUM_SEMANTICS)
    run = create_semantic_processing_run(
        session,
        document_id=document.id,
        structural_processing_run_id=structural_run.id,
        semantic_schema_version="educational-semantics-v1",
        prompt_version="task014-eureka-multiregion-v1",
        model_route_version=f"{route.provider}:{route.model}",
        provider=route.provider,
        model=route.model,
        settings_version=SETTINGS_VERSION,
        settings_metadata={
            "pages": list(REGION_PAGES),
            "max_items": MAX_ITEMS_PER_REGION,
        },
    )
    all_items: list[SemanticExtractionItem] = []
    sources_by_key: dict[str, DocumentStructuralItem] = {}
    for batch_index, page in enumerate(REGION_PAGES):
        page_items = list(
            session.execute(
                select(DocumentStructuralItem)
                .where(
                    DocumentStructuralItem.processing_run_id == structural_run.id,
                    DocumentStructuralItem.page_number == page,
                )
                .order_by(
                    DocumentStructuralItem.reading_order,
                    DocumentStructuralItem.item_key,
                )
            ).scalars()
        )
        region = [item for item in page_items if _is_learning_source(item)][
            :MAX_ITEMS_PER_REGION
        ]
        if not region:
            raise SystemExit(f"Eureka page {page} has no structural items.")
        print(f"Extracting Eureka region page={page} structural_items={len(region)}")
        output = _extract_batch(
            gateway,
            semantic_run=run,
            document=document,
            batch=region,
            batch_index=batch_index,
            parent_key_by_id={item.id: item.item_key for item in region},
            known_items=[],
        )
        available_keys = {item.item_key for item in region}
        validate_semantic_output(output, available_structural_item_keys=available_keys)
        _validate_semantic_coverage(region, output.items)
        all_items.extend(_namespace(item, page) for item in output.items)
        sources_by_key.update({item.item_key: item for item in region})

    create_semantic_items(
        session,
        document_id=document.id,
        semantic_processing_run_id=run.id,
        items=all_items,
        structural_items_by_key=sources_by_key,
    )
    run.status = "COMPLETED"
    return run


def _namespace(item: SemanticExtractionItem, page: int) -> SemanticExtractionItem:
    prefix = f"p{page}:"
    return item.model_copy(
        update={
            "semantic_key": prefix + item.semantic_key,
            "parent_semantic_key": (
                prefix + item.parent_semantic_key
                if item.parent_semantic_key is not None
                else None
            ),
        }
    )


def _is_learning_source(item: DocumentStructuralItem) -> bool:
    text = (item.text or "").strip()
    return bool(text.strip("_ ")) and text not in {"Name", "Date", "EURTEKA"}


if __name__ == "__main__":
    main()
