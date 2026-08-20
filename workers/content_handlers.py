"""Worker-owned registration for content derivation jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from services.content.processing import process_structural_document
from services.platform.db.models import ContentDocument, Job
from services.platform.storage import ObjectStorage

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


STRUCTURAL_PROCESSING_JOB = "content.structural_process"


def register_content_handlers(
    registry: "JobHandlerRegistry",
    *,
    session_factory: sessionmaker[Session],
    storage: ObjectStorage,
) -> None:
    """Attach only the content-owned job type to the generic worker registry."""

    def handle_structural_processing(job: Job) -> dict[str, object]:
        document_id = job.payload.get("document_id")
        processor_version = job.payload.get("processor_version")
        if not isinstance(document_id, str):
            raise ValueError("content.structural_process requires document_id.")
        if processor_version is not None and not isinstance(processor_version, str):
            raise ValueError("processor_version must be a string when supplied.")
        with session_factory() as session:
            document = session.get(ContentDocument, UUID(document_id))
            if document is None:
                raise LookupError(f"Source document {document_id!r} does not exist.")
            run = process_structural_document(session, storage=storage, document=document, processor_version=processor_version or "docling-2.121.0")
            session.commit()
            if run.status != "COMPLETED":
                raise RuntimeError(run.failure_detail or "Structural processing failed.")
            return {"document_id": str(document.id), "processing_run_id": str(run.id)}

    registry.register(STRUCTURAL_PROCESSING_JOB, handle_structural_processing)
