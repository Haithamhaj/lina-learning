"""PostgreSQL persistence contracts required before Session Finalization."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from importlib import import_module
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.authority import authoritative_evidence_ids
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    Job,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    PatternEvidence,
    LearningSegment,
    LearningSession,
    SegmentLearningReview,
    Student,
    User,
)
from services.platform.jobs import enqueue_job
from services.tutor.session_lifecycle import (
    SESSION_CONSOLIDATION_JOB,
    SESSION_INTELLIGENCE_FINALIZE_JOB,
    enqueue_session_intelligence_finalization_if_ready,
)
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once


PRIOR_REVISION = "e7b1f3c9a2d4"


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Session Finalization persistence tests",
)


@pytest.fixture(autouse=True)
def preserve_observability_logger_state():
    """Keep Alembic's logging reconfiguration local to each migration test."""

    logger = logging.getLogger("services.platform.observability.metrics")
    was_disabled = logger.disabled
    try:
        yield
    finally:
        logger.disabled = was_disabled


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE jobs, learning_evidence, learning_events, candidate_events, learning_messages, "
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


def _finalization_api() -> tuple[Any, type[Exception], type[Exception]]:
    module = import_module("services.intelligence.session_finalization")
    return (
        module.finalize_closed_session,
        module.SessionFinalizationBlockedError,
        module.SessionFinalizationValidationError,
    )


def _closed_lineage(
    session: Session,
    *,
    segment_count: int = 1,
    student: Student | None = None,
    pipeline: str = "segment-finalization-v1",
) -> tuple[Student, LearningSession, list[tuple[LearningSegment, LearningMessage]]]:
    student = student or _student(session)
    closed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    learning_session = LearningSession(
        student_id=student.id,
        subject="MATH",
        status="CLOSED",
        intelligence_pipeline=pipeline,
        closed_at=closed_at,
        last_activity_at=closed_at,
    )
    session.add(learning_session)
    session.flush()
    lineage: list[tuple[LearningSegment, LearningMessage]] = []
    for index in range(segment_count):
        segment = LearningSegment(
            session_id=learning_session.id,
            sequence=index + 1,
            closed_at=closed_at - timedelta(minutes=segment_count - index),
            closure_reason=(
                "SESSION_CLOSED" if index == segment_count - 1 else "NEXT_SEGMENT_CREATED"
            ),
        )
        session.add(segment)
        session.flush()
        message = LearningMessage(
            session_id=learning_session.id,
            segment_id=segment.id,
            role="student",
            content=f"Segment {index + 1}: I used equivalent fractions.",
            payload={},
            created_at=closed_at - timedelta(minutes=segment_count - index, seconds=30),
        )
        session.add(message)
        session.flush()
        lineage.append((segment, message))
    return student, learning_session, lineage


def _dimensions(**overrides: str) -> dict[str, str]:
    dimensions = {
        "understanding": "partial",
        "independence": "substantial_support",
        "reasoning_demonstration": "coherent",
        "transfer": "not_tested",
        "self_correction": "not_observed",
        "retention": "not_tested",
        "strategy_effectiveness": "not_evaluable",
        "persistence": "not_observed",
        "confidence_calibration": "not_observed",
    }
    dimensions.update(overrides)
    return dimensions


def _finding(
    message: LearningMessage,
    *,
    candidate_ids: list[str] | None = None,
    alignment: str = "SAME_AS_SESSION",
    concept_ref: str = "equivalent_fractions",
    event_type: str = "learning_attempt",
    summary: str = "The Student explained an equivalent-fractions relationship.",
    dimensions: dict[str, str] | None = None,
    relationship: str = "supports",
) -> dict[str, object]:
    return {
        "validated_event_type": event_type,
        "concept_ref": concept_ref,
        "event_summary": summary,
        "source_message_ids": [str(message.id)],
        "candidate_event_ids": candidate_ids or [],
        "school_or_extended": "school",
        "transfer_context": "not_tested",
        "retention_context": "not_tested",
        "dimensions": dimensions or _dimensions(),
        "relationship": relationship,
        "subject_alignment": alignment,
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
    findings: list[dict[str, object]] | None = None,
    status: str = "COMPLETED",
    provider: str = "fixture-a",
    model: str = "segment-fixture-a",
    schema_version: str = "segment-learning-review-v1",
    prompt_version: str = "segment-learning-review-prompt-v1",
    rubric_version: str = "evidence-rubric-v1",
    review_policy_version: str = "segment-review-policy-v1",
    output: dict[str, object] | None = None,
) -> SegmentLearningReview:
    review = SegmentLearningReview(
        student_id=student.id,
        session_id=learning_session.id,
        segment_id=segment.id,
        schema_version=schema_version,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
        review_policy_version=review_policy_version,
        provider=provider,
        model=model,
        status=status,
        output=(
            output
            if output is not None
            else ({"version": "segment-learning-review-v1", "findings": findings or []}
            if status == "COMPLETED"
            else None)
        ),
        completed_at=(datetime(2026, 8, 29, 12, tzinfo=UTC) if status == "COMPLETED" else None),
    )
    session.add(review)
    session.flush()
    return review


def _assert_no_activation(session: Session) -> None:
    assert session.query(IntelligenceProcessingRun).count() == 0
    assert session.query(IntelligenceSessionAuthority).count() == 0
    assert session.query(LearningEvent).count() == 0
    assert session.query(LearningEvidence).count() == 0
    assert session.query(CurrentLearningState).count() == 0
    assert session.query(LearnerPattern).count() == 0
    assert session.query(DecisionView).count() == 0


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


@pytest.mark.parametrize(
    ("status", "closed_at"),
    (("OPEN", datetime(2026, 8, 29, 12, tzinfo=UTC)), ("CLOSED", None)),
)
def test_only_durably_closed_sessions_can_finalize(
    factory: sessionmaker[Session],
    status: str,
    closed_at: datetime | None,
) -> None:
    """Catches an open or timestamp-incomplete Session activating intelligence."""

    finalize, blocked_error, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        learning_session.status = status
        learning_session.closed_at = closed_at
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[_finding(message)],
        )

        with pytest.raises(blocked_error):
            finalize(session, learning_session=learning_session)

        _assert_no_activation(session)


def test_closed_structurally_empty_segment_is_not_in_the_required_review_set(
    factory: sessionmaker[Session],
) -> None:
    """Catches structural emptiness becoming a missing semantic Review blocker."""

    finalize, _, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(reviewed_segment, message)] = _closed_lineage(session)
        reviewed_segment.closure_reason = "NEXT_SEGMENT_CREATED"
        empty_segment = LearningSegment(
            session_id=learning_session.id,
            sequence=2,
            closed_at=learning_session.closed_at,
            closure_reason="SESSION_CLOSED",
        )
        session.add(empty_segment)
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=reviewed_segment,
            findings=[_finding(message)],
        )

        outcome = finalize(session, learning_session=learning_session)

        assert outcome.event_count == 1
        assert outcome.processing_run.scope["required_segment_ids"] == [str(reviewed_segment.id)]
        assert session.query(SegmentLearningReview).filter_by(segment_id=empty_segment.id).count() == 0


@pytest.mark.parametrize(
    "blocked_review",
    (
        "missing",
        "PENDING",
        "RUNNING",
        "FAILED",
        "schema_version",
        "prompt_version",
        "rubric_version",
        "review_policy_version",
    ),
)
def test_incomplete_or_incompatible_required_review_set_blocks_all_activation(
    factory: sessionmaker[Session],
    blocked_review: str,
) -> None:
    """Catches one unsafe Segment activating a complete Session partially."""

    finalize, blocked_error, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, lineage = _closed_lineage(session, segment_count=2)
        first_segment, first_message = lineage[0]
        second_segment, second_message = lineage[1]
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=first_segment,
            findings=[_finding(first_message)],
        )
        if blocked_review != "missing":
            review_overrides: dict[str, object] = {}
            if blocked_review in {"PENDING", "RUNNING", "FAILED"}:
                review_overrides["status"] = blocked_review
            else:
                review_overrides[blocked_review] = f"incompatible-{blocked_review}-v9"
            _review(
                session,
                student=student,
                learning_session=learning_session,
                segment=second_segment,
                findings=[_finding(second_message)],
                **review_overrides,
            )

        with pytest.raises(blocked_error):
            finalize(session, learning_session=learning_session)

        _assert_no_activation(session)


def test_provider_and_model_differences_do_not_block_compatible_reviews(
    factory: sessionmaker[Session],
) -> None:
    """Catches execution provenance being mistaken for semantic compatibility."""

    finalize, _, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, lineage = _closed_lineage(session, segment_count=2)
        reviews = [
            _review(
                session,
                student=student,
                learning_session=learning_session,
                segment=segment,
                findings=[_finding(message, concept_ref=f"fractions_{index}")],
                provider=f"fixture-{index}",
                model=f"segment-model-{index}",
            )
            for index, (segment, message) in enumerate(lineage, start=1)
        ]

        outcome = finalize(session, learning_session=learning_session)
        events = session.query(LearningEvent).order_by(LearningEvent.segment_review_finding_index).all()

        assert outcome.event_count == 2
        assert {event.segment_review_id for event in events} == {review.id for review in reviews}
        assert {event.concept_ref for event in events} == {"fractions_1", "fractions_2"}


@pytest.mark.parametrize(
    "invalid_lineage",
    ("unknown_message", "cross_session_candidate", "review_session", "malformed_envelope"),
)
def test_strict_review_and_raw_lineage_validation_precedes_materialization(
    factory: sessionmaker[Session],
    invalid_lineage: str,
) -> None:
    """Catches persisted staged output bypassing strict source authority checks."""

    finalize, _, validation_error = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        finding = _finding(message)
        review_session = learning_session
        output: dict[str, object] | None = None
        if invalid_lineage == "unknown_message":
            finding["source_message_ids"] = [str(uuid4())]
        elif invalid_lineage == "cross_session_candidate":
            _, other_session, [(_, other_message)] = _closed_lineage(session, student=student)
            candidate = CandidateEvent(
                session_id=other_session.id,
                message_id=other_message.id,
                event_type="learning_attempt",
                concept_ref="equivalent_fractions",
                signal="other_session_hint",
                payload={"source_message_ids": [str(other_message.id)]},
            )
            session.add(candidate)
            session.flush()
            finding["candidate_event_ids"] = [str(candidate.id)]
        elif invalid_lineage == "review_session":
            _, review_session, _ = _closed_lineage(session, student=student)
        else:
            output = {
                "version": "segment-learning-review-v1",
                "findings": [finding],
                "unexpected": "not permitted",
            }
        _review(
            session,
            student=student,
            learning_session=review_session,
            segment=segment,
            findings=[finding],
            output=output,
        )

        with pytest.raises(validation_error):
            finalize(session, learning_session=learning_session)

        _assert_no_activation(session)


@pytest.mark.parametrize(
    "invalid_finding",
    ("ungrounded_misconception", "invented_teaching_method"),
)
def test_compiled_finding_validation_blocks_all_activation(
    factory: sessionmaker[Session],
    invalid_finding: str,
) -> None:
    """Catches persisted output bypassing the Reviewer's semantic grounding contract."""

    finalize, _, validation_error = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        unsafe = _finding(message)
        if invalid_finding == "ungrounded_misconception":
            unsafe.update(
                validated_event_type="misconception_signal",
                event_summary="The Student has a fraction misconception.",
                misconception_evidence=None,
            )
        else:
            tutor = LearningMessage(
                session_id=learning_session.id,
                segment_id=segment.id,
                role="tutor",
                content="Use fraction circles.",
                payload={
                    "teaching_method_id": "CONCRETE_EXAMPLE",
                    "teaching_method_registry_version": "teaching-method-registry-v1",
                },
                created_at=message.created_at - timedelta(seconds=1),
            )
            session.add(tutor)
            session.flush()
            unsafe.update(
                source_message_ids=[str(tutor.id), str(message.id)],
                teaching_method_id="WORKED_EXAMPLE",
                teaching_method_source_tutor_message_id=str(tutor.id),
            )
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[
                _finding(message, concept_ref="safe_fraction_observation"),
                unsafe,
            ],
        )

        with pytest.raises(validation_error):
            finalize(session, learning_session=learning_session)

        _assert_no_activation(session)


def test_only_same_session_findings_materialize_with_complete_provenance(
    factory: sessionmaker[Session],
) -> None:
    """Catches cross-subject staging being silently attributed to Math or suppressing safe findings."""

    finalize, _, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        candidate = CandidateEvent(
            session_id=learning_session.id,
            message_id=message.id,
            event_type="learning_attempt",
            concept_ref="equivalent_fractions",
            signal="fraction_explanation",
            payload={"source_message_ids": [str(message.id)]},
        )
        session.add(candidate)
        session.flush()
        safe = _finding(message, candidate_ids=[str(candidate.id)])
        review = _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[
                safe,
                _finding(
                    message,
                    alignment="POSSIBLE_CROSS_SUBJECT",
                    concept_ref="plant_cells",
                    summary="A possible Science observation remains staged.",
                ),
                _finding(
                    message,
                    alignment="UNCERTAIN",
                    concept_ref="uncertain_topic",
                    summary="An uncertain observation remains staged.",
                ),
            ],
        )

        outcome = finalize(session, learning_session=learning_session)
        event = session.query(LearningEvent).one()
        evidence = session.query(LearningEvidence).one()

        assert outcome.event_count == 1
        assert outcome.withheld_finding_count == 2
        assert event.processing_run_id == outcome.processing_run.id
        assert event.session_id == learning_session.id
        assert event.segment_id == segment.id
        assert event.segment_review_id == review.id
        assert event.segment_review_finding_index == 0
        assert event.candidate_event_id == candidate.id
        assert event.candidate_event_ids == [str(candidate.id)]
        assert event.source_message_id == message.id
        assert event.source_message_ids == [str(message.id)]
        assert event.subject == "MATH"
        assert evidence.source_ref == (
            f"session:{learning_session.id}:segment:{segment.id}:review:{review.id}:finding:0"
        )
        assert session.query(LearningEvent).filter_by(concept_ref="plant_cells").count() == 0
        assert session.query(LearningEvent).filter_by(concept_ref="uncertain_topic").count() == 0


def test_candidate_free_finding_reaches_authority_projections_and_runtime_card(
    factory: sessionmaker[Session],
) -> None:
    """Catches Candidate joins silently deleting valid Review-authorized Evidence."""

    from services.intelligence.card import build_learner_intelligence_card

    finalize, _, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        review = _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[_finding(message)],
        )

        outcome = finalize(session, learning_session=learning_session)
        event = session.query(LearningEvent).one()
        evidence = session.query(LearningEvidence).one()
        state = session.query(CurrentLearningState).filter_by(state_type="active_difficulty").one()
        pattern = session.query(LearnerPattern).filter_by(pattern_type="support_need").one()
        views = session.query(DecisionView).filter_by(concept_ref="equivalent_fractions").all()
        card = build_learner_intelligence_card(
            session,
            student_id=student.id,
            subject="MATH",
            question="Can we practice equivalent fractions?",
        )

        assert outcome.authority.reprocess_run_id is None
        assert outcome.authority.evidence_processing_run_id == outcome.processing_run.id
        assert event.candidate_event_id is None
        assert event.candidate_event_ids == []
        assert event.segment_review_id == review.id
        assert evidence.id in authoritative_evidence_ids(session, student_id=student.id)
        assert str(evidence.id) in state.evidence_refs
        assert pattern.support_count == 1
        assert len(views) == 4
        assert all(str(evidence.id) in view.evidence_ids for view in views)
        assert state.id in card.debug.selected_source_ids


def test_candidate_free_concept_patterns_never_promote_an_invented_context(
    factory: sessionmaker[Session],
) -> None:
    """Catches Segment provenance being mistaken for semantic context or subject evidence."""

    finalize, _, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, lineage = _closed_lineage(session, segment_count=3)
        concepts = {
            "equivalent_fractions",
            "fraction_comparison",
            "fraction_addition",
        }
        for (segment, message), concept_ref in zip(lineage, sorted(concepts), strict=True):
            _review(
                session,
                student=student,
                learning_session=learning_session,
                segment=segment,
                findings=[_finding(message, concept_ref=concept_ref)],
            )

        finalize(session, learning_session=learning_session)

        patterns = session.query(LearnerPattern).filter_by(pattern_type="support_need").all()
        links = session.query(PatternEvidence).all()
        assert {pattern.scope["scope_type"] for pattern in patterns} == {"concept"}
        assert {pattern.scope["concept_ref"] for pattern in patterns} == concepts
        assert len(links) == 3
        assert all(link.context_ref != "math_practice" for link in links)


def test_empty_review_finalizes_once_without_manufacturing_learner_memory(
    factory: sessionmaker[Session],
) -> None:
    """Catches a valid zero-Finding review being treated as failure or fake Evidence."""

    finalize, _, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, _)] = _closed_lineage(session)
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[],
        )

        first = finalize(session, learning_session=learning_session)
        second = finalize(session, learning_session=learning_session)

        assert first.processing_run.id == second.processing_run.id
        assert first.authority.id == second.authority.id
        assert first.event_count == second.event_count == 0
        assert first.evidence_count == second.evidence_count == 0
        assert session.query(IntelligenceProcessingRun).count() == 1
        assert session.query(IntelligenceSessionAuthority).count() == 1
        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert session.query(CurrentLearningState).count() == 0
        assert session.query(LearnerPattern).count() == 0
        assert session.query(DecisionView).count() == 0


def test_downstream_failure_rolls_back_the_entire_finalization_savepoint(
    factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches projection failure leaving an authoritative partial processing run."""

    module = import_module("services.intelligence.session_finalization")
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[_finding(message)],
        )

        def fail_patterns(*args: object, **kwargs: object) -> list[object]:
            del args, kwargs
            raise RuntimeError("forced downstream failure")

        monkeypatch.setattr(module, "apply_processing_run_patterns", fail_patterns)
        with pytest.raises(RuntimeError, match="forced downstream failure"):
            module.finalize_closed_session(session, learning_session=learning_session)

        _assert_no_activation(session)


def test_finalization_worker_validates_lineage_and_activates_without_a_model_call(
    factory: sessionmaker[Session],
) -> None:
    """Catches the deterministic finalization job being unregistered or model-gated."""

    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[_finding(message)],
        )
        job = enqueue_session_intelligence_finalization_if_ready(
            session,
            learning_session=learning_session,
        )
        assert job is not None
        job_id = job.id

    gateway_calls: list[str] = []

    def forbidden_gateway(session: Session) -> object:
        del session
        gateway_calls.append("called")
        raise AssertionError("finalization must not create a model gateway")

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        evidence_gateway_factory=forbidden_gateway,  # type: ignore[arg-type]
    )

    assert run_once(factory, registry, worker_id="finalization-worker").value == "COMPLETED"

    with factory() as session:
        persisted = session.get(Job, job_id)
        assert persisted is not None
        processing_run_id = session.query(IntelligenceProcessingRun.id).scalar()
        assert persisted.result == {
            "session_id": str(learning_session.id),
            "processing_run_id": str(processing_run_id),
            "event_count": session.query(LearningEvent).count(),
            "evidence_count": session.query(LearningEvidence).count(),
            "withheld_finding_count": 0,
            "current_state_count": session.query(CurrentLearningState).count(),
            "pattern_count": session.query(LearnerPattern).count(),
            "decision_view_count": session.query(DecisionView).count(),
            "reused": False,
        }
        assert session.query(IntelligenceSessionAuthority).count() == 1
        assert gateway_calls == []


@pytest.mark.parametrize("invalid_kind", ("wrong_student", "wrong_pipeline", "missing_review"))
def test_finalization_worker_refuses_early_or_invalid_payload_without_partial_activation(
    factory: sessionmaker[Session],
    invalid_kind: str,
) -> None:
    """Catches a forged or early job bypassing finalization readiness."""

    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(session)
        if invalid_kind != "missing_review":
            _review(
                session,
                student=student,
                learning_session=learning_session,
                segment=segment,
                findings=[_finding(message)],
            )
        payload = {
            "session_id": str(learning_session.id),
            "student_id": str(uuid4()) if invalid_kind == "wrong_student" else str(student.id),
            "intelligence_pipeline": (
                "legacy-session-evidence-v1"
                if invalid_kind == "wrong_pipeline"
                else "segment-finalization-v1"
            ),
        }
        job = enqueue_job(
            session,
            job_type=SESSION_INTELLIGENCE_FINALIZE_JOB,
            payload=payload,
            idempotency_key=f"invalid-finalization:{invalid_kind}:{learning_session.id}",
        )
        job_id = job.id

    registry = JobHandlerRegistry()
    register_intelligence_handlers(registry, session_factory=factory)

    assert run_once(factory, registry, worker_id="finalization-worker").value == "PENDING"

    with factory() as session:
        failed = session.get(Job, job_id)
        assert failed is not None and failed.attempt_count == 1
        _assert_no_activation(session)


def test_legacy_consolidation_handler_refuses_new_pipeline_without_calling_gateway(
    factory: sessionmaker[Session],
) -> None:
    """Catches a stale legacy job executing against a segment-finalization Session."""

    with factory.begin() as session:
        _, learning_session, _ = _closed_lineage(session)
        job = enqueue_job(
            session,
            job_type=SESSION_CONSOLIDATION_JOB,
            payload={"session_id": str(learning_session.id)},
            idempotency_key=f"stale-legacy:{learning_session.id}",
        )
        job_id = job.id

    gateway_calls: list[str] = []

    def forbidden_gateway(session: Session) -> object:
        del session
        gateway_calls.append("called")
        raise AssertionError("legacy gateway must not be created")

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        evidence_gateway_factory=forbidden_gateway,  # type: ignore[arg-type]
    )

    assert run_once(factory, registry, worker_id="legacy-worker").value == "PENDING"

    with factory() as session:
        failed = session.get(Job, job_id)
        assert failed is not None and failed.attempt_count == 1
        _assert_no_activation(session)
        assert gateway_calls == []


def test_legacy_session_is_refused_without_changing_legacy_authority(
    factory: sessionmaker[Session],
) -> None:
    """Catches Task 3 stealing historical Sessions from legacy consolidation/reprocess paths."""

    finalize, blocked_error, _ = _finalization_api()
    with factory.begin() as session:
        student, learning_session, [(segment, message)] = _closed_lineage(
            session,
            pipeline="legacy-session-evidence-v1",
        )
        _review(
            session,
            student=student,
            learning_session=learning_session,
            segment=segment,
            findings=[_finding(message)],
        )

        with pytest.raises(blocked_error):
            finalize(session, learning_session=learning_session)

        _assert_no_activation(session)


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
