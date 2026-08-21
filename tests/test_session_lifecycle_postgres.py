"""Deterministic contracts for automatic learning-session closure."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.config import Settings
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    Job,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningSession,
    Student,
    User,
)
from services.tutor.session_lifecycle import (
    SESSION_CONSOLIDATION_JOB,
    SessionLifecyclePolicy,
    close_inactive_sessions,
    session_lifecycle_policy,
)
from services.tutor.student_sessions import append_student_message, open_or_resume_math_session
from workers.job_worker import run_session_lifecycle_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for session lifecycle tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, users CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _open_session(session: Session, *, last_activity_at: datetime) -> LearningSession:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    learning_session = LearningSession(
        student_id=student.id,
        subject="MATH",
        status="OPEN",
        last_activity_at=last_activity_at,
    )
    session.add(learning_session)
    session.flush()
    return learning_session


def _policy() -> SessionLifecyclePolicy:
    return SessionLifecyclePolicy(
        version="fixture-v1",
        inactivity=timedelta(minutes=10),
        grace=timedelta(minutes=5),
    )


def _jobs_for(session: Session, learning_session: LearningSession) -> list[Job]:
    return list(
        session.query(Job)
        .filter_by(job_type=SESSION_CONSOLIDATION_JOB)
        .filter(Job.payload["session_id"].astext == str(learning_session.id))
        .all()
    )


def test_session_remains_open_during_configured_grace_window(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=12),
        )

        closed = close_inactive_sessions(
            session,
            now=now,
            policy=_policy(),
        )

        assert closed == []
        assert learning_session.status == "OPEN"


def test_recent_open_session_stays_open_without_a_consolidation_job(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=9),
        )

        assert close_inactive_sessions(session, now=now, policy=_policy()) == []
        assert learning_session.status == "OPEN"
        assert _jobs_for(session, learning_session) == []


def test_configured_policy_keeps_version_and_both_timing_values_central(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    del postgres_session_factory
    policy = session_lifecycle_policy(
        Settings(
            _env_file=None,
            session_lifecycle_policy_version="lifecycle-test-v2",
            session_inactivity_seconds=600,
            session_grace_seconds=120,
        )
    )

    assert policy.version == "lifecycle-test-v2"
    assert policy.inactivity == timedelta(minutes=10)
    assert policy.grace == timedelta(minutes=2)


@pytest.mark.parametrize("elapsed", [timedelta(minutes=9), timedelta(minutes=12)])
def test_student_return_before_close_resumes_the_same_open_session(
    postgres_session_factory: sessionmaker[Session],
    elapsed: timedelta,
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        original = _open_session(session, last_activity_at=now - elapsed)

        resumed = open_or_resume_math_session(
            session,
            student_id=original.student_id,
            now=now,
            lifecycle_policy=_policy(),
        )

        assert resumed.id == original.id
        assert resumed.status == "OPEN"
        assert resumed.last_activity_at == now
        assert _jobs_for(session, original) == []


def test_inactivity_plus_grace_closes_once_and_next_student_entry_creates_new_session(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        original = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=16),
        )

        replacement = open_or_resume_math_session(
            session,
            student_id=original.student_id,
            now=now,
            lifecycle_policy=_policy(),
        )

        assert original.status == "CLOSED"
        assert original.closed_at == now
        assert replacement.id != original.id
        assert replacement.status == "OPEN"
        jobs = _jobs_for(session, original)
        assert len(jobs) == 1
        assert jobs[0].payload == {
            "session_id": str(original.id),
            "lifecycle_policy_version": "fixture-v1",
            "closed_at": now.isoformat(),
        }


def test_repeated_lifecycle_scans_close_once_and_enqueue_one_consolidation_job(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=16),
        )

        assert close_inactive_sessions(session, now=now, policy=_policy()) == [learning_session]
        assert close_inactive_sessions(session, now=now, policy=_policy()) == []
        assert learning_session.status == "CLOSED"
        assert len(_jobs_for(session, learning_session)) == 1


def test_worker_lifecycle_tick_closes_eligible_session_and_queues_deferred_job(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=16),
        )
        learning_session_id = learning_session.id

    assert run_session_lifecycle_once(
        postgres_session_factory,
        now=now,
        policy=_policy(),
    ) == 1

    with postgres_session_factory() as session:
        persisted = session.get(LearningSession, learning_session_id)
        assert persisted is not None and persisted.status == "CLOSED"
        assert len(_jobs_for(session, persisted)) == 1


def test_simultaneous_lifecycle_scans_do_not_duplicate_the_close_job(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=16),
        )
        learning_session_id = learning_session.id

    first = postgres_session_factory()
    second = postgres_session_factory()
    try:
        first.begin()
        first_session = first.get(LearningSession, learning_session_id)
        assert first_session is not None
        assert close_inactive_sessions(first, now=now, policy=_policy()) == [first_session]

        with second.begin():
            assert close_inactive_sessions(second, now=now, policy=_policy()) == []

        first.commit()
        with postgres_session_factory() as check:
            persisted = check.get(LearningSession, learning_session_id)
            assert persisted is not None and persisted.status == "CLOSED"
            assert len(_jobs_for(check, persisted)) == 1
    finally:
        if first.in_transaction():
            first.rollback()
        first.close()
        second.close()


def test_student_activity_refreshes_the_open_session_timestamp(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    initial = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(session, last_activity_at=initial)
        append_student_message(
            session,
            learning_session=learning_session,
            content="I am ready to keep learning.",
        )

        assert learning_session.last_activity_at > initial


def test_closure_leaves_candidate_and_all_derived_learning_records_untouched(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _open_session(
            session,
            last_activity_at=now - timedelta(minutes=16),
        )
        session.add(
            CandidateEvent(
                session_id=learning_session.id,
                event_type="learning_attempt",
                signal="attempted_fraction_comparison",
                payload={"fixture": True},
            )
        )
        session.flush()

        assert close_inactive_sessions(session, now=now, policy=_policy()) == [learning_session]
        assert session.query(CandidateEvent).filter_by(session_id=learning_session.id).count() == 1
        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert session.query(CurrentLearningState).count() == 0
        assert session.query(LearnerPattern).count() == 0
