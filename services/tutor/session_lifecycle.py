"""Automatic, durable lifecycle decisions for raw learning sessions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import EVIDENCE_RUBRIC_VERSION
from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
)
from services.platform.config import Settings, get_settings
from services.platform.db.models import Job, LearningMessage, LearningSegment, LearningSession, SegmentLearningReview
from services.tutor.exchanges import clear_session_exchange_embeddings
from services.tutor.segment_lifecycle import (
    is_segment_structurally_reviewable,
    reconcile_segments_for_session_close,
)
from services.platform.jobs import enqueue_job

LEGACY_SESSION_EVIDENCE_PIPELINE = "legacy-session-evidence-v1"
SESSION_FINALIZATION_PIPELINE = "segment-finalization-v1"
SESSION_CONSOLIDATION_JOB = "SESSION_CONSOLIDATION"
SESSION_INTELLIGENCE_FINALIZE_JOB = "SESSION_INTELLIGENCE_FINALIZE"
PERSONAL_FACTS_EXTRACTION_JOB = "PERSONAL_FACTS_EXTRACTION"


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

    reconcile_segments_for_session_close(
        session,
        learning_session=learning_session,
        closed_at=now,
    )
    learning_session.status = "CLOSED"
    learning_session.closed_at = now
    clear_session_exchange_embeddings(session, learning_session=learning_session)
    # This queue is independent of Segment Review and Session Finalization. It
    # exists only when there is raw Student source material worth examining.
    has_student_message = session.scalar(
        select(LearningMessage.id)
        .where(
            LearningMessage.session_id == learning_session.id,
            LearningMessage.role == "student",
        )
        .limit(1)
    )
    if has_student_message is not None:
        enqueue_job(
            session,
            job_type=PERSONAL_FACTS_EXTRACTION_JOB,
            payload={
                "student_id": str(learning_session.student_id),
                "session_id": str(learning_session.id),
            },
            idempotency_key=f"personal-facts-extraction:{learning_session.id}",
        )
    if learning_session.intelligence_pipeline == LEGACY_SESSION_EVIDENCE_PIPELINE:
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
    elif learning_session.intelligence_pipeline == SESSION_FINALIZATION_PIPELINE:
        enqueue_session_intelligence_finalization_if_ready(
            session,
            learning_session=learning_session,
        )
    else:
        raise ValueError(
            f"Unsupported Session intelligence pipeline {learning_session.intelligence_pipeline!r}."
        )
    session.flush()
    return True


def enqueue_session_intelligence_finalization_if_ready(
    session: Session,
    *,
    learning_session: LearningSession,
) -> Job | None:
    """Queue one deterministic finalization job only for a complete Review set."""

    if (
        learning_session.intelligence_pipeline != SESSION_FINALIZATION_PIPELINE
        or learning_session.status != "CLOSED"
        or learning_session.closed_at is None
    ):
        return None

    required_segment_ids = [
        segment.id
        for segment in session.scalars(
            select(LearningSegment)
            .where(LearningSegment.session_id == learning_session.id)
            .order_by(LearningSegment.sequence, LearningSegment.id)
        )
        if is_segment_structurally_reviewable(
            session,
            learning_session=learning_session,
            segment=segment,
        )
    ]
    if required_segment_ids:
        completed_segment_ids = set(
            session.scalars(
                select(SegmentLearningReview.segment_id)
                .where(
                    SegmentLearningReview.segment_id.in_(required_segment_ids),
                    SegmentLearningReview.student_id == learning_session.student_id,
                    SegmentLearningReview.session_id == learning_session.id,
                    SegmentLearningReview.status == "COMPLETED",
                    SegmentLearningReview.schema_version
                    == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
                    SegmentLearningReview.prompt_version
                    == SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
                    SegmentLearningReview.rubric_version == EVIDENCE_RUBRIC_VERSION,
                    SegmentLearningReview.review_policy_version
                    == SEGMENT_REVIEW_POLICY_VERSION,
                )
            )
        )
        if any(segment_id not in completed_segment_ids for segment_id in required_segment_ids):
            return None

    return enqueue_job(
        session,
        job_type=SESSION_INTELLIGENCE_FINALIZE_JOB,
        payload={
            "session_id": str(learning_session.id),
            "student_id": str(learning_session.student_id),
            "intelligence_pipeline": SESSION_FINALIZATION_PIPELINE,
        },
        idempotency_key=f"session-intelligence-finalize:{learning_session.id}",
    )


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
