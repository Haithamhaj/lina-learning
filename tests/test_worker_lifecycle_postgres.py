"""Disposable PostgreSQL contracts for wake, drain, and scheduled recovery."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event, Thread
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.config import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.db.models import Job, JobStatus, LearningSession, Student, User, WorkerActivity, WorkerLifecycleState
from services.platform.db.session import get_session
from services.platform.jobs import JobStateError, claim_next_job, enqueue_job, renew_job_lease
from services.platform import worker_lifecycle as lifecycle
from workers.job_worker import JobHandlerRegistry, run_once
from workers import job_worker as worker_module

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Disposable PostgreSQL required")
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
TEST_JOB_TYPE = "content.structural_process"


class FakePool:
    def __init__(self, count: int = 0):
        self.count = count
        self.calls: list[int] = []
        self.fail_next: int | None = None
        self.on_scale = None
        self.reconciling = False
        self.operation_done = True
        self.operation_error = None

    def get_pool(self) -> dict:
        return {"scaling": {"manualInstanceCount": self.count}, "reconciling": self.reconciling}

    def set_instances(self, count: int) -> str:
        if self.fail_next == count:
            self.fail_next = None
            raise RuntimeError("simulated Cloud Run outage")
        self.calls.append(count)
        if self.on_scale is not None:
            self.on_scale(count)
        self.count = count
        return f"projects/test/locations/local/operations/{len(self.calls)}"

    def get_operation(self, name: str) -> dict:
        return {"done": self.operation_done, "error": self.operation_error}


@pytest.fixture
def configured(monkeypatch) -> Settings:
    settings = Settings(
        worker_lifecycle_enabled=True,
        worker_pool_project_id="test",
        worker_pool_region="local",
        worker_pool_name="lina-worker",
        worker_lifecycle_scheduler_audience="https://example.test/tick",
        worker_lifecycle_scheduler_email="scheduler@example.test",
    )
    monkeypatch.setattr(lifecycle, "get_settings", lambda: settings)
    return settings


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, users, worker_activity CASCADE"))
        connection.execute(text("UPDATE worker_lifecycle_state SET stop_requested=false, operation_name=NULL, operation_target=NULL WHERE id=1"))
    result = sessionmaker(engine, expire_on_commit=False)
    yield result
    engine.dispose()


def reconcile(factory, pool, settings, at):
    return lifecycle.reconcile_worker_pool(session_factory=factory, client=pool, settings=settings, now=at)


def activity(factory, at):
    with factory.begin() as session:
        lifecycle.record_user_activity(session, now=at)


def job(factory, *, at, status=JobStatus.PENDING.value, lease_expires_at=None):
    with factory.begin() as session:
        item = enqueue_job(session, job_type=TEST_JOB_TYPE, payload={}, run_after=at)
        item.status = status
        item.lease_expires_at = lease_expires_at
        return item.id


def test_single_and_concurrent_user_activity_extend_one_global_window(factory, configured):
    pool = FakePool()
    activity(factory, NOW)
    assert reconcile(factory, pool, configured, NOW) == "waking"
    assert pool.calls == [1]
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=9)) == "active"
    # A different user action has the same global effect; no tab heartbeat runs.
    activity(factory, NOW + timedelta(minutes=9))
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=11)) == "active"
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=28)) == "active"
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=29)) == "stopping"
    assert pool.calls == [1, 0]
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=30)) == "stopped"
    activity(factory, NOW + timedelta(minutes=31))
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=31)) == "waking"
    assert pool.calls == [1, 0, 1]


def test_running_job_blocks_stop_and_future_retry_wakes_after_zero(factory, configured):
    pool = FakePool(1)
    activity(factory, NOW)
    running_id = job(factory, at=NOW, status=JobStatus.RUNNING.value, lease_expires_at=NOW + timedelta(minutes=20))
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21)) == "active"
    with factory.begin() as session:
        running = session.get(Job, running_id)
        running.status = JobStatus.COMPLETED.value
    retry_id = job(factory, at=NOW + timedelta(minutes=25))
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=22)) == "stopping"
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=25)) == "waking"
    with factory() as session:
        assert session.get(Job, retry_id).status == JobStatus.PENDING.value
    assert pool.calls == [0, 1]


def test_immediately_runnable_job_prevents_stop_and_claim_gate_blocks_while_stopped(factory, configured):
    pool = FakePool(1)
    activity(factory, NOW)
    item_id = job(factory, at=NOW)
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21)) == "active"
    assert pool.calls == []
    with factory.begin() as session:
        state = session.get(WorkerLifecycleState, 1)
        state.stop_requested = True
    registry = JobHandlerRegistry()
    registry.register(TEST_JOB_TYPE, lambda item: {"ok": True})
    assert run_once(factory, registry, worker_id="test", now=NOW + timedelta(minutes=11)) is None
    with factory() as session:
        assert session.get(Job, item_id).status == JobStatus.PENDING.value
    with factory.begin() as session:
        session.get(WorkerLifecycleState, 1).stop_requested = False
    assert run_once(factory, registry, worker_id="test", now=NOW + timedelta(minutes=11)) == JobStatus.COMPLETED
    assert run_once(factory, registry, worker_id="test", now=NOW + timedelta(minutes=11)) is None


def test_shutdown_cloud_failure_leaves_claims_open_and_retries(factory, configured):
    pool = FakePool(1)
    pool.fail_next = 0
    activity(factory, NOW)
    with pytest.raises(RuntimeError, match="Cloud Run outage"):
        reconcile(factory, pool, configured, NOW + timedelta(minutes=21))
    with factory() as session:
        assert session.get(WorkerLifecycleState, 1).stop_requested is False
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=22)) == "stopping"


def test_activity_arriving_during_shutdown_is_recovered(factory, configured):
    pool = FakePool(1)
    activity(factory, NOW)
    pool.on_scale = lambda count: activity(factory, NOW + timedelta(minutes=21)) if count == 0 else None
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21)) == "stop_raced_with_demand"
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21, seconds=1)) == "waking"
    assert pool.calls == [0, 1]


def test_tick_closes_session_after_existing_policy_and_wakes_its_pipeline(factory, configured, monkeypatch):
    from services.platform.jobs import repository

    monkeypatch.setattr(repository, "_utc_now", lambda: NOW)
    pool = FakePool(0)
    with factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning = LearningSession(
            student_id=student.id,
            status="OPEN",
            last_activity_at=NOW - timedelta(minutes=26),
        )
        session.add(learning)
        session.flush()
        learning_id = learning.id
    assert reconcile(factory, pool, configured, NOW) == "waking"
    with factory() as session:
        assert session.get(LearningSession, learning_id).status == "CLOSED"
        assert session.scalar(select(Job.id).where(Job.job_type == "SESSION_INTELLIGENCE_FINALIZE")) is not None


def test_lost_notification_and_duplicate_tick_converge_from_database(factory, configured):
    pool = FakePool(0)
    activity(factory, NOW)
    assert reconcile(factory, pool, configured, NOW) == "waking"
    assert reconcile(factory, pool, configured, NOW) == "active"
    assert pool.calls == [1]


def test_concurrent_users_keep_the_latest_activity(factory, configured):
    gate = Barrier(2)
    errors = []

    def mark(at):
        try:
            gate.wait()
            activity(factory, at)
        except Exception as error:
            errors.append(error)

    threads = [
        Thread(target=mark, args=(NOW,)),
        Thread(target=mark, args=(NOW + timedelta(minutes=4),)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert not errors
    pool = FakePool(1)
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=23)) == "active"
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=24)) == "stopping"


def test_failed_start_is_retried_by_a_later_tick(factory, configured):
    pool = FakePool(0)
    pool.fail_next = 1
    activity(factory, NOW)
    with pytest.raises(RuntimeError, match="Cloud Run outage"):
        reconcile(factory, pool, configured, NOW)
    assert pool.count == 0
    assert reconcile(factory, pool, configured, NOW + timedelta(seconds=30)) == "waking"
    assert pool.calls == [1]


def test_unhandled_queue_row_does_not_hold_the_pool_running(factory, configured):
    pool = FakePool(1)
    with factory.begin() as session:
        enqueue_job(session, job_type="unsupported.old.job", payload={}, run_after=NOW)
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21)) == "stopping"
    assert pool.calls == [0]


def test_active_pool_wake_uses_the_database_fast_path(factory, configured, monkeypatch):
    pool = FakePool(1)
    activity(factory, NOW)
    assert reconcile(factory, pool, configured, NOW) == "active"
    monkeypatch.setattr(lifecycle, "get_engine", lambda: factory.kw["bind"])
    monkeypatch.setattr(lifecycle, "reconcile_worker_pool", lambda: pytest.fail("unexpected cloud call"))
    lifecycle.request_worker_wake()
    # More messages during an accepted start operation only extend activity;
    # the scheduled tick follows the operation and repairs a failure.
    with factory.begin() as session:
        state = session.get(WorkerLifecycleState, 1)
        state.operation_name = "projects/test/locations/local/operations/pending"
    lifecycle.request_worker_wake()


def test_failed_cloud_operation_clears_gate_and_surfaces_failure(factory, configured):
    pool = FakePool(0)
    activity(factory, NOW)
    assert reconcile(factory, pool, configured, NOW) == "waking"
    pool.operation_error = {"code": 7, "message": "simulated permission denial"}
    pool.count = 0
    assert reconcile(factory, pool, configured, NOW + timedelta(seconds=1)) == "operation_failed"
    with factory() as session:
        state = session.get(WorkerLifecycleState, 1)
        assert state.stop_requested is False
        assert state.operation_name is None
    pool.operation_error = None
    assert reconcile(factory, pool, configured, NOW + timedelta(seconds=2)) == "waking"


def test_pending_stop_operation_waits_before_rewake(factory, configured):
    pool = FakePool(1)
    activity(factory, NOW)
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21)) == "stopping"
    pool.operation_done = False
    activity(factory, NOW + timedelta(minutes=21))
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21, seconds=1)) == "operation_pending"
    assert pool.calls == [0]
    pool.operation_done = True
    assert reconcile(factory, pool, configured, NOW + timedelta(minutes=21, seconds=2)) == "waking"
    assert pool.calls == [0, 1]


def test_authenticated_session_open_signals_wake_but_status_read_does_not(factory, configured, monkeypatch):
    from apps.api.main import app
    from apps.api.routes import student as student_routes

    with factory.begin() as session:
        user = User(identity_provider="clerk", external_subject="worker-lifecycle-student", role="STUDENT")
        session.add(user)
        session.flush()
        session.add(Student(user_id=user.id))

    def database_session():
        with factory() as session:
            yield session

    hints = []
    monkeypatch.setattr(student_routes, "request_worker_wake", lambda: hints.append("wake"))
    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject="worker-lifecycle-student", role=UserRole.STUDENT, email=None,
    )
    try:
        client = TestClient(app)
        opened = client.post("/api/v1/student/daily/session")
        assert opened.status_code == 200
        with factory() as session:
            first_activity = session.get(WorkerActivity, 1).last_user_activity_at
        session_id = opened.json()["learning_session_id"]
        assert client.get(f"/api/v1/student/daily/session/{session_id}").status_code == 200
        with factory() as session:
            assert session.get(WorkerActivity, 1).last_user_activity_at == first_activity
        assert hints == ["wake"]
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)


def test_concurrent_controller_ticks_issue_one_start(factory, configured):
    pool = FakePool(0)
    activity(factory, NOW)
    gate = Barrier(2)
    results = []

    def tick():
        gate.wait()
        results.append(reconcile(factory, pool, configured, NOW))

    threads = [Thread(target=tick), Thread(target=tick)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert sorted(results) == ["active", "waking"]
    assert pool.calls == [1]


def test_voice_activity_uses_separate_transaction_without_closing_request(factory, configured, monkeypatch):
    hints = []
    monkeypatch.setattr(lifecycle, "request_worker_wake", lambda: hints.append("wake"))
    with factory.begin() as session:
        lifecycle.record_user_activity_immediately(session)
        # The transcription request can still write through its original scope.
        assert session.scalar(select(WorkerActivity.id).where(WorkerActivity.id == 1)) == 1
    assert hints == ["wake"]


def test_renewed_lease_prevents_a_second_worker_claim_after_original_expiry(factory, configured):
    item_id = job(factory, at=NOW)
    with factory.begin() as session:
        claimed = claim_next_job(session, worker_id="first", now=NOW)
        assert claimed is not None and claimed.id == item_id
        token = claimed.lease_token
    with factory.begin() as session:
        renewed = renew_job_lease(
            session, item_id, worker_id="first", lease_token=token,
            now=NOW + timedelta(minutes=4),
        )
        assert renewed.lease_expires_at == NOW + timedelta(minutes=9)
    with factory.begin() as session:
        assert claim_next_job(session, worker_id="second", now=NOW + timedelta(minutes=6)) is None
    with pytest.raises(JobStateError):
        with factory.begin() as session:
            renew_job_lease(session, item_id, worker_id="other", lease_token=token)


def test_running_handler_renews_its_lease_before_settlement(factory, configured, monkeypatch):
    item_id = job(factory, at=datetime.now(UTC))
    renewed = Event()
    original = worker_module.renew_job_lease
    monkeypatch.setattr(worker_module, "LEASE_RENEWAL_INTERVAL_SECONDS", 0.02)

    def observe_renewal(*args, **kwargs):
        result = original(*args, **kwargs)
        renewed.set()
        return result

    monkeypatch.setattr(worker_module, "renew_job_lease", observe_renewal)
    registry = JobHandlerRegistry()
    registry.register(TEST_JOB_TYPE, lambda item: {"renewed": renewed.wait(timeout=2)})
    assert run_once(factory, registry, worker_id="long-handler") == JobStatus.COMPLETED
    assert renewed.is_set()
    with factory() as session:
        assert session.get(Job, item_id).result == {"renewed": True}
