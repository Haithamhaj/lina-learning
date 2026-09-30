"""External controller for Lina's manually scaled Cloud Run worker pool.

The app and Scheduler run this code. The worker only observes the claim gate;
neither timers nor wake notifications depend on a running worker instance.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from services.platform.config import Settings, get_settings
from services.platform.db.connection import get_engine
from services.platform.db.models import Job, JobStatus, WorkerActivity, WorkerLifecycleState
from services.tutor.session_lifecycle import close_inactive_sessions

_logger = logging.getLogger(__name__)

# Keep this aligned with the registrations in workers/job_worker.py. Unknown
# historical rows must not hold the pool at one instance forever.
EXECUTABLE_JOB_TYPES = frozenset({
    "content.structural_process",
    "content.structural_index",
    "SESSION_CONSOLIDATION",
    "SESSION_INTELLIGENCE_FINALIZE",
    "SEGMENT_LEARNING_REVIEW",
    "INTELLIGENCE_REPROCESS",
    "LEARNING_INTELLIGENCE_PROJECTION_REFRESH",
    "PERSONAL_FACTS_EXTRACTION",
    "studio.canvas_specialist.compose.v1",
    "studio.agentic_canvas.compose.v1",
})


def record_user_activity(session: Session, *, now: datetime | None = None) -> None:
    """Record a real authenticated action in its existing transaction."""

    if not get_settings().worker_lifecycle_enabled:
        return
    occurred_at = now or datetime.now(UTC)
    statement = insert(WorkerActivity).values(id=1, last_user_activity_at=occurred_at)
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[WorkerActivity.id],
            set_={"last_user_activity_at": func.greatest(
                WorkerActivity.last_user_activity_at, statement.excluded.last_user_activity_at,
            )},
        )
    )


def record_user_activity_immediately(session: Session) -> None:
    """Stamp a validated long-running request without closing its own transaction."""

    if not get_settings().worker_lifecycle_enabled:
        return
    with Session(session.get_bind()) as activity_session:
        with activity_session.begin():
            record_user_activity(activity_session)
    request_worker_wake()


def request_worker_wake() -> None:
    """Request scaling before the HTTP response ends; the tick repairs failures."""

    if not get_settings().worker_lifecycle_enabled:
        return
    try:
        if _pool_requested_on():
            return
        result = reconcile_worker_pool()
        if result in {"operation_failed", "unhealthy"}:
            _logger.error("Worker wake needs operator attention: %s", result)
    except Exception:
        _logger.exception("Worker wake request failed; scheduled reconciliation will retry")


def _pool_requested_on() -> bool:
    """Avoid a cloud read on each turn, while serializing with idle shutdown."""

    factory = sessionmaker(get_engine(), expire_on_commit=False)
    with factory.begin() as session:
        state = session.scalar(
            select(WorkerLifecycleState).where(WorkerLifecycleState.id == 1).with_for_update()
        )
        return bool(
            state is not None and not state.stop_requested
            and state.operation_target == 1
        )


class CloudRunWorkerPoolClient:
    """Narrow Cloud Run Admin API adapter using the app service identity."""

    def __init__(self, settings: Settings):
        self.pool_name = (
            f"projects/{settings.worker_pool_project_id}/locations/"
            f"{settings.worker_pool_region}/workerPools/{settings.worker_pool_name}"
        )

    def _request(self, url: str, *, method: str = "GET", body: dict | None = None) -> dict:
        token_request = Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urlopen(token_request, timeout=5) as response:
            token = json.load(response)["access_token"]
        request = Request(
            url,
            data=None if body is None else json.dumps(body).encode("utf-8"),
            method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    def get_pool(self) -> dict:
        return self._request(f"https://run.googleapis.com/v2/{self.pool_name}")

    def set_instances(self, count: int) -> str:
        if count not in (0, 1):
            raise ValueError("The Lina worker controller only supports zero or one instance.")
        response = self._request(
            f"https://run.googleapis.com/v2/{self.pool_name}?update_mask=scaling.manualInstanceCount",
            method="PATCH",
            body={"scaling": {"manualInstanceCount": count}},
        )
        name = response.get("name")
        if not isinstance(name, str) or not name.startswith("projects/"):
            raise RuntimeError("Cloud Run did not return a worker-pool operation name.")
        return name

    def get_operation(self, name: str) -> dict:
        if not name.startswith("projects/") or "/operations/" not in name:
            raise ValueError("Invalid worker-pool operation name.")
        return self._request(f"https://run.googleapis.com/v2/{name}")


def _has_demand(session: Session, *, now: datetime, idle_seconds: int) -> bool:
    last_activity = session.scalar(select(WorkerActivity.last_user_activity_at).where(WorkerActivity.id == 1))
    if last_activity is not None and last_activity > now - timedelta(seconds=idle_seconds):
        return True
    runnable_or_running = or_(
        and_(
            Job.status == JobStatus.PENDING.value,
            Job.run_after <= now,
            Job.job_type.in_(EXECUTABLE_JOB_TYPES),
        ),
        # A prior revision may still be executing an unfamiliar job during a
        # rollout. Never scale it down solely because its type is unfamiliar.
        Job.status == JobStatus.RUNNING.value,
    )
    return session.scalar(select(Job.id).where(runnable_or_running).limit(1)) is not None


def _count(pool: dict) -> int:
    scaling = pool.get("scaling")
    if not isinstance(scaling, dict):
        raise RuntimeError("Worker pool has no manual scaling configuration.")
    # Cloud Run may omit a zero-valued proto field from the JSON response.
    count = scaling.get("manualInstanceCount", 0)
    if type(count) is not int or count not in (0, 1):
        raise RuntimeError("Worker pool is not in the expected zero-or-one manual scaling mode.")
    return count


def _finish_operation(client: CloudRunWorkerPoolClient, state: WorkerLifecycleState) -> str:
    if state.operation_name is None:
        return "done"
    operation = client.get_operation(state.operation_name)
    if not operation.get("done"):
        return "pending"
    state.operation_name = None
    if operation.get("error"):
        state.operation_target = None
        state.stop_requested = False
        _logger.error("Worker-pool scaling operation failed: %s", operation["error"])
        return "failed"
    return "done"


def reconcile_worker_pool(
    *,
    session_factory: sessionmaker[Session] | None = None,
    client: CloudRunWorkerPoolClient | None = None,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> str:
    """Converge one pool under the durable claim gate; safe for duplicate callers."""

    configured = settings or get_settings()
    if not configured.worker_lifecycle_enabled:
        return "disabled"
    factory = session_factory or sessionmaker(get_engine(), expire_on_commit=False)
    cloud = client or CloudRunWorkerPoolClient(configured)
    current = now or datetime.now(UTC)
    def demand_time() -> datetime:
        # Closing a session can enqueue a job a few microseconds after the
        # initial tick timestamp. Include it in this same reconciliation.
        return now or datetime.now(UTC)

    with factory.begin() as session:
        state = session.scalar(
            select(WorkerLifecycleState).where(WorkerLifecycleState.id == 1).with_for_update()
        )
        if state is None:
            raise RuntimeError("Worker lifecycle migration has not been applied.")
        # This policy also runs while the worker is at zero. The existing
        # idempotent finalization and Learning Intelligence jobs are unchanged.
        close_inactive_sessions(session, now=current)
        if state.operation_name is not None:
            operation_status = _finish_operation(cloud, state)
            if operation_status != "done":
                return f"operation_{operation_status}"

        pool = cloud.get_pool()
        count = _count(pool)
        state.operation_target = count
        demand = _has_demand(session, now=demand_time(), idle_seconds=configured.worker_lifecycle_idle_seconds)
        if demand:
            state.stop_requested = False
            if pool.get("reconciling"):
                return "cloud_reconciling"
            if count == 0:
                state.operation_name = cloud.set_instances(1)
                state.operation_target = 1
                return "waking"
            if pool.get("terminalCondition", {}).get("state") == "CONDITION_FAILED":
                _logger.error("Worker pool reports failed readiness while demand exists")
                return "unhealthy"
            return "active"

        if count == 0:
            state.stop_requested = True
            return "stopped"
        if pool.get("reconciling"):
            return "cloud_reconciling"

        # Claim attempts take the same row lock before leasing a job. This
        # closes the claim-vs-stop race without blocking activity writes.
        state.stop_requested = True
        session.flush()
        if _has_demand(session, now=demand_time(), idle_seconds=configured.worker_lifecycle_idle_seconds):
            state.stop_requested = False
            return "stop_cancelled"
        try:
            state.operation_name = cloud.set_instances(0)
            state.operation_target = 0
        except Exception:
            state.stop_requested = False
            raise
        # A new action/job can commit while the Cloud Run call is in flight.
        # Its notification or the next scheduled tick completes a pending
        # stop operation, then restores one instance. Recheck immediately too.
        if _has_demand(session, now=demand_time(), idle_seconds=configured.worker_lifecycle_idle_seconds):
            return "stop_raced_with_demand"
        return "stopping"


def worker_claim_allowed(session: Session) -> bool:
    """Lock the claim gate in the same transaction as claim_next_job."""

    if not get_settings().worker_lifecycle_enabled:
        return True
    state = session.scalar(
        select(WorkerLifecycleState).where(WorkerLifecycleState.id == 1).with_for_update()
    )
    if state is None:
        raise RuntimeError("Worker lifecycle migration has not been applied.")
    return not state.stop_requested
