# CS-01 — Contract + Runtime Specialist Skill — Implementation Record

**Status:** READY / NOT STARTED  
**Prepared:** 2026-09-07  
**Execution branch:** `codex/ctx-03`  
**Preparation baseline inspected:** `dbcdffa321fb50cd6282be81e192e9bf920b124b`  
**Implementation start rule:** begin from the current `codex/ctx-03` HEAD that contains this Implementation Record and the Canvas Specialist documentation sync; do not reset or execute from the older preparation baseline.  
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

_Not started. Record only meaningful decisions/deviations here._

## 8. Actual changed paths

_Not started._

## 9. Verification results

_Not run._

## 10. Independent review

_Not performed._

## 11. Known unverified evidence / blockers

- Specialist runtime execution intentionally remains unimplemented until CS-04.
- Visual Toolbelt installation intentionally remains blocked until CS-02.
- Tutor Visual Order/Frozen Pack intentionally remains blocked until CS-03.
- Natural Process production composition intentionally remains blocked until CS-05.

## 12. Scope review

**Before implementation:** documentation-only preparation. No CS-01 source changes have been made yet.

## 13. Product Owner disposition

**READY / NOT STARTED.** Execute CS-01 only. After implementation and verification, submit this record for review and stop. CS-02 remains BLOCKED until explicit Product Owner acceptance/promotion.