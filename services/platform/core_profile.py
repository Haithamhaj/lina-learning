"""Deterministic Parent/System-authoritative Student Core Profile helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from services.platform.db.models import GradePeriod, Student


class InvalidDateOfBirth(ValueError):
    """Raised when an application-owned date of birth cannot be valid."""


class EffectiveGradePeriodConflict(RuntimeError):
    """Raised when configuration provides more than one effective grade."""


class StudentCoreProfileNotFound(LookupError):
    """Raised only for an internal call that cannot resolve its Student."""


@dataclass(frozen=True)
class StudentCoreContext:
    """The bounded Parent/System-authoritative input permitted to reach Tutor."""

    display_name: str | None
    age_years: int | None
    grade_level: int | None

    def as_model_input(self) -> dict[str, object]:
        """Omit unavailable fields and never expose DOB or database lineage."""

        return {
            key: value
            for key, value in {
                "display_name": self.display_name,
                "age_years": self.age_years,
                "grade_level": self.grade_level,
            }.items()
            if value is not None
        }


def derive_age_years(date_of_birth: date | None, *, as_of: date) -> int | None:
    """Derive whole completed years without storing a separate mutable age."""

    if date_of_birth is None:
        return None
    if date_of_birth > as_of:
        raise InvalidDateOfBirth("Date of birth cannot be in the future.")
    return as_of.year - date_of_birth.year - (
        (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day)
    )


def resolve_effective_grade_period(
    session: Session,
    *,
    student_id: UUID,
    as_of: date,
) -> GradePeriod | None:
    """Return exactly one active in-range period, never an arbitrary choice."""

    periods = list(
        session.scalars(
            select(GradePeriod)
            .where(
                GradePeriod.student_id == student_id,
                GradePeriod.is_active.is_(True),
                GradePeriod.starts_on <= as_of,
                or_(GradePeriod.ends_on.is_(None), GradePeriod.ends_on >= as_of),
            )
            .order_by(GradePeriod.starts_on, GradePeriod.id)
        )
    )
    if len(periods) > 1:
        raise EffectiveGradePeriodConflict(
            "Student has multiple effective GradePeriods for the requested date."
        )
    return periods[0] if periods else None


def student_core_context(
    session: Session,
    *,
    student_id: UUID,
    as_of: date,
) -> StudentCoreContext:
    """Build the single small Core Profile projection allowed into Tutor context."""

    student = session.get(Student, student_id)
    if student is None:
        raise StudentCoreProfileNotFound("Student Core Profile is unavailable.")
    period = resolve_effective_grade_period(session, student_id=student.id, as_of=as_of)
    return StudentCoreContext(
        display_name=student.display_name,
        age_years=derive_age_years(student.date_of_birth, as_of=as_of),
        grade_level=period.grade_level if period is not None else None,
    )


def set_active_grade_period(
    session: Session,
    *,
    student_id: UUID,
    grade_level: int,
    starts_on: date,
    ends_on: date | None,
    as_of: date,
) -> GradePeriod:
    """Set one explicit Parent/System current GradePeriod without hiding conflicts."""

    if ends_on is not None and ends_on < starts_on:
        raise ValueError("GradePeriod end date cannot precede its start date.")
    period = session.scalar(
        select(GradePeriod).where(
            GradePeriod.student_id == student_id,
            GradePeriod.starts_on == starts_on,
        )
    )
    current = resolve_effective_grade_period(session, student_id=student_id, as_of=as_of)
    overlapping_periods = list(
        session.scalars(
            select(GradePeriod).where(
                GradePeriod.student_id == student_id,
                GradePeriod.is_active.is_(True),
                GradePeriod.starts_on <= (ends_on or date.max),
                or_(GradePeriod.ends_on.is_(None), GradePeriod.ends_on >= starts_on),
            )
        )
    )
    current_transition = (
        current
        if current is not None and current.id != (period.id if period is not None else None) and starts_on > as_of
        else None
    )
    conflicts = [
        existing
        for existing in overlapping_periods
        if existing.id != (period.id if period is not None else None)
        and existing.id != (current_transition.id if current_transition is not None else None)
    ]
    if conflicts:
        raise EffectiveGradePeriodConflict(
            "New GradePeriod overlaps an existing active GradePeriod."
        )
    if period is None:
        period = GradePeriod(
            student_id=student_id,
            grade_level=grade_level,
            starts_on=starts_on,
            ends_on=ends_on,
            is_active=True,
        )
        session.add(period)
    else:
        period.grade_level = grade_level
        period.ends_on = ends_on
        period.is_active = True
    if current_transition is not None:
        transition_end = starts_on - timedelta(days=1)
        if current_transition.ends_on is None or current_transition.ends_on >= starts_on:
            current_transition.ends_on = transition_end
    elif current is not None and current.id != period.id:
        current.is_active = False
    session.flush()
    return period
