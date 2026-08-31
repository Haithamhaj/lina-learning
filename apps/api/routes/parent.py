"""Minimal Parent-only Student identity proof route."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from services.content.status import ParentContentStatus, parent_content_status_for_student
from services.platform.auth import AuthenticatedPrincipal, UserRole, require_role
from services.platform.auth.parent_student import (
    ParentStudentAccessDenied,
    require_parent_student_access,
)
from services.platform.core_profile import (
    EffectiveGradePeriodConflict,
    InvalidDateOfBirth,
    derive_age_years,
    set_active_grade_period,
    student_core_context,
)
from services.platform.db.models import Student
from services.platform.db.session import get_session


router = APIRouter(prefix="/api/v1/parent", tags=["parent"])


class ParentStudentSummaryResponse(BaseModel):
    """The smallest identity summary needed to prove linked access."""

    id: UUID
    display_name: str | None


class ActiveGradePeriodRequest(BaseModel):
    grade_level: int = Field(ge=1, le=12)
    starts_on: date
    ends_on: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ActiveGradePeriodRequest":
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("GradePeriod end date cannot precede its start date.")
        return self


class ParentStudentCoreProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    date_of_birth: date | None = None
    active_grade_period: ActiveGradePeriodRequest | None = None


class ParentStudentCoreProfileResponse(BaseModel):
    id: UUID
    display_name: str | None
    date_of_birth: date | None
    age_years: int | None
    grade_level: int | None


def _core_profile_response(session: Session, *, student_id: UUID) -> ParentStudentCoreProfileResponse:
    student = session.get(Student, student_id)
    assert student is not None
    context = student_core_context(session, student_id=student.id, as_of=date.today())
    return ParentStudentCoreProfileResponse(
        id=student.id,
        display_name=student.display_name,
        date_of_birth=student.date_of_birth,
        age_years=context.age_years,
        grade_level=context.grade_level,
    )


def _require_linked_student(session: Session, *, principal: AuthenticatedPrincipal, student_id: UUID):
    try:
        return require_parent_student_access(session, principal=principal, student_id=student_id)
    except ParentStudentAccessDenied:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.") from None


@router.get("/students/{student_id}/summary", response_model=ParentStudentSummaryResponse)
def student_summary_for_parent(
    student_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> ParentStudentSummaryResponse:
    """Return a linked Student's minimal identity without permitting enumeration."""

    student = _require_linked_student(session, principal=principal, student_id=student_id)
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

    student = _require_linked_student(session, principal=principal, student_id=student_id)
    return parent_content_status_for_student(session, student_id=student.id)


@router.get("/students/{student_id}/core-profile", response_model=ParentStudentCoreProfileResponse)
def core_profile_for_parent(
    student_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> ParentStudentCoreProfileResponse:
    _require_linked_student(session, principal=principal, student_id=student_id)
    try:
        return _core_profile_response(session, student_id=student_id)
    except EffectiveGradePeriodConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None


@router.put("/students/{student_id}/core-profile", response_model=ParentStudentCoreProfileResponse)
def update_core_profile_for_parent(
    student_id: UUID,
    request: ParentStudentCoreProfileUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(require_role(UserRole.PARENT_ADMIN)),
    session: Session = Depends(get_session),
) -> ParentStudentCoreProfileResponse:
    student = _require_linked_student(session, principal=principal, student_id=student_id)
    today = date.today()
    try:
        if "display_name" in request.model_fields_set:
            student.display_name = request.display_name.strip() if request.display_name else None
        if "date_of_birth" in request.model_fields_set:
            if request.date_of_birth is not None:
                derive_age_years(request.date_of_birth, as_of=today)
            student.date_of_birth = request.date_of_birth
        if "active_grade_period" in request.model_fields_set and request.active_grade_period is not None:
            set_active_grade_period(
                session,
                student_id=student.id,
                grade_level=request.active_grade_period.grade_level,
                starts_on=request.active_grade_period.starts_on,
                ends_on=request.active_grade_period.ends_on,
                as_of=today,
            )
        session.flush()
        return _core_profile_response(session, student_id=student.id)
    except InvalidDateOfBirth as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from None
    except EffectiveGradePeriodConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
