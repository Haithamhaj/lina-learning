"""PostgreSQL acceptance coverage for SUBJ-01 Subject authority."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
)
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    LearningEvent,
    LearningMessage,
    LearningSegment,
    LearningSession,
    SegmentLearningReview,
    Student,
    User,
)
from services.platform.db.models import ModelTask


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Subject attribution tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _student(session: Session) -> Student:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Subject Fixture")
    session.add(student)
    session.flush()
    return student


def _finding(message: LearningMessage, *, concept_ref: str) -> dict[str, object]:
    return {
        "validated_event_type": "learning_attempt",
        "concept_ref": concept_ref,
        "event_summary": f"The Student demonstrated {concept_ref}.",
        "source_message_ids": [str(message.id)],
        "candidate_event_ids": [],
        "historical_anchor_evidence_ids": [],
        "transfer_context": "not_tested",
        "retention_context": "not_tested",
        "dimensions": {
            "understanding": "demonstrated",
            "independence": "independent",
            "reasoning_demonstration": "coherent",
            "transfer": "not_tested",
            "self_correction": "not_observed",
            "retention": "not_tested",
            "strategy_effectiveness": "not_evaluable",
            "persistence": "not_observed",
            "confidence_calibration": "not_observed",
        },
        "relationship": "supports",
        "reported_broad_subject": None,
        "teaching_method_id": None,
        "teaching_method_source_tutor_message_id": None,
        "misconception_evidence": None,
    }


def _review(
    session: Session,
    *,
    student: Student,
    learning_session: LearningSession,
    segment: LearningSegment,
    primary_broad_subject: str,
    finding: dict[str, object],
) -> SegmentLearningReview:
    review = SegmentLearningReview(
        student_id=student.id,
        session_id=learning_session.id,
        segment_id=segment.id,
        schema_version=SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
        prompt_version=SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
        rubric_version="evidence-rubric-v1",
        review_policy_version=SEGMENT_REVIEW_POLICY_VERSION,
        provider="fixture",
        model="fixture",
        status="COMPLETED",
        output={
            "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
            "segment_kind": "LEARNING",
            "primary_broad_subject": primary_broad_subject,
            "school_context": {
                "school_relation": "UNKNOWN",
                "school_subject_ref": None,
                "school_domain_path": [],
                "unit_ref": None,
                "lesson_ref": None,
                "page_refs": [],
                "source_refs": [],
            },
            "findings": [finding],
        },
        completed_at=learning_session.closed_at,
    )
    session.add(review)
    session.flush()
    return review


class _Provider:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.payloads: list[dict[str, object]] = []

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        self.payloads.append(payload)
        return ModelResult(output=self.output, input_tokens=1, output_tokens=1)


def _gateway(session: Session, provider: _Provider) -> ModelGateway:
    return ModelGateway(
        session,
        routes={ModelTask.SEGMENT_EVIDENCE: ModelRoute("fixture", "fixture")},
        providers={"fixture": provider},
    )


def test_finalization_uses_each_reviewed_segment_subject_not_session_subject(
    factory: sessionmaker[Session],
) -> None:
    """Catches Math-first Session defaults contaminating cross-Subject Evidence."""

    from services.intelligence.session_finalization import finalize_closed_session

    with factory.begin() as session:
        student = _student(session)
        closed_at = datetime(2026, 8, 30, 12, tzinfo=UTC)
        learning_session = LearningSession(
            student_id=student.id,
            subject="MATH",
            status="CLOSED",
            closed_at=closed_at,
            intelligence_pipeline="segment-finalization-v1",
        )
        session.add(learning_session)
        session.flush()

        expected = (("MATH", "equivalent_fractions"), ("SCIENCE", "stars"), ("MATH", "fraction_comparison"))
        for sequence, (subject, concept_ref) in enumerate(expected, start=1):
            segment = LearningSegment(
                session_id=learning_session.id,
                sequence=sequence,
                closed_at=closed_at - timedelta(minutes=4 - sequence),
                closure_reason="SESSION_CLOSED" if sequence == 3 else "NEXT_SEGMENT_CREATED",
            )
            session.add(segment)
            session.flush()
            message = LearningMessage(
                session_id=learning_session.id,
                segment_id=segment.id,
                role="student",
                content=f"I am learning {concept_ref}.",
                payload={},
                created_at=closed_at - timedelta(minutes=4 - sequence, seconds=30),
            )
            session.add(message)
            session.flush()
            _review(
                session,
                student=student,
                learning_session=learning_session,
                segment=segment,
                primary_broad_subject=subject,
                finding=_finding(message, concept_ref=concept_ref),
            )

        outcome = finalize_closed_session(session, learning_session=learning_session)
        events = session.query(LearningEvent).order_by(LearningEvent.segment_review_finding_index).all()

        assert outcome.event_count == 3
        assert [(event.subject, event.concept_ref) for event in events] == list(expected)


def test_background_review_uses_current_segment_not_stale_session_subject(
    factory: sessionmaker[Session],
) -> None:
    """Catches a Math entry Subject biasing a later Science Segment Review."""

    from services.intelligence.segment_reviews import review_completed_segment

    with factory.begin() as session:
        student = _student(session)
        closed_at = datetime(2026, 8, 30, 12, tzinfo=UTC)
        learning_session = LearningSession(
            student_id=student.id,
            subject="MATH",
            status="CLOSED",
            closed_at=closed_at,
        )
        session.add(learning_session)
        session.flush()
        segment = LearningSegment(
            session_id=learning_session.id,
            sequence=2,
            closed_at=closed_at,
            closure_reason="SESSION_CLOSED",
        )
        session.add(segment)
        session.flush()
        message = LearningMessage(
            session_id=learning_session.id,
            segment_id=segment.id,
            role="student",
            content="Why do stars shine?",
            payload={},
            created_at=closed_at,
        )
        session.add(message)
        session.flush()
        provider = _Provider(
            {
                "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
                "segment_kind": "LEARNING",
                "primary_broad_subject": "SCIENCE",
                "school_context": {
                    "school_relation": "UNKNOWN",
                    "school_subject_ref": None,
                    "school_domain_path": [],
                    "unit_ref": None,
                    "lesson_ref": None,
                    "page_refs": [],
                    "source_refs": [],
                },
                "findings": [_finding(message, concept_ref="stars")],
            }
        )

        outcome = review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, provider),
        )

        assert outcome.review.output is not None
        assert outcome.review.output["primary_broad_subject"] == "SCIENCE"
        assert outcome.review.output["school_context"]["school_relation"] == "UNKNOWN"
        assert "session_subject" not in str(provider.payloads[0]["input"])
        assert json.loads(str(provider.payloads[0]["input"]))["broad_subject_registry"]["keys"] == [
            "MATH",
            "SCIENCE",
            "LANGUAGE_ARTS",
            "SOCIAL_STUDIES",
            "COMPUTING",
            "RELIGIOUS_STUDIES",
            "ARTS",
            "PHYSICAL_EDUCATION",
            "GENERAL_KNOWLEDGE",
            "OTHER",
        ]


def test_finalization_withholds_a_conflicting_finding_but_preserves_its_review(
    factory: sessionmaker[Session],
) -> None:
    """Catches a Science Finding being silently stamped as Math Evidence."""

    from services.intelligence.session_finalization import finalize_closed_session

    with factory.begin() as session:
        student = _student(session)
        closed_at = datetime(2026, 8, 30, 12, tzinfo=UTC)
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="CLOSED", closed_at=closed_at)
        session.add(learning_session)
        session.flush()
        segment = LearningSegment(session_id=learning_session.id, sequence=1, closed_at=closed_at, closure_reason="SESSION_CLOSED")
        session.add(segment)
        session.flush()
        message = LearningMessage(session_id=learning_session.id, segment_id=segment.id, role="student", content="Stars shine by fusion.", payload={})
        session.add(message)
        session.flush()
        finding = _finding(message, concept_ref="stars")
        finding["reported_broad_subject"] = "SCIENCE"
        review = _review(session, student=student, learning_session=learning_session, segment=segment, primary_broad_subject="MATH", finding=finding)

        outcome = finalize_closed_session(session, learning_session=learning_session)

        assert outcome.event_count == 0
        assert outcome.withheld_finding_count == 1
        assert review.output is not None
        assert review.output["findings"][0]["reported_broad_subject"] == "SCIENCE"


def test_non_learning_review_materializes_no_academic_evidence(
    factory: sessionmaker[Session],
) -> None:
    """Catches casual conversation acquiring an academic Subject or Evidence."""

    from services.intelligence.session_finalization import finalize_closed_session

    with factory.begin() as session:
        student = _student(session)
        closed_at = datetime(2026, 8, 30, 12, tzinfo=UTC)
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="CLOSED", closed_at=closed_at)
        session.add(learning_session)
        session.flush()
        segment = LearningSegment(session_id=learning_session.id, sequence=1, closed_at=closed_at, closure_reason="SESSION_CLOSED")
        session.add(segment)
        session.flush()
        message = LearningMessage(session_id=learning_session.id, segment_id=segment.id, role="student", content="How are you?", payload={})
        session.add(message)
        session.flush()
        session.add(
            SegmentLearningReview(
                student_id=student.id, session_id=learning_session.id, segment_id=segment.id,
                schema_version=SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION, prompt_version=SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
                rubric_version="evidence-rubric-v1", review_policy_version=SEGMENT_REVIEW_POLICY_VERSION,
                provider="fixture", model="fixture", status="COMPLETED",
                output={"version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION, "segment_kind": "NON_LEARNING", "primary_broad_subject": None, "school_context": None, "findings": []},
                completed_at=closed_at,
            )
        )
        session.flush()

        outcome = finalize_closed_session(session, learning_session=learning_session)

        assert outcome.event_count == outcome.evidence_count == 0
