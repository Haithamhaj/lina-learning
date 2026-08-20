# Lina Personal Learning System — Project State

## Current goal

Restore the Production Learning Engine acceptance path from the independently
audited implementation. The active goal is to repair and verify the Content,
Tutor, and Learning Intelligence contracts before any real-Lina calibration or
product expansion. TASK-011 is the immediate remediation target.

## Current reality

- An independent implementation audit found that the existing development
  sandbox proves useful plumbing, but does **not** prove the Production Learning
  Engine or Phase 3 complete. The affected TASK-011 through TASK-026 work has
  been reopened in `TASKS.md`.
- Verified foundation infrastructure remains usable: typed configuration,
  PostgreSQL/Alembic/pgvector foundation, Clerk role boundaries, private object
  storage, PostgreSQL jobs/worker foundation, Model Gateway/AI ledger,
  SafetyDecision persistence, source-document provenance, and Parent/Admin
  source upload.
- The local Eureka Grade 5 PDF and Sandbox/Test Learner remain development/test
  fixtures only. Existing structural, retrieval, Tutor, Candidate Event, and
  derived-intelligence code remains available as a remediation baseline, not as
  a production-complete engine claim.
- No real-Lina calibration, Phase 1/2/3 exit claim, or later product expansion
  is currently authorized.

## Active decisions

- Use a modular monolith; retain verified infrastructure unless a concrete
  contract or maintenance reason requires change.
- Existing implementation has **no sunk-cost protection**. If it does not
  satisfy an approved contract, it may be replaced cleanly rather than patched
  superficially. Independently verified infrastructure should not be rewritten
  without cause.
- A task is not production-complete merely because its demo works or its
  implementing agent marked it `DONE`. Its stated verification criteria must
  pass and the implementation must match the governing contract.
- Preserve raw sources, raw interactions, provenance, rebuildability,
  Model-Gateway-only AI routing, explicit runtime safety enforcement, and the
  Evidence → State/Pattern → Intelligence Card architecture.
- Keep the approved reuse decisions and dependency-light platform direction;
  do not add new infrastructure merely to remediate a contract gap.

## Protected areas

Evidence-first intelligence; current behavior outranking historical
personalization; raw-source preservation; layered child safety and Parent
Learning Boundaries; one primary Tutor call; derived mastery/confidence views;
rebuildability; modular-monolith architecture; and the required calibration and
Real Lina decision gates.

## Active risks

- TASK-011 must restore a versioned, source-linked Docling structural
  representation that preserves hierarchy before semantic extraction,
  indexing, retrieval, Tutor, or intelligence remediation becomes actionable.
- The temporary local PostgreSQL instance is appropriate for the sandbox demo
  but not for destructive integration tests. A disposable PostgreSQL test
  database/workflow remains a deferred local-development improvement.
- Real AWS/S3 staging verification remains deferred and non-blocking; do not
  request credentials or remove the existing S3 implementation.
- The following remain frozen until the Production Engine Acceptance Gate
  passes: Lina Validation UI beyond the existing surface; Science; Voice/STT;
  production Vision/handwriting/drawing; Learning Canvas; Interactive Artifact
  Engine; advanced motion/gamification; Grade-transition production work; and
  Phase 4 and later work.

## Next recommended action

Implement and verify **TASK-011 — Docling Structural Representation** only.
Do not start TASK-012 or later work until TASK-011 satisfies its approved
contract and verification criteria.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`
- Independent implementation audit (REC-01 remediation basis)
