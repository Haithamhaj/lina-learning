"""Versioned structural processing for the supported local fixture format."""

from __future__ import annotations

from sqlalchemy.orm import Session

from services.platform.db.models import ContentDocument, ContentProcessingRun
from services.platform.storage import ObjectStorage

from .docling_adapter import extract_pdf_structural_markdown, extract_structural_markdown
from .repository import create_content_block, create_processing_run


def process_markdown_document(
    session: Session,
    *,
    storage: ObjectStorage,
    document: ContentDocument,
) -> ContentProcessingRun:
    """Parse a fixture Markdown original and persist a reproducible run."""

    source_content = storage.get(document.original_storage_key).content
    run = create_processing_run(
        session,
        document_id=document.id,
        kind="STRUCTURAL",
        processor_version="docling-2.20.0",
    )
    if document.content_type == "text/markdown":
        normalized = extract_structural_markdown(source_content.decode("utf-8"))
    elif document.content_type == "application/pdf":
        normalized = extract_pdf_structural_markdown(source_content)
    else:
        raise ValueError("The structural processor does not support this content type.")
    create_content_block(
        session,
        document_id=document.id,
        processing_run_id=run.id,
        text=normalized,
        block_type="STRUCTURAL",
        page_number=1,
        source_ref=f"{document.filename}#document",
    )
    run.status = "COMPLETED"
    document.status = "STRUCTURAL_READY"
    session.flush()
    return run
