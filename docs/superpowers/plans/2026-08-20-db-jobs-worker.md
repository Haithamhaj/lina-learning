# DB-Backed Jobs and Worker Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement PostgreSQL-safe DB-backed jobs, a separate worker loop, retries, leases, and database-enforced idempotency for TASK-006.

**Architecture:** `services.platform.jobs` owns the durable SQLAlchemy model,
repository, and enqueue/claim state transitions. `workers.job_worker` owns
registered handler execution and polling. PostgreSQL `FOR UPDATE SKIP LOCKED`
and a partial unique index provide concurrency and idempotency guarantees.

**Tech Stack:** Python 3.11, SQLAlchemy 2, Alembic, PostgreSQL, pytest.

**Spec:** `docs/superpowers/specs/2026-08-20-db-jobs-worker-design.md`

## Global Constraints

- Implement TASK-006 only; do not start TASK-007 or later work.
- Use PostgreSQL locking semantics for queue/concurrency/claim verification.
- Enforce idempotency in the database with a unique partial index.
- Do not add Redis, Celery, cron, a distributed scheduler, dashboards, routes,
  or unrelated platform features.
- Preserve raw learner work and do not move synchronous Tutor turns to jobs.

---

### Task 1: Durable Job Schema and PostgreSQL Test Fixture

**Files:**
- Create: `migrations/versions/0003_jobs_worker_foundation.py`
- Modify: `services/platform/db/models.py`
- Create: `tests/conftest.py`
- Test: `tests/test_jobs_postgres.py`

**Interfaces:**
- Produces `Job`, `JobStatus`, and a `jobs` table with status, payload,
  idempotency, attempt, lease, and audit columns.
- Produces a PostgreSQL test session fixture that skips only when
  `DATABASE_URL` is unavailable.

- [x] **Step 1: Write failing PostgreSQL schema tests**

```python
def test_jobs_table_has_database_idempotency_constraint(postgres_session):
    first = enqueue_job(postgres_session, job_type="fixture", idempotency_key="same")
    duplicate = enqueue_job(postgres_session, job_type="fixture", idempotency_key="same")
    assert duplicate.id == first.id
```

- [x] **Step 2: Run the schema test against PostgreSQL**

Run: `python -m pytest tests/test_jobs_postgres.py -v`

Expected: FAIL because the job model, migration, and enqueue interface do not
exist; SKIP only if `DATABASE_URL` is absent.

- [x] **Step 3: Add the model and migration**

```python
class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(Base):
    __tablename__ = "jobs"
    # id, job_type, payload, idempotency_key, status, attempt_count,
    # max_attempts, run_after, lease_expires_at, result, last_error, timestamps
```

Use a PostgreSQL partial unique index for non-null idempotency keys.

- [x] **Step 4: Apply migration and re-run the PostgreSQL schema test**

Run: `alembic upgrade head && python -m pytest tests/test_jobs_postgres.py -v`

Expected: PASS when PostgreSQL is configured.

### Task 2: Job Repository Lifecycle and Atomic Claim

**Files:**
- Create: `services/platform/jobs/__init__.py`
- Create: `services/platform/jobs/models.py`
- Create: `services/platform/jobs/repository.py`
- Test: `tests/test_jobs_postgres.py`

**Interfaces:**
- Produces `enqueue_job`, `claim_next_job`, `complete_job`, and `fail_job`.
- `claim_next_job(session, worker_id, now)` returns one claimed `Job | None`.

- [x] **Step 1: Write failing lifecycle and concurrency tests**

```python
def test_only_one_postgres_worker_claims_one_pending_job(postgres_session_factory):
    job = enqueue_job(...)
    first = claim_next_job(postgres_session_factory(), worker_id="one", now=NOW)
    second = claim_next_job(postgres_session_factory(), worker_id="two", now=NOW)
    assert first.id == job.id
    assert second is None
```

- [x] **Step 2: Run the focused PostgreSQL lifecycle tests**

Run: `python -m pytest tests/test_jobs_postgres.py -v`

Expected: FAIL because lifecycle and atomic claim operations do not exist.

- [x] **Step 3: Implement lifecycle methods**

Use `select(Job).where(...).with_for_update(skip_locked=True)` inside one
transaction. Include expired running leases as eligible claims. On handler
failure, schedule retry or mark `FAILED` after the last attempt.

- [x] **Step 4: Re-run focused PostgreSQL lifecycle tests**

Run: `python -m pytest tests/test_jobs_postgres.py -v`

Expected: PASS when PostgreSQL is configured.

### Task 3: Separate Worker Process and Handler Registry

**Files:**
- Create: `workers/__init__.py`
- Create: `workers/job_worker.py`
- Test: `tests/test_jobs_postgres.py`

**Interfaces:**
- Produces `JobHandler`, `JobHandlerRegistry`, `run_once`, and `run_forever`.
- `run_once(session_factory, registry, worker_id, now)` processes zero or one
  job and returns its final status or `None`.

- [x] **Step 1: Write failing worker behavior tests**

```python
def test_run_once_completes_a_claimed_job(postgres_session_factory):
    registry = JobHandlerRegistry({"fixture": lambda job: {"ok": True}})
    assert run_once(...) is JobStatus.COMPLETED
```

- [x] **Step 2: Run worker tests against PostgreSQL**

Run: `python -m pytest tests/test_jobs_postgres.py -v`

Expected: FAIL because no worker module exists.

- [x] **Step 3: Implement the registry and worker**

Keep `run_once` deterministic and let `run_forever` call it with an idle sleep.
Catch handler exceptions only to invoke `fail_job`; do not log payloads.

- [x] **Step 4: Re-run worker tests**

Run: `python -m pytest tests/test_jobs_postgres.py -v`

Expected: PASS when PostgreSQL is configured.

### Task 4: Verification and Operational-State Handoff

**Files:**
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`

- [x] **Step 1: Run complete verification**

Run: `python -m pytest`, `npm run typecheck`, and `npm run build`.

Expected: all executable checks pass; state exactly why any PostgreSQL-only or
external-S3 test was skipped.

- [x] **Step 2: Inspect migration and invariant impact**

Run: `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head`,
and `git diff --check`.

Expected: schema can be rebuilt, jobs do not change protected learning
semantics, and no whitespace errors remain.

- [x] **Step 3: Update operational records after successful verification**

Mark TASK-006 `DONE`, record the PostgreSQL jobs/worker foundation and its
lease/idempotency boundaries in `PROJECT_STATE.md`, leave TASK-007 and TASK-008
as `READY`, and leave later tasks blocked.
