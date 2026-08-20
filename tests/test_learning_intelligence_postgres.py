"""Phase 2–3 vertical-loop tests against PostgreSQL-derived records."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.repository import create_content_block, create_content_document, create_processing_run
from services.intelligence.core import close_and_consolidate, consolidate_student_history
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import CandidateEvent, CurrentLearningState, LearningEvidence, Student, User
from services.retrieval.embeddings import deterministic_embedding
from services.tutor.runtime import start_session, tutor_turn
from services.tutor.session_lifecycle import close_inactive_sessions
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required")


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE learning_evidence, learning_events, candidate_events, learning_messages, learning_sessions, current_learning_states, pattern_evidence, learner_patterns, learner_intelligence_cards, decision_views, intelligence_processing_runs, content_blocks, curriculum_nodes, content_processing_runs, content_documents CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_candidate_to_evidence_to_card_and_later_context(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user); session.flush()
        student = Student(user_id=user.id, display_name="Sandbox")
        session.add(student); session.flush()
        document = create_content_document(session, student_id=student.id, grade_level=5, subject="MATH", original_storage_key="fixture", original_checksum=uuid4().hex + uuid4().hex, filename="place-value.md", content_type="text/markdown")
        document.status = "STRUCTURAL_READY"
        run = create_processing_run(session, document_id=document.id, kind="STRUCTURAL", processor_version="fixture-v1")
        run.status = "COMPLETED"
        create_content_block(session, document_id=document.id, processing_run_id=run.id, text="Use place value to multiply decimal numbers by 10. 3.452 × 10 = 34.52.", block_type="exercise", page_number=2, source_ref="fixture#page=2", embedding=deterministic_embedding("Use place value to multiply decimal numbers by 10. 3.452 × 10 = 34.52."))
        first = start_session(session, student_id=student.id)
        turn = tutor_turn(session, learning_session=first, question="I think 3.452 × 10 = 34.52")
        assert turn.candidate_event_id is not None
        close_and_consolidate(session, learning_session=first)
        assert session.query(LearningEvidence).count() == 1
        assert session.query(CurrentLearningState).count() == 0
        later = start_session(session, student_id=student.id)
        later_turn = tutor_turn(session, learning_session=later, question="Can we multiply 8.2 by 10?")
        assert later_turn.sources[0]["source_ref"] == "fixture#page=2"
        # One support-seeking attempt makes a current state and a non-stable pattern.
        tutor_turn(session, learning_session=later, question="I tried 8.2 × 10 but I need help")
        close_and_consolidate(session, learning_session=later)
        assert session.query(CurrentLearningState).count() >= 1
        assert session.query(CandidateEvent).count() >= 3
        third = start_session(session, student_id=student.id)
        personalized = tutor_turn(session, learning_session=third, question="Can we multiply 6.4 by 10?")
        assert personalized.intelligence
        rebuilt = consolidate_student_history(session, student_id=student.id)
        assert rebuilt.rubric_version == "evidence-rubric-v1"


def test_inactive_session_closes_once_and_worker_consolidates(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user); session.flush(); student = Student(user_id=user.id); session.add(student); session.flush()
        learning_session = start_session(session, student_id=student.id)
        learning_session.last_activity_at = datetime.now(UTC) - timedelta(hours=1)
        assert close_inactive_sessions(session, inactivity=timedelta(minutes=10)) == [learning_session]
    registry = JobHandlerRegistry(); register_intelligence_handlers(registry, session_factory=postgres_session_factory)
    assert run_once(postgres_session_factory, registry, worker_id="intelligence-test") == "COMPLETED"
    with postgres_session_factory() as session:
        assert session.get(type(learning_session), learning_session.id).status == "CLOSED"
        assert close_inactive_sessions(session, inactivity=timedelta(minutes=10)) == []
