"""PostgreSQL contracts for SEG-EVID-01C staged semantic Segment Reviews."""

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
    SEGMENT_REVIEW_RESPONSE_SCHEMA,
    SegmentReviewCapacityError,
    SegmentReviewValidationError,
    review_completed_segment,
)
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.config import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    Job,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    ModelTask,
    SegmentLearningReview,
    Student,
    User,
)
from services.platform.jobs import enqueue_job
from services.tutor.candidate_events import CANDIDATE_EVENT_SCHEMA_VERSION
from services.tutor.segment_lifecycle import (
    SEGMENT_LEARNING_REVIEW_JOB,
    SEGMENT_REVIEW_REQUEST_VERSION,
)
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Segment semantic Review tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


class _Provider:
    def __init__(self, output: dict[str, object] | Exception) -> None:
        self.output = output
        self.calls = 0
        self.payloads: list[dict[str, object]] = []

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        self.calls += 1
        self.payloads.append(payload)
        if isinstance(self.output, Exception):
            raise self.output
        return ModelResult(output=self.output, input_tokens=12, output_tokens=8)


def _lineage(session: Session) -> tuple[Student, LearningSession, LearningSegment]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Fixture Student")
    session.add(student)
    session.flush()
    learning_session = LearningSession(
        student_id=student.id,
        subject="MATH",
        status="CLOSED",
        closed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
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
    return student, learning_session, segment


def _message(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
    role: str,
    content: str,
    payload: dict[str, object] | None = None,
    created_at: datetime | None = None,
) -> LearningMessage:
    message = LearningMessage(
        session_id=learning_session.id,
        segment_id=segment.id,
        role=role,
        content=content,
        payload=payload or {},
        created_at=created_at or datetime(2026, 8, 29, 11, tzinfo=UTC),
    )
    session.add(message)
    session.flush()
    return message


def _gateway(session: Session, provider: _Provider) -> ModelGateway:
    return ModelGateway(
        session,
        routes={ModelTask.SEGMENT_EVIDENCE: ModelRoute("fixture", "segment-fixture")},
        providers={"fixture": provider},
    )


def _dimensions(**overrides: str) -> dict[str, str]:
    values = {
        "understanding": "not_observed",
        "independence": "not_applicable",
        "reasoning_demonstration": "not_observed",
        "transfer": "not_tested",
        "self_correction": "not_observed",
        "retention": "not_tested",
        "strategy_effectiveness": "not_evaluable",
        "persistence": "not_observed",
        "confidence_calibration": "not_observed",
    }
    values.update(overrides)
    return values


def _finding(student_message: LearningMessage, **overrides: object) -> dict[str, object]:
    finding: dict[str, object] = {
        "validated_event_type": "learning_attempt",
        "concept_ref": "equivalent_fractions",
        "event_summary": "The Student explained why equivalent fractions name the same amount.",
        "source_message_ids": [str(student_message.id)],
        "candidate_event_ids": [],
        "school_or_extended": "school",
        "transfer_context": "not_tested",
        "retention_context": "not_tested",
        "dimensions": _dimensions(
            understanding="demonstrated",
            independence="independent",
            reasoning_demonstration="coherent",
        ),
        "relationship": "supports",
        "subject_alignment": "SAME_AS_SESSION",
        "teaching_method_id": None,
        "teaching_method_source_tutor_message_id": None,
        "misconception_evidence": None,
    }
    finding.update(overrides)
    return finding


def _output(*findings: dict[str, object]) -> dict[str, object]:
    return {"version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION, "findings": list(findings)}


def _candidate_payload(
    student: LearningMessage,
    *,
    source_message_ids: list[str] | None = None,
    **overrides: object,
) -> dict[str, object]:
    """Mirror the persisted runtime Candidate shape without invoking its parser."""

    payload: dict[str, object] = {
        "candidate_schema_version": CANDIDATE_EVENT_SCHEMA_VERSION,
        "source_message_ids": source_message_ids or [str(student.id)],
        "summary": "A provisional raw-source hint.",
        "school_or_extended": "school",
        "observed_student_outcome": None,
    }
    payload.update(overrides)
    return payload


def test_empty_segment_review_completes_without_downstream_intelligence(factory: sessionmaker[Session]) -> None:
    """Catches a valid empty staged Review being treated as a failed interpretation."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        _message(session, learning_session=learning_session, segment=segment, role="student", content="Hi Lina!")
        provider = _Provider(_output())

        outcome = review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, provider),
        )

        assert outcome.review.status == "COMPLETED"
        assert outcome.finding_count == 0
        assert outcome.model_called is True
        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert session.query(CurrentLearningState).count() == 0
        assert session.query(LearnerPattern).count() == 0
        assert session.query(DecisionView).count() == 0
        assert session.query(LearnerIntelligenceCard).count() == 0


def test_raw_source_grounded_finding_is_valid_without_candidate(factory: sessionmaker[Session]) -> None:
    """Catches Candidate Events becoming a hidden prerequisite for semantic findings."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="One half equals two fourths because both are the same amount.",
        )
        provider = _Provider(_output(_finding(student)))

        outcome = review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, provider),
        )

        assert outcome.finding_count == 1
        assert outcome.review.output == _output(_finding(student))
        request = json.loads(str(provider.payloads[0]["input"]))
        assert request["raw_messages"] == [
            {
                "id": str(student.id),
                "role": "student",
                "content": student.content,
                "created_at": student.created_at.isoformat(),
            }
        ]
        assert request["historical_anchors"] == []
        assert request["candidate_hints"] == []


@pytest.mark.parametrize("source_kind", ["hallucinated", "foreign", "tutor_only"])
def test_review_rejects_finding_without_exact_student_segment_grounding(
    factory: sessionmaker[Session], source_kind: str
) -> None:
    """Catches output that cites a hallucinated, foreign, or Tutor-only source."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="I think one half is bigger.")
        tutor = _message(session, learning_session=learning_session, segment=segment, role="tutor", content="Compare the pieces.")
        source_id = uuid4()
        if source_kind == "foreign":
            foreign = LearningSegment(
                session_id=learning_session.id,
                sequence=2,
                closed_at=learning_session.closed_at,
                closure_reason="SESSION_CLOSED",
            )
            session.add(foreign)
            session.flush()
            source_id = _message(session, learning_session=learning_session, segment=foreign, role="student", content="Foreign source.").id
        elif source_kind == "tutor_only":
            source_id = tutor.id
        finding = _finding(student, source_message_ids=[str(source_id)])
        provider = _Provider(_output(finding))

        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                gateway=_gateway(session, provider),
            )
        review = session.query(SegmentLearningReview).one()
        assert review.status == "FAILED"
        assert review.output is None


def test_misconception_requires_exact_student_reasoning_and_accepts_it_when_present(
    factory: sessionmaker[Session],
) -> None:
    """Catches bare wrong answers being escalated to durable staged misconception findings."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="One fourth is bigger than one half because 4 is bigger than 2.",
        )
        bare = _finding(student, validated_event_type="misconception_signal")
        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                gateway=_gateway(session, _Provider(_output(bare))),
            )

        valid = _finding(
            student,
            validated_event_type="misconception_signal",
            misconception_evidence={
                "version": "misconception-evidence-v1",
                "incorrect_model": "A larger denominator always makes a fraction larger.",
                "explicit_student_reasoning": "4 is bigger than 2",
                "source_message_id": str(student.id),
            },
        )
        outcome = review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, _Provider(_output(valid))),
        )
        assert outcome.review.status == "COMPLETED"


def test_review_prompt_requires_an_exact_cited_student_quote_for_misconception_evidence(
    factory: sessionmaker[Session],
) -> None:
    """Catches a semantic paraphrase being emitted where the validator requires a source quote."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="One fourth is bigger than one half because 4 is bigger than 2.",
        )
        provider = _Provider(_output(_finding(student)))

        review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, provider),
        )

        instructions = str(provider.payloads[0]["instructions"])
        assert SEGMENT_LEARNING_REVIEW_PROMPT_VERSION == "segment-learning-review-prompt-v2"
        assert "exact normalized substring" in instructions
        assert "explicit_student_reasoning" in instructions


def test_transfer_and_retention_contracts_fail_closed_without_authoritative_history(
    factory: sessionmaker[Session],
) -> None:
    """Catches near-identical practice or unprovided history becoming transfer/retention."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="I can use halves for this one too.")
        transfer = _finding(
            student,
            validated_event_type="transfer_attempt",
            transfer_context="near_identical",
            dimensions=_dimensions(transfer="demonstrated"),
        )
        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(_output(transfer))))

        retention = _finding(student, dimensions=_dimensions(retention="retained"))
        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(_output(retention))))


def test_retention_failure_relationship_is_rejected_without_historical_anchors(
    factory: sessionmaker[Session],
) -> None:
    """Catches C v1 accepting the shared retention_failure backdoor."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="I remember equivalent fractions.")
        finding = _finding(student, relationship="retention_failure")

        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                gateway=_gateway(session, _Provider(_output(finding))),
            )

        review = session.query(SegmentLearningReview).one()
        assert (review.status, review.output) == ("FAILED", None)


@pytest.mark.parametrize(
    ("invalid_kind", "event_type", "candidate_on", "payload_overrides"),
    [
        ("tutor_only_source", "learning_attempt", "tutor", {}),
        ("current_focus_signal", "current_focus_signal", "student", {}),
        ("missing_schema", "learning_attempt", "student", {"candidate_schema_version": None}),
        ("unknown_schema", "learning_attempt", "student", {"candidate_schema_version": "candidate-event-v0"}),
        ("malformed_misconception", "misconception_signal", "student", {}),
        (
            "invalid_strategy_lineage",
            "strategy_outcome",
            "student",
            {
                "observed_student_outcome": "The Student used the representation.",
                "strategy_key": "CONCRETE_EXAMPLE",
                "strategy_registry_version": "teaching-method-registry-v0",
                "strategy_source_tutor_message_id": str(uuid4()),
            },
        ),
    ],
)
def test_invalid_candidate_hint_is_excluded_while_raw_segment_review_continues(
    factory: sessionmaker[Session],
    invalid_kind: str,
    event_type: str,
    candidate_on: str,
    payload_overrides: dict[str, object],
) -> None:
    """Catches stale or malformed Candidate metadata influencing the Reviewer."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="Two fourths equals one half because both cover the same amount.",
        )
        tutor = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="tutor",
            content="Explain your fraction reasoning.",
        )
        source = tutor if candidate_on == "tutor" else student
        session.add(
            CandidateEvent(
                session_id=learning_session.id,
                message_id=source.id,
                event_type=event_type,
                signal=f"invalid-{invalid_kind}",
                payload=_candidate_payload(source, **payload_overrides),
            )
        )
        session.flush()
        provider = _Provider(_output(_finding(student)))

        outcome = review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, provider),
        )

        request = json.loads(str(provider.payloads[0]["input"]))
        assert outcome.review.status == "COMPLETED"
        assert request["candidate_hints"] == []


def test_valid_current_and_misconception_candidates_are_optional_safe_hints(
    factory: sessionmaker[Session],
) -> None:
    """Catches the CAND-01 grounding contract being lost before AI input."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="One fourth is bigger than one half because 4 is bigger than 2.",
        )
        current = CandidateEvent(
            session_id=learning_session.id,
            message_id=student.id,
            event_type="incorrect_attempt",
            signal="current",
            payload=_candidate_payload(student),
        )
        misconception = CandidateEvent(
            session_id=learning_session.id,
            message_id=student.id,
            event_type="misconception_signal",
            signal="grounded-misconception",
            payload=_candidate_payload(
                student,
                misconception_evidence={
                    "version": "misconception-evidence-v1",
                    "incorrect_model": "A larger denominator makes a fraction larger.",
                    "explicit_student_reasoning": "4 is bigger than 2",
                    "source_message_id": str(student.id),
                },
            ),
        )
        session.add_all([current, misconception])
        session.flush()
        provider = _Provider(_output(_finding(student)))

        review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=_gateway(session, provider),
        )

        request = json.loads(str(provider.payloads[0]["input"]))
        assert {hint["candidate_id"] for hint in request["candidate_hints"]} == {str(current.id), str(misconception.id)}


def test_candidate_hint_can_be_reinterpreted_but_foreign_candidate_is_rejected(
    factory: sessionmaker[Session],
) -> None:
    """Catches Candidate metadata controlling semantic truth or crossing Segment lineage."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="I used a picture to compare the fractions.")
        candidate = CandidateEvent(
            session_id=learning_session.id,
            message_id=student.id,
            event_type="incorrect_attempt",
            concept_ref="fractions",
            signal="candidate-hint",
            payload=_candidate_payload(student, summary="A provisional hint."),
        )
        session.add(candidate)
        session.flush()
        foreign = LearningSegment(session_id=learning_session.id, sequence=2, closed_at=learning_session.closed_at, closure_reason="SESSION_CLOSED")
        session.add(foreign)
        session.flush()
        foreign_message = _message(session, learning_session=learning_session, segment=foreign, role="student", content="A foreign Segment source.")
        foreign_candidate = CandidateEvent(
            session_id=learning_session.id,
            message_id=foreign_message.id,
            event_type="learning_attempt",
            signal="foreign",
            payload={"source_message_ids": [str(foreign_message.id)]},
        )
        session.add(foreign_candidate)
        session.flush()
        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                gateway=_gateway(session, _Provider(_output(_finding(student, candidate_event_ids=[str(foreign_candidate.id)])))),
                version=None,
            )
        reinterpretation = _finding(student, candidate_event_ids=[str(candidate.id)], validated_event_type="explanation_attempt")
        assert review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(_output(reinterpretation)))).finding_count == 1


def test_teaching_method_lineage_and_strategy_outcome_require_exact_server_identity(
    factory: sessionmaker[Session],
) -> None:
    """Catches AI invention of a method or effectiveness without a later Student outcome."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        tutor = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="tutor",
            content="Use fraction circles.",
            payload={"teaching_method_id": "CONCRETE_EXAMPLE", "teaching_method_registry_version": "teaching-method-registry-v1"},
            created_at=datetime(2026, 8, 29, 11, tzinfo=UTC),
        )
        student = _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="The circles show one half is larger than one fourth.",
            created_at=datetime(2026, 8, 29, 11, tzinfo=UTC) + timedelta(seconds=1),
        )
        valid = _finding(
            student,
            validated_event_type="strategy_outcome",
            source_message_ids=[str(tutor.id), str(student.id)],
            teaching_method_id="CONCRETE_EXAMPLE",
            teaching_method_source_tutor_message_id=str(tutor.id),
            dimensions=_dimensions(strategy_effectiveness="helped"),
        )
        assert review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(_output(valid)))).finding_count == 1

        second = LearningSegment(
            session_id=learning_session.id,
            sequence=2,
            closed_at=learning_session.closed_at,
            closure_reason="SESSION_CLOSED",
        )
        session.add(second)
        session.flush()
        second_tutor = _message(
            session,
            learning_session=learning_session,
            segment=second,
            role="tutor",
            content="Use fraction circles again.",
            payload={"teaching_method_id": "CONCRETE_EXAMPLE", "teaching_method_registry_version": "teaching-method-registry-v1"},
        )
        second_student = _message(session, learning_session=learning_session, segment=second, role="student", content="I can compare the circles.")
        invented = _finding(second_student, teaching_method_id="WORKED_EXAMPLE", teaching_method_source_tutor_message_id=str(second_tutor.id))
        with pytest.raises(SegmentReviewValidationError):
            review_completed_segment(session, learning_session=learning_session, segment=second, gateway=_gateway(session, _Provider(_output(invented))))


def test_valid_transfer_and_cross_subject_finding_remain_staged(factory: sessionmaker[Session]) -> None:
    """Catches valid transfer or possible cross-subject interpretation being discarded or activated."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="Moon phases change because of the Sun, Earth, and Moon positions.")
        finding = _finding(
            student,
            validated_event_type="transfer_attempt",
            transfer_context="meaningfully_changed",
            subject_alignment="POSSIBLE_CROSS_SUBJECT",
            dimensions=_dimensions(transfer="demonstrated"),
        )
        outcome = review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(_output(finding))))
        assert outcome.review.output is not None
        assert outcome.review.output["findings"][0]["subject_alignment"] == "POSSIBLE_CROSS_SUBJECT"
        assert session.query(LearningEvent).count() == 0


def test_failed_review_retries_the_same_identity_without_partial_output(factory: sessionmaker[Session]) -> None:
    """Catches retryable Review failure being rolled back or duplicated."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="Two fourths equals one half.")
        with pytest.raises(Exception, match="SegmentReviewProviderError"):
            review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(RuntimeError("provider detail"))))
        failed = session.query(SegmentLearningReview).one()
        assert (failed.status, failed.output, failed.failure_detail) == ("FAILED", None, "SegmentReviewProviderError")
        retried = review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, _Provider(_output(_finding(student)))))
        assert retried.review.id == failed.id
        assert retried.review.status == "COMPLETED"


def test_completed_exact_review_is_reused_without_a_second_model_call(factory: sessionmaker[Session]) -> None:
    """Catches a retry duplicating an exact completed semantic interpretation."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        student = _message(session, learning_session=learning_session, segment=segment, role="student", content="Two fourths is one half.")
        provider = _Provider(_output(_finding(student)))
        first = review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, provider))
        second = review_completed_segment(session, learning_session=learning_session, segment=segment, gateway=_gateway(session, provider))

        assert second.review.id == first.review.id
        assert second.model_called is False
        assert provider.calls == 1


def test_capacity_rejects_complete_raw_segment_without_calling_model(factory: sessionmaker[Session]) -> None:
    """Catches silent raw-Segment truncation under the configured capacity guardrail."""

    with factory.begin() as session:
        _, learning_session, segment = _lineage(session)
        _message(session, learning_session=learning_session, segment=segment, role="student", content="x" * 200)
        provider = _Provider(_output())

        with pytest.raises(SegmentReviewCapacityError, match="SEGMENT_REVIEW_CAPACITY_EXCEEDED"):
            review_completed_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                gateway=_gateway(session, provider),
                settings=Settings(_env_file=None, segment_review_context_capacity=1),
            )
        assert provider.calls == 0
        review = session.query(SegmentLearningReview).one()
        assert review.status == "FAILED"
        assert review.output is None


def test_worker_claims_b_request_and_completes_staged_review(factory: sessionmaker[Session]) -> None:
    """Catches B's pending request remaining unhandled after C registration."""

    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        _message(session, learning_session=learning_session, segment=segment, role="student", content="Hello.")
        enqueue_job(
            session,
            job_type=SEGMENT_LEARNING_REVIEW_JOB,
            payload={
                "segment_id": str(segment.id),
                "session_id": str(learning_session.id),
                "student_id": str(student.id),
                "review_request_version": SEGMENT_REVIEW_REQUEST_VERSION,
                "closed_at": segment.closed_at.isoformat(),
                "closure_reason": segment.closure_reason,
            },
            idempotency_key=f"fixture:{segment.id}",
        )
        segment_id = segment.id

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        segment_evidence_gateway_factory=lambda session: _gateway(session, _Provider(_output())),
    )
    assert run_once(factory, registry, worker_id="fixture-worker") is not None

    with factory() as session:
        review = session.query(SegmentLearningReview).filter_by(segment_id=segment_id).one()
        assert review.status == "COMPLETED"


def test_review_settlement_and_repeated_completed_job_enqueue_finalization_once(
    factory: sessionmaker[Session],
) -> None:
    """Catches missing settlement notification and duplicate finalization jobs."""

    from services.tutor.session_lifecycle import SESSION_INTELLIGENCE_FINALIZE_JOB

    closed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        _message(
            session,
            learning_session=learning_session,
            segment=segment,
            role="student",
            content="Two fourths equals one half.",
        )
        payload = {
            "segment_id": str(segment.id),
            "session_id": str(learning_session.id),
            "student_id": str(student.id),
            "review_request_version": SEGMENT_REVIEW_REQUEST_VERSION,
            "closed_at": segment.closed_at.isoformat(),
            "closure_reason": segment.closure_reason,
        }
        enqueue_job(
            session,
            job_type=SEGMENT_LEARNING_REVIEW_JOB,
            payload=payload,
            idempotency_key=f"settlement:{segment.id}",
            run_after=closed_at - timedelta(minutes=2),
        )

    provider = _Provider(_output())
    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        segment_evidence_gateway_factory=lambda session: _gateway(session, provider),
    )
    assert run_once(factory, registry, worker_id="fixture-worker", now=closed_at).value == "COMPLETED"

    with factory.begin() as session:
        final_jobs = session.query(Job).filter_by(job_type=SESSION_INTELLIGENCE_FINALIZE_JOB).all()
        assert len(final_jobs) == 1
        final_jobs[0].run_after = closed_at + timedelta(hours=1)
        enqueue_job(
            session,
            job_type=SEGMENT_LEARNING_REVIEW_JOB,
            payload=payload,
            idempotency_key=f"settlement-repeat:{segment.id}",
            run_after=closed_at - timedelta(minutes=1),
        )

    assert run_once(factory, registry, worker_id="fixture-worker", now=closed_at).value == "COMPLETED"

    with factory() as session:
        reviews = session.query(SegmentLearningReview).filter_by(segment_id=segment.id).all()
        final_jobs = session.query(Job).filter_by(job_type=SESSION_INTELLIGENCE_FINALIZE_JOB).all()
        assert len(reviews) == 1
        assert len(final_jobs) == 1
        assert provider.calls == 1


def test_worker_preserves_failed_review_before_retrying_the_same_identity(
    factory: sessionmaker[Session],
) -> None:
    """Catches the Job rollback erasing a Review's safe FAILED marker before retry."""

    now = datetime(2026, 8, 29, 12, tzinfo=UTC)
    with factory.begin() as session:
        student, learning_session, segment = _lineage(session)
        _message(session, learning_session=learning_session, segment=segment, role="student", content="Hello.")
        job = enqueue_job(
            session,
            job_type=SEGMENT_LEARNING_REVIEW_JOB,
            payload={
                "segment_id": str(segment.id),
                "session_id": str(learning_session.id),
                "student_id": str(student.id),
                "review_request_version": SEGMENT_REVIEW_REQUEST_VERSION,
                "closed_at": segment.closed_at.isoformat(),
                "closure_reason": segment.closure_reason,
            },
            idempotency_key=f"retry:{segment.id}",
            run_after=now,
        )
        job_id = job.id
        segment_id = segment.id

    providers = iter([_Provider(RuntimeError("provider detail")), _Provider(_output())])
    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        segment_evidence_gateway_factory=lambda session: _gateway(session, next(providers)),
    )
    assert run_once(factory, registry, worker_id="fixture-worker", now=now).value == "PENDING"
    with factory() as session:
        failed = session.query(SegmentLearningReview).filter_by(segment_id=segment_id).one()
        assert failed.status == "FAILED"
        review_id = failed.id
        assert session.get(type(job), job_id).status == "PENDING"

    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(seconds=31)).value == "COMPLETED"
    with factory() as session:
        retried = session.query(SegmentLearningReview).filter_by(segment_id=segment_id).one()
        assert (retried.id, retried.status) == (review_id, "COMPLETED")


def test_segment_review_strict_schema_requires_every_object_property() -> None:
    """Catches OpenAI strict-schema regressions from omitted nullable properties."""

    def check(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                assert set(node.get("required", [])) == set(properties)
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    assert ModelTask.SEGMENT_EVIDENCE.value == "segment_evidence"
    check(SEGMENT_REVIEW_RESPONSE_SCHEMA["schema"])
