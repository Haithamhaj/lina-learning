"""Explicit persistence helpers for source and derived content."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import ContentBlock, ContentDocument, ContentProcessingRun


def create_content_document(
    session: Session,
    *,
    student_id: UUID,
    grade_level: int,
    subject: str,
    original_storage_key: str,
    original_checksum: str,
    filename: str,
    content_type: str,
) -> ContentDocument:
    document = ContentDocument(
        student_id=student_id,
        grade_level=grade_level,
        subject=subject,
        original_storage_key=original_storage_key,
        original_checksum=original_checksum,
        filename=filename,
        content_type=content_type,
    )
    session.add(document)
    session.flush()
    return document


def create_processing_run(
    session: Session,
    *,
    document_id: UUID,
    kind: str,
    processor_version: str,
) -> ContentProcessingRun:
    run = ContentProcessingRun(
        document_id=document_id,
        kind=kind,
        processor_version=processor_version,
    )
    session.add(run)
    session.flush()
    return run


def find_processing_run(
    session: Session,
    *,
    document_id: UUID,
    kind: str,
    processor_version: str,
) -> ContentProcessingRun | None:
    """Return the single idempotent derivation run for an input/version pair."""

    return session.execute(
        select(ContentProcessingRun).where(
            ContentProcessingRun.document_id == document_id,
            ContentProcessingRun.kind == kind,
            ContentProcessingRun.processor_version == processor_version,
        )
    ).scalar_one_or_none()


def create_content_block(
    session: Session,
    *,
    document_id: UUID,
    processing_run_id: UUID,
    text: str,
    block_type: str,
    page_number: int | None,
    source_ref: str,
    attributes: dict[str, object] | None = None,
    embedding: list[float] | None = None,
) -> ContentBlock:
    block = ContentBlock(
        document_id=document_id,
        processing_run_id=processing_run_id,
        text=text,
        block_type=block_type,
        page_number=page_number,
        source_ref=source_ref,
        attributes=attributes or {},
        embedding=embedding,
    )
    session.add(block)
    session.flush()
    return block
