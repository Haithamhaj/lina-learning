"""Phase 3 Gate B composed Math-learning journey."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.card import build_learner_intelligence_card
from services.intelligence.reprocess import (
    EvidenceVersionSelection,
    IntelligenceReprocessRequest,
    activate_reprocess_scope,
    enqueue_intelligence_reprocess,
    process_intelligence_reprocess_session,
)
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    Job,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    LearningSession,
    ModelTask,
    Student,
    User,
)
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import ContextBudget, TutorContextBuilder
from services.tutor.runtime import TutorRuntime, TutorTurn
from services.tutor.teaching_decisions import TeachingStrategy
from services.tutor.session_lifecycle import SESSION_CONSOLIDATION_JOB, SessionLifecyclePolicy, close_inactive_sessions
from services.tutor.student_sessions import append_student_message, open_or_resume_math_session
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for the Gate B journey",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


class _AllowPolicy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(SafetyAction.ALLOW, None, "BASELINE", 1, "TEST_ALLOW", "normal", None)


class _RedirectPolicy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(
            SafetyAction.REDIRECT_TO_PARENT,
            None,
            "BASELINE",
            1,
            "TEST_REDIRECT",
            "sensitive",
            "Please ask a trusted grown-up for help with this topic.",
        )


class _Retrieval:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def retrieve(self, **kwargs: object) -> list[RetrievedBlock]:
        self.calls.append(kwargs)
        return [
            RetrievedBlock(
                text="Equivalent fractions represent the same amount, such as one half and two fourths.",
                source_ref="fixture-book#page=12",
                page_number=12,
                block_type="EXERCISE",
                score=1.0,
                semantic_key="equivalent_fractions",
                semantic_type="EXERCISE",
                concept_key="equivalent_fractions",
                source_refs=("fixture-book#page=12",),
                page_numbers=(12,),
                matched=True,
            )
        ]


class _TutorProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.payloads: list[dict[str, object]] = []

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.calls += 1
        self.payloads.append(payload)
        output: dict[str, object] = {
            "text": "Let’s compare the same-sized pieces carefully.",
            "suggested_actions": [],
            "teaching_mode": "LEARN",
            "teaching_strategy": "INDEPENDENT_CHECK" if self.calls == 3 else "EXPLAIN_WITH_EXAMPLE",
            "teaching_method_id": "CONCRETE_EXAMPLE",
            "prior_method_relation": None,
            "candidate_metadata": None,
        }
        if self.calls == 1:
            source_id = payload["candidate_source_message_id"]
            output["candidate_metadata"] = {
                "version": "candidate-event-v1",
                "candidates": [{
                    "event_type": "explanation_attempt",
                    "concept_ref": "equivalent_fractions",
                    "summary": "The Student explained why one half and two fourths name the same amount.",
                    "signal": "explained_equivalent_fraction_reasoning",
                    "source_message_ids": [source_id],
                    "school_or_extended": "school",
                }],
            }
        yield StreamDelta("Let’s compare ")
        yield StreamComplete(ModelResult(output=output, input_tokens=12, output_tokens=10))


class _EvidenceProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.payloads: list[dict[str, object]] = []

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        self.calls += 1
        self.payloads.append(payload)
        parsed = json.loads(str(payload["input"]))
        candidate = parsed["candidates"][0]
        source = parsed["relevant_excerpts"][0]
        return ModelResult(output={
            "version": "session-evidence-v1",
            "events": [{
                "candidate_event_id": candidate["id"],
                "source_message_ids": [source["id"]],
                "subject": "MATH",
                "concept_ref": "equivalent_fractions",
                "event_type": "explanation_attempt",
                "event_summary": "The Student needed substantial support explaining equivalent fractions.",
                "school_or_extended": "school",
                "dimensions": {
                    "understanding": "partial",
                    "independence": "substantial_support",
                    "reasoning_demonstration": "coherent",
                    "transfer": "not_tested",
                    "self_correction": "not_observed",
                    "retention": "not_tested",
                    "strategy_effectiveness": "not_evaluable",
                    "persistence": "continued_with_support",
                    "confidence_calibration": "not_observed",
                },
                "relationship": "supports",
            }],
        }, input_tokens=16, output_tokens=10)


class _NoEvidenceProvider:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route, payload
        self.calls += 1
        return ModelResult(output={"version": "session-evidence-v1", "events": []})


def _policy() -> SessionLifecyclePolicy:
    return SessionLifecyclePolicy("gate-b-fixture-v1", timedelta(minutes=10), timedelta(minutes=5))


def _student(session: Session) -> Student:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    return student


def _runtime(session: Session, *, provider: _TutorProvider, retrieval: _Retrieval, safety: object) -> TutorRuntime:
    return TutorRuntime(
        session,
        context_builder=TutorContextBuilder(
            session,
            retrieval_service=retrieval,  # type: ignore[arg-type]
            budget=ContextBudget(retrieval_characters=1400, intelligence_characters=600),
        ),
        safety_policy=safety,  # type: ignore[arg-type]
        gateway=ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "gate-b-tutor")},
            providers={"fixture": provider},
        ),
    )


def test_gate_b_math_journey_reaches_bounded_later_tutor_context(factory: sessionmaker[Session]) -> None:
    """Fails if the composed path skips provenance, closure, intelligence, or bounded reuse."""

    tutor_provider = _TutorProvider()
    evidence_provider = _EvidenceProvider()
    retrieval = _Retrieval()
    clock = datetime(2030, 1, 10, 12, tzinfo=UTC)

    with factory.begin() as session:
        student = _student(session)
        first_session = open_or_resume_math_session(session, student_id=student.id, now=clock, lifecycle_policy=_policy())
        first_session.intelligence_pipeline = "legacy-session-evidence-v1"
        runtime = _runtime(session, provider=tutor_provider, retrieval=retrieval, safety=_AllowPolicy())
        first_turn = list(runtime.stream_turn(
            learning_session=first_session,
            question="I think 1/2 equals 2/4 because both show the same amount, but I need help explaining why.",
        ))[-1]
        greeting_turn = list(runtime.stream_turn(learning_session=first_session, question="Thank you!"))[-1]
        assert isinstance(first_turn, TutorTurn) and isinstance(greeting_turn, TutorTurn)
        first_candidate = session.query(CandidateEvent).filter_by(session_id=first_session.id).one()
        raw_student = session.get(LearningMessage, first_candidate.message_id)
        assert raw_student is not None
        assert session.query(LearningEvidence).count() == 0
        assert first_candidate.payload["source_message_ids"] == [str(raw_student.id)]
        assert tutor_provider.calls == 2

        first_session.last_activity_at = clock - timedelta(minutes=16)
        assert close_inactive_sessions(session, now=clock, policy=_policy()) == [first_session]
        jobs = session.query(Job).filter_by(job_type=SESSION_CONSOLIDATION_JOB).all()
        assert len(jobs) == 1
        assert session.query(LearningEvidence).count() == 0

    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        evidence_gateway_factory=lambda worker_session: ModelGateway(
            worker_session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "gate-b-evidence")},
            providers={"fixture": evidence_provider},
        ),
    )
    assert run_once(factory, registry, worker_id="gate-b-worker", now=clock) == "COMPLETED"

    with factory.begin() as session:
        first_session = session.get(LearningSession, first_session.id)
        assert first_session is not None and first_session.status == "CLOSED"
        candidate = session.query(CandidateEvent).filter_by(session_id=first_session.id).one()
        event = session.query(LearningEvent).filter_by(candidate_event_id=candidate.id).one()
        evidence = session.query(LearningEvidence).filter_by(event_id=event.id).one()
        state = session.query(CurrentLearningState).filter_by(
            student_id=student.id,
            concept_ref="equivalent_fractions",
            state_type="active_difficulty",
            status="ACTIVE",
        ).one()
        patterns = session.query(LearnerPattern).filter_by(student_id=student.id).all()
        views = session.query(DecisionView).filter_by(student_id=student.id, concept_ref="equivalent_fractions").all()
        assert evidence_provider.calls == 1
        assert event.session_id == first_session.id
        assert event.source_message_id == candidate.message_id
        assert evidence.source_ref.endswith(f"candidate:{candidate.id}:message:{candidate.message_id}")
        assert state.evidence_refs == [str(evidence.id)]
        assert all(pattern.status != "STABLE" for pattern in patterns)
        assert views and all(view.conclusion.isupper() and "%" not in view.explanation for view in views)

        later_session = open_or_resume_math_session(
            session,
            student_id=student.id,
            now=clock + timedelta(minutes=1),
            lifecycle_policy=_policy(),
        )
        assert later_session.id != first_session.id and later_session.status == "OPEN"
        for index in range(6):
            append_student_message(session, learning_session=later_session, content=f"old later-session message {index}")
        later_turn = list(_runtime(session, provider=tutor_provider, retrieval=retrieval, safety=_AllowPolicy()).stream_turn(
            learning_session=later_session,
            question="I solved another equivalent fractions task myself: 3/6 equals 1/2. Can you check my reasoning?",
        ))[-1]
        assert isinstance(later_turn, TutorTurn)
        later_payload = tutor_provider.payloads[-1]
        later_tutor = session.query(LearningMessage).filter_by(session_id=later_session.id, role="tutor").one()
        card = build_learner_intelligence_card(
            session,
            student_id=student.id,
            subject="MATH",
            question="Can you check another equivalent fractions task?",
        )
        assert later_turn.strategy is TeachingStrategy.INDEPENDENT_CHECK
        assert later_payload["intelligence"] == [entry.text for entry in card.entries]
        assert later_payload["intelligence"]
        assert len(later_tutor.payload["context_debug"]["session_message_ids"]) <= 4
        assert "old later-session message 0" not in str(later_payload["input"])
        assert retrieval.calls[-1]["character_budget"] == 1400
        assert len(str(later_payload["intelligence"][0])) <= 600
        assert "Current demonstrated behavior outranks historical learning notes" in str(later_payload["instructions"])

        model_calls_before_redirect = tutor_provider.calls
        redirect_turn = list(_runtime(session, provider=tutor_provider, retrieval=retrieval, safety=_RedirectPolicy()).stream_turn(
            learning_session=later_session,
            question="Can you explain this sensitive private topic?",
        ))[-1]
        assert isinstance(redirect_turn, TutorTurn)
        assert tutor_provider.calls == model_calls_before_redirect
        assert session.query(AIExecution).filter_by(task=ModelTask.TUTOR.value).count() == 3
        assert session.query(AIExecution).filter_by(task=ModelTask.SESSION_EVIDENCE.value).count() == 1

        first_session_id = first_session.id
        student_id = student.id

    no_evidence_provider = _NoEvidenceProvider()
    with factory.begin() as session:
        reprocess = enqueue_intelligence_reprocess(
            session,
            request=IntelligenceReprocessRequest(
                student_id=student_id,
                session_ids=(first_session_id,),
                evidence=EvidenceVersionSelection(provider="fixture", model="gate-b-evidence-v2"),
            ),
        )
    with factory.begin() as session:
        staged = process_intelligence_reprocess_session(
            session,
            reprocess_run_id=reprocess.reprocess_run.id,
            session_id=first_session_id,
            gateway=ModelGateway(
                session,
                routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "gate-b-evidence-v2")},
                providers={"fixture": no_evidence_provider},
            ),
        )
        assert staged["staged"] is True
        assert session.query(CurrentLearningState).filter_by(
            student_id=student_id,
            state_type="active_difficulty",
            status="ACTIVE",
        ).count() == 1
        activation = activate_reprocess_scope(session, reprocess_run_id=reprocess.reprocess_run.id)
        assert activation["status"] == "COMPLETED"
        assert session.query(CurrentLearningState).filter_by(
            student_id=student_id,
            state_type="active_difficulty",
            status="ACTIVE",
        ).count() == 0
        assert session.query(LearningEvidence).count() == 1
        assert session.query(CurrentLearningState).filter_by(
            student_id=student_id,
            state_type="active_difficulty",
            status="SUPERSEDED",
        ).count() == 1
        assert no_evidence_provider.calls == 1
