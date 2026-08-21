"""PostgreSQL-only integration tests for the durable jobs foundation."""

import os
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread
from uuid import UUID

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.connection import get_engine
from services.platform.db.models import Job, JobStatus
from services.platform.jobs import (
    JobStateError,
    claim_next_job,
    complete_job,
    enqueue_job,
    fail_job,
)
from workers.job_worker import JobHandlerRegistry, run_once


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for jobs queue semantics tests",
)


def test_postgres_schema_contains_the_jobs_table() -> None:
    """The queue must be durable rather than an in-process worker structure."""

    assert "jobs" in inspect(get_engine()).get_table_names()


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    """Provide a clean PostgreSQL queue table for each integration test."""

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(normalize_database_url(database_url))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs"))

    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


NOW = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)


def test_database_idempotency_returns_one_job_for_duplicate_enqueue(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        first = enqueue_job(
            session,
            job_type="fixture",
            payload={"source": "first"},
            idempotency_key="document:123",
        )
        first_id = first.id

    with postgres_session_factory.begin() as session:
        duplicate = enqueue_job(
            session,
            job_type="fixture",
            payload={"source": "duplicate"},
            idempotency_key="document:123",
        )

    assert duplicate.id == first_id
    with postgres_session_factory() as session:
        assert session.query(Job).count() == 1


def test_database_rejects_a_duplicate_idempotency_key_without_repository_checks(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        session.add(
            Job(
                job_type="fixture",
                payload={},
                idempotency_key="document:123",
                run_after=NOW,
            )
        )

    with pytest.raises(IntegrityError):
        with postgres_session_factory.begin() as session:
            session.add(
                Job(
                    job_type="fixture",
                    payload={},
                    idempotency_key="document:123",
                    run_after=NOW,
                )
            )
            session.flush()


def test_only_one_postgres_worker_claims_one_pending_job(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={},
            run_after=NOW,
        ).id

    barrier = Barrier(2)
    claims: list[UUID | None] = []

    def claim(worker_id: str) -> None:
        with postgres_session_factory.begin() as session:
            job = claim_next_job(session, worker_id=worker_id, now=NOW)
            claims.append(job.id if job else None)
            barrier.wait(timeout=5)

    first = Thread(target=claim, args=("worker-one",))
    second = Thread(target=claim, args=("worker-two",))
    first.start()
    second.start()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert sorted(claims, key=lambda value: value is None) == [job_id, None]


def test_claim_then_completion_moves_a_job_from_pending_to_running_to_completed(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={},
            run_after=NOW,
        ).id

    with postgres_session_factory.begin() as session:
        running = claim_next_job(session, worker_id="worker", now=NOW)
        assert running is not None
        assert running.status == JobStatus.RUNNING
        assert running.attempt_count == 1

    with postgres_session_factory.begin() as session:
        complete_job(
            session,
            job_id,
            worker_id="worker",
            lease_token=running.lease_token,
            result={"outcome": "complete"},
            now=NOW + timedelta(seconds=1),
        )

    with postgres_session_factory() as session:
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == JobStatus.COMPLETED
        assert completed.result == {"outcome": "complete"}


def test_failure_schedules_retry_then_records_terminal_failure(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={},
            max_attempts=2,
            run_after=NOW,
        ).id

    with postgres_session_factory.begin() as session:
        claimed = claim_next_job(session, worker_id="worker", now=NOW)
        assert claimed is not None
        fail_job(
            session,
            claimed.id,
            worker_id="worker",
            lease_token=claimed.lease_token,
            error=RuntimeError("first"),
            now=NOW,
        )

    with postgres_session_factory() as session:
        after_retry = session.get(Job, job_id)
        assert after_retry is not None
        assert after_retry.status == JobStatus.PENDING
        assert after_retry.attempt_count == 1
        assert after_retry.last_error == "RuntimeError: first"
        retry_at = after_retry.run_after

    with postgres_session_factory.begin() as session:
        claimed = claim_next_job(
            session,
            worker_id="worker",
            now=retry_at + timedelta(seconds=1),
        )
        assert claimed is not None
        fail_job(
            session,
            claimed.id,
            worker_id="worker",
            lease_token=claimed.lease_token,
            error=RuntimeError("second"),
            now=retry_at + timedelta(seconds=1),
        )

    with postgres_session_factory() as session:
        terminal = session.get(Job, job_id)
        assert terminal is not None
        assert terminal.status == JobStatus.FAILED
        assert terminal.attempt_count == 2
        assert terminal.last_error == "RuntimeError: second"


def test_expired_lease_is_claimable_by_a_recovery_worker(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={},
            run_after=NOW,
        ).id

    with postgres_session_factory.begin() as session:
        first = claim_next_job(
            session,
            worker_id="failed-worker",
            now=NOW,
            lease_duration=timedelta(seconds=1),
        )
        assert first is not None

    with postgres_session_factory.begin() as session:
        recovered = claim_next_job(
            session,
            worker_id="recovery-worker",
            now=NOW + timedelta(seconds=2),
        )

    assert recovered is not None
    assert recovered.id == job_id
    assert recovered.claimed_by == "recovery-worker"
    assert recovered.attempt_count == 2


def test_stale_worker_cannot_settle_a_job_reclaimed_by_the_same_host(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={},
            run_after=NOW,
        ).id

    with postgres_session_factory.begin() as session:
        original = claim_next_job(
            session,
            worker_id="same-host-worker",
            now=NOW,
            lease_duration=timedelta(seconds=1),
        )
        assert original is not None
        original_token = original.lease_token

    with postgres_session_factory.begin() as session:
        reclaimed = claim_next_job(
            session,
            worker_id="same-host-worker",
            now=NOW + timedelta(seconds=2),
        )
        assert reclaimed is not None
        assert reclaimed.lease_token != original_token

    with pytest.raises(JobStateError, match="lease"):
        with postgres_session_factory.begin() as session:
            complete_job(
                session,
                job_id,
                worker_id="same-host-worker",
                lease_token=original_token,
                result={"stale": True},
                now=NOW + timedelta(seconds=3),
            )

    with pytest.raises(JobStateError, match="lease"):
        with postgres_session_factory.begin() as session:
            fail_job(
                session,
                job_id,
                worker_id="same-host-worker",
                lease_token=original_token,
                error=RuntimeError("stale"),
                now=NOW + timedelta(seconds=3),
            )

    with postgres_session_factory() as session:
        current = session.get(Job, job_id)
        assert current is not None
        assert current.status == JobStatus.RUNNING
        assert current.claimed_by == "same-host-worker"
        assert current.lease_token == reclaimed.lease_token


def test_settling_requires_the_current_lease_token(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={},
            run_after=NOW,
        ).id

    with postgres_session_factory.begin() as session:
        claimed = claim_next_job(session, worker_id="worker", now=NOW)
        assert claimed is not None

    with pytest.raises(JobStateError, match="lease"):
        with postgres_session_factory.begin() as session:
            complete_job(
                session,
                job_id,
                worker_id="worker",
                lease_token=None,
                result={"invalid": True},
                now=NOW + timedelta(seconds=1),
            )


def test_run_once_completes_one_job_with_a_registered_handler(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="fixture",
            payload={"value": 7},
            run_after=NOW,
        ).id

    registry = JobHandlerRegistry()
    registry.register("fixture", lambda job: {"doubled": job.payload["value"] * 2})

    status = run_once(
        postgres_session_factory,
        registry,
        worker_id="test-worker",
        now=NOW,
    )

    assert status == JobStatus.COMPLETED
    with postgres_session_factory() as session:
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == JobStatus.COMPLETED
        assert completed.result == {"doubled": 14}


def test_worker_leaves_deferred_session_consolidation_pending_until_its_handler_exists(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        job_id = enqueue_job(
            session,
            job_type="SESSION_CONSOLIDATION",
            payload={"session_id": "fixture-session"},
            run_after=NOW,
        ).id

    assert run_once(
        postgres_session_factory,
        JobHandlerRegistry(),
        worker_id="test-worker",
        now=NOW,
    ) is None

    with postgres_session_factory() as session:
        pending = session.get(Job, job_id)
        assert pending is not None
        assert pending.status == JobStatus.PENDING
        assert pending.attempt_count == 0
