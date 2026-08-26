"""PostgreSQL contracts for CTX-03C temporary complete-exchange embeddings."""

from __future__ import annotations

import os
import logging
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningExchangeEmbedding, LearningMessage, LearningSegment, LearningSession, Student, User
from services.tutor.exchanges import clear_session_exchange_embeddings, persist_exchange_embedding


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for CTX-03C exchange tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE learning_exchange_embeddings, learning_messages, learning_segments, "
                "learning_sessions, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def test_exchange_embedding_is_temporary_session_scoped_complete_exchange_storage(
    factory: sessionmaker[Session],
) -> None:
    """Catches removal of the durable temporary-vector lineage contract."""

    with factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        segment = LearningSegment(session_id=learning_session.id, sequence=1)
        session.add(segment)
        session.flush()
        student_message = LearningMessage(
            session_id=learning_session.id,
            segment_id=segment.id,
            role="student",
            content="How do fractions work?",
        )
        tutor_message = LearningMessage(
            session_id=learning_session.id,
            segment_id=segment.id,
            role="tutor",
            content="Fractions show equal parts.",
        )
        session.add_all([student_message, tutor_message])
        session.flush()
        embedding = LearningExchangeEmbedding(
            session_id=learning_session.id,
            segment_id=segment.id,
            student_message_id=student_message.id,
            tutor_message_id=tutor_message.id,
            embedding=[0.0] * 1536,
            embedding_model="text-embedding-3-small",
            dimensions=1536,
        )
        session.add(embedding)
        session.flush()

        assert embedding.session_id == learning_session.id
        assert embedding.segment_id == segment.id
        assert len(embedding.embedding) == 1536


def test_exchange_embedding_rejects_cross_segment_pair(factory: sessionmaker[Session]) -> None:
    """Catches a vector row that would silently breach Segment-only recall."""

    with factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        first = LearningSegment(session_id=learning_session.id, sequence=1)
        second = LearningSegment(session_id=learning_session.id, sequence=2)
        session.add_all([first, second])
        session.flush()
        student_message = LearningMessage(session_id=learning_session.id, segment_id=first.id, role="student", content="First")
        tutor_message = LearningMessage(session_id=learning_session.id, segment_id=second.id, role="tutor", content="Second")
        session.add_all([student_message, tutor_message])
        session.flush()

        with pytest.raises(ValueError, match="same LearningSession and LearningSegment"):
            persist_exchange_embedding(
                session,
                student_message=student_message,
                tutor_message=tutor_message,
                embedding=[0.0] * 1536,
                embedding_model="text-embedding-3-small",
            )


def test_session_cleanup_removes_only_temporary_exchange_vectors(factory: sessionmaker[Session]) -> None:
    """Catches session close cleanup that deletes raw conversation instead of its temporary index."""

    with factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        segment = LearningSegment(session_id=learning_session.id, sequence=1)
        session.add(segment)
        session.flush()
        student_message = LearningMessage(session_id=learning_session.id, segment_id=segment.id, role="student", content="Question")
        tutor_message = LearningMessage(session_id=learning_session.id, segment_id=segment.id, role="tutor", content="Reply")
        session.add_all([student_message, tutor_message])
        session.flush()
        persist_exchange_embedding(session, student_message=student_message, tutor_message=tutor_message, embedding=[0.0] * 1536, embedding_model="text-embedding-3-small")

        clear_session_exchange_embeddings(session, learning_session=learning_session)

        assert session.query(LearningExchangeEmbedding).count() == 0
        assert session.get(LearningMessage, student_message.id) is not None
        assert session.get(LearningMessage, tutor_message.id) is not None
        assert session.get(LearningSegment, segment.id) is not None


def test_exchange_embedding_migration_upgrades_empty_and_downgrades_cleanly(
    factory: sessionmaker[Session],
) -> None:
    """Catches a migration that backfills history or leaves a table on downgrade."""

    observability_logger = logging.getLogger("services.platform.observability.metrics")
    logger_was_disabled = observability_logger.disabled
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "a4d8e2f6b1c3")
        engine = factory.kw["bind"]
        assert engine is not None
        assert "learning_exchange_embeddings" not in inspect(engine).get_table_names()
        command.upgrade(config, "head")
        assert "learning_exchange_embeddings" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM learning_exchange_embeddings")).scalar_one() == 0
    finally:
        try:
            command.upgrade(config, "head")
        finally:
            observability_logger.disabled = logger_was_disabled
