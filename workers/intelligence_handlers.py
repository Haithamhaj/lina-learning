"""Worker-owned session consolidation handler."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.consolidation import consolidate_closed_session
from services.intelligence.current_state import apply_processing_run_current_state
from services.intelligence.patterns import apply_processing_run_patterns
from services.model_gateway.factory import create_session_evidence_gateway
from services.model_gateway.gateway import ModelGateway
from services.platform.db.models import Job, LearningSession
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
            }

    registry.register(SESSION_CONSOLIDATION_JOB, handle_consolidation)
