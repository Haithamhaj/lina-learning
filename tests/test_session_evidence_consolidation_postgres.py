"""PostgreSQL contracts for source-grounded session evidence consolidation."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import services.intelligence.consolidation as consolidation_module
from services.intelligence.consolidation import (
    ConsolidationError,
    ConsolidationValidationError,
    consolidate_closed_session,
)
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.model_gateway.lineage import derived_objects_for_execution, executions_for_processing_run, executions_for_student
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    AIExecution,
    CurrentLearningState,
    DecisionView,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    LearningSession,
    Job,
    IntelligenceProcessingRun,
    ModelTask,
    Student,
    User,
)
from services.platform.jobs import enqueue_job
from services.tutor.session_lifecycle import SESSION_CONSOLIDATION_JOB
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for session evidence tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


class _Provider:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls = 0
        self.payloads: list[dict[str, object]] = []

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        self.calls += 1
        self.payloads.append(payload)
        return ModelResult(output=self.output, input_tokens=12, output_tokens=8)


def _closed_session(session: Session) -> LearningSession:
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
        closed_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    session.add(learning_session)
    session.flush()
    return learning_session


def _candidate(
    session: Session,
    *,
    learning_session: LearningSession,
    event_type: str = "independent_success",
    signal: str = "solved_independently",
    observed_student_outcome: str | None = None,
    created_at: datetime | None = None,
) -> tuple[CandidateEvent, LearningMessage]:
    student_message = LearningMessage(
        session_id=learning_session.id,
        role="student",
        content="One half equals two fourths because both name the same amount.",
        payload={"source": "fixture"},
    )
    tutor_message = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Explain why those fractions have the same value.",
        payload={"source": "fixture"},
    )
    session.add_all([student_message, tutor_message])
    session.flush()
    candidate = CandidateEvent(
        session_id=learning_session.id,
        message_id=student_message.id,
        event_type=event_type,
        concept_ref="equivalent_fractions",
        signal=signal,
        payload={
            "candidate_schema_version": "candidate-event-v1",
            "summary": "The Student independently explained equivalent fractions.",
            "school_or_extended": "school",
            "source_message_ids": [str(student_message.id)],
            "subject": "MATH",
            "observed_student_outcome": observed_student_outcome,
        },
        created_at=created_at or datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    session.add(candidate)
    session.flush()
    return candidate, student_message


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


def _event_output(
    candidate: CandidateEvent,
    source_message: LearningMessage,
    *,
    dimensions: dict[str, str],
    event_type: str | None = None,
    summary: str = "The Student demonstrated a contextual learning event.",
    transfer_context: str = "not_tested",
    retention_context: str = "not_tested",
) -> dict[str, object]:
    return {
        "version": "session-evidence-v1",
        "events": [
            {
                "candidate_event_id": str(candidate.id),
                "source_message_ids": [str(source_message.id)],
                "subject": "MATH",
                "concept_ref": "equivalent_fractions",
                "event_type": event_type or candidate.event_type,
                "event_summary": summary,
                "school_or_extended": "school",
                "transfer_context": transfer_context,
                "retention_context": retention_context,
                "dimensions": dimensions,
                "relationship": "insufficient",
            }
        ],
    }


def _prior_validated_evidence(
    session: Session,
    *,
    learning_session: LearningSession,
    candidate: CandidateEvent,
    source_message: LearningMessage,
    understanding: str,
) -> LearningEvidence:
    """Persist an already-completed, source-linked Evidence record from a prior session."""

    run = IntelligenceProcessingRun(
        student_id=learning_session.student_id,
        rubric_version="evidence-rubric-v1",
        policy_version="session-consolidation-policy-v1",
        status="COMPLETED",
        scope={"session_id": str(learning_session.id)},
    )
    session.add(run)
    session.flush()
    event = LearningEvent(
        processing_run_id=run.id,
        session_id=learning_session.id,
        candidate_event_id=candidate.id,
        subject="MATH",
        concept_ref="equivalent_fractions",
        event_type=candidate.event_type,
        description="Prior validated concept evidence.",
        source_message_id=source_message.id,
    )
    session.add(event)
    session.flush()
    evidence = LearningEvidence(
        event_id=event.id,
        concept_ref="equivalent_fractions",
        dimensions=_dimensions(understanding=understanding),
        relationship="supports",
        source_ref=f"session:{learning_session.id}:candidate:{candidate.id}:message:{source_message.id}",
    )
    session.add(evidence)
    session.flush()
    return evidence


def test_closed_session_uses_one_source_grounded_model_call_and_never_creates_later_intelligence(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(session, learning_session=learning_session)
        provider = _Provider(
            {
                "version": "session-evidence-v1",
                "events": [
                    {
                        "candidate_event_id": str(candidate.id),
                        "source_message_ids": [str(source_message.id)],
                        "subject": "MATH",
                        "concept_ref": "equivalent_fractions",
                        "event_type": "independent_success",
                        "event_summary": "The Student explained that one half and two fourths name the same amount without instructional support.",
                        "school_or_extended": "school",
                        "dimensions": _dimensions(
                            understanding="demonstrated",
                            independence="independent",
                            reasoning_demonstration="coherent",
                        ),
                        "relationship": "insufficient",
                    }
                ],
            }
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        outcome = consolidate_closed_session(
            session,
            learning_session=learning_session,
            gateway=gateway,
        )

        event = session.query(LearningEvent).one()
        evidence = session.query(LearningEvidence).one()
        assert provider.calls == 1
        assert outcome.processing_run.status == "COMPLETED"
        assert event.candidate_event_id == candidate.id
        assert event.source_message_id == source_message.id
        assert evidence.source_ref == f"session:{learning_session.id}:candidate:{candidate.id}:message:{source_message.id}"
        assert evidence.dimensions["independence"] == "independent"
        assert provider.payloads[0]["response_schema"]["name"] == "session_evidence_v1"
        assert str(source_message.id) in str(provider.payloads[0]["input"])
        execution = session.query(AIExecution).filter_by(task="session_evidence").one()
        assert (execution.provider, execution.model, execution.success) == (
            "fixture",
            "fixture-evidence",
            True,
        )
        assert execution.student_id == learning_session.student_id
        assert execution.learning_session_id == learning_session.id
        assert execution.intelligence_processing_run_id == outcome.processing_run.id
        assert execution.source_candidate_event_ids == [str(candidate.id)]
        assert executions_for_student(session, student_id=learning_session.student_id) == [execution]
        assert executions_for_processing_run(session, processing_run_id=outcome.processing_run.id, kind="intelligence", student_id=learning_session.student_id) == [execution]
        derived = derived_objects_for_execution(session, execution=execution)
        assert derived.learning_event_ids == (event.id,)
        assert derived.learning_evidence_ids == (evidence.id,)
        assert session.query(CurrentLearningState).count() == 0
        assert session.query(LearnerPattern).count() == 0
        assert session.query(LearnerIntelligenceCard).count() == 0


def test_session_consolidation_job_uses_the_closed_session_evidence_handler(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(session, learning_session=learning_session)
        provider = _Provider(
            {
                "version": "session-evidence-v1",
                "events": [
                    {
                        "candidate_event_id": str(candidate.id),
                        "source_message_ids": [str(source_message.id)],
                        "subject": "MATH",
                        "concept_ref": "equivalent_fractions",
                        "event_type": "independent_success",
                        "event_summary": "The Student explained equivalent fractions independently.",
                        "school_or_extended": "school",
                        "dimensions": _dimensions(
                            understanding="not_demonstrated",
                            independence="substantial_support",
                        ),
                        "relationship": "insufficient",
                    }
                ],
            }
        )
        job_id = enqueue_job(
            session,
            job_type=SESSION_CONSOLIDATION_JOB,
            payload={"session_id": str(learning_session.id)},
        ).id

    def gateway_factory(worker_session: Session) -> ModelGateway:
        return ModelGateway(
            worker_session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=postgres_session_factory,
        evidence_gateway_factory=gateway_factory,
    )

    assert run_once(postgres_session_factory, registry, worker_id="evidence-worker") == "COMPLETED"
    with postgres_session_factory() as session:
        assert session.get(type(learning_session), learning_session.id).status == "CLOSED"
        assert session.query(LearningEvent).count() == 1
        assert session.query(LearningEvidence).count() == 1
        assert session.query(CurrentLearningState).filter_by(
            state_type="active_difficulty",
            status="ACTIVE",
        ).count() == 1
        assert session.query(DecisionView).count() == 4
        assert provider.calls == 1
        job = session.get(Job, job_id)
        assert job is not None and job.status == "COMPLETED"


def test_greeting_only_closed_session_completes_without_model_call_or_derived_rows(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        session.add_all(
            [
                LearningMessage(session_id=learning_session.id, role="student", content="Hello!", payload={}),
                LearningMessage(session_id=learning_session.id, role="tutor", content="Hi Lina!", payload={}),
            ]
        )
        provider = _Provider({"version": "session-evidence-v1", "events": []})
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        outcome = consolidate_closed_session(
            session,
            learning_session=learning_session,
            gateway=gateway,
        )

        assert outcome.event_count == 0
        assert outcome.model_called is False
        assert provider.calls == 0
        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0


def test_open_session_is_rejected_before_any_evidence_model_call(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        learning_session.status = "OPEN"
        provider = _Provider({"version": "session-evidence-v1", "events": []})
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationError, match="CLOSED"):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert provider.calls == 0
        assert session.query(IntelligenceProcessingRun).count() == 0


@pytest.mark.parametrize(
    ("event_type", "dimensions", "transfer_context", "expected"),
    [
        (
            "guided_success",
            _dimensions(understanding="demonstrated", independence="moderate_support"),
            "not_tested",
            {"independence": "moderate_support"},
        ),
        (
            "misconception_signal",
            _dimensions(understanding="not_demonstrated", reasoning_demonstration="fragmented"),
            "not_tested",
            {"understanding": "not_demonstrated"},
        ),
        (
            "self_correction",
            _dimensions(self_correction="self_initiated"),
            "not_tested",
            {"self_correction": "self_initiated"},
        ),
        (
            "self_correction",
            _dimensions(self_correction="prompted"),
            "not_tested",
            {"self_correction": "prompted"},
        ),
        (
            "explanation_attempt",
            _dimensions(reasoning_demonstration="coherent"),
            "not_tested",
            {"reasoning_demonstration": "coherent"},
        ),
        (
            "transfer_attempt",
            _dimensions(transfer="not_tested"),
            "near_identical",
            {"transfer": "not_tested"},
        ),
        (
            "transfer_attempt",
            _dimensions(transfer="demonstrated", understanding="demonstrated"),
            "meaningfully_changed",
            {"transfer": "demonstrated"},
        ),
        (
            "strategy_outcome",
            _dimensions(strategy_effectiveness="helped"),
            "not_tested",
            {"strategy_effectiveness": "helped"},
        ),
    ],
)
def test_golden_rubric_scenarios_preserve_only_contextual_supported_values(
    postgres_session_factory: sessionmaker[Session],
    event_type: str,
    dimensions: dict[str, str],
    transfer_context: str,
    expected: dict[str, str],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type=event_type,
            observed_student_outcome=("Lina correctly applied the visual model." if event_type == "strategy_outcome" else None),
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=dimensions,
                transfer_context=transfer_context,
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        evidence = session.query(LearningEvidence).one()
        for key, value in expected.items():
            assert evidence.dimensions[key] == value


def test_strategy_without_observable_student_outcome_cannot_become_effectiveness_evidence(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type="learning_attempt",
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(strategy_effectiveness="helped"),
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError, match="Strategy effectiveness"):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0


@pytest.mark.parametrize(
    ("event_type", "dimensions", "transfer_context", "summary", "error"),
    [
        (
            "guided_success",
            _dimensions(understanding="demonstrated", independence="independent"),
            "not_tested",
            "The Student reached the answer after guided work.",
            "Guided success",
        ),
        (
            "independent_success",
            _dimensions(understanding="strong_demonstration", independence="full_teaching"),
            "not_tested",
            "The Student repeated the Tutor explanation.",
            "Strong understanding",
        ),
        (
            "transfer_attempt",
            _dimensions(transfer="demonstrated"),
            "near_identical",
            "The Student completed a near-identical second problem.",
            "Transfer",
        ),
        (
            "misconception_signal",
            _dimensions(understanding="partial"),
            "not_tested",
            "The Student is a visual learner.",
            "contract",
        ),
    ],
)
def test_unsupported_inferences_are_rejected_before_any_evidence_persists(
    postgres_session_factory: sessionmaker[Session],
    event_type: str,
    dimensions: dict[str, str],
    transfer_context: str,
    summary: str,
    error: str,
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type=event_type,
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=dimensions,
                transfer_context=transfer_context,
                summary=summary,
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError, match=error):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0


def test_immediate_repeat_cannot_claim_retention(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type="retention_check",
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(retention="retained"),
                retention_context="immediate",
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError, match="Retention"):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvidence).count() == 0


def test_old_candidate_only_cannot_support_a_retention_claim(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        prior_session = _closed_session(session)
        _candidate(
            session,
            learning_session=prior_session,
            created_at=now - timedelta(days=8),
        )
        learning_session = LearningSession(
            student_id=prior_session.student_id,
            subject="MATH",
            status="CLOSED",
            closed_at=now,
        )
        session.add(learning_session)
        session.flush()
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type="retention_check",
            created_at=now,
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(retention="retained", understanding="demonstrated"),
                retention_context="meaningfully_delayed",
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError, match="Retention"):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvidence).count() == 0


def test_old_misconception_evidence_cannot_support_a_retention_claim(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        prior_session = _closed_session(session)
        prior_candidate, prior_message = _candidate(
            session,
            learning_session=prior_session,
            event_type="misconception_signal",
            created_at=now - timedelta(days=8),
        )
        _prior_validated_evidence(
            session,
            learning_session=prior_session,
            candidate=prior_candidate,
            source_message=prior_message,
            understanding="not_demonstrated",
        )
        learning_session = LearningSession(
            student_id=prior_session.student_id,
            subject="MATH",
            status="CLOSED",
            closed_at=now,
        )
        session.add(learning_session)
        session.flush()
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type="retention_check",
            created_at=now,
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(retention="retained", understanding="demonstrated"),
                retention_context="meaningfully_delayed",
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError, match="Retention"):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvidence).count() == 1


def test_prior_demonstrated_understanding_allows_a_delayed_retention_check(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        prior_session = _closed_session(session)
        prior_session.closed_at = now - timedelta(days=8)
        prior_candidate, prior_message = _candidate(
            session,
            learning_session=prior_session,
            created_at=now - timedelta(days=8),
        )
        _prior_validated_evidence(
            session,
            learning_session=prior_session,
            candidate=prior_candidate,
            source_message=prior_message,
            understanding="demonstrated",
        )
        learning_session = LearningSession(
            student_id=prior_session.student_id,
            subject="MATH",
            status="CLOSED",
            closed_at=now,
        )
        session.add(learning_session)
        session.flush()
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type="retention_check",
            created_at=now,
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(retention="retained", understanding="demonstrated"),
                retention_context="meaningfully_delayed",
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        evidence = session.query(LearningEvidence).all()
        assert len(evidence) == 2
        assert any(item.dimensions["retention"] == "retained" for item in evidence)


def test_immediate_prior_demonstrated_understanding_cannot_support_retention(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        prior_session = _closed_session(session)
        prior_session.closed_at = now - timedelta(days=1)
        prior_candidate, prior_message = _candidate(
            session,
            learning_session=prior_session,
            created_at=now - timedelta(days=1),
        )
        _prior_validated_evidence(
            session,
            learning_session=prior_session,
            candidate=prior_candidate,
            source_message=prior_message,
            understanding="demonstrated",
        )
        learning_session = LearningSession(
            student_id=prior_session.student_id,
            subject="MATH",
            status="CLOSED",
            closed_at=now,
        )
        session.add(learning_session)
        session.flush()
        candidate, source_message = _candidate(
            session,
            learning_session=learning_session,
            event_type="retention_check",
            created_at=now,
        )
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(retention="retained", understanding="demonstrated"),
                retention_context="meaningfully_delayed",
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError, match="Retention"):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvidence).count() == 1


def test_malformed_output_is_rejected_without_partial_events_or_evidence(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(session, learning_session=learning_session)
        output = _event_output(
            candidate,
            source_message,
            dimensions=_dimensions(understanding="demonstrated"),
        )
        output["events"][0]["dimensions"]["understanding"] = "mastered"
        provider = _Provider(output)
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        with pytest.raises(ConsolidationValidationError):
            consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert session.query(IntelligenceProcessingRun).one().status == "FAILED"


def test_completed_consolidation_is_idempotent_and_calls_the_model_once(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(session, learning_session=learning_session)
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(understanding="demonstrated", independence="independent"),
            )
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

        first = consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)
        second = consolidate_closed_session(session, learning_session=learning_session, gateway=gateway)

        assert first.model_called is True
        assert second.model_called is False
        assert provider.calls == 1
        assert session.query(IntelligenceProcessingRun).count() == 1
        assert session.query(LearningEvent).count() == 1
        assert session.query(LearningEvidence).count() == 1


@pytest.mark.parametrize("changed_identity", ["model"])
def test_changed_interpretation_identity_creates_a_new_queryable_processing_version(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    changed_identity: str,
) -> None:
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(session, learning_session=learning_session)
        provider = _Provider(
            _event_output(
                candidate,
                source_message,
                dimensions=_dimensions(understanding="demonstrated", independence="independent"),
            )
        )
        first_gateway = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence-v1")},
            providers={"fixture": provider},
        )
        first = consolidate_closed_session(
            session,
            learning_session=learning_session,
            gateway=first_gateway,
        )

        if changed_identity == "prompt":
            monkeypatch.setattr(
                consolidation_module,
                "SESSION_EVIDENCE_PROMPT_VERSION",
                "session-evidence-prompt-v2",
            )
            second_gateway = first_gateway
        elif changed_identity == "schema":
            monkeypatch.setattr(
                consolidation_module,
                "SESSION_EVIDENCE_SCHEMA_VERSION",
                "session-evidence-v2",
            )
            second_gateway = first_gateway
        else:
            second_gateway = ModelGateway(
                session,
                routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence-v2")},
                providers={"fixture": provider},
            )

        second = consolidate_closed_session(
            session,
            learning_session=learning_session,
            gateway=second_gateway,
        )

        runs = session.query(IntelligenceProcessingRun).order_by(IntelligenceProcessingRun.created_at).all()
        assert first.processing_run.id != second.processing_run.id
        assert first.processing_run.id in {run.id for run in runs}
        assert len(runs) == 2
        assert session.query(LearningEvent).filter_by(processing_run_id=first.processing_run.id).count() == 1
        assert session.query(LearningEvidence).count() == 2
        assert provider.calls == 2


def test_failed_job_retry_reuses_its_processing_version_without_duplicate_rows(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    with postgres_session_factory.begin() as session:
        learning_session = _closed_session(session)
        candidate, source_message = _candidate(session, learning_session=learning_session)
        provider = _Provider({"version": "session-evidence-v1", "events": [{"bad": "output"}]})
        enqueue_job(
            session,
            job_type=SESSION_CONSOLIDATION_JOB,
            payload={"session_id": str(learning_session.id)},
            run_after=now,
        )

    def gateway_factory(worker_session: Session) -> ModelGateway:
        return ModelGateway(
            worker_session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence")},
            providers={"fixture": provider},
        )

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=postgres_session_factory,
        evidence_gateway_factory=gateway_factory,
    )

    assert run_once(postgres_session_factory, registry, worker_id="retry-worker", now=now) == "PENDING"
    with postgres_session_factory() as session:
        assert session.query(IntelligenceProcessingRun).one().status == "FAILED"
        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0

    provider.output = _event_output(
        candidate,
        source_message,
        dimensions=_dimensions(understanding="demonstrated", independence="independent"),
    )
    assert run_once(
        postgres_session_factory,
        registry,
        worker_id="retry-worker",
        now=now + timedelta(minutes=1),
    ) == "COMPLETED"
    with postgres_session_factory() as session:
        assert provider.calls == 2
        assert session.query(IntelligenceProcessingRun).count() == 1
        assert session.query(IntelligenceProcessingRun).one().status == "COMPLETED"
        assert session.query(LearningEvent).count() == 1
        assert session.query(LearningEvidence).count() == 1
