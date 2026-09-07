# CS-04 — Real Canvas Specialist Execution Runtime — Implementation Record

**Status:** IMPLEMENTED / AWAITING PRODUCT OWNER REVIEW
**Prepared:** 2026-09-07
**Execution branch:** `codex/ctx-03`
**Implementation baseline:** `b4b1f605dbddbb1f8309513a566ecf199b44c0b2`

## Purpose

Execute one admitted Canvas Specialist generation through the existing Job,
Worker, Model Gateway and AIExecution architecture, and durably persist a
strict typed Process semantic proposal. This task stops before Scene creation,
acceptance, activation, ProcessView, frontend, or production routing.

## Proposed lifecycle and call invariant

Committed admitted Tutor lineage and an execution-enabled exact Process
capability identity may atomically create one logical Job and one
`StudioCanvasSpecialistRun`. A worker performs a short preflight transaction,
closes it, makes at most one provider call through `ModelTask.CANVAS_SPECIALIST`,
then re-enters a short settlement transaction to record AIExecution and a
validated typed proposal. The Job has `max_attempts=1`; there is no fallback,
critic, repair, automatic retry, or extra Tutor call.

## Likely migration and persistence decision

The existing dormant `StudioCanvasSpecialistRun` seam will be inspected for a
durable proposal body and explicit order/proposal digests. If missing, add the
smallest additive, nullable/backward-compatible migration rather than a new
table. The durable run, not `Job.result`, will own the typed proposal.

## Failure, deadline, and reconciliation model

Preflight validates lineage, deadline, capability identity and causal status.
Provider inference never spans an application database transaction. Expired,
cancelled or superseded work never calls or re-enters the provider. A late
result cannot become usable after supersession/deadline. Unknown provider
outcomes are terminal and never regenerated. Reconciliation must settle a
committed run whose Job missed settlement without inference, and terminally
resolve orphaned final-attempt runs with no durable proposal.

## Planned verification

- focused strict proposal, Gateway, admission/idempotency and Worker tests;
- canonical disposable PostgreSQL admission/concurrency/lifecycle/migration
  proof, including no transaction across inference and crash reconciliation;
- relevant CS-03 Tutor/visual-order regressions;
- compilation and `git diff --check`;
- live Luna proof only when valid configuration is available, recorded
  separately from mock evidence.

## Protected boundaries

No WorkspaceIntent meaning change; no Scene/Event/Snapshot/ProcessView/frontend
change; no renderer/engine/code authority; no direct Safety, Evidence, Personal
Facts or Learner Intelligence effect; no full transcript/retrieval/personal
memory rebuild; and no CS-05 work.

## CS-04A — Admission Foundation

**Status:** VERIFIED

- Migration `d1c4a7e2b9f0` adds only nullable `order_digest`,
  `proposal_payload`, and `proposal_digest` to the dormant run plus the partial
  unique execution identity index `(source_message_id, order_digest,
  capability_profile_version)`. Canonical disposable PostgreSQL upgraded from
  `c7d8e9f0a1b2` through the new revision successfully.
- The application-derived identity is
  `canvas-specialist:{source-message-id}:{order-digest}:process-capability-pack-v1`.
  Job idempotency and the Run partial unique index jointly ensure one logical
  Job/Run; the competing insert is contained in a savepoint and resolves the
  existing Run rather than leaking a uniqueness error.
- Admission reads only a locked committed Tutor message with `ADMITTED` hidden
  visual metadata, canonical frozen-pack digest, matching Student/session/
  runtime, and `process-capability-pack-v1`. Historical
  `SPECIALIST_CAPABILITY_PACK_V1` remains disabled and creates no work.
- PostgreSQL proof: repeated admission, genuine two-session concurrent
  admission, non-requested state, and disabled-pack state passed (**4 passed,
  0 failed, 0 skipped**). Both valid repeated/concurrent cases leave exactly
  one Job (`studio.canvas_specialist.compose.v1`, `max_attempts=1`) and one
  pending Run. No Worker/provider/AIExecution/Scene activity is part of CS-04A.
- Historical Important finding: rollback/orphan and complete wrong-lineage/
  non-executable proof were initially missing. Resolved by failure-injection
  rollback coverage plus explicit foreign-session Tutor, foreign-Student Tutor,
  and non-Tutor-source lineage cases. Each yields bounded
  `SOURCE_LINEAGE_INVALID` with zero Job, Run, or AIExecution side effects.

## Completed execution runtime

- `ModelTask.CANVAS_SPECIALIST` has a provider-neutral Gateway route; the Worker
  registers one bounded `studio.canvas_specialist.compose.v1` handler.
- Preflight opens and commits a short locked transaction, copies only the
  committed frozen pack into a detached envelope, then inference happens with
  no database transaction or row lock held. Settlement uses a separate short
  transaction. The Worker never rebuilds Retrieval or Personal Facts.
- Proposal output is strict Pydantic semantic data; schema, topology, support
  identities, stage bounds and permitted affordances are checked against the
  exact frozen pack. No Scene/Event/Snapshot is created.
- Provider and invalid-proposal failures terminally fail the Run and retain the
  associated AIExecution. Cancellation/supersession/deadline terminal states
  cannot accept a late result. Reconciliation repairs a completed proposal when
  only Job settlement was lost, and marks expired final-attempt outcomes as
  ambiguous terminal failures without another generation.

## Product Owner review corrections after `b4b1f605`

- The executable `runtime/canvas-specialist/process-capability-pack-v1.md` is
  committed and paired with `SKILL.md` for Worker instructions. Historical
  `SPECIALIST_CAPABILITY_PACK_V1` remains disabled and never acts as fallback.
- Persisted Tutor completion automatically admits an `ADMITTED` visual order
  when the Daily session has its matching Studio runtime. It atomically creates
  one `max_attempts=1` Job and one pending Run; null, rejected, redirected, and
  non-Studio paths create neither. Specialist inference remains asynchronous.
- The OpenAI Responses request receives the exact strict Pydantic proposal
  schema with `strict=true`. Every object forbids extra properties and requires
  all properties; absent values are required nullable fields. Focus, motion,
  and affordances are registry-bounded rather than free-form control channels.
- A later admitted order supersedes prior pending/running work for the same
  Studio runtime. Pending work becomes terminal before claim; an already
  started call may finish but cannot make its superseded Run usable. No work is
  regenerated.
- Implementation-control validation uses explicit token/markup/URL/code
  patterns, so “chemical reaction”, “reaction”, and “reactants” remain valid
  while React, Konva, SVG/HTML/JavaScript, URLs, renderer direction, and code
  control remain invalid.
- Deadline-before-inference, invalid proposal, final lease expiry, completed
  Run/lost-Job reconciliation, and terminal Run states are terminal; none
  re-enters the provider.

## Verification

- Canonical disposable PostgreSQL migration through `d1c4a7e2b9f0`: passed.
- Focused CS-04 admission/proposal/Worker/OpenAI/Job matrix: **64 passed, 0
  failed**. It covers Tutor-completion admission, one Job/Run and
  `max_attempts=1`, frozen input, no transaction across inference, strict
  OpenAI schema, lease/final-attempt handling, terminal non-reentry, invalid
  proposal, supersession, and no repair/critic path.
- Affected CS-03 Visual Order/Frozen Pack, Tutor, Studio and Runtime-03 matrix:
  **207 passed, 0 failed, 1 external deprecation warning**.
- Disposable PostgreSQL reset applied all migrations through `d1c4a7e2b9f0`.
- `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with
  pytest python -m compileall -q services workers`: passed.
- `alembic current` on the disposable PostgreSQL database: `d1c4a7e2b9f0
  (head)`.
- `npm run typecheck`, `npm run build`, and `git diff --check`: passed.
- Mock proof confirms one Job (`max_attempts=1`), one Run, one provider call,
  frozen input only, no transaction across inference, durable proposal/AIExecution
  lineage, no Scene/Event/Snapshot and no Evidence/PF/LI writes.
- **LIVE LUNA NOT VERIFIED — CONFIGURATION UNAVAILABLE.** No provider secret was
  read, copied, or exposed; mock evidence is not represented as live evidence.

## Scope and independent review request

Changed CS-04 paths are Gateway/ModelTask, Run migration/model, Visual Order
capability identity, Specialist admission/proposal contracts, Worker handler/
reconciliation, focused tests and this record. No CS-05 Scene acceptance,
renderer/engine authority, frontend, Runtime-03, Evidence, Personal Facts or
Learning Intelligence path is changed. Submit for independent review with the
call-count, no-transaction, terminal lifecycle and no-Scene boundaries checked.
