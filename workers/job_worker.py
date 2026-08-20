"""Separate polling worker for database-backed jobs."""

from __future__ import annotations

import logging
import os
import socket
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import TypeAlias
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import get_engine
from services.platform.db.models import Job, JobStatus
from services.platform.jobs import claim_next_job, complete_job, fail_job

JobHandler: TypeAlias = Callable[[Job], Mapping[str, object] | None]
_logger = logging.getLogger(__name__)


class JobHandlerRegistry:
    """Explicit registry that keeps future job types owned by their domain."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        if not job_type:
            raise ValueError("job_type must be non-empty.")
        if job_type in self._handlers:
            raise ValueError(f"A handler is already registered for {job_type!r}.")
        self._handlers[job_type] = handler

    def get(self, job_type: str) -> JobHandler | None:
        return self._handlers.get(job_type)


def run_once(
    session_factory: sessionmaker[Session],
    registry: JobHandlerRegistry,
    *,
    worker_id: str,
    now: datetime | None = None,
) -> JobStatus | None:
    """Claim and handle at most one job without holding a database lock to run it."""

    claim_time = now or datetime.now(UTC)
    with session_factory.begin() as session:
        job = claim_next_job(session, worker_id=worker_id, now=claim_time)
        if job is None:
            return None
        session.expunge(job)

    handler = registry.get(job.job_type)
    try:
        if handler is None:
            raise LookupError(f"No handler is registered for job type {job.job_type!r}.")
        result = handler(job)
    except Exception as error:
        with session_factory.begin() as session:
            failed = fail_job(
                session,
                job.id,
                worker_id=worker_id,
                lease_token=job.lease_token,
                error=error,
                now=now,
            )
        return JobStatus(failed.status)

    with session_factory.begin() as session:
        completed = complete_job(
            session,
            job.id,
            worker_id=worker_id,
            lease_token=job.lease_token,
            result=dict(result) if result is not None else None,
            now=now,
        )
    return JobStatus(completed.status)


def run_forever(
    session_factory: sessionmaker[Session],
    registry: JobHandlerRegistry,
    *,
    worker_id: str,
    idle_seconds: float = 1.0,
) -> None:
    """Poll for durable jobs from the independent worker process."""

    if idle_seconds <= 0:
        raise ValueError("idle_seconds must be positive.")

    while True:
        status = run_once(session_factory, registry, worker_id=worker_id)
        if status is None:
            time.sleep(idle_seconds)


def main() -> None:
    """Run the worker process; future domain tasks register their own handlers."""

    logging.basicConfig(level=logging.INFO)
    session_factory = sessionmaker(get_engine(), expire_on_commit=False)
    worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:8]}"
    _logger.info("Starting jobs worker %s", worker_id)
    run_forever(session_factory, JobHandlerRegistry(), worker_id=worker_id)


if __name__ == "__main__":
    main()
