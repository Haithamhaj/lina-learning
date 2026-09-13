# Lina execution queue

An explicit current Product Owner instruction authorizes its requested working slice. Status labels provide operational context; roadmap presence alone does not authorize implementation.

## Current review patch

### TUTOR-PEDAGOGY-REFINE-01 — Bounded Option D instruction refinement

**Status:** IMPLEMENTATION AND STRUCTURAL REVIEW COMPLETE / INDEPENDENT REVIEW ACCEPTED (`ACCEPT_PATCH_FOR_COMMIT`).
**Authority:** Product Owner approved the exact section-C wording and one duplicate deletion from the A–G review, then accepted independent review and authorized one local closure commit only. No push, merge, deployment, or paid evaluation.
**Engineering baseline:** `codex/full-power-canvas-01`, `b5ebfffc613a0cfac93bb461263a7c0b53070028`; tracked files matched HEAD before editing. This is not a deployment assertion.
**Scope:** Replace only the teaching block from “Prefer short sentences” through the emoji sentence in `services/tutor/runtime.py`; remove only the three-line pedagogical sentence beginning “When repeated confusion” from `runtime/tutor/visual-guidance-v1.md`. Preserve the following DID_NOT_HELP and method-relation rules, operational Canvas instructions, and every other runtime contract.
**Reference:** `docs/TUTOR_PEDAGOGY_REFERENCE.md`, copied byte-for-byte from the Product Owner-supplied Downloads file; SHA-256 `5e50985b7bc2a8d7842a1193e8ae0384c6c81ee4abdbcf44b123ad8123f122ac`. Authoring/evaluation only; no runtime load or Student truth.

| Reference sections / matrix rows | Bounded change |
| --- | --- |
| §§5–6; rows 1–6, 22 | Relevant prerequisites, useful attempts, concise worked reasoning, contingent support and fading; no fixed hint/success counts. |
| §§8–9; rows 7–10, 15–16 | Useful application checks, actionable correction/self-correction, selective deeper questions; no Evidence-seeking checks. Existing misconception/source rules unchanged. |
| §7; rows 11–13 | Explicit object/visual/verbal/symbolic connections; move the duplicate stalled-learning guidance into the common block. |
| §10; rows 17, 19–20 | Useful progression/variation, low-pressure recall with feedback; no review schedule or automatic transfer claim. |
| §§8, 10–13; rows 14, 18, 21, 23, 25–26 | Detailed comparison, interleaving, metacognition, and subject overlays remain reference/evaluation material; no dedicated runtime rules. |
| §12; row 24 | Existing conditional visual/number-line capabilities retained; no mandatory representation. |
| §§2–3, 14 | Existing current-behavior priority, Profile/Memory, Evidence/support/method-lineage, Safety and source boundaries retained. |

**Verification (2026-09-13):** Updated three wording-dependent existing contract tests: initial RED was 3 failed / 17 passed before runtime edits; subsequent focused suite 151 passed in 0.44 s. Disposable PostgreSQL 17/pgvector suite 153 passed in 19.10 s, no skips. No historical data used or reprocessed; isolated temporary cluster stopped after tests.
Commands used from this worktree with the already installed Python interpreter:
```sh
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/test_tutor_runtime_contract.py tests/test_tutor_runtime_scenarios.py tests/test_tutor_context_capacity.py tests/test_tutor_context_contract.py tests/test_studio_tutor_context.py tests/test_process_visual_awareness.py tests/test_candidate_event_contract.py
```
For PostgreSQL, used existing `scripts.test_postgres.test_environment(test_database_url())` with `LINA_TEST_DATABASE_PORT=64037`, canonical database `lina_learning_test`, and `MODEL_PROVIDER=mock`; ran `python -m alembic upgrade head`, then:
```sh
"$PYTHON" -m pytest -q -p no:cacheprovider tests/test_session_evidence_consolidation_postgres.py tests/test_segment_learning_review_postgres.py tests/test_session_finalization_postgres.py tests/test_studio_state_postgres.py tests/test_studio_gateway_composition_postgres.py tests/test_studio_tutor_context_postgres.py tests/test_process_visual_awareness_postgres.py tests/test_candidate_event_postgres.py
```
`PYTHON` denotes the existing `/Users/haitham/development/Lina Personal Learning System/.venv/bin/python`; tests import this selected worktree, not the main checkout. No new environment/dependency was installed.

**Actual-patch measurements:** Compared HEAD instruction literals against the imported edited instructions; exact approved replacement verified. Assembled instructions 19,091 → 19,088 characters (replacement block 1,593 → 1,831, duplicate removal 241). New assembled instruction SHA-256: `2e2123f5d96a0dd937e4323c5842eff389129e31adad3416808554fce1ebcc59`. Existing `tutor_turn_v11` schema and execution lineage unchanged; no separate Tutor instruction-version field was found or invented.
Used existing `tests/test_tutor_context_capacity.py` helpers and `tests/test_process_visual_awareness.py` workspace/source fixture through existing builders and capacity guards, in memory with network disabled. Both variants used identical objects. Boundary cases extend fixture strings synthetically, not real Student data or evidence of admission correctness.

| Case | Final capacity metric, before → after | Final provider JSON, before → after | Context result |
| --- | --- | --- | --- |
| Chat fixture | 40,661 → 40,655 | 40,750 → 40,744 | No removal |
| Chat at limit minus 1 | 63,999 → 63,993 | 64,088 → 64,082 | No removal |
| Chat initially limit plus 100 | 63,684 → 63,678 | 63,773 → 63,767 | Same semantic-recall exchange removed |
| Studio Process fixture | 35,108 → 35,102 | 35,197 → 35,191 | Full visual/source retained |
| Studio at limit minus 1 | 63,999 → 63,993 | 64,088 → 64,082 | Full visual/source retained |
| Studio initially limit plus 100 | 63,974 → 63,968 | 64,063 → 64,057 | Identical reduced visual; source retained |

Capacity remains 64,000 serialized instruction/input/schema characters; output limit remains 2,000 tokens. Provider-adapter serialization used the locally configured model string `mock` without transmission. JSON escaping accounts for the -6 serialized versus -3 raw-character change. Non-instruction fields matched; no additional context removal. Token counts, latency, cost, and behavioral gains were not measured.

**Acceptance limits:** Comparative teaching quality NOT YET EVALUATED; longitudinal learning benefit NOT ESTABLISHED. String/mock/compatibility tests are not teaching-quality evidence. Later existing evaluation must verify (1) clear, manageable, child-appropriate explanations, and (2) a useful chance to apply correction when appropriate, without forced retries after every answer. Preserve support attribution, meaningful transfer conditions and method-outcome lineage; different valid dialogue may yield different Evidence, so do not require identical Evidence outputs. Paid/live evaluations were not run.
**Out of scope:** Existing CanvasBrief/legacy-workspace instruction drift remains unchanged; Canvas-to-Evidence coverage is not inferred absent and no coverage work is included. Full reference remains non-governing authoring material.
**Hygiene:** `python scripts/check_repository_truth.py` and `git diff --check` passed. Exact source-boundary comparison confirmed no runtime code/text changes outside the approved block/deletion; reference byte identity passed; index remained unchanged.
**Independent closure review:** Accepted for local commit. The independent reviewer reran 151 tests and inspected 153 PostgreSQL test results from the implementation run; the latter were not independently rerun. Runtime, visual-guidance, test and reference content remain unchanged from the accepted patch. Closure reruns only repository-truth and diff checks, not the database suite. Repository-truth and working-tree diff checks passed. The full staged diff check reports 32 trailing-whitespace lines, all original Markdown two-space hard breaks in the byte-identical reference; preserved as approved. The other five staged files pass the whitespace check.
**Provenance limitation (non-blocking):** The existing instruction-provenance limitation remains; `tutor_turn_v11` is unchanged. For later evaluation, use the existing evaluation record to associate execution/message IDs with the code version and actual instruction hash. No provenance mechanism is introduced.
**Next:** Retain the accepted patch in one local commit. Comparative teaching quality remains NOT YET EVALUATED and longitudinal learning benefit NOT ESTABLISHED; later evaluation requires separate authorization. No push, merge or deployment.

## Current completed baseline

| Task | Status | Scope / evidence |
| --- | --- | --- |
| REPO-TRUTH-01..05 | DONE | Repository truth, cleanup, canonical mainline, and protection work completed. |
| PRODUCT-IDENTITY-01 | DONE | Product identity/philosophy reconciled. |
| STUDIO-AGENTIC-01 | DONE | Tutor-led Agentic Canvas, bounded Agents SDK composition, typed Scene settlement, generated-asset lineage, interactions, same-Tutor continuity, replay, real-provider proof. |
| CANVAS-VISUAL-INTELLIGENCE-01 | DONE | Filtered visual learner context, Scene v2 presentation persistence, stronger visual skills, deterministic geometry rendering, disposable PostgreSQL and production-renderer browser proof. |

## Completed engineering closure

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
**Closure:** Engineering closure branch is published. No merge or deployment. Broad production CREATE reliability, authenticated Daily use and learning benefit remain separate production-use gates.


### FULL-POWER-CANVAS-01 — Full-Power Hybrid Canvas

**Status:** DONE — published engineering closure; no merge/deployment
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

### Historical implementation breakdown

FPC-01..06 below are retained to explain how the completed architecture was built. They are not an active execution queue and do not authorize further Canvas work.

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

## Historical execution rule

FPC-01..06 are one continuous implementation slice. They are **not approval checkpoints**. Codex may combine or reorder reversible implementation work when repository evidence shows a simpler correct path.

Do not treat this historical instruction as authority for new work.

## Next phase — not authorized

| Task | Status | Reason |
| --- | --- | --- |
| CONTROLLED-PRODUCTION-USE-01 | NOT AUTHORIZED | A separately approved real-use / controlled-production phase must establish authenticated Daily use, reliability, correctness/replay and learning-benefit evidence. It must not treat AI Development Review as release authority. |
| UI-REFINE-01 | LATER | UI work is not part of the current closure. |
