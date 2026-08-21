"""Automatic, durable lifecycle decisions for raw learning sessions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.config import Settings, get_settings
from services.platform.db.models import LearningSession
from services.platform.jobs import enqueue_job

SESSION_CONSOLIDATION_JOB = "SESSION_CONSOLIDATION"


@dataclass(frozen=True)
class SessionLifecyclePolicy:
    """Versioned timing parameters for automatic session closure."""

    version: str
    inactivity: timedelta
    grace: timedelta

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("Session lifecycle policy version must be non-empty.")
        if self.inactivity <= timedelta(0):
            raise ValueError("Session inactivity timeout must be positive.")
        if self.grace < timedelta(0):
            raise ValueError("Session grace window must not be negative.")

    def closes_at(self, last_activity_at: datetime) -> datetime:
        return last_activity_at + self.inactivity + self.grace


def session_lifecycle_policy(settings: Settings | None = None) -> SessionLifecyclePolicy:
    """Build the centrally configured lifecycle policy for this process."""

    configured = settings or get_settings()
    return SessionLifecyclePolicy(
        version=configured.session_lifecycle_policy_version,
        inactivity=timedelta(seconds=configured.session_inactivity_seconds),
        grace=timedelta(seconds=configured.session_grace_seconds),
    )


def close_session_if_eligible(
    session: Session,
    *,
    learning_session: LearningSession,
    now: datetime,
    policy: SessionLifecyclePolicy,
) -> bool:
    """Close one open session after inactivity plus grace and enqueue once."""

    if learning_session.status != "OPEN" or now < policy.closes_at(learning_session.last_activity_at):
        return False

    learning_session.status = "CLOSED"
    learning_session.closed_at = now
    enqueue_job(
        session,
        job_type=SESSION_CONSOLIDATION_JOB,
        payload={
            "session_id": str(learning_session.id),
            "lifecycle_policy_version": policy.version,
            "closed_at": now.isoformat(),
        },
        idempotency_key=f"session-consolidation:{learning_session.id}",
    )
    session.flush()
    return True


def close_inactive_sessions(
    session: Session,
    *,
    now: datetime | None = None,
    policy: SessionLifecyclePolicy | None = None,
) -> list[LearningSession]:
    """Close sessions past inactivity and grace, without running consolidation."""

    current = now or datetime.now(UTC)
    effective_policy = policy or session_lifecycle_policy()
    sessions = session.execute(
        select(LearningSession)
        .where(
            LearningSession.status == "OPEN",
            LearningSession.last_activity_at <= current - effective_policy.inactivity - effective_policy.grace,
        )
        .with_for_update(skip_locked=True)
    ).scalars().all()
    closed: list[LearningSession] = []
    for learning_session in sessions:
        if close_session_if_eligible(
            session,
            learning_session=learning_session,
            now=current,
            policy=effective_policy,
        ):
            closed.append(learning_session)
    session.flush()
    return closed
