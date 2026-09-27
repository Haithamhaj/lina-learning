#!/usr/bin/env python3
"""Preview or apply an existing Student's Core Profile without creating an account."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.platform.config import Settings
from services.platform.core_profile import (
    EffectiveGradePeriodConflict,
    InvalidDateOfBirth,
    StudentCoreProfileNotFound,
    derive_age_years,
    resolve_effective_grade_period,
    set_active_grade_period,
    student_core_context,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import Student


def bootstrap_student_core_profile(
    factory: sessionmaker[Session],
    *,
    student_id: UUID,
    display_name: str,
    date_of_birth: date,
    grade_level: int,
    grade_starts_on: date,
    apply: bool = False,
    as_of: date | None = None,
) -> dict[str, object]:
    """Validate and preview the exact Student; commit only with explicit apply."""

    today = as_of or date.today()
    name = display_name.strip()
    if not name or len(name) > 200:
        raise ValueError("Display name must contain 1 to 200 characters after trimming.")
    derive_age_years(date_of_birth, as_of=today)
    if not 1 <= grade_level <= 12:
        raise ValueError("Grade level must be between 1 and 12.")
    if grade_starts_on > today:
        raise ValueError("Active GradePeriod start date cannot be in the future.")

    with factory() as session:
        try:
            student = session.scalar(select(Student).where(Student.id == student_id).with_for_update())
            if student is None or not student.is_active:
                raise StudentCoreProfileNotFound("Active Student with the supplied ID was not found.")

            current = resolve_effective_grade_period(session, student_id=student_id, as_of=today)
            before = _summary(session, student, as_of=today)
            changed = (
                student.display_name != name
                or student.date_of_birth != date_of_birth
                or current is None
                or current.grade_level != grade_level
                or current.starts_on != grade_starts_on
                or current.ends_on is not None
            )

            student.display_name = name
            student.date_of_birth = date_of_birth
            set_active_grade_period(
                session,
                student_id=student_id,
                grade_level=grade_level,
                starts_on=grade_starts_on,
                ends_on=None,
                as_of=today,
            )
            after = _summary(session, student, as_of=today)
            if apply:
                session.commit()
            else:
                session.rollback()
            return {
                "student_id": str(student_id),
                "mode": "APPLIED" if apply else "PREVIEW_ROLLED_BACK",
                "changed": changed,
                "before": before,
                "after": after,
            }
        except Exception:
            session.rollback()
            raise


def _summary(session: Session, student: Student, *, as_of: date) -> dict[str, object]:
    core = student_core_context(session, student_id=student.id, as_of=as_of)
    period = resolve_effective_grade_period(session, student_id=student.id, as_of=as_of)
    return {
        **core.as_model_input(),
        "date_of_birth_set": student.date_of_birth is not None,
        "grade_starts_on": period.starts_on.isoformat() if period is not None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-id", type=UUID, required=True, help="Exact existing Student UUID")
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--date-of-birth", type=date.fromisoformat, required=True)
    parser.add_argument("--grade-level", type=int, required=True)
    parser.add_argument("--grade-starts-on", type=date.fromisoformat, required=True)
    parser.add_argument("--env-file", help="Explicit settings file; otherwise use normal environment")
    parser.add_argument("--apply", action="store_true", help="Commit the previewed change")
    args = parser.parse_args()

    settings = Settings(_env_file=args.env_file) if args.env_file else Settings()
    if not settings.database_url:
        parser.error("DATABASE_URL is required.")
    engine = create_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)
    try:
        result = bootstrap_student_core_profile(
            sessionmaker(engine, expire_on_commit=False),
            student_id=args.student_id,
            display_name=args.display_name,
            date_of_birth=args.date_of_birth,
            grade_level=args.grade_level,
            grade_starts_on=args.grade_starts_on,
            apply=args.apply,
        )
    except (ValueError, StudentCoreProfileNotFound, EffectiveGradePeriodConflict, InvalidDateOfBirth) as error:
        parser.error(str(error))
    finally:
        engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
