"""Worker-owned session consolidation handler."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.core import close_and_consolidate
from services.platform.db.models import Job, LearningSession
from services.tutor.session_lifecycle import CONSOLIDATE_SESSION_JOB

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


def register_intelligence_handlers(registry: "JobHandlerRegistry", *, session_factory: sessionmaker[Session]) -> None:
    def handle_consolidation(job: Job) -> dict[str, object]:
        session_id = job.payload.get("session_id")
        if not isinstance(session_id, str):
            raise ValueError("intelligence.consolidate_session requires session_id.")
        with session_factory() as session:
            learning_session = session.get(LearningSession, UUID(session_id))
            if learning_session is None:
                raise LookupError(f"Learning session {session_id!r} does not exist.")
            run = close_and_consolidate(session, learning_session=learning_session)
            session.commit()
            return {"session_id": session_id, "processing_run_id": str(run.id)}
    registry.register(CONSOLIDATE_SESSION_JOB, handle_consolidation)
