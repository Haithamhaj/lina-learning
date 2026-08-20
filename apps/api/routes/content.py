"""Minimal Parent-only source document intake."""

from base64 import b64decode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.content.ingestion import ingest_source_document
from services.platform.auth import AuthenticatedPrincipal, UserRole, require_role
from services.platform.config import get_settings
from services.platform.db.session import get_session
from services.platform.storage import create_object_storage

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
