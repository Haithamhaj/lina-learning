"""Minimal Parent-only source document intake."""

from base64 import b64decode
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.content.ingestion import ingest_source_document
from services.platform.auth import AuthenticatedPrincipal, UserRole, require_role
from services.platform.config import get_settings
from services.platform.db.session import get_session
from services.platform.db.models import ContentDocument, ContentProcessingRun
from services.platform.jobs import enqueue_job
from services.platform.storage import create_object_storage
from workers.content_handlers import STRUCTURAL_PROCESSING_JOB

router = APIRouter(prefix="/api/v1/content", tags=["content"])


class SourceUploadRequest(BaseModel):
    student_id: UUID
    grade_level: int
    subject: str
    filename: str
    content_type: str
    content_base64: str


@router.post("/documents", status_code=status.HTTP_201_CREATED)
def upload_source_document(
    request: SourceUploadRequest,
    _: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    try:
        content = b64decode(request.content_base64, validate=True)
        document = ingest_source_document(
            session,
            storage=create_object_storage(get_settings()),
            student_id=request.student_id,
            grade_level=request.grade_level,
            subject=request.subject,
            filename=request.filename,
            content_type=request.content_type,
            content=content,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return {"document_id": str(document.id), "status": document.status}


@router.get("/documents/{document_id}")
def content_status(
    document_id: UUID,
    _: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    document = session.get(ContentDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found.")
    runs = session.query(ContentProcessingRun).filter_by(document_id=document.id).all()
    return {"document_id": str(document.id), "status": document.status, "processing_runs": [{"id": str(run.id), "version": run.processor_version, "status": run.status, "failure_detail": run.failure_detail} for run in runs]}


@router.post("/documents/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
def request_reprocess(
    document_id: UUID,
    _: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if session.get(ContentDocument, document_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found.")
    version = f"docling-2.121.0-reprocess-{uuid4().hex[:8]}"
    job = enqueue_job(session, job_type=STRUCTURAL_PROCESSING_JOB, payload={"document_id": str(document_id), "processor_version": version}, idempotency_key=f"content-reprocess:{document_id}:{version}")
    return {"job_id": str(job.id), "status": job.status, "processor_version": version}
