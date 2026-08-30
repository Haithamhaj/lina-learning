"""Run the Math-only SEG-EVID-01F acceptance journey on an isolated database.

This harness deliberately uses the normal Tutor runtime, durable lifecycle,
queued Segment Review handler, deterministic finalization, and E reprocessing.
It never writes semantic outputs or derived intelligence rows itself.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from scripts.run_full_system_acceptance import canonical_database_identity
from services.intelligence.reprocess import (
    EvidenceVersionSelection,
    IntelligenceReprocessRequest,
    enqueue_intelligence_reprocess,
)
from services.model_gateway.factory import create_segment_evidence_gateway, create_tutor_gateway
from services.platform.config import get_settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    CurrentLearningState,
    DecisionView,
    IntelligenceReprocessRun,
    IntelligenceSessionAuthority,
    Job,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSession,
    ModelTask,
    SegmentLearningReview,
    Student,
    User,
)
from services.retrieval.service import RetrievalService
from services.platform.safety import SafetyPolicyService
from services.tutor.context import TutorContextBuilder
from services.tutor.runtime import TutorRuntime, start_session
from services.tutor.session_lifecycle import SessionLifecyclePolicy, close_session_if_eligible
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once


class AcceptanceConfigurationError(ValueError):
    """A credential-free, fail-closed acceptance setup failure."""


@dataclass(frozen=True)
class AcceptanceConfiguration:
    source: object = field(repr=False)
    target: object = field(repr=False)
    provider: str
    model: str


def validate_configuration(
    *, source_database_url: str, target_database_url: str, provider: str, model: str
) -> AcceptanceConfiguration:
    """Require an isolated acceptance target and the approved real model route."""

    try:
        source_url = make_url(source_database_url)
        target_url = make_url(target_database_url)
        source = canonical_database_identity(source_database_url)
        target = canonical_database_identity(target_database_url)
    except Exception as error:  # noqa: BLE001 - safe public configuration boundary.
        raise AcceptanceConfigurationError("Acceptance database configuration is invalid.") from error
    if source == target or not target.database.startswith("lina_acceptance_"):
        raise AcceptanceConfigurationError("Acceptance target must be a distinct lina_acceptance_ database.")
    if provider != "openai" or model != "gpt-5.6-luna":
        raise AcceptanceConfigurationError("SEG-EVID-01F requires openai / gpt-5.6-luna.")
    return AcceptanceConfiguration(source=source_url, target=target_url, provider=provider, model=model)


def _factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(create_engine(normalize_database_url(database_url)), expire_on_commit=False)


def _runtime(session: Session) -> TutorRuntime:
    """Use the production Tutor/Model Gateway path without embedding-model calls."""

    settings = get_settings()
    return TutorRuntime(
        session,
        context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
        safety_policy=SafetyPolicyService(session),
        gateway=create_tutor_gateway(session, settings=settings),
    )


def _normal_tutor_turn(session: Session, *, learning_session: LearningSession, question: str) -> None:
    final = None
    for event in _runtime(session).stream_turn(learning_session=learning_session, question=question):
        if hasattr(event, "text") and hasattr(event, "intelligence"):
            final = event
    if final is None:
        raise RuntimeError("Normal Tutor runtime did not produce a completed turn.")


def _new_student(session: Session) -> Student:
    user = User(identity_provider="seg-evid-01f-acceptance", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="SEG-EVID-01F Acceptance")
    session.add(student)
    session.flush()
    return student


def _run_jobs_for_session(
    factory: sessionmaker[Session], *, learning_session_id: UUID, student_id: UUID
) -> None:
    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=factory,
        segment_evidence_gateway_factory=create_segment_evidence_gateway,
    )
    while True:
        with factory() as session:
            jobs = list(
                session.scalars(
                    select(Job).where(
                        Job.payload["session_id"].astext == str(learning_session_id),
                        Job.payload["student_id"].astext == str(student_id),
                        Job.status == "PENDING",
                    )
                )
            )
        if not jobs:
            return
        status = run_once(
            factory,
            registry,
            worker_id="seg-evid-01f-acceptance",
            job_ids=[job.id for job in jobs],
        )
        if status != "COMPLETED":
            raise RuntimeError("Required acceptance job did not complete.")


def _close_and_process(
    factory: sessionmaker[Session], *, learning_session_id: UUID, closed_at: datetime
) -> None:
    with factory.begin() as session:
        learning_session = session.get(LearningSession, learning_session_id, with_for_update=True)
        assert learning_session is not None
        policy = SessionLifecyclePolicy(version="seg-evid-01f-acceptance-v1", inactivity=timedelta(seconds=1), grace=timedelta())
        if not close_session_if_eligible(session, learning_session=learning_session, now=closed_at, policy=policy):
            raise RuntimeError("Acceptance Session was not eligible for normal lifecycle close.")
        student_id = learning_session.student_id
    _run_jobs_for_session(factory, learning_session_id=learning_session_id, student_id=student_id)


def _run_session(
    factory: sessionmaker[Session], *, student_id: UUID, questions: tuple[str, ...], close_offset: timedelta
) -> UUID:
    with factory.begin() as session:
        learning_session = start_session(session, student_id=student_id)
        for question in questions:
            _normal_tutor_turn(session, learning_session=learning_session, question=question)
        session_id = learning_session.id
        close_at = learning_session.last_activity_at + timedelta(seconds=1) + close_offset
    _close_and_process(factory, learning_session_id=session_id, closed_at=close_at)
    return session_id


def _summary(session: Session, *, student_id: UUID, session_ids: list[UUID]) -> dict[str, object]:
    reviews = list(session.scalars(select(SegmentLearningReview).where(SegmentLearningReview.student_id == student_id)))
    executions = list(session.scalars(select(AIExecution).where(AIExecution.student_id == student_id)))
    sessions: dict[str, object] = {}
    for session_id in session_ids:
        run_ids = list(session.scalars(select(LearningEvent.processing_run_id).where(LearningEvent.session_id == session_id)))
        sessions[str(session_id)] = {
            "events": session.query(LearningEvent).filter_by(session_id=session_id).count(),
            "evidence": session.query(LearningEvidence).join(LearningEvent).filter(LearningEvent.session_id == session_id).count(),
            "states": session.query(CurrentLearningState).filter(CurrentLearningState.processing_run_id.in_(run_ids)).count() if run_ids else 0,
            "patterns": session.query(LearnerPattern).filter(LearnerPattern.processing_run_id.in_(run_ids)).count() if run_ids else 0,
            "decisions": session.query(DecisionView).filter(DecisionView.processing_run_id.in_(run_ids)).count() if run_ids else 0,
        }
    return {
        "student_id": str(student_id),
        "session_ids": [str(value) for value in session_ids],
        "completed_reviews": sum(review.status == "COMPLETED" for review in reviews),
        "review_count": len(reviews),
        "authorities": session.query(IntelligenceSessionAuthority).filter_by(student_id=student_id).count(),
        "events": session.query(LearningEvent).join(LearningSession).filter(LearningSession.student_id == student_id).count(),
        "evidence": session.query(LearningEvidence).join(LearningEvent).join(LearningSession).filter(LearningSession.student_id == student_id).count(),
        "cards": session.query(LearnerIntelligenceCard).filter_by(student_id=student_id).count(),
        "real_luna_tutor_calls": sum(execution.task == ModelTask.TUTOR.value and execution.provider == "openai" and execution.model == "gpt-5.6-luna" and execution.success for execution in executions),
        "real_luna_segment_review_calls": sum(execution.task == ModelTask.SEGMENT_EVIDENCE.value and execution.provider == "openai" and execution.model == "gpt-5.6-luna" and execution.success for execution in executions),
        "sessions": sessions,
    }


def run_acceptance(*, target_database_url: str) -> dict[str, object]:
    """Run the controlled Math journey and one E-path reprocess on new raw data."""

    factory = _factory(target_database_url)
    with factory.begin() as session:
        student = _new_student(session)
        student_id = student.id
    first = _run_session(
        factory,
        student_id=student_id,
        questions=(
            "I am confused about equivalent fractions. Please show me with a simple example.",
            "One fourth is bigger than one half.",
            "I think one fourth is bigger than one half because 4 is bigger than 2.",
            "I see the correction: one half is bigger, and two fourths equals one half because the same whole is split into equal pieces.",
        ),
        close_offset=timedelta(),
    )
    second = _run_session(
        factory,
        student_id=student_id,
        questions=(
            "For a recipe, can I replace one half cup with two fourths cup? I think yes because the amounts are equal.",
            "I can explain it independently: multiplying the numerator and denominator by the same number keeps the amount equal.",
        ),
        close_offset=timedelta(days=8),
    )
    third = _run_session(
        factory,
        student_id=student_id,
        questions=(
            "Without a hint, two fourths is one half because each fourth is half of a half.",
            "Please give me one new equivalent-fraction question so I can prove it myself.",
        ),
        close_offset=timedelta(days=9),
    )
    with factory.begin() as session:
        queued = enqueue_intelligence_reprocess(
            session,
            request=IntelligenceReprocessRequest(
                student_id=student_id,
                session_ids=(second,),
                evidence=EvidenceVersionSelection(provider="openai", model="gpt-5.6-luna"),
            ),
        )
        reprocess_job_id = queued.job.id
    registry = JobHandlerRegistry()
    register_intelligence_handlers(registry, session_factory=factory, segment_evidence_gateway_factory=create_segment_evidence_gateway)
    if run_once(factory, registry, worker_id="seg-evid-01f-reprocess", job_ids=[reprocess_job_id]) != "COMPLETED":
        raise RuntimeError("E-path reprocessing did not complete.")
    with factory() as session:
        report = _summary(session, student_id=student_id, session_ids=[first, second, third])
        reprocess = session.query(IntelligenceReprocessRun).filter_by(id=queued.reprocess_run.id).one()
        report["reprocess_status"] = reprocess.status
        report["reprocess_run_id"] = str(reprocess.id)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-database-env", default="LINA_ACCEPTANCE_SOURCE_DATABASE_URL")
    parser.add_argument("--target-database-env", default="LINA_ACCEPTANCE_TARGET_DATABASE_URL")
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    source = os.environ.get(args.source_database_env)
    target = os.environ.get(args.target_database_env)
    settings = get_settings()
    if source is None or target is None:
        raise SystemExit("Required acceptance database environment variable is missing.")
    validate_configuration(source_database_url=source, target_database_url=target, provider=settings.model_provider, model=settings.model_name)
    report = run_acceptance(target_database_url=target)
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in {"student_id", "session_ids"}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
