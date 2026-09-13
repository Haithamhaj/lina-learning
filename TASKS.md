# Lina execution queue

An explicit current Product Owner instruction authorizes its requested working slice. Status labels provide operational context; roadmap presence alone does not authorize implementation.

## Current completed baseline

| Task | Status | Scope / evidence |
| --- | --- | --- |
| REPO-TRUTH-01..05 | DONE | Repository truth, cleanup, canonical mainline, and protection work completed. |
| PRODUCT-IDENTITY-01 | DONE | Product identity/philosophy reconciled. |
| STUDIO-AGENTIC-01 | DONE | Tutor-led Agentic Canvas, bounded Agents SDK composition, typed Scene settlement, generated-asset lineage, interactions, same-Tutor continuity, replay, real-provider proof. |
| CANVAS-VISUAL-INTELLIGENCE-01 | DONE | Filtered visual learner context, Scene v2 presentation persistence, stronger visual skills, deterministic geometry rendering, disposable PostgreSQL and production-renderer browser proof. |

## Active implementation

### CANVAS-DEVELOPMENT-REVIEW-01 — Independent engineering evidence and AI reports

**Status:** DONE — local engineering slice; reviewer accuracy is not accepted.
**Authority:** Product Owner requested a separate retained development path and AI reports; explicit OpenAI evidence transmission approved 2026-09-13.
**Scope:** Operator CLI, existing run index, bounded independent evidence captures, private screenshots/source, one-shot Model Gateway review, cited Arabic recommendations; no student intelligence writes or runtime hooks.
**Verification:** 39 focused review/provider tests passed. Full integrated regression: 1426 passed, 12 skipped (68.95 s) on isolated PostgreSQL 55438. Additive migration verified on isolated databases; actual six-image OpenAI report saved with unchanged source-record counts. Repository truth/diff checks passed.
**Limit:** First real report missed a known grid-scale defect. Review generation is proven; reviewer accuracy and educational effectiveness are not accepted. No dashboard, automatic collection, merge or deployment.
**Reference:** `docs/proposals/CANVAS-DEVELOPMENT-REVIEW.md`.


### FULL-POWER-CANVAS-HARDENING — Production autonomy and measured quality

**Status:** DONE — engineering/build closure; production-use acceptance remains a separate phase
**Authority:** Product Owner request 2026-09-12, continued 2026-09-13.
**Baseline:** `ebac3fef92427ac203d241f7cd60eafdb1187c6c`.
**Scope:** General production preview/interaction/replay and bounded same-Luna review;
instruction reconciliation; measured CREATE/REUSE efficiency and observability;
diverse wide/narrow live acceptance without developer source repair.
**Verification:** Focused contract/browser/security tests during implementation;
one integrated regression near closure; six diverse real-Luna cases with actual
browser interactions and quality review; before/after timing/token/cost evidence.
**Result:** 1420 integrated tests passed, 12 skipped. Desktop-only acceptance is ACTIVE after early independent review, canonical state diagnostics, capability-aware REUSE and reliable screenshot capture. True qualified REUSE and desktop ADAPT lineage/browser handoffs are verified; individual fraction, balance and Arabic sentence CREATE interactions work. Broad CREATE reliability remains unaccepted; the final captured Canvas configuration completed 2/6 protocols, with a human-detected semantic false acceptance in reflection. See `docs/FULL-POWER-CANVAS-HARDENING.md` and its portable metrics for measured evidence.
**Closure:** Branch publication is authorized. No merge or deployment. Broad production CREATE reliability, authenticated Daily use and learning benefit remain separate production-use gates.


### FULL-POWER-CANVAS-01 — Full-Power Hybrid Canvas

**Status:** DONE — local engineering closure; no push/merge/deployment
**Authority:** Product Owner approved `docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md`
**Baseline:** `62df59bcc8c43074c223d79b73bcf97a0905ed4c`
**Closure evidence:** `docs/FULL-POWER-CANVAS-01_CLOSURE.md` (actual persisted CREATE/REUSE/ADAPT, screenshots, source-review lineage and evidence limits).
**Execution mode:** continuous native Codex; no Superpowers; no Product Owner checkpoints except protected blockers.

**Purpose:** Remove the expressive visual ceiling while preserving Tutor authority, Studio persistence, filtered learner context, safety, ownership, provenance, and cost observability.

**Target output:**

```text
Tutor
→ CanvasBrief + bounded learner context
→ Full-Power Canvas Agent
→ REUSE / ADAPT / CREATE
→ typed/reusable/custom visual runtime
→ safe sandbox where generated code runs
→ Semantic Manifest + Studio
→ same Tutor
```

### Ordered work items

#### FPC-01 — Governance and contract foundations
**Dependencies:** completed baseline only
**Purpose:** Reconcile Canvas authority and add the minimum versioned contracts for reusable artifacts, custom packages, Semantic Manifest, semantic event bridge, and runtime identity.
**Expected output:** protected contract layer that permits full-power visuals without expanding system authority.
**Likely areas:** `docs/`, Canvas contracts/schemas, Studio/agent contract modules.
**Verification:** lightweight RED→GREEN tests for context/privacy/authority/Manifest boundaries; no full regression.

#### FPC-02 — Reusable Visual Registry + REUSE/ADAPT
**Dependencies:** FPC-01 contracts
**Purpose:** Store/search/inspect/instantiate/version reusable visual definitions separately from student-specific instances and build history.
**Expected output:** immutable artifact/version identity, parameter binding, bounded lookup, one proven REUSE, one proven ADAPT/fork/version path.
**Likely areas:** Studio/Canvas domain services, PostgreSQL migrations/repositories, ObjectStorage where needed.
**Verification:** new values render without regeneration; student/private instance data cannot enter reusable definition; affected DB tests only.

#### FPC-03 — Custom Visual Runtime + sandbox
**Dependencies:** FPC-01
**Purpose:** Allow custom generated visual code without giving it Lina application authority.
**Expected output:** validated package → allowlisted compile → isolated browser sandbox → bounded semantic bridge; Tutor remains available on failure.
**Likely areas:** web runtime, build/worker services, object storage, package/dependency registry, CSP/sandbox host.
**Verification:** compile/render positive case + forbidden network/application-authority negative case + timeout/failure containment.

#### FPC-04 — Full-Power Canvas Agent capabilities
**Dependencies:** FPC-01, enough of FPC-02/FPC-03 to call both paths
**Purpose:** Let the existing one Canvas Agent autonomously choose REUSE, ADAPT, or CREATE according to educational fit, quality, latency, and cost.
**Expected output:** registry/tool/custom-creation capabilities and updated skills without subject-specific standing agents.
**Likely areas:** `runtime/canvas-agent/`, `services/studio/agent/`, model/tool adapters.
**Verification:** focused tool-selection/authority tests plus real-provider route evidence.

#### FPC-05 — Semantic Manifest + same-Tutor continuity
**Dependencies:** FPC-02/FPC-03/FPC-04
**Purpose:** Ensure every finalized Canvas can be explained by the same Primary Tutor regardless of renderer technology.
**Expected output:** validated Manifest + stable semantic IDs + meaningful semantic Studio actions + compact Tutor observation.
**Likely areas:** Canvas/Studio contracts, settlement/reducer/observation path, Tutor context.
**Verification:** meaningful action → Studio → same Tutor round-trip; generated code never becomes teaching authority.

#### FPC-06 — Final integrated acceptance and closure
**Dependencies:** FPC-01..05
**Purpose:** Prove product behavior rather than only infrastructure.
**Expected output:** bounded evidence for REUSE, ADAPT, novel CREATE, age/grade calibration, language/RTL, Tutor round-trip, and sandbox-negative behavior.
**Likely areas:** real-provider acceptance scripts, Clerk-independent production `StudioRendererHost` browser harness, evidence output.
**Verification:** exact Agent-produced artifact rendered in browser; screenshots reviewed against prior quality floor; focused affected PostgreSQL/security gates; typecheck/build status; `git diff --check`; one broad regression near closure.

## Execution rule

FPC-01..06 are one continuous implementation slice. They are **not approval checkpoints**. Codex may combine or reorder reversible implementation work when repository evidence shows a simpler correct path.

Do not stop after each item, commit, or test. Solve ordinary engineering problems autonomously.

## Paused / later

| Task | Status | Reason |
| --- | --- | --- |
| UI-REFINE-01 | PLANNED | Resume after Full-Power Canvas stabilizes the Workspace capability surface so UI refinement does not optimize around a superseded Canvas ceiling. |
| DAILY-E2E-01 | PLANNED | Authenticated disposable-Student end-to-end Daily journey after current Canvas implementation slice. |
| REAL-LINA-01 | PLANNED | Real learner-use observation after the implementation is stable enough to produce meaningful experience evidence. |
