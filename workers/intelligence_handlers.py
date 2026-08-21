"""Worker-owned session consolidation handler."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.consolidation import consolidate_closed_session
from services.intelligence.current_state import apply_processing_run_current_state
from services.intelligence.decisions import apply_processing_run_decision_views
from services.intelligence.patterns import apply_processing_run_patterns
from services.model_gateway.factory import create_session_evidence_gateway
from services.model_gateway.gateway import ModelGateway
from services.platform.db.models import Job, LearningSession
from services.platform.db.models import IntelligenceReprocessRun
from services.intelligence.reprocess import (
    INTELLIGENCE_REPROCESS_JOB,
    process_intelligence_reprocess_session,
    record_reprocess_session_failure,
)
from services.tutor.session_lifecycle import SESSION_CONSOLIDATION_JOB

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


def register_intelligence_handlers(
    registry: "JobHandlerRegistry",
    *,
    session_factory: sessionmaker[Session],
    evidence_gateway_factory: Callable[[Session], ModelGateway] = create_session_evidence_gateway,
) -> None:
    """Register only the approved closed-session evidence job for TASK-021."""

    def handle_consolidation(job: Job) -> dict[str, object]:
        session_id = job.payload.get("session_id")
        if not isinstance(session_id, str):
            raise ValueError("SESSION_CONSOLIDATION requires session_id.")
        with session_factory() as session:
            learning_session = session.get(LearningSession, UUID(session_id), with_for_update=True)
            if learning_session is None:
                raise LookupError(f"Learning session {session_id!r} does not exist.")
            try:
                outcome = consolidate_closed_session(
                    session,
                    learning_session=learning_session,
                    gateway=evidence_gateway_factory(session),
                )
                states = apply_processing_run_current_state(
                    session,
                    processing_run_id=outcome.processing_run.id,
                )
                patterns = apply_processing_run_patterns(
                    session,
                    processing_run_id=outcome.processing_run.id,
                )
                decision_views = apply_processing_run_decision_views(
                    session,
                    processing_run_id=outcome.processing_run.id,
                )
            except Exception:
                session.commit()
                raise
            session.commit()
            return {
                "session_id": session_id,
                "processing_run_id": str(outcome.processing_run.id),
                "event_count": outcome.event_count,
                "current_state_count": len(states),
                "pattern_count": len(patterns),
                "decision_view_count": len(decision_views),
            }

    registry.register(SESSION_CONSOLIDATION_JOB, handle_consolidation)

    def handle_reprocess(job: Job) -> dict[str, object]:
        raw_run_id = job.payload.get("reprocess_run_id")
        if not isinstance(raw_run_id, str):
            raise ValueError("INTELLIGENCE_REPROCESS requires reprocess_run_id.")
        reprocess_run_id = UUID(raw_run_id)
        with session_factory.begin() as session:
            reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
            if reprocess_run is None:
                raise LookupError(f"Reprocess run {raw_run_id!r} does not exist.")
            reprocess_run.status = "RUNNING"
            from datetime import UTC, datetime
            reprocess_run.started_at = reprocess_run.started_at or datetime.now(UTC)
            session_ids = reprocess_run.scope.get("session_ids", []) if isinstance(reprocess_run.scope, dict) else []
        results: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []
        for raw_session_id in session_ids:
            target_session_id = UUID(str(raw_session_id))
            try:
                with session_factory.begin() as session:
                    result = process_intelligence_reprocess_session(
                        session,
                        reprocess_run_id=reprocess_run_id,
                        session_id=target_session_id,
                        gateway=evidence_gateway_factory(session),
                    )
                    results.append(result)
            except Exception as error:
                with session_factory.begin() as session:
                    failures.append(
                        record_reprocess_session_failure(
                            session,
                            reprocess_run_id=reprocess_run_id,
                            session_id=target_session_id,
                            error=error,
                        )
                    )
        with session_factory.begin() as session:
            reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
            assert reprocess_run is not None
            from datetime import UTC, datetime
            reprocess_run.result = {"completed_sessions": results, "failed_sessions": failures}
            reprocess_run.status = "COMPLETED" if not failures else "PARTIAL_FAILED"
            reprocess_run.completed_at = datetime.now(UTC)
            reprocess_run.error = failures[0]["error"] if failures else None
            if failures:
                reprocess_run.failed_at = datetime.now(UTC)
        if failures:
            raise RuntimeError("Intelligence reprocess has failed sessions; retry will resume only those sessions.")
        return {"reprocess_run_id": raw_run_id, "completed_sessions": results, "failed_sessions": failures}

    registry.register(INTELLIGENCE_REPROCESS_JOB, handle_reprocess)
