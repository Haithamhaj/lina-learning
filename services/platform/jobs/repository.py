"""PostgreSQL-safe persistence operations for background jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from services.platform.db.models import Job, JobStatus

DEFAULT_LEASE_DURATION = timedelta(minutes=5)
DEFAULT_RETRY_DELAY = timedelta(seconds=30)
MAX_ERROR_LENGTH = 1_000


class JobStateError(RuntimeError):
    """Raised when a worker tries to settle a job it does not own."""


def enqueue_job(
    session: Session,
    *,
    job_type: str,
    payload: dict[str, object],
    idempotency_key: str | None = None,
    max_attempts: int = 3,
    run_after: datetime | None = None,
) -> Job:
    """Persist a pending job, returning an existing idempotent job if present."""

    if not job_type:
        raise ValueError("job_type must be non-empty.")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive.")

    values: dict[str, Any] = {
        "job_type": job_type,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "max_attempts": max_attempts,
        "run_after": run_after or _utc_now(),
        "status": JobStatus.PENDING.value,
    }
    if idempotency_key is None:
        job = Job(**values)
        session.add(job)
        session.flush()
        return job

    statement = (
        insert(Job)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=[Job.job_type, Job.idempotency_key],
            index_where=Job.idempotency_key.is_not(None),
        )
        .returning(Job.id)
    )
    job_id = session.execute(statement).scalar_one_or_none()
    if job_id is not None:
        return session.get(Job, job_id)  # type: ignore[return-value]

    return session.execute(
        select(Job).where(
            Job.job_type == job_type,
            Job.idempotency_key == idempotency_key,
        )
    ).scalar_one()


def claim_next_job(
    session: Session,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_duration: timedelta = DEFAULT_LEASE_DURATION,
) -> Job | None:
    """Atomically lease one eligible PostgreSQL job using ``SKIP LOCKED``."""

    if not worker_id:
        raise ValueError("worker_id must be non-empty.")
    if lease_duration <= timedelta(0):
        raise ValueError("lease_duration must be positive.")

    claim_time = now or _utc_now()
    eligible = or_(
        and_(Job.status == JobStatus.PENDING.value, Job.run_after <= claim_time),
        and_(
            Job.status == JobStatus.RUNNING.value,
            Job.lease_expires_at.is_not(None),
            Job.lease_expires_at <= claim_time,
        ),
    )

    while True:
        job = session.execute(
            select(Job)
            .where(eligible)
            .order_by(Job.run_after, Job.created_at, Job.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        ).scalar_one_or_none()
        if job is None:
            return None

        if job.status == JobStatus.RUNNING.value and job.attempt_count >= job.max_attempts:
            job.status = JobStatus.FAILED.value
            job.completed_at = claim_time
            job.lease_token = None
            job.lease_expires_at = None
            job.last_error = "Worker lease expired after the final attempt."
            session.flush()
            continue

        job.status = JobStatus.RUNNING.value
        job.attempt_count += 1
        job.claimed_by = worker_id
        job.lease_token = uuid4()
        job.started_at = claim_time
        job.lease_expires_at = claim_time + lease_duration
        session.flush()
        return job


def complete_job(
    session: Session,
    job_id: UUID,
    *,
    worker_id: str,
    lease_token: UUID | None,
    result: dict[str, object] | None,
    now: datetime | None = None,
) -> Job:
    """Record a successful handler outcome for the current job lease holder."""

    job = _owned_running_job(session, job_id, worker_id, lease_token)
    job.status = JobStatus.COMPLETED.value
    job.result = result
    job.completed_at = now or _utc_now()
    job.lease_token = None
    job.lease_expires_at = None
    job.last_error = None
    session.flush()
    return job


def fail_job(
    session: Session,
    job_id: UUID,
    *,
    worker_id: str,
    lease_token: UUID | None,
    error: Exception,
    now: datetime | None = None,
    retry_delay: timedelta = DEFAULT_RETRY_DELAY,
) -> Job:
    """Record a handler failure and either schedule retry or mark it terminal."""

    if retry_delay <= timedelta(0):
        raise ValueError("retry_delay must be positive.")

    failure_time = now or _utc_now()
    job = _owned_running_job(session, job_id, worker_id, lease_token)
    job.last_error = _safe_error_message(error)
    job.lease_token = None
    job.lease_expires_at = None
    if job.attempt_count >= job.max_attempts:
        job.status = JobStatus.FAILED.value
        job.completed_at = failure_time
    else:
        job.status = JobStatus.PENDING.value
        job.claimed_by = None
        job.run_after = failure_time + retry_delay * (2 ** (job.attempt_count - 1))
    session.flush()
    return job


def _owned_running_job(
    session: Session,
    job_id: UUID,
    worker_id: str,
    lease_token: UUID | None,
) -> Job:
    job = session.execute(
        select(Job).where(Job.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if (
        job is None
        or job.status != JobStatus.RUNNING.value
        or job.claimed_by != worker_id
        or lease_token is None
        or job.lease_token is None
        or job.lease_token != lease_token
    ):
        raise JobStateError("Job is not running under this worker lease.")
    return job


def _safe_error_message(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"[:MAX_ERROR_LENGTH]


def _utc_now() -> datetime:
    return datetime.now(UTC)
