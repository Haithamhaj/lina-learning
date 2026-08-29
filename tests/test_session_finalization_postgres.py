"""PostgreSQL persistence contracts required before Session Finalization."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearningSession,
    Student,
    User,
)


PRIOR_REVISION = "e7b1f3c9a2d4"


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Session Finalization persistence tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE learning_evidence, learning_events, candidate_events, learning_messages, "
                "learning_segments, segment_learning_reviews, intelligence_session_authorities, "
                "intelligence_reprocess_sessions, intelligence_reprocess_runs, "
                "intelligence_processing_runs, learning_sessions, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _student(session: Session) -> Student:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Fixture Student")
    session.add(student)
    session.flush()
    return student


def _processing_run(session: Session, student: Student) -> IntelligenceProcessingRun:
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="learning-rubric-v1",
        policy_version="session-policy-v1",
    )
    session.add(run)
    session.flush()
    return run


def test_new_session_defaults_to_segment_finalization_pipeline(factory: sessionmaker[Session]) -> None:
    """Catches a new normal Session silently falling back to legacy consolidation."""

    with factory.begin() as session:
        student = _student(session)
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()

        assert learning_session.intelligence_pipeline == "segment-finalization-v1"


def test_live_authority_allows_null_reprocess_lineage_but_remains_unique(
    factory: sessionmaker[Session],
) -> None:
    """Catches live authority being reprocess-gated or duplicate for one Student/Session."""

    with factory.begin() as session:
        student = _student(session)
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        first_run = _processing_run(session, student)
        second_run = _processing_run(session, student)
        authority = IntelligenceSessionAuthority(
            student_id=student.id,
            session_id=learning_session.id,
            reprocess_run_id=None,
            evidence_processing_run_id=first_run.id,
        )
        session.add(authority)
        session.flush()

        assert authority.reprocess_run_id is None
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(
                    IntelligenceSessionAuthority(
                        student_id=student.id,
                        session_id=learning_session.id,
                        reprocess_run_id=None,
                        evidence_processing_run_id=second_run.id,
                    )
                )
                session.flush()


def test_migration_refuses_to_relabel_a_finalization_session_as_legacy(
    factory: sessionmaker[Session],
) -> None:
    """Catches downgrade/upgrade silently changing a new Session's pipeline identity."""

    config = Config("alembic.ini")
    try:
        with factory.begin() as session:
            student = _student(session)
            session.add(LearningSession(student_id=student.id, subject="MATH"))

        with pytest.raises(RuntimeError, match="segment-finalization-v1"):
            command.downgrade(config, PRIOR_REVISION)
    finally:
        command.upgrade(config, "head")


def test_migration_refuses_downgrade_with_live_authority(
    factory: sessionmaker[Session],
) -> None:
    """Catches downgrade trying to force live nullable authority into the legacy schema."""

    config = Config("alembic.ini")
    try:
        with factory.begin() as session:
            student = _student(session)
            learning_session = LearningSession(
                student_id=student.id,
                subject="MATH",
                intelligence_pipeline="legacy-session-evidence-v1",
            )
            session.add(learning_session)
            session.flush()
            processing_run = _processing_run(session, student)
            session.add(
                IntelligenceSessionAuthority(
                    student_id=student.id,
                    session_id=learning_session.id,
                    reprocess_run_id=None,
                    evidence_processing_run_id=processing_run.id,
                )
            )

        with pytest.raises(IntegrityError, match="reprocess_run_id"):
            command.downgrade(config, PRIOR_REVISION)
    finally:
        command.upgrade(config, "head")


def test_finalization_contract_migration_backfills_legacy_and_round_trips_safely(
    factory: sessionmaker[Session],
) -> None:
    """Catches historical Sessions being relabeled or migration fields drifting from models."""

    logger = logging.getLogger("services.platform.observability.metrics")
    logger_was_disabled = logger.disabled
    config = Config("alembic.ini")
    engine = factory.kw["bind"]
    assert engine is not None
    user_id = uuid4()
    student_id = uuid4()
    legacy_session_id = uuid4()
    legacy_message_id = uuid4()
    new_session_id = uuid4()
    try:
        command.downgrade(config, PRIOR_REVISION)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, identity_provider, external_subject) "
                    "VALUES (:id, 'fixture', :external_subject)"
                ),
                {"id": user_id, "external_subject": uuid4().hex},
            )
            connection.execute(
                text(
                    "INSERT INTO students (id, user_id, display_name) "
                    "VALUES (:id, :user_id, 'Legacy Student')"
                ),
                {"id": student_id, "user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO learning_sessions (id, student_id, subject) "
                    "VALUES (:id, :student_id, 'MATH')"
                ),
                {"id": legacy_session_id, "student_id": student_id},
            )
            connection.execute(
                text(
                    "INSERT INTO learning_messages (id, session_id, role, content, segment_id) "
                    "VALUES (:id, :session_id, 'student', 'Legacy raw message', NULL)"
                ),
                {"id": legacy_message_id, "session_id": legacy_session_id},
            )

        command.upgrade(config, "head")
        columns = {
            table: {column["name"]: column for column in inspect(engine).get_columns(table)}
            for table in (
                "learning_sessions",
                "intelligence_session_authorities",
                "learning_events",
            )
        }
        assert columns["learning_sessions"]["intelligence_pipeline"]["nullable"] is False
        assert columns["intelligence_session_authorities"]["reprocess_run_id"]["nullable"] is True
        assert columns["learning_events"]["segment_review_finding_index"]["nullable"] is True

        with engine.begin() as connection:
            assert connection.execute(
                text(
                    "SELECT intelligence_pipeline FROM learning_sessions "
                    "WHERE id = :session_id"
                ),
                {"session_id": legacy_session_id},
            ).scalar_one() == "legacy-session-evidence-v1"
            assert connection.execute(
                text(
                    "SELECT count(*), count(segment_id) FROM learning_messages "
                    "WHERE id = :message_id"
                ),
                {"message_id": legacy_message_id},
            ).one() == (1, 0)
            new_pipeline = connection.execute(
                text(
                    "INSERT INTO learning_sessions (id, student_id, subject) "
                    "VALUES (:id, :student_id, 'MATH') RETURNING intelligence_pipeline"
                ),
                {"id": new_session_id, "student_id": student_id},
            ).scalar_one()
            assert new_pipeline == "segment-finalization-v1"
            connection.execute(
                text("DELETE FROM learning_sessions WHERE id = :session_id"),
                {"session_id": new_session_id},
            )

        command.downgrade(config, PRIOR_REVISION)
        prior_columns = {
            table: {column["name"] for column in inspect(engine).get_columns(table)}
            for table in (
                "learning_sessions",
                "intelligence_session_authorities",
                "learning_events",
            )
        }
        assert "intelligence_pipeline" not in prior_columns["learning_sessions"]
        assert "segment_review_finding_index" not in prior_columns["learning_events"]

        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT intelligence_pipeline FROM learning_sessions "
                    "WHERE id = :session_id"
                ),
                {"session_id": legacy_session_id},
            ).scalar_one() == "legacy-session-evidence-v1"
            assert connection.execute(
                text(
                    "SELECT count(*), count(segment_id) FROM learning_messages "
                    "WHERE id = :message_id"
                ),
                {"message_id": legacy_message_id},
            ).one() == (1, 0)
    finally:
        try:
            command.upgrade(config, "head")
        finally:
            logger.disabled = logger_was_disabled
