# CS-01 — Contract + Runtime Specialist Skill — Implementation Record

**Status:** DONE / ACCEPTED
**Prepared:** 2026-09-07  
**Execution branch:** `codex/ctx-03`  
**Preparation baseline inspected:** `dbcdffa321fb50cd6282be81e192e9bf920b124b`  
**Implementation baseline:** `aa60cb49d848c095ca8835caebfac1f99ea3d25b`
**Implementation start rule:** began from the current `codex/ctx-03` HEAD containing this Implementation Record and the Canvas Specialist documentation sync; no reset or protected-work discard was used.
**Purpose:** Create the runtime Canvas Specialist Visual Learning Composer Skill and reconcile the disabled per-run capability boundary, without enabling Specialist model execution or changing Student runtime behavior.

## 1. Governing references

Read before implementation:

1. `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`
2. `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md` — CS-01 only
3. `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md` — CS-01 acceptance
4. `docs/LINA_EDUCATIONAL_VISUALS_GUIDE.md`
5. `skills/lina-educational-visuals/SKILL.md` — development-only source; must remain development-only
6. `runtime/tutor/visual-guidance-v1.md` — protected Primary Tutor runtime subset
7. `runtime/canvas-specialist/visual-capability-pack-v1.md` — current disabled future Specialist subset
8. `docs/DAILY_USE_RELEASE_DECISIONS.md` decisions 35, 38, 39, 40
9. `project-state/PROJECT_STATE.md`
10. `project-state/DAILY_USE_RELEASE_TASKS.md`

## 2. Protected invariants

CS-01 must preserve:

- Primary Tutor remains the sole Student-facing teacher.
- `workspace_intent-v1` meaning is unchanged.
- Specialist remains proposal/composition-only with no renderer/engine, persistence, Safety, Evidence, Personal Facts, Learner Intelligence or grading authority.
- Existing Tutor visual guidance does not load Specialist-only instructions.
- Existing accepted ProcessView/Process awareness behavior is unchanged.
- Existing Studio Runtime/Registry/Protocol/Runtime-03 behavior is unchanged.
- No new normal-turn or background model call is enabled.
- No database/schema/migration/dependency change.
- No Student production behavior change.

## 3. Required outputs

### A. Runtime Specialist Skill

Create:

`runtime/canvas-specialist/SKILL.md`

The Skill must define the Canvas Specialist as a **Visual Learning Composer** and cover:

- objective-first visual reasoning;
- representation/composition hierarchy and grouping;
- meaningful spatial relations and concise labels;
- progressive detail/focus/de-emphasis/reveal/trace;
- meaningful motion intent only when it explains attention, relation, sequence, transformation or conserved equivalence;
- Arabic/English/mixed direction;
- narrow/responsive behavior;
- keyboard/touch/reduced-motion/text-equivalent accessibility;
- optional, non-forced visual personalization from the bounded Visual Learner Context;
- strict grounding/support discipline;
- exact Capability Pack obedience;
- pre-output self-review for missing required meaning, unsupported relation, clutter, forced personalization, readability and capability violation.

It must explicitly forbid:

- competing Student-facing teaching dialogue or independent lesson/assessment;
- arbitrary renderer/engine selection;
- SVG/HTML/JS/CSS/executable code generation authority;
- layout-coordinate/timing implementation authority;
- database/persistence mutation;
- Safety/Parent Boundary override;
- Evidence/PF/LI writes or inferred learner traits;
- expansion beyond the active per-run Capability Pack.

### B. Capability pack reconciliation

Review and update only as needed:

`runtime/canvas-specialist/visual-capability-pack-v1.md`

It must remain a **per-run capability boundary**, not the general Skill. It should clearly state that current production Process execution is not enabled by CS-01 and that later packs supply exact registered limits/capabilities.

Keep accepted current Process boundaries where relevant: 2–8 stages and existing label/detail/relation/handle limits until a separately approved production contract changes them.

### C. Focused contract tests

Add the smallest tests needed to prove:

- Primary Tutor instructions contain `VISUAL_GUIDANCE_V1` but not Specialist runtime Skill/capability contents;
- development-only `skills/lina-educational-visuals/SKILL.md` is not runtime-loaded;
- Specialist Skill/capability text does not grant forbidden authorities;
- existing Process awareness/Tutor visual guidance tests remain valid.

Do not test a Specialist model call; none should exist in CS-01.

## 4. Expected changed paths

Expected/allowed implementation paths are intentionally narrow:

- `runtime/canvas-specialist/SKILL.md` — new
- `runtime/canvas-specialist/visual-capability-pack-v1.md` — bounded update if needed
- focused tests under `tests/` that verify runtime instruction separation/authority
- this implementation record during/after execution

`runtime/tutor/visual-guidance-v1.md` may change **only** if implementation discovers a concrete contradiction with the accepted contract; any such change must preserve Tutor authority and be explicitly justified in this record.

Any need to modify WorkspaceIntent, Tutor output schemas, ModelTask/Gateway/Worker, database/migrations, ProcessView/Host, package dependencies or Student routes is **outside CS-01** and must stop for Product Owner review rather than expanding scope.

## 5. Planned verification

Minimum planned verification:

1. focused new CS-01 Skill/authority tests;
2. existing Process visual awareness/Skill guidance tests that prove development/runtime separation;
3. Primary Tutor payload/instruction assertion: Specialist Skill/capability does not appear;
4. relevant existing Tutor runtime contract tests affected by runtime instruction files;
5. `git diff --check` / equivalent whitespace integrity;
6. scope review confirming no ModelTask/Gateway/Worker/database/dependency/Student behavior change.

Run additional relevant regressions if the actual changed paths make them necessary. Record exact commands/results below during execution.

## 6. Evidence status before implementation

| Evidence category | Status |
|---|---|
| Static/contract review | PLANNED |
| Unit/contract tests | NOT RUN |
| PostgreSQL integration | NOT REQUIRED unless implementation unexpectedly touches persistence — which would be a scope violation |
| Mock Specialist model | NOT APPLICABLE — CS-01 does not enable execution |
| Live Luna | NOT APPLICABLE — CS-01 does not enable execution |
| Production web build | NOT REQUIRED unless web/runtime import path unexpectedly changes |
| Browser | NOT APPLICABLE |
| Controlled Student journey | NOT APPLICABLE |
| Real Lina use | NOT AUTHORIZED |
| Longitudinal benefit | OUT OF SCOPE |

## 7. Implementation decisions

- Added `runtime/canvas-specialist/SKILL.md` as the runtime-only
  `CANVAS_SPECIALIST_VISUAL_LEARNING_COMPOSER_V1` instruction boundary. It
  composes an admitted semantic proposal and explicitly leaves Tutor,
  application/Studio, renderer, Safety, persistence, and learning-authority
  responsibilities unchanged.
- Reconciled `visual-capability-pack-v1.md` by identifying it as the exact,
  bounded, application-supplied **per-run** pack, distinct from the general
  Skill and not execution authorization. The accepted Process seed bounds
  remain unchanged, including 2–8 stages.
- Added focused marker-based tests rather than a full-prose snapshot. They
  assert Primary Tutor instruction isolation plus Specialist and pack authority
  boundaries. No change to `runtime/tutor/visual-guidance-v1.md` was needed:
  source inspection confirms it is the sole runtime visual file appended to
  shared Primary Tutor instructions.

## 8. Actual changed paths

- `runtime/canvas-specialist/SKILL.md` — new runtime Visual Learning Composer
  Skill.
- `runtime/canvas-specialist/visual-capability-pack-v1.md` — clarified
  per-run/general-Skill/execution separation only.
- `tests/test_canvas_specialist_skill.py` — focused authority and instruction
  isolation contract tests.
- `docs/reviews/CS-01/IMPLEMENTATION_RECORD.md` — this completion record.

## 9. Verification results

| Command | Result |
|---|---|
| `uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_canvas_specialist_skill.py` | COLLECTION FAILURE — `ModuleNotFoundError: No module named 'services'`; the repository root was absent from the Python import path. |
| `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_canvas_specialist_skill.py` | PASS — **3 passed** in 0.09s; 0 failed, 0 skipped. |
| `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_process_visual_awareness.py tests/test_tutor_runtime_contract.py` | PASS — **34 passed** in 0.10s; 0 failed, 0 skipped. Existing coverage executed: `test_process_visual_awareness.py` proves `VISUAL_GUIDANCE_V1`, development-only/runtime separation, and Primary Tutor instruction behavior; `test_tutor_runtime_contract.py` covers the affected Tutor runtime contract. |
| `git diff --check` | PASS — no whitespace errors. |
| `rg -n "visual-guidance-v1|canvas-specialist/SKILL|visual-capability-pack|VISUAL_GUIDANCE_V1|SPECIALIST_CAPABILITY_PACK_V1|CANVAS_SPECIALIST_VISUAL_LEARNING_COMPOSER_V1" services runtime tests --glob '!tests/test_canvas_specialist_skill.py'` | PASS — only Primary Tutor guidance is runtime-loaded; no Specialist Skill/pack runtime loader exists. |
| `npm run test:python` | DIAGNOSTIC NON-PASS — PostgreSQL container setup and all migrations completed. A full-suite aggregate count was not obtained because the foreground command capture stopped before completion. The first-error diagnostic run below classifies the observed failure. |

No tests were skipped and counted as passes.

### Broader-suite diagnostic classification

To obtain a bounded first failure, the canonical script was run with
`PYTEST_ADDOPTS='--maxfail=1 --tb=short' npm run test:python`. PostgreSQL setup
and all Alembic migrations completed successfully. Pytest then reached a final
diagnostic result of **19 passed, 1 error, 1 warning** in 5.98s:

- `tests/test_candidate_event_postgres.py::test_same_call_candidate_persists_raw_source_and_never_creates_derived_intelligence`
  — **ENVIRONMENT / INFRASTRUCTURE FAILURE.** Its setup fixture failed before
  the test body while truncating the disposable PostgreSQL database with
  `psycopg.errors.DeadlockDetected` / `sqlalchemy.exc.OperationalError`.
  The lock cycle was between PostgreSQL processes holding `AccessExclusiveLock`
  and `RowShareLock`. The same setup deadlock reproduced when the implicated
  test was run alone through the canonical disposable-database script.

The CS-01 diff does not alter this test, PostgreSQL fixtures, migrations,
database code, or the test runner. Earlier diagnostic runs had overlapping
canonical-suite processes against the single named disposable database; that
shared-runner contention is the observed environmental cause. No baseline
comparison was needed because the classification has no source-level overlap
with the four CS-01 paths. No CS-01 regression was observed.

## 10. Independent review

No independent reviewer was available or authorized. A separate static
self-review found no Critical or Important issue in the CS-01 diff: the sole
shared Primary Tutor runtime loader remains
`runtime/tutor/visual-guidance-v1.md`, while the new Specialist Skill and pack
have no runtime loader. Focused test evidence is independently reproducible
through the repository-declared `uv` environment; the broader suite remains
non-passing with no captured final aggregate count.

## 11. Known unverified evidence / blockers

- Specialist runtime execution intentionally remains unimplemented until CS-04.
- Visual Toolbelt installation intentionally remains blocked until CS-02.
- Tutor Visual Order/Frozen Pack intentionally remains blocked until CS-03.
- Natural Process production composition intentionally remains blocked until CS-05.
- The required CS-01 focused tests and existing visual-awareness/Tutor contract
  tests are verified. The broader canonical Python regression needs a later
  clean, non-overlapping run to obtain its full aggregate count; its first
  classified failure is PostgreSQL lock contention, not CS-01. No CS-01-related
  failure appeared in the focused runs.

## 12. Scope review

Reviewed complete tracked and CS-01 untracked diff. Changes are limited to the
new runtime Skill, the disabled capability-pack wording, focused tests, and this
record. No change was made to Tutor authority or shared Tutor guidance,
WorkspaceIntent, ModelTask/Gateway/Worker, database/schema/migrations,
dependencies, Student runtime, ProcessView, production routing, or
Evidence/PF/LI boundaries. No model execution path was enabled.

## 13. Product Owner disposition

**DONE / ACCEPTED — 2026-09-07.** Product Owner accepted the reviewed CS-01
implementation with Critical: 0, Important: 0, Minor: 0. Retained acceptance
evidence: CS-01 focused tests **3 passed, 0 failed, 0 skipped**; affected
Tutor/Process contracts **34 passed, 0 failed, 0 skipped**; and `git diff
--check` passed. Primary Tutor loads only its accepted Tutor visual guidance,
not the Canvas Specialist Skill or capability pack. The broader canonical
regression diagnostic encountered an environment/infrastructure PostgreSQL
deadlock during fixture `TRUNCATE` before the test body; no failure was
attributable to CS-01. No dependency, schema, ModelTask, Gateway, Worker,
Student runtime, WorkspaceIntent, ProcessView, or routing change occurred. No
live Luna, browser, or PostgreSQL product evidence was required or claimed for
CS-01. CS-02 is READY but not started.
