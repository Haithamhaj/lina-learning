"""PostgreSQL contracts for CTX-03A Segment/message lineage."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    LearningMessage,
    LearningSegment,
    LearningSession,
    Student,
    User,
)
from services.tutor.segments import (
    SegmentAssignmentError,
    assign_message_to_segment,
    create_next_segment,
    latest_segment_for_session,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Segment lineage tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE learning_messages, learning_segments, learning_sessions, students, users CASCADE")
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _learning_session(session: Session) -> LearningSession:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="fixture")
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    session.add(learning_session)
    session.flush()
    return learning_session


def _message(session: Session, learning_session: LearningSession, content: str = "same text") -> LearningMessage:
    message = LearningMessage(session_id=learning_session.id, role="student", content=content, payload={})
    session.add(message)
    session.flush()
    return message


def test_segment_is_persisted_for_exactly_one_session(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        segment = create_next_segment(session, learning_session=learning_session)

        assert segment.session_id == learning_session.id
        assert segment.sequence == 1
        assert segment.created_at is not None


def test_next_segment_sequence_is_monotonic_within_a_session(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)

        first = create_next_segment(session, learning_session=learning_session)
        second = create_next_segment(session, learning_session=learning_session)

        assert (first.sequence, second.sequence) == (1, 2)


def test_latest_segment_is_scoped_to_its_session(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        first_session = _learning_session(session)
        second_session = _learning_session(session)
        first = create_next_segment(session, learning_session=first_session)
        create_next_segment(session, learning_session=first_session)
        second = create_next_segment(session, learning_session=second_session)

        assert latest_segment_for_session(session, session_id=first_session.id).sequence == 2
        assert latest_segment_for_session(session, session_id=second_session.id).id == second.id
        assert latest_segment_for_session(session, session_id=uuid4()) is None
        assert first.session_id != second.session_id


def test_database_rejects_duplicate_sequence_in_one_session(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        create_next_segment(session, learning_session=learning_session)

        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(LearningSegment(session_id=learning_session.id, sequence=1))
                session.flush()


def test_assigns_unsegmented_message_to_same_session_segment(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        segment = create_next_segment(session, learning_session=learning_session)
        message = _message(session, learning_session)

        assigned = assign_message_to_segment(session, message=message, segment=segment)

        assert assigned.id == message.id
        assert message.segment_id == segment.id


def test_legacy_unsegmented_message_remains_valid(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        message = _message(session, learning_session)

        assert message.segment_id is None


def test_repeated_message_text_has_distinct_lineage_ids(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        segment = create_next_segment(session, learning_session=learning_session)
        first = _message(session, learning_session, "repeat")
        second = _message(session, learning_session, "repeat")

        assign_message_to_segment(session, message=first, segment=segment)
        assign_message_to_segment(session, message=second, segment=segment)

        assert first.id != second.id
        assert first.segment_id == second.segment_id == segment.id


def test_assignment_rejects_segment_from_another_session(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        first_session = _learning_session(session)
        second_session = _learning_session(session)
        message = _message(session, first_session)
        foreign_segment = create_next_segment(session, learning_session=second_session)

        with pytest.raises(SegmentAssignmentError, match="same LearningSession"):
            assign_message_to_segment(session, message=message, segment=foreign_segment)

        assert message.segment_id is None


def test_assignment_to_same_segment_is_idempotent(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        segment = create_next_segment(session, learning_session=learning_session)
        message = _message(session, learning_session)

        assign_message_to_segment(session, message=message, segment=segment)
        again = assign_message_to_segment(session, message=message, segment=segment)

        assert again.id == message.id
        assert message.segment_id == segment.id


def test_assignment_never_overwrites_another_segment(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        first = create_next_segment(session, learning_session=learning_session)
        second = create_next_segment(session, learning_session=learning_session)
        message = _message(session, learning_session)
        assign_message_to_segment(session, message=message, segment=first)

        with pytest.raises(SegmentAssignmentError, match="already belongs"):
            assign_message_to_segment(session, message=message, segment=second)

        assert message.segment_id == first.id


def test_deleting_segment_preserves_raw_message_and_clears_lineage(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        segment = create_next_segment(session, learning_session=learning_session)
        message = _message(session, learning_session)
        assign_message_to_segment(session, message=message, segment=segment)
        message_id: UUID = message.id

        session.delete(segment)
        session.flush()
        session.expire(message)
        persisted = session.get(LearningMessage, message_id)

        assert persisted is not None
        assert persisted.segment_id is None


def test_segment_creation_uses_owning_session_row_as_serialization_point(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        create_next_segment(session, learning_session=learning_session)

        next_segment = create_next_segment(session, learning_session=learning_session)

        assert next_segment.sequence == 2
