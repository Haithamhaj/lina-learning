"""Versioned Docling structural processing for immutable source documents."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from services.platform.db.models import ContentBlock, ContentDocument, ContentProcessingRun
from services.platform.storage import ObjectStorage

from .docling_adapter import extract_structural_items
from .repository import create_content_block, create_processing_run, find_processing_run
from services.retrieval.embeddings import deterministic_embedding

DOCLING_PROCESSOR_VERSION = "docling-2.121.0"


def process_structural_document(
    session: Session,
    *,
    storage: ObjectStorage,
    document: ContentDocument,
    processor_version: str = DOCLING_PROCESSOR_VERSION,
) -> ContentProcessingRun:
    """Create one source-linked, versioned Docling run for an original document.

    A document row lock makes direct re-runs safe, while a database uniqueness
    constraint makes the input/version identity durable across worker retries.
    """

    locked_document = session.execute(
        select(ContentDocument)
        .where(ContentDocument.id == document.id)
        .with_for_update()
    ).scalar_one()
    run = find_processing_run(
        session,
        document_id=locked_document.id,
        kind="STRUCTURAL",
        processor_version=processor_version,
    )
    if run is not None and run.status == "COMPLETED":
        return run
    if run is None:
        run = create_processing_run(
            session,
            document_id=locked_document.id,
            kind="STRUCTURAL",
            processor_version=processor_version,
        )
    else:
        session.execute(delete(ContentBlock).where(ContentBlock.processing_run_id == run.id))
        run.status = "PENDING"
        run.failure_detail = None

    locked_document.status = "PROCESSING"
    try:
        source_content = storage.get(locked_document.original_storage_key).content
        items = extract_structural_items(
            content_type=locked_document.content_type,
            content=source_content,
            filename=locked_document.filename,
        )
        if not items:
            raise ValueError("Docling produced no structural items for the source document.")
        for item in items:
            create_content_block(
                session,
                document_id=locked_document.id,
                processing_run_id=run.id,
                text=item.text,
                block_type=item.item_type,
                page_number=item.page_number,
                source_ref=item.source_ref,
                attributes=item.attributes,
                embedding=deterministic_embedding(item.text),
            )
    except Exception as error:
        run.status = "FAILED"
        run.failure_detail = f"{type(error).__name__}: {error}"[:1000]
        locked_document.status = "PROCESSING_FAILED"
        session.flush()
        return run

    run.status = "COMPLETED"
    run.completed_at = datetime.now(UTC)
    locked_document.status = "STRUCTURAL_READY"
    session.flush()
    return run


def process_markdown_document(
    session: Session,
    *,
    storage: ObjectStorage,
    document: ContentDocument,
) -> ContentProcessingRun:
    """Compatibility name for the original fixture-only task path."""

    return process_structural_document(session, storage=storage, document=document)
