"""PostgreSQL persistence contracts for SEG-EVID-01A only."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import os
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import services.platform.db.models as db_models
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    LearningSegment,
    LearningSession,
    LearnerPattern,
    Student,
    User,
)


PRIOR_REVISION = "1e94c7b8a2d6"


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for SEG-EVID-01A persistence tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE learning_evidence, learning_events, candidate_events, learning_messages, "
                "learning_segments, learning_sessions, intelligence_processing_runs, "
                "current_learning_states, learner_patterns, decision_views, "
                "intelligence_session_authorities, ai_executions, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _review_class():
    """Keep the RED tests importable before the new persistence model exists."""

    return getattr(db_models, "SegmentLearningReview")


def _lineage(session: Session) -> tuple[Student, LearningSession, LearningSegment]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Fixture Student")
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH")
    session.add(learning_session)
    session.flush()
    segment = LearningSegment(session_id=learning_session.id, sequence=1)
    session.add(segment)
    session.flush()
    return student, learning_session, segment


def _legacy_lineage(session: Session) -> tuple[Student, LearningSession]:
    """Create only columns available before the SEG-EVID-01A migration."""

    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Fixture Student")
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH")
    session.add(learning_session)
    session.flush()
    return student, learning_session


def _review(
    student: Student,
    learning_session: LearningSession,
    segment: LearningSegment,
    **overrides: object,
):
    values: dict[str, object] = {
        "student_id": student.id,
        "session_id": learning_session.id,
        "segment_id": segment.id,
        "schema_version": "segment-review-v1",
        "prompt_version": "segment-review-prompt-v1",
        "rubric_version": "learning-rubric-v1",
        "review_policy_version": "segment-review-policy-v1",
        "provider": "fixture",
        "model": "fixture-model",
        "status": "PENDING",
    }
    values.update(overrides)
    return _review_class()(**values)


def _processing_run(session: Session, student: Student) -> IntelligenceProcessingRun:
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="learning-rubric-v1",
        policy_version="session-policy-v1",
    )
    session.add(run)
    session.flush()
    return run


def _message(session: Session, learning_session: LearningSession, segment: LearningSegment) -> LearningMessage:
    message = LearningMessage(
        session_id=learning_session.id,
        segment_id=segment.id,
        role="student",
        content="One half is the same as two fourths.",
    )
    session.add(message)
    session.flush()
    return message


def _candidate(session: Session, learning_session: LearningSession, message: LearningMessage) -> CandidateEvent:
    candidate = CandidateEvent(
        session_id=learning_session.id,
        message_id=message.id,
        event_type="attempt",
        signal="fixture-signal",
    )
    session.add(candidate)
    session.flush()
    return candidate


def test_segment_closure_persists_only_open_or_approved_closed_states(
    factory: sessionmaker[Session],
) -> None:
    """Catches a closure schema that accepts incomplete or invented lifecycle facts."""

    with factory.begin() as session:
        student, learning_session, open_segment = _lineage(session)
        next_segment = LearningSegment(
            session_id=learning_session.id,
            sequence=2,
            closed_at=datetime.now(UTC),
            closure_reason="NEXT_SEGMENT_CREATED",
        )
        session_closed_segment = LearningSegment(
            session_id=learning_session.id,
            sequence=3,
            closed_at=datetime.now(UTC),
            closure_reason="SESSION_CLOSED",
        )
        session.add_all([next_segment, session_closed_segment])
        session.flush()

        assert open_segment.closed_at is None
        assert open_segment.closure_reason is None
        assert next_segment.closure_reason == "NEXT_SEGMENT_CREATED"
        assert session_closed_segment.closure_reason == "SESSION_CLOSED"

        session_id = learning_session.id

    invalid_states = (
        (4, "NULL, 'NEXT_SEGMENT_CREATED'"),
        (5, "now(), NULL"),
        (6, "now(), 'NEW_SEGMENT'"),
    )
    engine = factory.kw["bind"]
    assert engine is not None
    for sequence, closure_values in invalid_states:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "INSERT INTO learning_segments "
                    "(id, session_id, sequence, closed_at, closure_reason) "
                    f"VALUES (gen_random_uuid(), '{session_id}', {sequence}, {closure_values})"
                )


def test_segment_learning_review_persists_pending_and_terminal_contracts(
    factory: sessionmaker[Session],
) -> None:
    """Catches a review record missing its versioned semantic/audit identity."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        pending = _review(student, learning_session, segment)
        session.add(pending)
        session.flush()

        execution = AIExecution(
            task="fixture",
            provider="fixture",
            model="fixture-model",
            latency_ms=1,
            success=True,
        )
        session.add(execution)
        session.flush()
        pending.status = "COMPLETED"
        pending.output = {"staged_findings": []}
        pending.ai_execution_id = execution.id
        pending.completed_at = datetime.now(UTC)
        session.flush()

        assert pending.output == {"staged_findings": []}
        assert pending.ai_execution_id == execution.id
        assert pending.completed_at is not None


def test_segment_learning_review_rejects_unknown_status(factory: sessionmaker[Session]) -> None:
    """Catches a new review lifecycle state being persisted without approval."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(_review(student, learning_session, segment, status="ACTIVE"))
                session.flush()


def test_segment_learning_review_identity_is_unique_but_versioned(factory: sessionmaker[Session]) -> None:
    """Catches duplicate exact reviews or blocks a changed semantic contract."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        session.add(_review(student, learning_session, segment))
        session.flush()
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(_review(student, learning_session, segment))
                session.flush()

        different_prompt = _review(
            student,
            learning_session,
            segment,
            prompt_version="segment-review-prompt-v2",
        )
        session.add(different_prompt)
        session.flush()

        assert different_prompt.id is not None


def test_review_persistence_helper_rejects_inconsistent_ownership(
    factory: sessionmaker[Session],
) -> None:
    """Catches a Review row being assembled with unrelated student/session/Segment lineage."""

    from services.intelligence.segment_reviews import (
        SegmentLearningReviewLineageError,
        create_segment_learning_review,
    )

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        other_student, other_session, _ = _lineage(session)
        review = create_segment_learning_review(
            session,
            student_id=student.id,
            session_id=learning_session.id,
            segment_id=segment.id,
            schema_version="segment-review-v1",
            prompt_version="segment-review-prompt-v1",
            rubric_version="learning-rubric-v1",
            review_policy_version="segment-review-policy-v1",
            provider="fixture",
            model="fixture-model",
        )
        session.flush()

        assert review.student_id == student.id
        with pytest.raises(SegmentLearningReviewLineageError, match="Segment"):
            create_segment_learning_review(
                session,
                student_id=other_student.id,
                session_id=other_session.id,
                segment_id=segment.id,
                schema_version="segment-review-v1",
                prompt_version="segment-review-prompt-v1",
                rubric_version="learning-rubric-v1",
                review_policy_version="segment-review-policy-v1",
                provider="fixture",
                model="fixture-model",
            )


def test_legacy_learning_event_preserves_singular_anchors_and_empty_plural_defaults(
    factory: sessionmaker[Session],
) -> None:
    """Catches the new lineage contract breaking legacy Session Evidence writes."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        processing_run = _processing_run(session, student)
        message = _message(session, learning_session, segment)
        candidate = _candidate(session, learning_session, message)
        event = LearningEvent(
            processing_run_id=processing_run.id,
            session_id=learning_session.id,
            candidate_event_id=candidate.id,
            subject="MATH",
            event_type="independent_success",
            description="Legacy Session Evidence event.",
            source_message_id=message.id,
        )
        session.add(event)
        session.flush()

        assert event.candidate_event_id == candidate.id
        assert event.source_message_id == message.id
        assert event.candidate_event_ids == []
        assert event.source_message_ids == []


def test_deleting_candidate_keeps_authorized_learning_event(factory: sessionmaker[Session]) -> None:
    """Catches optional Candidate provenance still cascading into an Event deletion."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        processing_run = _processing_run(session, student)
        message = _message(session, learning_session, segment)
        candidate = _candidate(session, learning_session, message)
        event = LearningEvent(
            processing_run_id=processing_run.id,
            session_id=learning_session.id,
            candidate_event_id=candidate.id,
            candidate_event_ids=[str(candidate.id)],
            source_message_ids=[str(message.id)],
            subject="MATH",
            event_type="independent_success",
            description="An authorized Event retains its own durable identity.",
            source_message_id=message.id,
        )
        session.add(event)
        session.flush()
        event_id = event.id
        session.delete(candidate)
        session.flush()

        retained = session.get(LearningEvent, event_id)
        assert retained is not None
        session.expire(retained, ["candidate_event_id"])
        assert retained.candidate_event_id is None
        assert retained.candidate_event_ids == [str(candidate.id)]


def test_segment_derived_event_allows_no_candidate_anchor(factory: sessionmaker[Session]) -> None:
    """Catches Segment findings remaining incorrectly Candidate-gated."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        processing_run = _processing_run(session, student)
        review = _review(student, learning_session, segment)
        session.add(review)
        session.flush()
        event = LearningEvent(
            processing_run_id=processing_run.id,
            session_id=learning_session.id,
            candidate_event_id=None,
            candidate_event_ids=[],
            source_message_ids=[],
            segment_id=segment.id,
            segment_review_id=review.id,
            subject="MATH",
            event_type="supported_learning_occurrence",
            description="A Segment Review may identify a source-supported occurrence without a Candidate hint.",
        )
        session.add(event)
        session.flush()

        assert event.candidate_event_id is None
        assert event.candidate_event_ids == []
        assert event.segment_id == segment.id
        assert event.segment_review_id == review.id


def test_learning_event_preserves_complete_multi_message_provenance(
    factory: sessionmaker[Session],
) -> None:
    """Catches an Event collapsing multi-message support to one primary anchor."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        processing_run = _processing_run(session, student)
        review = _review(student, learning_session, segment)
        session.add(review)
        session.flush()
        messages = [_message(session, learning_session, segment) for _ in range(3)]
        event = LearningEvent(
            processing_run_id=processing_run.id,
            session_id=learning_session.id,
            candidate_event_id=None,
            candidate_event_ids=[],
            source_message_ids=[str(message.id) for message in messages],
            segment_id=segment.id,
            segment_review_id=review.id,
            subject="MATH",
            event_type="supported_learning_occurrence",
            description="A staged finding preserves complete source lineage.",
        )
        session.add(event)
        session.flush()

        assert event.source_message_ids == [str(message.id) for message in messages]


def test_learning_event_preserves_multiple_candidate_hints(factory: sessionmaker[Session]) -> None:
    """Catches plural Candidate provenance being reduced to one hint."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        processing_run = _processing_run(session, student)
        review = _review(student, learning_session, segment)
        session.add(review)
        session.flush()
        message = _message(session, learning_session, segment)
        first = _candidate(session, learning_session, message)
        second = _candidate(session, learning_session, message)
        event = LearningEvent(
            processing_run_id=processing_run.id,
            session_id=learning_session.id,
            candidate_event_id=first.id,
            candidate_event_ids=[str(first.id), str(second.id)],
            source_message_ids=[str(message.id)],
            segment_id=segment.id,
            segment_review_id=review.id,
            subject="MATH",
            event_type="supported_learning_occurrence",
            description="A staged finding may retain multiple provisional Candidate hints.",
        )
        session.add(event)
        session.flush()

        assert event.candidate_event_ids == [str(first.id), str(second.id)]


def test_persisting_review_has_no_intelligence_activation_side_effects(
    factory: sessionmaker[Session],
) -> None:
    """Catches persistence-only A silently activating downstream intelligence."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        before = (
            session.query(LearningEvent).count(),
            session.query(LearningEvidence).count(),
            session.query(CurrentLearningState).count(),
            session.query(LearnerPattern).count(),
            session.query(DecisionView).count(),
            session.query(IntelligenceSessionAuthority).count(),
        )
        session.add(_review(student, learning_session, segment))
        session.flush()
        after = (
            session.query(LearningEvent).count(),
            session.query(LearningEvidence).count(),
            session.query(CurrentLearningState).count(),
            session.query(LearnerPattern).count(),
            session.query(DecisionView).count(),
            session.query(IntelligenceSessionAuthority).count(),
        )

        assert before == (0, 0, 0, 0, 0, 0)
        assert after == before


def test_segment_review_migration_backfills_legacy_lineage_and_safe_downgrade(
    factory: sessionmaker[Session],
) -> None:
    """Catches unsafe backfill or a downgrade that corrupts Candidate-free Events."""

    logger = logging.getLogger("services.platform.observability.metrics")
    logger_was_disabled = logger.disabled
    config = Config("alembic.ini")
    engine = factory.kw["bind"]
    assert engine is not None
    legacy_event_id = uuid4()
    candidate_free_event_id: UUID | None = None
    try:
        command.downgrade(config, PRIOR_REVISION)
        with factory.begin() as session:
            student, learning_session = _legacy_lineage(session)
            processing_run = _processing_run(session, student)
            message = LearningMessage(
                session_id=learning_session.id,
                role="student",
                content="One half is the same as two fourths.",
            )
            session.add(message)
            session.flush()
            candidate = _candidate(session, learning_session, message)
            session.execute(
                text(
                    "INSERT INTO learning_events "
                    "(id, processing_run_id, session_id, candidate_event_id, subject, event_type, description, source_message_id) "
                    "VALUES (:id, :run_id, :session_id, :candidate_id, 'MATH', 'legacy_event', 'Legacy Event', :message_id)"
                ),
                {
                    "id": legacy_event_id,
                    "run_id": processing_run.id,
                    "session_id": learning_session.id,
                    "candidate_id": candidate.id,
                    "message_id": message.id,
                },
            )

        command.upgrade(config, "head")
        with factory.begin() as session:
            legacy = session.get(LearningEvent, legacy_event_id)
            assert legacy is not None
            assert legacy.candidate_event_ids == [str(legacy.candidate_event_id)]
            assert legacy.source_message_ids == [str(legacy.source_message_id)]
            assert legacy.segment_id is None
            assert legacy.segment_review_id is None

            student, learning_session, segment = _lineage(session)
            processing_run = _processing_run(session, student)
            review = _review(student, learning_session, segment)
            session.add(review)
            session.flush()
            candidate_free = LearningEvent(
                processing_run_id=processing_run.id,
                session_id=learning_session.id,
                candidate_event_id=None,
                candidate_event_ids=[],
                source_message_ids=[],
                segment_id=segment.id,
                segment_review_id=review.id,
                subject="MATH",
                event_type="candidate_free_event",
                description="Post-A Candidate-free Event.",
            )
            session.add(candidate_free)
            session.flush()
            candidate_free_event_id = candidate_free.id

        with pytest.raises(RuntimeError, match="candidate_event_id"):
            command.downgrade(config, PRIOR_REVISION)

        command.upgrade(config, "head")
        with factory.begin() as session:
            session.execute(
                text("DELETE FROM learning_events WHERE id = :event_id"),
                {"event_id": candidate_free_event_id},
            )

        command.downgrade(config, PRIOR_REVISION)
        assert "segment_learning_reviews" not in inspect(engine).get_table_names()
        with engine.connect() as connection:
            candidate_column = next(
                column
                for column in inspect(engine).get_columns("learning_events")
                if column["name"] == "candidate_event_id"
            )
            assert candidate_column["nullable"] is False
            assert connection.execute(
                text("SELECT count(*) FROM learning_events WHERE candidate_event_id IS NULL")
            ).scalar_one() == 0

        command.upgrade(config, "head")
        assert "segment_learning_reviews" in inspect(engine).get_table_names()
    finally:
        try:
            command.upgrade(config, "head")
        finally:
            logger.disabled = logger_was_disabled
