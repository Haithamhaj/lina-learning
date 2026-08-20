"""Session inactivity detection delegates consolidation to the durable worker."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningSession
from services.platform.jobs import enqueue_job

CONSOLIDATE_SESSION_JOB = "intelligence.consolidate_session"


def close_inactive_sessions(session: Session, *, now: datetime | None = None, inactivity: timedelta = timedelta(minutes=20)) -> list[LearningSession]:
    """Close eligible sessions once and enqueue a database-idempotent job."""

    current = now or datetime.now(UTC)
    if inactivity <= timedelta(0):
        raise ValueError("inactivity must be positive.")
    sessions = session.execute(select(LearningSession).where(LearningSession.status == "OPEN", LearningSession.last_activity_at <= current - inactivity).with_for_update(skip_locked=True)).scalars().all()
    for learning_session in sessions:
        learning_session.status = "CLOSED"
        learning_session.closed_at = current
        enqueue_job(session, job_type=CONSOLIDATE_SESSION_JOB, payload={"session_id": str(learning_session.id)}, idempotency_key=f"consolidate:{learning_session.id}")
    session.flush()
    return sessions
