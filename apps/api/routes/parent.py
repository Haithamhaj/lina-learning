"""Minimal Parent-only Student identity proof route."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.content.status import ParentContentStatus, parent_content_status_for_student
from services.platform.auth import AuthenticatedPrincipal, UserRole, require_role
from services.platform.auth.parent_student import (
    ParentStudentAccessDenied,
    require_parent_student_access,
)
from services.platform.db.session import get_session


router = APIRouter(prefix="/api/v1/parent", tags=["parent"])


class ParentStudentSummaryResponse(BaseModel):
    """The smallest identity summary needed to prove linked access."""

    id: UUID
    display_name: str | None


@router.get("/students/{student_id}/summary", response_model=ParentStudentSummaryResponse)
def student_summary_for_parent(
    student_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> ParentStudentSummaryResponse:
    """Return a linked Student's minimal identity without permitting enumeration."""

    try:
        student = require_parent_student_access(
            session,
            principal=principal,
            student_id=student_id,
        )
    except ParentStudentAccessDenied:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        ) from None
    return ParentStudentSummaryResponse(id=student.id, display_name=student.display_name)


@router.get(
    "/students/{student_id}/content-status",
    response_model=ParentContentStatus,
)
def content_status_for_parent(
    student_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> ParentContentStatus:
    """Return a linked Student's compact, current-lineage content readiness."""

    try:
        student = require_parent_student_access(
            session,
            principal=principal,
            student_id=student_id,
        )
    except ParentStudentAccessDenied:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        ) from None
    return parent_content_status_for_student(session, student_id=student.id)
