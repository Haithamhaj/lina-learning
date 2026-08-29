"""PostgreSQL contracts for SEG-EVID-01B structural Review requests only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    Job,
    LearningMessage,
    LearningSegment,
    LearningSession,
    SegmentLearningReview,
    Student,
    User,
)
from services.tutor.session_lifecycle import (
    SessionLifecyclePolicy,
    close_inactive_sessions,
)
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for SEG-EVID-01B tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _lineage(session: Session, *, last_activity_at: datetime | None = None) -> tuple[Student, LearningSession]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Fixture Student")
    session.add(student)
    session.flush()
    learning_session = LearningSession(
        student_id=student.id,
        subject="MATH",
        status="OPEN",
        last_activity_at=last_activity_at or datetime.now(UTC),
    )
    session.add(learning_session)
    session.flush()
    return student, learning_session


def _segment(session: Session, learning_session: LearningSession, *, sequence: int) -> LearningSegment:
    segment = LearningSegment(session_id=learning_session.id, sequence=sequence)
    session.add(segment)
    session.flush()
    return segment


def _student_message(session: Session, learning_session: LearningSession, segment: LearningSegment) -> LearningMessage:
    message = LearningMessage(
        session_id=learning_session.id,
        segment_id=segment.id,
        role="student",
        content="I want help with fractions.",
    )
    session.add(message)
    session.flush()
    return message


def _review_jobs(session: Session, segment_id: UUID) -> list[Job]:
    return list(
        session.query(Job)
        .filter_by(job_type="SEGMENT_LEARNING_REVIEW")
        .filter(Job.payload["segment_id"].astext == str(segment_id))
        .all()
    )


def _policy() -> SessionLifecyclePolicy:
    return SessionLifecyclePolicy(
        version="fixture-v1",
        inactivity=timedelta(minutes=10),
        grace=timedelta(minutes=5),
    )


def test_student_raw_interaction_alone_makes_closed_segment_reviewable(factory: sessionmaker[Session]) -> None:
    """Catches semantic metadata being required before a structural Review request."""

    from services.tutor.segment_lifecycle import (
        SEGMENT_REVIEW_REQUEST_VERSION,
        complete_segment,
    )

    closed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    with factory.begin() as session:
        student, learning_session = _lineage(session)
        segment = _segment(session, learning_session, sequence=1)
        _student_message(session, learning_session, segment)

        job = complete_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            closure_reason="SESSION_CLOSED",
            closed_at=closed_at,
        )

        assert job is not None
        assert segment.closed_at == closed_at
        assert segment.closure_reason == "SESSION_CLOSED"
        assert job.idempotency_key == f"segment-learning-review:{segment.id}:{SEGMENT_REVIEW_REQUEST_VERSION}"
        assert job.payload == {
            "segment_id": str(segment.id),
            "session_id": str(learning_session.id),
            "student_id": str(student.id),
            "review_request_version": SEGMENT_REVIEW_REQUEST_VERSION,
            "closed_at": closed_at.isoformat(),
            "closure_reason": "SESSION_CLOSED",
        }
        assert session.query(CandidateEvent).count() == 0
        assert session.query(SegmentLearningReview).count() == 0


def test_closed_segment_without_student_raw_interaction_is_not_reviewable(
    factory: sessionmaker[Session],
) -> None:
    """Catches an empty structural record generating an unnecessary Review job."""

    from services.tutor.segment_lifecycle import complete_segment

    with factory.begin() as session:
        _, learning_session = _lineage(session)
        segment = _segment(session, learning_session, sequence=1)

        assert complete_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            closure_reason="SESSION_CLOSED",
            closed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        ) is None
        assert _review_jobs(session, segment.id) == []


def test_same_reason_completion_preserves_timestamp_and_reuses_one_review_job(
    factory: sessionmaker[Session],
) -> None:
    """Catches retrying lifecycle completion from rewriting history or duplicating work."""

    from services.tutor.segment_lifecycle import complete_segment

    first_closed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    with factory.begin() as session:
        _, learning_session = _lineage(session)
        segment = _segment(session, learning_session, sequence=1)
        _student_message(session, learning_session, segment)

        first = complete_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            closure_reason="SESSION_CLOSED",
            closed_at=first_closed_at,
        )
        second = complete_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            closure_reason="SESSION_CLOSED",
            closed_at=first_closed_at + timedelta(minutes=1),
        )

        assert first is not None and second is not None
        assert second.id == first.id
        assert segment.closed_at == first_closed_at
        assert len(_review_jobs(session, segment.id)) == 1


def test_conflicting_segment_closure_reason_is_rejected_without_mutation(
    factory: sessionmaker[Session],
) -> None:
    """Catches a later lifecycle path silently rewriting durable closure history."""

    from services.tutor.segment_lifecycle import SegmentLifecycleError, complete_segment

    first_closed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    with factory.begin() as session:
        _, learning_session = _lineage(session)
        segment = _segment(session, learning_session, sequence=1)
        _student_message(session, learning_session, segment)
        complete_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            closure_reason="NEXT_SEGMENT_CREATED",
            closed_at=first_closed_at,
        )

        with pytest.raises(SegmentLifecycleError, match="closure reason"):
            complete_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                closure_reason="SESSION_CLOSED",
                closed_at=first_closed_at + timedelta(minutes=1),
            )

        assert segment.closed_at == first_closed_at
        assert segment.closure_reason == "NEXT_SEGMENT_CREATED"


def test_rollback_removes_closure_review_job_and_next_segment(factory: sessionmaker[Session]) -> None:
    """Catches a failed transition leaving partial closure or Review state durable."""

    from services.tutor.segment_lifecycle import complete_segment

    with factory.begin() as session:
        _, learning_session = _lineage(session)
        segment = _segment(session, learning_session, sequence=1)
        _student_message(session, learning_session, segment)
        session_id = learning_session.id
        segment_id = segment.id

    with pytest.raises(RuntimeError, match="force rollback"):
        with factory.begin() as session:
            learning_session = session.get(LearningSession, session_id)
            segment = session.get(LearningSegment, segment_id)
            assert learning_session is not None and segment is not None
            complete_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                closure_reason="NEXT_SEGMENT_CREATED",
                closed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
            )
            session.add(LearningSegment(session_id=learning_session.id, sequence=2))
            session.flush()
            raise RuntimeError("force rollback")

    with factory() as session:
        segment = session.get(LearningSegment, segment_id)
        assert segment is not None
        assert segment.closed_at is None
        assert segment.closure_reason is None
        assert _review_jobs(session, segment_id) == []
        assert session.query(LearningSegment).filter_by(session_id=session_id).count() == 1


def test_session_close_reconciles_open_segments_and_keeps_legacy_consolidation(
    factory: sessionmaker[Session],
) -> None:
    """Catches Session close omitting pre-B Segments or replacing legacy authority."""

    now = datetime(2026, 8, 29, 12, tzinfo=UTC)
    with factory.begin() as session:
        _, learning_session = _lineage(session, last_activity_at=now - timedelta(minutes=16))
        learning_session.intelligence_pipeline = "legacy-session-evidence-v1"
        first = _segment(session, learning_session, sequence=1)
        second = _segment(session, learning_session, sequence=2)
        third = _segment(session, learning_session, sequence=3)
        _student_message(session, learning_session, first)
        _student_message(session, learning_session, third)

        assert close_inactive_sessions(session, now=now, policy=_policy()) == [learning_session]

        assert (first.closed_at, first.closure_reason) == (now, "NEXT_SEGMENT_CREATED")
        assert (second.closed_at, second.closure_reason) == (now, "NEXT_SEGMENT_CREATED")
        assert (third.closed_at, third.closure_reason) == (now, "SESSION_CLOSED")
        assert len(_review_jobs(session, first.id)) == 1
        assert _review_jobs(session, second.id) == []
        assert len(_review_jobs(session, third.id)) == 1
        assert session.query(Job).filter_by(job_type="SESSION_CONSOLIDATION").count() == 1


def test_session_close_preserves_valid_closed_segment_and_ensures_its_review_job(
    factory: sessionmaker[Session],
) -> None:
    """Catches session reconciliation mutating valid history or skipping its pending Review."""

    now = datetime(2026, 8, 29, 12, tzinfo=UTC)
    original_closed_at = now - timedelta(minutes=3)
    with factory.begin() as session:
        _, learning_session = _lineage(session, last_activity_at=now - timedelta(minutes=16))
        prior = _segment(session, learning_session, sequence=1)
        latest = _segment(session, learning_session, sequence=2)
        _student_message(session, learning_session, prior)
        _student_message(session, learning_session, latest)
        prior.closed_at = original_closed_at
        prior.closure_reason = "NEXT_SEGMENT_CREATED"
        session.flush()

        assert close_inactive_sessions(session, now=now, policy=_policy()) == [learning_session]

        assert (prior.closed_at, prior.closure_reason) == (original_closed_at, "NEXT_SEGMENT_CREATED")
        assert (latest.closed_at, latest.closure_reason) == (now, "SESSION_CLOSED")
        assert len(_review_jobs(session, prior.id)) == 1
        assert len(_review_jobs(session, latest.id)) == 1


def test_unregistered_review_job_remains_pending(factory: sessionmaker[Session]) -> None:
    """Catches B registering a no-op worker handler before semantic Review exists."""

    from services.tutor.segment_lifecycle import SEGMENT_LEARNING_REVIEW_JOB, complete_segment

    with factory.begin() as session:
        _, learning_session = _lineage(session)
        segment = _segment(session, learning_session, sequence=1)
        _student_message(session, learning_session, segment)
        job = complete_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            closure_reason="SESSION_CLOSED",
            closed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        )
        assert job is not None and job.job_type == SEGMENT_LEARNING_REVIEW_JOB
        job_id = job.id

    assert run_once(factory, JobHandlerRegistry(), worker_id="fixture-worker") is None

    with factory() as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "PENDING"
        assert job.attempt_count == 0
