from __future__ import annotations

from datetime import UTC, datetime
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.current_state import apply_evidence_to_current_state
from services.intelligence.patterns import apply_evidence_to_patterns
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    IntelligenceProcessingRun,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningSegment,
    LearningSession,
    Student,
    User,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required.",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _dimensions(*, understanding: str, independence: str, strategy: str = "not_evaluable"):
    return {
        "understanding": understanding,
        "independence": independence,
        "reasoning_demonstration": "not_observed",
        "transfer": "not_tested",
        "self_correction": "not_observed",
        "retention": "not_tested",
        "strategy_effectiveness": strategy,
        "persistence": "not_observed",
        "confidence_calibration": "not_observed",
    }


def test_real_use_mixed_sequence_does_not_turn_one_wrong_answer_into_durable_support_need(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(
            student_id=student.id,
            subject="MATH",
            status="CLOSED",
            closed_at=datetime(2026, 9, 27, tzinfo=UTC),
        )
        session.add(learning_session)
        session.flush()
        segment = LearningSegment(
            session_id=learning_session.id,
            sequence=1,
            closed_at=learning_session.closed_at,
            closure_reason="SESSION_CLOSED",
        )
        session.add(segment)
        session.flush()
        run = IntelligenceProcessingRun(
            student_id=student.id,
            rubric_version="evidence-rubric-v1",
            policy_version="segment-review-policy-v3",
            status="COMPLETED",
            scope={
                "session_id": str(learning_session.id),
                "intelligence_pipeline": "segment-finalization-v1",
                "segment_review_schema_version": "segment-learning-review-v3",
                "segment_review_prompt_version": "segment-learning-review-prompt-v8",
                "segment_review_rubric_version": "evidence-rubric-v1",
                "segment_review_policy_version": "segment-review-policy-v3",
            },
        )
        session.add(run)
        session.flush()

        evidence_rows: list[LearningEvidence] = []
        guided_candidate = None
        sequence = [
            ("independent_success", "demonstrated", "independent", "supports", "not_evaluable"),
            ("independent_success", "demonstrated", "independent", "supports", "not_evaluable"),
            ("independent_success", "demonstrated", "independent", "supports", "not_evaluable"),
            ("incorrect_attempt", "partial", "independent", "insufficient", "not_evaluable"),
            ("guided_success", "demonstrated", "moderate_support", "supports", "not_evaluable"),
            ("strategy_outcome", "demonstrated", "moderate_support", "supports", "helped"),
        ]
        for index, (event_type, understanding, independence, relationship, strategy) in enumerate(sequence):
            if event_type == "strategy_outcome":
                candidate = guided_candidate
            else:
                candidate = CandidateEvent(
                    session_id=learning_session.id,
                    event_type=event_type,
                    concept_ref="5 times table",
                    signal=f"signal-{index}",
                    payload=(
                        {
                            "strategy_key": "DECOMPOSITION",
                            "observed_student_outcome": "Student answered after scaffold.",
                        }
                        if event_type == "guided_success"
                        else {}
                    ),
                    created_at=learning_session.closed_at,
                )
                session.add(candidate)
                session.flush()
                if event_type == "guided_success":
                    guided_candidate = candidate
            event = LearningEvent(
                processing_run_id=run.id,
                session_id=learning_session.id,
                candidate_event_id=candidate.id,
                candidate_event_ids=[str(candidate.id)],
                segment_id=segment.id,
                segment_review_finding_index=index,
                subject="MATH",
                concept_ref="5 times table",
                event_type=event_type,
                description=f"fixture {event_type}",
                source_message_ids=[],
            )
            session.add(event)
            session.flush()
            evidence = LearningEvidence(
                event_id=event.id,
                concept_ref="5 times table",
                dimensions=_dimensions(
                    understanding=understanding,
                    independence=independence,
                    strategy=strategy,
                ),
                relationship=relationship,
                source_ref=f"fixture:{index}",
            )
            session.add(evidence)
            session.flush()
            evidence_rows.append(evidence)

        for evidence in evidence_rows:
            apply_evidence_to_current_state(session, evidence_id=evidence.id)
            apply_evidence_to_patterns(session, evidence_id=evidence.id)

        support = session.query(LearnerPattern).filter_by(pattern_type="support_need").one()
        active_states = session.query(CurrentLearningState).filter(
            CurrentLearningState.state_type.in_(("active_difficulty", "open_learning_loop")),
            CurrentLearningState.status == "ACTIVE",
        ).all()

        assert support.support_count == 1
        assert support.status == "CANDIDATE"
        assert active_states == []
        assert session.query(LearnerPattern).filter_by(pattern_type="strategy_effectiveness").count() == 1
