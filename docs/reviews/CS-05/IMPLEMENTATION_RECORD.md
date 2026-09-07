# CS-05 — Process Production Integration — Implementation Record

**Status:** IMPLEMENTED / AWAITING PRODUCT OWNER REVIEW
**Prepared:** 2026-09-08
**Execution branch:** `codex/ctx-03`
**Baseline:** `8de9a752b00998f6d1f2a2b24102ba49cf5a1b2a`

## Purpose and non-scope

CS-05 turns one already-completed, validated Process Specialist proposal into
an atomic accepted/active Process Scene, then renders it through the protected
existing `ProcessView`. It adds no new renderer/engine, model call, transport,
generic composition, learning evidence, Personal Fact, Learner Intelligence,
or CS-06 trial.

## Governing boundaries

The implementation follows `CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`, the
CS-05 plan and acceptance specification. Primary Tutor remains the sole
Student-facing teacher; the Specialist is semantic-only; Studio remains the
durable Scene/Event/Snapshot authority; `workspace_intent-v1` is unchanged;
and the older deterministic `process_sequence_workspace` remains separate.

The Product Owner's 2026-09-08 authorization-snapshot decision is applied:
Safety, Parent Boundary, and source rights are resolved by the Primary
Tutor/admission path. An ADMITTED visual order plus its persisted Frozen
Composition Pack is the authorization snapshot for that composition. CS-05
acceptance performs causal, structural, capability, semantic-support, allowed
art-handle, run-eligibility and stale-state checks only; it does not rerun
Safety, Parent Boundary, source rights, Retrieval, or a Tutor/model judgment.
Later policy-setting changes apply prospectively to future visual orders.

## Changed paths and decisions

- Adds `process-visual-production-*-v1`, an additive profile/reducer and a
  short acceptance adapter. It maps only a frozen-supported proposal to the
  existing Process seed shape and validates it before Scene persistence.
- The acceptance unit locks Run, source Tutor lineage and active Scene; it
  rejects stale/deadline/causally mismatched work, then supersedes, accepts,
  activates, snapshots and links the Run in one transaction. A failed unit
  leaves the prior active Scene usable.
- The established Worker settlement calls that adapter only when the existing
  authoritative Studio Snapshot exists. No provider call occurs at completion.
- The existing Runtime-03 path now recognizes the production Process identity,
  so an object or relation request supplies exact replayed object/relation
  provenance to one same-Primary-Tutor continuation.
- The existing `ProcessView` is reused via a small production host adapter;
  focus, reveal and trace remain record-only Studio operations.

## Verification evidence

- Focused Python contracts: **27 passed** (`test_process_production_contract`,
  proposal and existing Process-awareness contracts).
- PostgreSQL CS-05 matrix: **5 passed**. It covers first activation, atomic
  replacement, injected rollback, stale rejection, idempotent re-entry,
  Snapshot replay, record-only focus/reveal/trace and one same-Tutor Runtime-03
  relation explanation with exact source/target relation provenance.
- Fresh combined CS-05 and affected CS-04 PostgreSQL matrix: **37 passed**
  after test-database migration through `e2f6a9c4d8b1`.
- Web typecheck: passed. Next production build: passed.
- Full Python regression: **1,136 passed, 7 skipped, 2 failed, 1 external
  deprecation warning**. The failures are outside CS-05: a Number Line browser
  preflight still hard-codes the prior migration head `c7d8e9f0a1b2` rather
  than the accepted CS-04 head `d1c4a7e2b9f0`; and the pre-existing strategy
  pattern test expected `WEAKENING` but received `CANDIDATE`. The isolated
  CS-04 admission file passed 16/0 and all CS-05-focused/affected matrices
  above passed. These unrelated regressions are retained rather than changed
  under the CS-05 scope.
- Controlled browser harness: the production adapter rendered the existing
  `ProcessView`, emitted exact `FOCUS_OBJECT` on stage activation, and exposed
  semantic keyboard focus. Sanitized local screenshot:
  `output/playwright/cs05-process-production/focus-operation.png` (private
  evidence, intentionally not staged).
- `git diff --check`: passed before review staging.

## Model, quality, and limitations

CS-05 makes zero Specialist calls for focus/reveal/trace and no automatic Tutor
call at Specialist completion. The Runtime-03 test uses one mock primary-Tutor
call and records no fake Student message. No live Luna call, real Student
journey, latency/cost baseline, or production deployment is claimed; those are
CS-06/operations evidence, not substitutes for the verified contracts above.

## Independent review and scope check

The first independent review found three important items: acceptance timing
for Safety/Parent Boundary/source rights, separated semantic/relation support
coverage with `must_not_imply`, and fail-closed browser state parsing. The
Product Owner's authorization-snapshot decision resolves the first without
weakening future Tutor-turn enforcement. The latter two are fixed with focused
regressions and will be checked by the final independent review before this
record is committed. That review checks Scene transaction atomicity,
replay/stale/idempotency boundaries, exact relation provenance, no direct
learning-authority writes, and that the adapter remains the only production
bridge to the existing ProcessView.

The final independent review then found four causal/concurrency gaps: base
Scene identity, newer admitted-order supersession, persisted capability
identity, and Runtime/Run lock order. CS-05 now persists and rechecks the
base Scene ID plus version, supersedes every unaccepted earlier run when a new
order is admitted, validates the persisted Run and Frozen Pack identity, and
uses Runtime-to-Run locking in admission/settlement/acceptance. The fresh
PostgreSQL matrix above passed after those corrections; final re-review is
recorded with the review checkpoint.

## Product Owner disposition

**AWAITING PRODUCT OWNER REVIEW.** This record does not mark CS-05 accepted
and does not authorize CS-06.

## Correction checkpoint

The Product Owner required a durable-proposal boundary and truthful production
trace reconciliation. Settlement now commits the completed Specialist proposal
before opening a separate deterministic acceptance transaction; acceptance
failure cannot erase the proposal or trigger another generation. Production
`TRACE_RELATION` now persists `tracing_relation_id` in authoritative Process
state so the existing ProcessView renders its established trace after reload.

Final affected PostgreSQL verification after the trace-state correction:
**61 passed, 1 external deprecation warning** across CS-05 production,
CS-04 admission/execution, Process awareness, and process-sequence lifecycle
coverage. The matrix caught and fixed one CS-05 admission-ordering regression:
same-transaction Tutor messages share a database timestamp, so only a strictly
later admitted order blocks an older admission. No Candidate, Evidence,
CurrentState, Pattern, Learner Intelligence, or Personal Fact writes are made
by CS-05 Scene acceptance or record-only operations.

## Product Owner acceptance-boundary clarification

The Product Owner clarified that CS-05 is production-integration proof and
CS-06 owns the complete Daily/browser/experience matrix. CS-05 therefore
retains one controlled isolated-review Student smoke of the production Renderer
Host resolving the production Process Scene into the existing ProcessView and
emitting `FOCUS_OBJECT`; its private local capture is
`output/playwright/cs05-process-production/focus-operation.png` and is not
staged. The full sequence/cycle, locale, viewport, pointer/keyboard/touch,
reduced-motion, trace and explanation product-UI matrix remains mandatory and
is explicitly assigned to blocked CS-06.

Focused structural contracts now explicitly cover SEQUENCE at 2 and 8 stages
and CYCLE at 2 stages (**7 passed**). The fresh affected PostgreSQL/lifecycle
matrix is **61 passed, 1 external deprecation warning**. Web typecheck and
production build pass. The prior full-suite result remains unchanged: 1,136
passed, 7 skipped, 2 documented unrelated failures.
