# DB-Backed Jobs and Worker Foundation Design

## Goal

Provide durable, PostgreSQL-backed asynchronous work for document processing,
session consolidation, and rebuilds without Redis, Celery, cron, or a new
service.

## Scope

This design implements only TASK-006. It does not add content processing,
session consolidation logic, API endpoints, dashboards, scheduling products,
or any TASK-007+ functionality.

## Architecture

`services.platform.jobs` owns job persistence and lifecycle transitions. A
separate `workers` process owns polling and handler execution. API routes and
future domain services enqueue through the job service; they never claim or
execute jobs themselves.

The `jobs` table is authoritative. It stores a stable job type, JSON payload,
optional database-enforced idempotency key, attempt/lease timing, outcome, and
safe failure text. PostgreSQL workers claim one eligible row inside a
transaction using `SELECT … FOR UPDATE SKIP LOCKED`, so concurrent workers
cannot both claim the same row.

## Lifecycle

```text
enqueue
  -> PENDING
  -> RUNNING (leased by one worker)
  -> COMPLETED
  -> or PENDING (retry scheduled after handler failure)
  -> or FAILED (retry budget exhausted)

expired RUNNING lease -> PENDING claim by a later worker
```

`attempt_count` increments when a worker claims a job. A failure before the
maximum attempt count stores a bounded error summary and schedules `run_after`
using deterministic backoff. A final failure remains auditable as `FAILED`.

## Idempotency and Concurrency

When an enqueuer supplies `idempotency_key`, PostgreSQL enforces uniqueness on
`(job_type, idempotency_key)` with a partial unique index. The enqueue method
returns the existing row when that database constraint reports a collision;
application-side pre-checks are not relied upon for correctness.

The PostgreSQL integration tests prove both properties with real database
transactions: concurrent claims produce exactly one winner, and duplicate
idempotent enqueue attempts create exactly one row. SQLite is not used as a
substitute for those semantics. If `DATABASE_URL` is unavailable, the relevant
tests remain explicitly skipped rather than silently changing database behavior.

Each claim also receives a fresh, opaque lease token. A worker must supply that
token when recording success or failure, so an expired worker cannot settle a
job that a recovery worker has re-leased, even if both workers use the same
host-derived worker identifier.

## Worker Contract

Handlers implement a small callable contract: `handler(job) -> result mapping`.
The registry is explicitly populated by future owning tasks; this foundation
ships a test handler only. `run_once` claims and handles at most one job, making
behavior deterministic for tests and controlled invocations. `run_forever`
polls with a configurable idle delay. Neither logs job payloads nor adds
distributed scheduling.

## Data and Safety Boundaries

- Interactive Tutor turns remain synchronous/streaming.
- Derived processing is versionable and rebuildable; job rows are operational
  records and do not alter raw learner work.
- Lease recovery prevents a worker crash from permanently stranding a job.
- Job payloads/results use JSON but are not exposed through a new API surface.

## Verification

1. PostgreSQL integration tests cover lifecycle success, retry/final failure,
   idempotent duplicate enqueue, concurrent `SKIP LOCKED` claiming, expired
   lease recovery, and stale-lease settlement rejection.
2. Relevant migration/model tests run against PostgreSQL when configured.
3. The complete Python suite, TypeScript check, and production build run before
   TASK-006 is marked DONE.
