"""TASK-026 contracts for bounded, versioned intelligence reprocessing."""

from __future__ import annotations

import os
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.reprocess import (
    EvidenceVersionSelection,
    IntelligenceReprocessRequest,
    INTELLIGENCE_REPROCESS_JOB,
    activate_reprocess_scope,
    enqueue_intelligence_reprocess,
    preview_intelligence_reprocess,
)
from services.intelligence.card import build_learner_intelligence_card
from services.intelligence.current_state import CurrentStatePolicyError
from services.intelligence.consolidation import EvidenceContractError
from services.intelligence.decisions import DecisionViewPolicyError
from services.intelligence.patterns import PatternPolicyError
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    IntelligenceReprocessRun,
    IntelligenceReprocessSession,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearnerPattern,
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


def _evidence_identity(*, model: str = "fixture-evidence") -> EvidenceVersionSelection:
    return EvidenceVersionSelection(provider="fixture", model=model)


def test_bounded_preview_and_same_version_request_are_idempotent(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2026, 1, 10, tzinfo=UTC))
        other = _closed_session(session, closed_at=datetime(2026, 2, 10, tzinfo=UTC))
        request = IntelligenceReprocessRequest(
            student_id=target.student_id,
            subject="MATH",
            session_ids=(target.id,),
            evidence=_evidence_identity(),
        )

        preview = preview_intelligence_reprocess(session, request=request)
        first = enqueue_intelligence_reprocess(session, request=request)
        second = enqueue_intelligence_reprocess(session, request=request)
        different_model = enqueue_intelligence_reprocess(
            session,
            request=IntelligenceReprocessRequest(
                student_id=target.student_id,
                subject="MATH",
                session_ids=(target.id,),
                evidence=_evidence_identity(model="fixture-evidence-v2"),
            ),
        )

        assert preview.selected_session_ids == (target.id,)
        assert preview.selected_session_count == 1
        assert preview.sessions_needing_processing == 1
        assert first.job.id == second.job.id
        assert first.reprocess_run.id == second.reprocess_run.id
        assert first.reprocess_run.id != different_model.reprocess_run.id
        assert first.reprocess_run.version_set["evidence"]["provider"] == "fixture"
        assert first.reprocess_run.version_set["evidence"]["model"] == "fixture-evidence"
        assert session.get(LearningSession, other.id) is not None


def test_date_range_scope_excludes_other_sessions_and_preview_writes_nothing(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        first = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        middle = _closed_session(session, closed_at=datetime(2025, 2, 10, tzinfo=UTC), student=session.get(Student, first.student_id))
        _closed_session(session, closed_at=datetime(2025, 3, 10, tzinfo=UTC), student=session.get(Student, first.student_id))
        request = IntelligenceReprocessRequest(
            student_id=first.student_id,
            evidence=_evidence_identity(),
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
        base = IntelligenceReprocessRequest(student_id=target.student_id, session_ids=(target.id,), evidence=_evidence_identity())
        changed = IntelligenceReprocessRequest(
            student_id=target.student_id,
            session_ids=(target.id,),
            evidence=EvidenceVersionSelection(provider="fixture", model="fixture-evidence", prompt_version="unsupported-prompt-v9"),
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
            evidence=_evidence_identity(),
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
        original_authoritative_run_id = authority.evidence_processing_run_id

    with factory.begin() as session:
        mismatched = enqueue_intelligence_reprocess(
            session,
            request=IntelligenceReprocessRequest(
                student_id=target.student_id,
                subject="MATH",
                session_ids=(target.id,),
                evidence=_evidence_identity(model="fixture-evidence-v2"),
            ),
        )
    assert run_once(factory, registry, worker_id="reprocess-worker") == "PENDING"
    with factory() as session:
        authority = session.query(IntelligenceSessionAuthority).one()
        failed_run = session.get(IntelligenceReprocessRun, mismatched.reprocess_run.id)
        assert authority.evidence_processing_run_id == original_authoritative_run_id
        assert failed_run is not None and failed_run.status == "PARTIAL_FAILED"


def test_preview_reuses_exact_completed_evidence_version_without_writing(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        request = IntelligenceReprocessRequest(student_id=target.student_id, session_ids=(target.id,), evidence=_evidence_identity())
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
                evidence=_evidence_identity(model="fixture-evidence-v2"),
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
            evidence=_evidence_identity(),
            current_state_policy_version="current-state-policy-v9",
        )

        with pytest.raises(CurrentStatePolicyError):
            enqueue_intelligence_reprocess(session, request=request)
        assert session.query(IntelligenceReprocessRun).count() == 0


@pytest.mark.parametrize(
    ("field", "error"),
    [("pattern_policy_version", PatternPolicyError), ("decision_policy_version", DecisionViewPolicyError)],
)
def test_unsupported_downstream_policy_is_rejected_before_reprocess(
    factory: sessionmaker[Session],
    field: str,
    error: type[Exception],
) -> None:
    with factory.begin() as session:
        target = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        request = IntelligenceReprocessRequest(
            student_id=target.student_id,
            session_ids=(target.id,),
            evidence=_evidence_identity(),
            **{field: "unsupported-policy-v99"},
        )

        with pytest.raises(error):
            enqueue_intelligence_reprocess(session, request=request)
        assert session.query(IntelligenceReprocessRun).count() == 0


def test_partial_multi_session_reprocess_keeps_the_previous_scope_authority(
    factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with factory.begin() as session:
        first = _closed_session(session, closed_at=datetime(2025, 1, 10, tzinfo=UTC))
        student = session.get(Student, first.student_id)
        assert student is not None
        second = _closed_session(session, closed_at=datetime(2025, 1, 11, tzinfo=UTC), student=student)
        third = _closed_session(session, closed_at=datetime(2025, 1, 12, tzinfo=UTC), student=student)
        old_reprocess = IntelligenceReprocessRun(
            student_id=student.id,
            idempotency_key="old-scope-authority",
            scope={"session_ids": [str(first.id), str(second.id), str(third.id)]},
            version_set={},
            status="COMPLETED",
        )
        session.add(old_reprocess)
        session.flush()
        old_runs: dict[object, IntelligenceProcessingRun] = {}
        for learning_session in (first, second, third):
            old_run = IntelligenceProcessingRun(
                student_id=student.id,
                rubric_version="evidence-rubric-v1",
                policy_version="session-consolidation-policy-v1",
                status="COMPLETED",
                scope={"session_id": str(learning_session.id)},
            )
            session.add(old_run)
            session.flush()
            old_runs[learning_session.id] = old_run
            session.add(
                IntelligenceSessionAuthority(
                    student_id=student.id,
                    session_id=learning_session.id,
                    reprocess_run_id=old_reprocess.id,
                    evidence_processing_run_id=old_run.id,
                )
            )
        old_state = CurrentLearningState(
            student_id=student.id,
            processing_run_id=old_runs[first.id].id,
            subject="MATH",
            concept_ref="fractions",
            state_type="active_difficulty",
            detail="Fractions currently needs support.",
            status="ACTIVE",
            policy_version="current-state-policy-v1",
            evidence_refs=[],
            detected_at=first.closed_at,
            updated_at=first.closed_at,
        )
        session.add(old_state)
        raw_candidate_signals = {
            candidate.id: candidate.signal
            for candidate in session.query(CandidateEvent).filter(
                CandidateEvent.session_id.in_((first.id, second.id, third.id))
            )
        }
        raw_messages = {
            message.id: message.content
            for message in session.query(LearningMessage).filter(
                LearningMessage.session_id.in_((first.id, second.id, third.id))
            )
        }
        queued = enqueue_intelligence_reprocess(
            session,
            request=IntelligenceReprocessRequest(
                student_id=student.id,
                subject="MATH",
                session_ids=(first.id, second.id, third.id),
                evidence=_evidence_identity(model="fixture-evidence-v2"),
            ),
        )

    calls = 0

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            nonlocal calls
            del route
            calls += 1
            if calls == 2:
                raise RuntimeError("fixture session failure")
            source_input = payload["input"]
            assert isinstance(source_input, str)
            model_input = json.loads(source_input)
            candidate = model_input["candidates"][0]
            source = model_input["relevant_excerpts"][0]
            return ModelResult(output={
                "version": "session-evidence-v1",
                "events": [{
                    "candidate_event_id": candidate["id"],
                    "source_message_ids": [source["id"]],
                    "subject": "MATH",
                    "concept_ref": "fractions",
                    "event_type": "independent_success",
                    "event_summary": "Student independently solved a fractions task.",
                    "school_or_extended": "school",
                    "dimensions": {
                        "understanding": "demonstrated", "independence": "independent",
                        "reasoning_demonstration": "well_supported", "transfer": "not_tested",
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
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "fixture-evidence-v2")},
            providers={"fixture": Provider()},
        ),
    )
    assert run_once(factory, registry, worker_id="atomic-authority-worker") == "PENDING"

    with factory() as session:
        run = session.get(IntelligenceReprocessRun, queued.reprocess_run.id)
        authorities = {
            authority.session_id: authority.evidence_processing_run_id
            for authority in session.query(IntelligenceSessionAuthority).filter_by(student_id=student.id)
        }
        items = {
            item.session_id: item.status
            for item in session.query(IntelligenceReprocessSession).filter_by(reprocess_run_id=queued.reprocess_run.id)
        }
        card = build_learner_intelligence_card(
            session,
            student_id=student.id,
            subject="MATH",
            question="Can you help with fractions?",
        )
        assert session.query(LearnerPattern).count() == 0
        assert session.query(DecisionView).count() == 0

    assert run is not None and run.status == "PARTIAL_FAILED"
    assert calls == 3
    assert items == {first.id: "COMPLETED", second.id: "FAILED", third.id: "COMPLETED"}
    assert authorities == {session_id: processing_run.id for session_id, processing_run in old_runs.items()}
    assert [entry.source_id for entry in card.entries] == [old_state.id]

    from services.intelligence import current_state as current_state_service

    original_apply = current_state_service.apply_processing_run_current_state

    def fail_activation(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("fixture activation failure")

    monkeypatch.setattr(current_state_service, "apply_processing_run_current_state", fail_activation)
    assert run_once(
        factory,
        registry,
        worker_id="atomic-authority-worker",
        now=datetime(2030, 1, 1, tzinfo=UTC),
    ) == "PENDING"
    with factory() as session:
        failed_activation = session.get(IntelligenceReprocessRun, queued.reprocess_run.id)
        authorities_after_rollback = {
            authority.session_id: authority.evidence_processing_run_id
            for authority in session.query(IntelligenceSessionAuthority).filter_by(student_id=student.id)
        }
        state_after_rollback = session.get(CurrentLearningState, old_state.id)
    assert failed_activation is not None and failed_activation.status == "FAILED"
    assert authorities_after_rollback == {session_id: processing_run.id for session_id, processing_run in old_runs.items()}
    assert state_after_rollback is not None and state_after_rollback.status == "ACTIVE"

    monkeypatch.setattr(current_state_service, "apply_processing_run_current_state", original_apply)
    assert run_once(
        factory,
        registry,
        worker_id="atomic-authority-worker",
        now=datetime(2031, 1, 1, tzinfo=UTC),
    ) == "COMPLETED"
    with factory() as session:
        completed = session.get(IntelligenceReprocessRun, queued.reprocess_run.id)
        authorities_after_activation = {
            authority.session_id: authority.evidence_processing_run_id
            for authority in session.query(IntelligenceSessionAuthority).filter_by(student_id=student.id)
        }
        state_after_activation = session.get(CurrentLearningState, old_state.id)
        card_after_activation = build_learner_intelligence_card(
            session,
            student_id=student.id,
            subject="MATH",
            question="Can you help with fractions?",
        )
        decision_count = session.query(DecisionView).count()
        assert completed is not None
        activation = completed.result["activation"] if completed.result is not None else None
        assert isinstance(activation, dict)
        activation_repeat = activate_reprocess_scope(session, reprocess_run_id=completed.id)
        decision_count_after_repeat = session.query(DecisionView).count()
        raw_candidate_signals_after = {
            candidate.id: candidate.signal
            for candidate in session.query(CandidateEvent).filter(
                CandidateEvent.session_id.in_((first.id, second.id, third.id))
            )
        }
        raw_messages_after = {
            message.id: message.content
            for message in session.query(LearningMessage).filter(
                LearningMessage.session_id.in_((first.id, second.id, third.id))
            )
        }
        historical_old_runs = session.query(IntelligenceProcessingRun).filter(
            IntelligenceProcessingRun.id.in_([run.id for run in old_runs.values()])
        ).count()

    assert calls == 4  # A/C Evidence is reused after B's retry and activation retry.
    assert completed.status == "COMPLETED"
    assert set(authorities_after_activation) == {first.id, second.id, third.id}
    assert all(authorities_after_activation[session_id] != old_runs[session_id].id for session_id in old_runs)
    assert state_after_activation is not None and state_after_activation.status == "RESOLVED"
    assert not card_after_activation.entries
    assert decision_count > 0
    assert decision_count_after_repeat == decision_count
    assert raw_candidate_signals_after == raw_candidate_signals
    assert raw_messages_after == raw_messages
    assert historical_old_runs == 3
    assert activation["previous_authority_by_session"] == {
        str(session_id): {
            "reprocess_run_id": str(old_reprocess.id),
            "evidence_processing_run_id": str(old_runs[session_id].id),
        }
        for session_id in (first.id, second.id, third.id)
    }
    assert activation["new_evidence_processing_runs_by_session"] == {
        str(session_id): str(authorities_after_activation[session_id])
        for session_id in (first.id, second.id, third.id)
    }
    assert activation_repeat == activation
