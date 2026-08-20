"""Immutable source-document ingestion through the project storage boundary."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import ContentDocument
from services.platform.storage import ObjectAlreadyExistsError, ObjectStorage

from .repository import create_content_document


_SUPPORTED_SOURCE_TYPES = {
    "text/markdown": {"md", "markdown"},
    "application/pdf": {"pdf"},
}


def _validate_source_file(*, filename: str, content_type: str, content: bytes) -> str:
    """Reject unsupported files before preserving an immutable original."""

    if content_type not in _SUPPORTED_SOURCE_TYPES:
        raise ValueError("Only Markdown fixture documents and PDF books are supported.")
    if not filename or "." not in filename:
        raise ValueError("A supported source filename is required.")

    suffix = filename.rsplit(".", 1)[-1].lower()
    if suffix not in _SUPPORTED_SOURCE_TYPES[content_type]:
        raise ValueError("The filename must match the declared source type.")
    if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("PDF source must have a valid PDF header.")
    return suffix


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
    suffix = _validate_source_file(
        filename=filename,
        content_type=content_type,
        content=content,
    )

    checksum = sha256(content).hexdigest()
    existing = session.execute(
        select(ContentDocument).where(
            ContentDocument.student_id == student_id,
            ContentDocument.original_checksum == checksum,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    key = f"content/{student_id}/{checksum}.{suffix}"
    try:
        stored = storage.put(
            key,
            content,
            content_type=content_type,
            metadata={"kind": "original-book", "student_id": str(student_id)},
        )
    except ObjectAlreadyExistsError:
        # A prior interrupted database transaction may leave an immutable
        # original safely published. Reuse only when its digest proves identity.
        stored = storage.head(key)
        if stored.checksum_sha256 != checksum:
            raise
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
