"""Worker-owned registration for content derivation jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from services.content.indexing import (
    BLOCK_SCHEMA_VERSION,
    INDEX_SETTINGS_VERSION,
    build_content_index,
)
from services.content.processing import DOCLING_PROCESSOR_VERSION
from services.content.processing import process_structural_document
from services.model_gateway.factory import create_embedding_gateway
from services.platform.db.models import ContentDocument, ContentProcessingRun, Job
from services.platform.jobs import enqueue_job
from services.platform.storage import ObjectStorage

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


STRUCTURAL_PROCESSING_JOB = "content.structural_process"
STRUCTURAL_INDEX_JOB = "content.structural_index"


def structural_processing_idempotency_key(
    *, document_id: UUID, processor_version: str
) -> str:
    return f"content-structural-process:{document_id}:{processor_version}"


def structural_index_idempotency_key(
    *, document_id: UUID, structural_run_id: UUID
) -> str:
    return (
        f"content-structural-index:{document_id}:{structural_run_id}:"
        f"{BLOCK_SCHEMA_VERSION}:{INDEX_SETTINGS_VERSION}"
    )


def register_content_handlers(
    registry: "JobHandlerRegistry",
    *,
    session_factory: sessionmaker[Session],
    storage: ObjectStorage,
) -> None:
    """Attach content-owned structural processing and indexing jobs."""

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
            run = process_structural_document(
                session,
                storage=storage,
                document=document,
                processor_version=processor_version or DOCLING_PROCESSOR_VERSION,
            )
            if run.status != "COMPLETED":
                session.commit()
                raise RuntimeError(run.failure_detail or "Structural processing failed.")
            index_job = enqueue_job(
                session,
                job_type=STRUCTURAL_INDEX_JOB,
                payload={
                    "document_id": str(document.id),
                    "structural_processing_run_id": str(run.id),
                },
                idempotency_key=structural_index_idempotency_key(
                    document_id=document.id,
                    structural_run_id=run.id,
                ),
            )
            session.commit()
            return {
                "document_id": str(document.id),
                "processing_run_id": str(run.id),
                "index_job_id": str(index_job.id),
            }

    def handle_structural_index(job: Job) -> dict[str, object]:
        document_id = job.payload.get("document_id")
        structural_run_id = job.payload.get("structural_processing_run_id")
        if not isinstance(document_id, str) or not isinstance(structural_run_id, str):
            raise ValueError(
                "content.structural_index requires document_id and structural_processing_run_id."
            )
        with session_factory() as session:
            document = session.get(ContentDocument, UUID(document_id))
            structural_run = session.get(ContentProcessingRun, UUID(structural_run_id))
            if document is None or structural_run is None:
                raise LookupError("Source document or structural processing run does not exist.")
            if structural_run.document_id != document.id or structural_run.status != "COMPLETED":
                raise ValueError("content.structural_index requires a completed structural run for its document.")
            index_run = build_content_index(
                session,
                document=document,
                structural_run=structural_run,
                gateway=create_embedding_gateway(session),
            )
            session.commit()
            if index_run.status != "COMPLETED":
                raise RuntimeError(index_run.failure_detail or "Structural indexing failed.")
            return {
                "document_id": str(document.id),
                "structural_processing_run_id": str(structural_run.id),
                "content_index_run_id": str(index_run.id),
            }

    registry.register(STRUCTURAL_PROCESSING_JOB, handle_structural_processing)
    registry.register(STRUCTURAL_INDEX_JOB, handle_structural_index)
