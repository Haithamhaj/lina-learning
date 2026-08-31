"""Deterministic contracts for the Parent/System Student Core Profile."""

from datetime import date
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.core_profile import (
    EffectiveGradePeriodConflict,
    InvalidDateOfBirth,
    derive_age_years,
    resolve_effective_grade_period,
    set_active_grade_period,
    student_core_context,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import GradePeriod, Student, User


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Student Core Profile tests",
)


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    database_url = normalize_database_url(os.environ["DATABASE_URL"])
    schema = f"student_core_profile_{uuid4().hex}"
    admin_engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema},public"})
    for table in (User.__table__, Student.__table__, GradePeriod.__table__):
        table.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def _student(session: Session, *, name: str | None = None, dob: date | None = None) -> Student:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=name, date_of_birth=dob)
    session.add(student)
    session.flush()
    return student


@pytest.mark.parametrize(
    ("date_of_birth", "as_of", "expected"),
    [
        (date(2015, 8, 31), date(2026, 8, 31), 11),
        (date(2015, 9, 1), date(2026, 8, 31), 10),
        (date(2016, 2, 29), date(2025, 2, 28), 8),
        (date(2016, 2, 29), date(2025, 3, 1), 9),
    ],
)
def test_derive_age_years_respects_birthday_boundaries(
    date_of_birth: date,
    as_of: date,
    expected: int,
) -> None:
    assert derive_age_years(date_of_birth, as_of=as_of) == expected


def test_derive_age_years_keeps_missing_date_of_birth_unavailable() -> None:
    assert derive_age_years(None, as_of=date(2026, 8, 31)) is None


def test_derive_age_years_rejects_future_date_of_birth() -> None:
    with pytest.raises(InvalidDateOfBirth, match="cannot be in the future"):
        derive_age_years(date(2026, 9, 1), as_of=date(2026, 8, 31))


def test_resolve_effective_grade_period_returns_only_the_current_student_period(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        student_a = _student(session, name="A")
        student_b = _student(session, name="B")
        session.add_all(
            [
                GradePeriod(student_id=student_a.id, grade_level=5, starts_on=date(2026, 8, 1), is_active=True),
                GradePeriod(student_id=student_b.id, grade_level=8, starts_on=date(2026, 8, 1), is_active=True),
            ]
        )
        session.flush()
        period = resolve_effective_grade_period(session, student_id=student_a.id, as_of=date(2026, 8, 31))

    assert period is not None
    assert period.student_id == student_a.id
    assert period.grade_level == 5


@pytest.mark.parametrize(
    "starts_on,ends_on",
    [
        (date(2025, 8, 1), date(2026, 7, 31)),
        (date(2026, 9, 1), None),
    ],
)
def test_resolve_effective_grade_period_ignores_non_effective_periods(
    session_factory: sessionmaker[Session],
    starts_on: date,
    ends_on: date | None,
) -> None:
    with session_factory.begin() as session:
        student = _student(session)
        session.add(GradePeriod(student_id=student.id, grade_level=5, starts_on=starts_on, ends_on=ends_on, is_active=True))
        session.flush()
        period = resolve_effective_grade_period(session, student_id=student.id, as_of=date(2026, 8, 31))

    assert period is None


def test_resolve_effective_grade_period_rejects_conflicting_current_periods(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        student = _student(session)
        session.add_all(
            [
                GradePeriod(student_id=student.id, grade_level=5, starts_on=date(2026, 8, 1), is_active=True),
                GradePeriod(student_id=student.id, grade_level=6, starts_on=date(2026, 8, 15), is_active=True),
            ]
        )
        session.flush()
        with pytest.raises(EffectiveGradePeriodConflict, match="multiple effective GradePeriods"):
            resolve_effective_grade_period(session, student_id=student.id, as_of=date(2026, 8, 31))


def test_scheduling_future_grade_caps_open_current_period_without_a_gap(
    session_factory: sessionmaker[Session],
) -> None:
    today = date(2026, 8, 31)
    future_start = date(2026, 9, 15)
    with session_factory.begin() as session:
        student = _student(session)
        current = GradePeriod(
            student_id=student.id,
            grade_level=5,
            starts_on=date(2026, 8, 1),
            is_active=True,
        )
        session.add(current)
        session.flush()

        future = set_active_grade_period(
            session,
            student_id=student.id,
            grade_level=6,
            starts_on=future_start,
            ends_on=None,
            as_of=today,
        )

        assert resolve_effective_grade_period(session, student_id=student.id, as_of=today) == current
        assert resolve_effective_grade_period(session, student_id=student.id, as_of=future_start - date.resolution) == current
        assert resolve_effective_grade_period(session, student_id=student.id, as_of=future_start) == future
        assert current.ends_on == future_start - date.resolution
        assert future.starts_on == future_start
        assert current.is_active is True
        assert future.is_active is True


def test_scheduling_future_grade_does_not_extend_a_current_period_that_already_ends(
    session_factory: sessionmaker[Session],
) -> None:
    today = date(2026, 8, 31)
    existing_end = date(2026, 9, 5)
    with session_factory.begin() as session:
        student = _student(session)
        current = GradePeriod(
            student_id=student.id,
            grade_level=5,
            starts_on=date(2026, 8, 1),
            ends_on=existing_end,
            is_active=True,
        )
        session.add(current)
        session.flush()

        set_active_grade_period(
            session,
            student_id=student.id,
            grade_level=6,
            starts_on=date(2026, 9, 15),
            ends_on=None,
            as_of=today,
        )

        assert current.ends_on == existing_end


def test_scheduling_future_grade_caps_a_current_period_that_extends_past_transition(
    session_factory: sessionmaker[Session],
) -> None:
    today = date(2026, 8, 31)
    future_start = date(2026, 9, 15)
    with session_factory.begin() as session:
        student = _student(session)
        current = GradePeriod(
            student_id=student.id,
            grade_level=5,
            starts_on=date(2026, 8, 1),
            ends_on=date(2026, 10, 31),
            is_active=True,
        )
        session.add(current)
        session.flush()

        set_active_grade_period(
            session,
            student_id=student.id,
            grade_level=6,
            starts_on=future_start,
            ends_on=None,
            as_of=today,
        )

        assert current.ends_on == date(2026, 9, 14)


def test_scheduling_future_grade_without_current_period_leaves_context_empty_until_start(
    session_factory: sessionmaker[Session],
) -> None:
    today = date(2026, 8, 31)
    future_start = date(2026, 9, 15)
    with session_factory.begin() as session:
        student = _student(session)
        set_active_grade_period(
            session,
            student_id=student.id,
            grade_level=6,
            starts_on=future_start,
            ends_on=None,
            as_of=today,
        )

        assert student_core_context(session, student_id=student.id, as_of=today).grade_level is None
        assert student_core_context(session, student_id=student.id, as_of=future_start).grade_level == 6


def test_scheduling_overlapping_future_grade_periods_raises_configuration_conflict(
    session_factory: sessionmaker[Session],
) -> None:
    today = date(2026, 8, 31)
    with session_factory.begin() as session:
        student = _student(session)
        session.add(
            GradePeriod(
                student_id=student.id,
                grade_level=6,
                starts_on=date(2026, 9, 15),
                ends_on=date(2026, 10, 31),
                is_active=True,
            )
        )
        session.flush()

        with pytest.raises(EffectiveGradePeriodConflict, match="overlaps an existing active GradePeriod"):
            set_active_grade_period(
                session,
                student_id=student.id,
                grade_level=7,
                starts_on=date(2026, 10, 1),
                ends_on=None,
                as_of=today,
            )


def test_scheduling_student_a_future_grade_does_not_modify_student_b_periods(
    session_factory: sessionmaker[Session],
) -> None:
    today = date(2026, 8, 31)
    with session_factory.begin() as session:
        student_a = _student(session, name="A")
        student_b = _student(session, name="B")
        current_a = GradePeriod(student_id=student_a.id, grade_level=5, starts_on=date(2026, 8, 1), is_active=True)
        current_b = GradePeriod(student_id=student_b.id, grade_level=8, starts_on=date(2026, 8, 1), is_active=True)
        session.add_all([current_a, current_b])
        session.flush()

        set_active_grade_period(
            session,
            student_id=student_a.id,
            grade_level=6,
            starts_on=date(2026, 9, 15),
            ends_on=None,
            as_of=today,
        )

        assert current_a.ends_on == date(2026, 9, 14)
        assert current_b.ends_on is None
        assert current_b.is_active is True
        assert student_core_context(session, student_id=student_b.id, as_of=today).grade_level == 8


def test_student_core_context_projects_only_compact_authoritative_fields(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as session:
        student = _student(session, name="Lina", dob=date(2015, 8, 31))
        session.add(GradePeriod(student_id=student.id, grade_level=5, starts_on=date(2026, 8, 1), is_active=True))
        session.flush()
        context = student_core_context(session, student_id=student.id, as_of=date(2026, 8, 31))

    assert context.as_model_input() == {"display_name": "Lina", "age_years": 11, "grade_level": 5}
    assert "date_of_birth" not in context.as_model_input()
    assert "student_id" not in context.as_model_input()
