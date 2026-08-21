"""TASK-026 contracts for bounded, versioned intelligence reprocessing."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.reprocess import (
    EvidenceVersionSelection,
    IntelligenceReprocessRequest,
    INTELLIGENCE_REPROCESS_JOB,
    enqueue_intelligence_reprocess,
    preview_intelligence_reprocess,
)
from services.intelligence.current_state import CurrentStatePolicyError
from services.intelligence.consolidation import EvidenceContractError
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    IntelligenceReprocessRun,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearnerIntelligenceCard,
    LearningEvidence,
    LearningMessage,
    LearningSession,
    ModelTask,
    Student,
    User,
)
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for intelligence reprocessing tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _closed_session(session: Session, *, closed_at: datetime, student: Student | None = None) -> LearningSession:
    if student is None:
        user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="CLOSED", closed_at=closed_at)
    session.add(learning_session)
    session.flush()
    message = LearningMessage(session_id=learning_session.id, role="student", content="I solved it.", payload={})
    session.add(message)
    session.flush()
    session.add(
        CandidateEvent(
            session_id=learning_session.id,
            message_id=message.id,
            event_type="independent_success",
            concept_ref="fractions",
            signal="solved_independently",
            payload={
                "candidate_schema_version": "candidate-event-v1",
                "summary": "Student solved fractions independently.",
                "school_or_extended": "school",
                "source_message_ids": [str(message.id)],
                "subject": "MATH",
            },
            created_at=closed_at,
        )
    )
    return learning_session


def test_bounded_preview_and_same_version_request_are_idempotent(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2026, 1, 10, tzinfo=UTC))
        other = _closed_session(session, closed_at=datetime(2026, 2, 10, tzinfo=UTC))
        request = IntelligenceReprocessRequest(
            student_id=target.student_id,
            subject="MATH",
            session_ids=(target.id,),
            evidence=EvidenceVersionSelection(),
        )

        preview = preview_intelligence_reprocess(session, request=request)
        first = enqueue_intelligence_reprocess(session, request=request)
        second = enqueue_intelligence_reprocess(session, request=request)

        assert preview.selected_session_ids == (target.id,)
        assert preview.selected_session_count == 1
        assert preview.sessions_needing_processing == 1
        assert first.job.id == second.job.id
        assert first.reprocess_run.id == second.reprocess_run.id
        assert session.get(LearningSession, other.id) is not None


def test_date_range_scope_excludes_other_sessions_and_preview_writes_nothing(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        first = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        middle = _closed_session(session, closed_at=datetime(2025, 2, 10, tzinfo=UTC), student=session.get(Student, first.student_id))
        _closed_session(session, closed_at=datetime(2025, 3, 10, tzinfo=UTC), student=session.get(Student, first.student_id))
        request = IntelligenceReprocessRequest(
            student_id=first.student_id,
            subject="MATH",
            start_at=datetime(2025, 2, 1, tzinfo=UTC),
            end_at=datetime(2025, 2, 28, tzinfo=UTC),
        )
        preview = preview_intelligence_reprocess(session, request=request)

        assert preview.selected_session_ids == (middle.id,)
        assert session.query(IntelligenceReprocessRun).count() == 0
        assert session.query(LearningEvidence).count() == 0


def test_changed_evidence_version_creates_separate_reprocess_request(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        base = IntelligenceReprocessRequest(student_id=target.student_id, session_ids=(target.id,))
        changed = IntelligenceReprocessRequest(
            student_id=target.student_id,
            session_ids=(target.id,),
            evidence=EvidenceVersionSelection(prompt_version="unsupported-prompt-v9"),
        )
        first = enqueue_intelligence_reprocess(session, request=base)
        with pytest.raises(EvidenceContractError, match="Evidence interpretation"):
            enqueue_intelligence_reprocess(session, request=changed)

        assert session.query(IntelligenceReprocessRun).count() == 1


def test_reprocess_job_preserves_raw_history_and_activates_only_successful_session(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        candidate = session.query(CandidateEvent).filter_by(session_id=target.id).one()
        request = IntelligenceReprocessRequest(
            student_id=target.student_id,
            subject="MATH",
            session_ids=(target.id,),
            evidence=EvidenceVersionSelection(),
        )
        queued = enqueue_intelligence_reprocess(session, request=request)

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route, payload
            return ModelResult(output={
                "version": "session-evidence-v1",
                "events": [{
                    "candidate_event_id": str(candidate.id),
                    "source_message_ids": [str(candidate.message_id)],
                    "subject": "MATH",
                    "concept_ref": "fractions",
                    "event_type": "independent_success",
                    "event_summary": "Student independently solved a fractions task.",
                    "school_or_extended": "school",
                    "dimensions": {
                        "understanding": "partial", "independence": "substantial_support",
                        "reasoning_demonstration": "coherent", "transfer": "not_tested",
                        "self_correction": "not_observed", "retention": "not_tested",
                        "strategy_effectiveness": "not_evaluable", "persistence": "not_observed",
                        "confidence_calibration": "not_observed",
                    },
                    "relationship": "improvement",
                }],
            })

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        evidence_gateway_factory=lambda worker_session: ModelGateway(
            worker_session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": Provider()},
        ),
    )
    assert INTELLIGENCE_REPROCESS_JOB in registry.job_types()
    assert run_once(factory, registry, worker_id="reprocess-worker") == "COMPLETED"

    with factory() as session:
        run = session.get(IntelligenceReprocessRun, queued.reprocess_run.id)
        authority = session.query(IntelligenceSessionAuthority).one()
        state = session.query(CurrentLearningState).filter_by(state_type="active_difficulty").one()
        unchanged = session.get(CandidateEvent, candidate.id)
        assert run is not None and run.status == "COMPLETED"
        assert authority.session_id == target.id
        assert authority.reprocess_run_id == run.id
        assert state.policy_version == "current-state-policy-v1"
        assert state.detected_at == target.closed_at
        assert unchanged is not None and unchanged.signal == "solved_independently"
        assert session.query(LearnerIntelligenceCard).count() == 0


def test_preview_reuses_exact_completed_evidence_version_without_writing(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        request = IntelligenceReprocessRequest(student_id=target.student_id, session_ids=(target.id,))
        queued = enqueue_intelligence_reprocess(session, request=request)
        session.add(
            IntelligenceProcessingRun(
                student_id=target.student_id,
                rubric_version="evidence-rubric-v1",
                policy_version="session-consolidation-policy-v1",
                status="COMPLETED",
                scope={
                    "session_id": str(target.id),
                    "consolidation_schema_version": "session-evidence-v1",
                    "prompt_version": "session-evidence-prompt-v1",
                    "provider": "fixture",
                    "model": "fixture-evidence",
                },
            )
        )
        session.flush()
        preview = preview_intelligence_reprocess(session, request=request)
        changed_route = preview_intelligence_reprocess(
            session,
            request=IntelligenceReprocessRequest(
                student_id=target.student_id,
                session_ids=(target.id,),
                evidence=EvidenceVersionSelection(provider="fixture", model="fixture-evidence-v2"),
            ),
        )

        assert preview.selected_session_count == 1
        assert preview.sessions_needing_processing == 0
        assert changed_route.sessions_needing_processing == 1
        assert session.get(IntelligenceReprocessRun, queued.reprocess_run.id) is not None


def test_unsupported_current_state_policy_is_rejected_before_reprocess(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        request = IntelligenceReprocessRequest(
            student_id=target.student_id,
            session_ids=(target.id,),
            current_state_policy_version="current-state-policy-v9",
        )

        with pytest.raises(CurrentStatePolicyError):
            enqueue_intelligence_reprocess(session, request=request)
        assert session.query(IntelligenceReprocessRun).count() == 0
