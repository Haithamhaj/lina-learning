# Canvas Specialist Implementation Plan

**Status:** APPROVED EXECUTION PLAN — derived from the accepted Canvas Specialist contract and direct Product Owner instruction on 2026-09-07.  
**Canonical contract:** `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`  
**Verification authority:** `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`  
**Current execution rule:** one READY task at a time; stop after each task for verification/review and Product Owner acceptance before promoting the next.

## 1. Goal

Reach a real `/student/daily` trial in the shortest safe sequence where:

```text
Student question
→ Primary Tutor decides a new Process visual helps
→ one bounded Luna Canvas Specialist call
→ validated/accepted/active Process Scene
→ existing ProcessView renders
→ Student selects object/relation
→ same Primary Tutor explains through existing Runtime-03
```

The plan deliberately prepares a broader visual Toolbelt while production-enabling only the Process slice first.

## 2. Protected baseline

Do not reopen or redesign accepted:

- Studio Runtime/Scene/Event/Snapshot/Protocol/feed;
- Subject Registry exact-version authority;
- WorkspaceIntent v1 meaning and deterministic Router;
- Runtime-03 StudentInteraction/Tutor continuation;
- `/student/daily` server-authoritative Studio integration;
- accepted ProcessView/Checkpoint-2 visual direction;
- Personal Facts and Student Core Profile authority split;
- Learning Intelligence and Safety boundaries.

`docs/STUDIO_VISUAL_EXPLANATION_SPEC.md` remains a broader accepted design source. `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md` governs conflicts for this bounded track.

## 3. Task sequence

```text
CS-01 Contract + Runtime Specialist Skill        DONE / ACCEPTED
  ↓
CS-02 Complete Visual Toolbelt                   DONE / ACCEPTED
  ↓
CS-03 Tutor ↔ Specialist Runtime Alignment       DONE / ACCEPTED
  ↓
CS-04 Real Canvas Specialist Execution Runtime   DONE / ACCEPTED
  ↓
CS-05 Process Production Integration             READY
  ↓
CS-06 Real Daily End-to-End Trial                BLOCKED
  ↓
CS-07 Visual Specialist Lab                      BLOCKED
```

No later task becomes READY automatically because code exists. Promotion follows the acceptance process in `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`.

---

# CS-01 — Contract + Runtime Specialist Skill

**Status:** DONE / ACCEPTED
**Purpose:** Convert the accepted visual-composer behavior into a runtime Skill/capability boundary without enabling any Specialist model execution.

## Required outputs

1. Create `runtime/canvas-specialist/SKILL.md` as the runtime Visual Learning Composer skill.
2. Revise `runtime/canvas-specialist/visual-capability-pack-v1.md` only as needed so it is consistent with the accepted contract and clearly separates general Skill from per-run Capability Pack.
3. Preserve `skills/lina-educational-visuals/SKILL.md` as development-only.
4. Add focused contract tests proving the runtime Specialist Skill is **not** loaded into the Primary Tutor and does not grant renderer/persistence/Safety/Evidence/PF/LI authority.
5. Record exact runtime Skill/capability versions and limits; no provider call is added.

## Likely areas

- `runtime/canvas-specialist/`
- `runtime/tutor/visual-guidance-v1.md` only if a contradiction must be corrected without expanding Tutor authority
- focused tests around Tutor/runtime visual guidance and capability-pack loading

## Must not change

- WorkspaceIntent v1 schema/meaning;
- ModelTask/Gateway/Worker execution;
- ProcessView;
- database/schema;
- dependencies;
- Student runtime behavior.

## Verification

- focused Skill/contract tests;
- existing Process awareness/Tutor guidance tests;
- confirm `SPECIALIST` instructions do not appear in Primary Tutor request payload;
- no code path can execute the Specialist yet.

## Documentation before closure

Create/update `docs/reviews/CS-01/IMPLEMENTATION_RECORD.md` with baseline SHA, exact changed paths, contract/version decisions, verification, unverified evidence and boundary.

**Stop gate:** accepted; CS-02 is closed.

---

# CS-02 — Complete Visual Toolbelt

**Status:** DONE / ACCEPTED
**Purpose:** Install and prove the approved visual engines without enabling new production learning routing.

## Approved Toolbelt target

- `motion`
- `react-konva@18` + `konva`
- `jsxgraph`
- `mathlive`

React/DOM/SVG remain the existing baseline.

## Required outputs

1. Install compatible versions and update lockfile.
2. Create small application-owned client adapters/proof mounts for each engine.
3. Ensure Konva/JSXGraph/MathLive remain lazy/client-loaded behind their adapters where practical.
4. Motion proof must demonstrate semantic SVG/DOM animation capability without rewriting accepted ProcessView.
5. Konva proof must demonstrate mount/unmount plus one bounded spatial interaction.
6. JSXGraph proof must demonstrate mount/unmount plus one bounded mathematical construction/number-line-like object.
7. MathLive proof must demonstrate editable math input and controlled event/value handoff without making browser input authoritative learning truth.
8. Record reuse fit decision and any required CSS/assets/fonts/sounds handling.

## Likely areas

- `apps/web/package.json`
- root/package lockfiles as applicable
- `apps/web/lib/studio/visual-toolbelt/` or equivalent local adapter boundary
- isolated review/proof components/tests only

## Must not change

- Workspace Router/admission;
- Tutor output schema;
- Specialist runtime execution;
- Process production registration;
- accepted activity behavior.

## Verification

- clean install/lockfile;
- web typecheck;
- production build;
- isolated mount/unmount tests;
- real browser proof for Canvas/web-component behavior where jsdom is insufficient;
- no server import/window-document failure;
- no regression to existing Studio renderer host or ProcessView.

## Failure rule

A library compatibility problem must be solved inside a bounded adapter first. Do not redesign Next.js/Studio to satisfy an unused engine. If a genuine blocker remains, record it and return for Product Owner decision; do not silently drop the approved library.

## Documentation

`docs/reviews/CS-02/IMPLEMENTATION_RECORD.md` plus sanitized screenshots/proofs where useful.

**Stop gate:** accepted; CS-03 is READY.

---

# CS-03 — Tutor ↔ Specialist Runtime Alignment

**Status:** DONE / ACCEPTED
**Purpose:** Add the bounded Primary Tutor visual-order and frozen composition context while preserving existing WorkspaceIntent/Router meaning and without yet executing a Specialist model.

## Required outputs

1. Add an additive required-nullable versioned visual-order sibling to the Primary Tutor result.
2. Preserve historical/current Tutor schema compatibility explicitly; do not reinterpret missing fields as null silently.
3. Implement the Semantic Alignment Envelope: bounded objective, required semantic/fact/relation support identities and must-not-imply constraints.
4. Build application admission after complete Primary Tutor parsing/policy handling.
5. Build a deterministic Frozen Composition Pack.
6. Build the transient Visual Learner Context from:
   - Student Core Profile for authoritative display name/age/Grade when relevant;
   - a small current subset of safe relevant Personal Facts for optional visual personalization.
7. No additional normal-turn model call may be introduced for Personal Fact selection or visual-order admission.
8. Derive an application-owned order digest/idempotency identity and capture relevant current Scene/capability/source versions.
9. Persist the accepted order/lineage in the established Tutor message/audit boundary; do not dispatch a Worker yet.

## Likely areas

- `services/tutor/candidate_events.py` or the exact Tutor output-schema owner
- `services/tutor/runtime.py`
- `services/tutor/context.py` / bounded projection helper
- `services/studio/workspace_intent.py` must remain v1-compatible
- `services/studio/router.py` only for additive authority metadata if necessary, not meaning rewrite
- new exact visual-order/pack contracts under `services/studio/`
- provider strict-schema parity tests

## Key negative tests

- Chat-only valid result → no visual order effect.
- Existing known/reusable path → no composition requirement.
- invalid visual order cannot mutate Scene or enqueue work.
- implementation technology terms are rejected from Tutor educational fields.
- Personal Facts do not replace Core Profile age/Grade or inject history.
- no Specialist/model/Job call exists yet.

## Documentation

`docs/reviews/CS-03/IMPLEMENTATION_RECORD.md` with exact schema/version decisions and compatibility evidence.

**Stop gate:** accepted; CS-04 is READY.

---

# CS-04 — Real Canvas Specialist Execution Runtime

**Status:** DONE / ACCEPTED
**Purpose:** Execute one admitted Canvas Specialist generation through the existing Worker/Gateway/AIExecution architecture without accepting a production Process Scene yet.

## Required outputs

1. Add a dedicated `ModelTask.CANVAS_SPECIALIST` or equivalent stable task identity.
2. Route it through the existing Model Gateway; current model decision is GPT-5.6 Luna.
3. Build the Specialist provider payload from the frozen order/pack plus `runtime/canvas-specialist/SKILL.md` and exact per-run capability pack.
4. Reuse PostgreSQL Job + Worker architecture; Specialist Job must use `max_attempts=1`.
5. Reuse/complete `StudioCanvasSpecialistRun` lifecycle and exact source Tutor message/Job/AIExecution lineage.
6. Ensure DB transactions/locks do not span provider inference.
7. Implement deadline/cancel/fail/supersede/stale settlement and explicit ambiguous-provider-outcome handling.
8. Strict typed Specialist output schema; no executable markup/code.
9. No automatic repair/critic/third Tutor call.
10. Implement safe reconciliation for the handler-complete/queue-settlement crash windows without another inference.

## Likely areas

- `services/platform/db/models.py` only if exact additive task/run constraints require it; migration only when truly necessary
- `services/model_gateway/factory.py` / Gateway task route
- `services/studio/service.py` / exact run admission/settlement helpers
- `services/studio/contracts.py`
- `workers/job_worker.py` registry and a bounded Specialist handler module
- focused Postgres/Gateway tests

## Verification

- duplicate admission does not duplicate accepted work;
- exactly one provider generation attempt in normal path;
- provider failure/timeout leaves committed Tutor work intact;
- stale/cancelled/superseded run cannot later accept;
- AIExecution provider/model/tokens/latency/cost lineage recorded;
- live Luna structured-output route proof when configured, clearly distinguished from mock tests.

## Documentation

`docs/reviews/CS-04/IMPLEMENTATION_RECORD.md` including mock vs live-model evidence, call counts, failure behavior and any migration decision.

**Accepted implementation:** `8de9a752b00998f6d1f2a2b24102ba49cf5a1b2a`.
**Independent review disposition:** Critical: 0; Important: 0; Blocking: 0.
**Retained evidence limitation:** **LIVE LUNA NOT VERIFIED — CONFIGURATION UNAVAILABLE.** This is retained evidence and not a CS-04 acceptance blocker.

**Stop gate:** accepted; CS-05 is READY.

---

# CS-05 — Process Production Integration

**Status:** READY
**Purpose:** Turn one valid Process Specialist proposal into the first production natural-composition Scene while reusing accepted Process semantics/visuals/Tutor awareness.

## Required outputs

1. Add an additive exact production Process profile/renderer/scene version; do not mutate the accepted awareness-only profile into production silently.
2. First slice: sequence/cycle, 2–8 stages, approved art handles, focus/reveal/trace, object/relation explanation.
3. Validate structural shape and Semantic Alignment support before acceptance.
4. Treat the admitted visual order plus Frozen Composition Pack as the authorization snapshot: Safety, Parent Boundary, and source rights are resolved before admission. In the short acceptance transaction, recheck only run eligibility, exact source/order identity, supersession, capability/profile identity, structural and semantic-support validity, allowed art handles, and causal/stale Scene state. Later policy-setting changes apply prospectively to future visual orders.
5. Atomically supersede prior active Scene when needed, accept new Scene, activate it, update Event/Snapshot and complete the run link.
6. Add the smallest production Host/adapter mapping authoritative Process Scene/state to the **existing accepted ProcessView**.
7. Add production operation plumbing for focus/reveal/trace and object/relation `REQUEST_EXPLANATION` without visual redesign.
8. Preserve the older deterministic `process_sequence_workspace` activity as a separate accepted capability.
9. Existing Studio feed/snapshot/reload remains delivery authority; no new transport.
10. Specialist completion creates no automatic Tutor call or fake Student message.

## Likely areas

- `services/studio/subjects/process_visual.py` plus additive production contract/helper or separate exact module
- `services/studio/subjects/__init__.py` / registry current profile mapping as explicitly bounded
- `services/studio/service.py` / bounded result acceptance adapter
- `apps/web/lib/studio/renderer-host.ts`
- `apps/web/components/daily-student/studio-renderer-host.tsx`
- local Process adapter around existing `apps/web/components/studio/visual-explanation/process-view.tsx`
- Postgres/process/Host/browser tests

## Verification

- accepted proposal renders through unchanged ProcessView meaning;
- invalid support/topology/art/stale proposal creates no accepted Scene;
- prior Scene survives failed replacement;
- reload/replay reconstructs exact active Process;
- focus/reveal/trace use zero Specialist calls;
- object/relation explanation uses one same-Primary-Tutor Runtime-03 continuation and zero Specialist calls;
- no direct Candidate/Evidence/PF/LI writes.

## Documentation

`docs/reviews/CS-05/IMPLEMENTATION_RECORD.md` plus sanitized wide/narrow Arabic/English and interaction screenshots.

**Stop gate:** Product Owner acceptance before CS-06.

---

# CS-06 — Real Daily End-to-End Trial

**Status:** BLOCKED pending CS-05 acceptance  
**Purpose:** Prove the natural product experience rather than only code contracts.

## Core journey

```text
Student asks a natural Process question
→ same Primary Tutor teaches and emits admitted visual order
→ exactly one Luna Specialist composition
→ valid accepted/active Process Scene
→ `/student/daily` shows existing ProcessView
→ Student selects object and relation
→ same Primary Tutor explains exact targets through Runtime-03
```

## Required scenario set

At minimum include:

1. one grounded cycle stress case (butterfly or equally verified source-supported cycle);
2. one non-cycle sequence;
3. Arabic or mixed-direction visual;
4. Chat-only/no-visual case proving zero Specialist call;
5. supported reuse/update case proving zero composition call;
6. malformed/provider-failure or controlled stale-result case proving safe failure.

Use Lina's actual account/content only when separately authorized; otherwise use an isolated Student identity and clearly label the evidence.

## Quality gate — blocking

Product Owner/reviewer must confirm semantic fidelity, pedagogical usefulness, visual clarity, age/Grade appropriateness, relation readability, Arabic/English behavior, accessible/narrow behavior and non-forced personalization. Automated structural pass alone cannot close CS-06.

## Speed/cost — measured, then optimized

Record separately:

- Tutor first useful text;
- Tutor terminal result;
- queue delay;
- Specialist generation;
- validation/Scene commit;
- first visible Canvas;
- Tutor input/output/cached tokens and cost when available;
- Specialist input/output/cached tokens and cost when available;
- failure/rejection/supersession counts.

Do not invent latency/cost pass thresholds before this baseline. Quality is evaluated first; then measured bottlenecks may be optimized without lowering accepted quality.

## Documentation

`docs/reviews/CS-06/IMPLEMENTATION_RECORD.md` is the real-trial closure report and includes prompt/scenario matrix, screenshots, timing/cost table, mock/live/browser distinctions, failures, limitations and Product Owner disposition.

**Stop gate:** CS-06 must be explicitly accepted before CS-07 or any broader production pattern promotion.

---

# CS-07 — Visual Specialist Lab

**Status:** BLOCKED pending CS-06 acceptance  
**Purpose:** Explore the already-installed Toolbelt with the same Specialist brain using controlled capability packs before any new engine becomes a production teaching capability.

## Controlled labs

- **Motion Lab:** relation traces, focus transitions and explanatory transformations.
- **Konva Lab:** bounded drag/group/place/label spatial interaction.
- **JSXGraph Lab:** number line, geometry or coordinate construction.
- **MathLive Lab:** editable fractions/expressions/math input feeding a bounded application contract.

## Rule

These are capability experiments, not blanket production promotion. Each lab records quality, interaction correctness, accessibility, browser behavior, bundle/loading implications, latency/cost where AI is involved, and whether the capability should be killed/modified/kept.

Each lab evaluates two independent axes. **Technical Capability** covers
correctness, interaction capability, semantic-state handoff, lifecycle,
accessibility, browser/mobile behavior, performance, bundle/loading
implications, reliability and appropriate engine fit. **Visual Quality / Lina
Visual Language** covers attractiveness, hierarchy, clarity, Grade-appropriate
information density, typography, spacing, shape/control language,
focus/de-emphasis, motion character, Arabic/English/mixed-direction appearance,
consistency with Lina's visual system, and whether application-owned
wrappers/design tokens/components can make the result one coherent Lina Canvas
that is clearer than a simpler React/SVG alternative when relevant.

A technically capable engine does not qualify for production promotion merely
because it works. It must also be capable of producing a visually coherent,
child-appropriate Lina experience through application-owned styling/wrappers.
Native/default library styling need not itself look like Lina; JSXGraph, Konva
and MathLive may remain internal beneath the application-owned wrapper.

A later production slice is selected only after Product Owner review. Each
KILL / MODIFY / KEEP justification records separate Technical and Visual
findings.

## Documentation

`docs/reviews/CS-07/IMPLEMENTATION_RECORD.md` plus sub-sections/evidence for each engine. Do not create four competing canonical specifications.

---

## 4. Documentation lifecycle for every CS task

Every task follows the same documentation workflow:

1. **Before code:** create `docs/reviews/<TASK-ID>/IMPLEMENTATION_RECORD.md` with status, baseline SHA, purpose, dependencies, protected boundaries, expected files and planned verification.
2. **During implementation:** record only meaningful deviations/decisions; do not turn it into a diary.
3. **Before claiming complete:** record actual changed files, exact tests/build/browser/live-model evidence, call counts/metrics, known unverified evidence, scope review and risks.
4. **Review:** update `docs/reviews/README.md` with canonical record/status.
5. **Acceptance:** only Product Owner acceptance changes the task to DONE / ACCEPTED.
6. **State transition:** update `project-state/PROJECT_STATE.md` and `project-state/DAILY_USE_RELEASE_TASKS.md`; promote the next task only with explicit Product Owner authorization.
7. Canonical contract/plan/spec files change only when the governing decision changes, not after every implementation detail.

Private raw evidence/secrets stay local. Publish sanitized evidence only.

## 5. Implementation philosophy

- reuse current seams before adding architecture;
- general Specialist Skill, exact per-run Capability Pack;
- semantic creativity, application-owned executable rendering;
- quality before speed before cost;
- one additional AI call only when new composition creates identifiable learning value;
- no generic Specialist platform before a concrete need proves it;
- reach CS-06 before expanding production scope.
