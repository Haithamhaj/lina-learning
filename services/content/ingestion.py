"""Immutable source-document ingestion through the project storage boundary."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import ContentDocument
from services.platform.storage import ObjectStorage

from .repository import create_content_document


def ingest_source_document(
    session: Session,
    *,
    storage: ObjectStorage,
    student_id: UUID,
    grade_level: int,
    subject: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> ContentDocument:
    """Store the immutable original once and register it with provenance."""

    if not content:
        raise ValueError("A source document must not be empty.")
    if content_type not in {"text/markdown", "application/pdf"}:
        raise ValueError("Only Markdown fixture documents and PDF books are supported.")

    checksum = sha256(content).hexdigest()
    existing = session.execute(
        select(ContentDocument).where(
            ContentDocument.student_id == student_id,
            ContentDocument.original_checksum == checksum,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    key = f"content/{student_id}/{checksum}.{suffix}"
    stored = storage.put(
        key,
        content,
        content_type=content_type,
        metadata={"kind": "original-book", "student_id": str(student_id)},
    )
    return create_content_document(
        session,
        student_id=student_id,
        grade_level=grade_level,
        subject=subject,
        original_storage_key=stored.key,
        original_checksum=stored.checksum_sha256,
        filename=filename,
        content_type=content_type,
    )
