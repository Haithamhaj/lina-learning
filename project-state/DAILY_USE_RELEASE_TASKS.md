# Daily-Use Lina Release 1 — Current Execution Tasks

**Status:** Current bounded execution overlay  
**Updated:** 2026-09-07  
**Execution rule:** only one task is `READY` at a time. Verify, document, review and obtain Product Owner acceptance before promoting the next task.  
**Historical ledger:** `TASKS.md` remains the preserved historical task ledger; accepted closure details also remain in their review/closure documents.

## Current accepted baseline relevant to this track

The following foundations are already DONE / ACCEPTED and must not be reopened by the Canvas Specialist track:

- Student Core Profile; Personal Facts/PF-02/PF-03; Learning Intelligence and Safety authorities.
- FE-01 visual direction and `/student/daily` greenfield Studio integration.
- Studio State, Subject Registry, Protocol, Runtime-01, Runtime-02 WorkspaceIntent/Router, Runtime-03 Canvas-originated same-Tutor continuation.
- Make-Ten, deterministic Science Process Sequence, English/Arabic sentence ordering, Decimal Number Line and Decimal Place Value accepted activities/renderers.
- `LINA-VISUAL-INTELLIGENCE-01` semantic Canvas awareness and visual grammar.
- `STUDIO-VISUAL-PROCESS-01` accepted Checkpoint-2 ProcessView and prepared-data Process foundation.

`STUDIO-ACCEPT-01`, deployment, real-Lina start, Voice/Vision, generated imagery/3D, remaining renderer families, generic reuse DB and broader custom composition remain separately blocked/not promoted.

## Active Canvas Specialist track

**Governing contract:** `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`  
**Detailed plan:** `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md`  
**Acceptance/verification:** `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`

```text
CS-01 Contract + Runtime Specialist Skill        DONE / ACCEPTED
  ↓
CS-02 Complete Visual Toolbelt                   DONE / ACCEPTED
  ↓
CS-03 Tutor ↔ Specialist Runtime Alignment       DONE / ACCEPTED
  ↓
CS-04 Real Canvas Specialist Execution Runtime   READY
  ↓
CS-05 Process Production Integration             BLOCKED
  ↓
CS-06 Real Daily End-to-End Trial                BLOCKED
  ↓
CS-07 Visual Specialist Lab                      BLOCKED
```

The previous recommendation-only `LINA-VISUAL-SKILL-01` is absorbed into **CS-01**. It is not a competing task. The older `optional STUDIO-SPECIALIST-01` generic-platform sequencing is superseded for this bounded track by the Product Owner-approved hybrid Process slice; broader generic specialist/custom-composition work remains separately blocked.

---

# CS-01 — Contract + Runtime Specialist Skill

**Status:** DONE / ACCEPTED
**Dependency:** accepted Canvas Specialist contract/documentation sync only.  
**Purpose:** create the runtime Visual Learning Composer Skill and align the current disabled capability pack without enabling model execution.

### Accepted closure evidence

Product Owner accepted CS-01 on 2026-09-07 with Critical: 0, Important: 0,
Minor: 0. Focused tests: 3 passed, 0 failed, 0 skipped; affected Tutor/Process
contracts: 34 passed, 0 failed, 0 skipped; `git diff --check` passed. Primary
Tutor loads only accepted Tutor visual guidance, not Specialist instructions.
The broader regression diagnostic found an environment PostgreSQL deadlock
during fixture `TRUNCATE` before the test body, not a CS-01 failure. No model
execution, dependency, schema, Student runtime, WorkspaceIntent, ProcessView,
or routing change occurred.

### Required

- create `runtime/canvas-specialist/SKILL.md`;
- preserve `skills/lina-educational-visuals/SKILL.md` as development-only;
- reconcile `runtime/canvas-specialist/visual-capability-pack-v1.md` with the accepted contract;
- encode objective-first visual composition, hierarchy/grouping/relations, meaningful motion, Arabic/mixed direction, accessibility, responsive/narrow design, optional visual personalization and self-review;
- explicitly preserve Primary Tutor, renderer, persistence, Safety, Evidence/PF/LI authority boundaries;
- add focused tests that Specialist instructions are not loaded into Primary Tutor runtime.

### Forbidden in CS-01

- no `ModelTask.CANVAS_SPECIALIST`;
- no Gateway/Worker call;
- no dependencies;
- no WorkspaceIntent schema/meaning change;
- no database/migration;
- no Process production routing or ProcessView modification;
- no Student runtime behavior change.

### Verification / documentation

Follow CS-01 requirements in `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`. Create `docs/reviews/CS-01/IMPLEMENTATION_RECORD.md` before implementation and complete it before review.

**Accepted closure:** CS-01 is closed. CS-02 is READY but must not be executed
without its own explicit Product Owner authorization.

---

# CS-02 — Complete Visual Toolbelt

**Status:** DONE / ACCEPTED
**Approved target:** Motion + `react-konva@18`/Konva + JSXGraph + MathLive, with React/DOM/SVG remaining baseline.

Purpose is installation/adapter/browser proof only. No new production learning routing. Heavy/client-only engines should remain isolated/lazy where practical. Accepted ProcessView is not rewritten simply because Motion is installed.

Documentation: `docs/reviews/CS-02/IMPLEMENTATION_RECORD.md` and sanitized browser evidence where useful.

**Accepted closure:** Product Owner accepted CS-02 with Critical 0, Important
0, Minor 0. Motion 13.2.0, React-Konva/Konva, JSXGraph and MathLive were
installed/proven behind isolated adapters; focused contracts 2/0/0, Process
visual-awareness 19/0/0, typecheck, build and diff-check passed. No production
routing, Tutor, Studio runtime, Specialist execution or ProcessView change.

---

# CS-03 — Tutor ↔ Specialist Runtime Alignment

**Status:** DONE / ACCEPTED.

Product Owner accepted Tutor v10 optional Visual Order, deterministic Semantic
Alignment/Frozen Pack lineage, and bounded complete-current Personal Fact
catalogue behavior. Focused affected tests passed 159/0/0; disposable
PostgreSQL proof passed 5/0/0; no Specialist call, Job, Scene mutation, or
Evidence/PF/LI effect exists. The broader-suite fixture TRUNCATE deadlock is
retained in the implementation record as environment/test-fixture evidence.

Documentation: `docs/reviews/CS-03/IMPLEMENTATION_RECORD.md`.

---

# CS-04 — Real Canvas Specialist Execution Runtime

**Status:** READY.

Required direction:

- dedicated Canvas Specialist ModelTask/route through existing Model Gateway;
- current model decision GPT-5.6 Luna;
- existing PostgreSQL Job/Worker + `StudioCanvasSpecialistRun` seam;
- explicit `max_attempts=1`;
- no DB transaction/lock across inference;
- strict semantic proposal schema;
- complete run deadline/cancel/fail/supersede/stale/settlement/reconciliation behavior;
- AIExecution tokens/latency/cost/provider lineage;
- no automatic critic/repair/third Tutor call or hidden inference retry;
- live Luna structured-output proof when configured, distinct from mock evidence.

Documentation: `docs/reviews/CS-04/IMPLEMENTATION_RECORD.md`.

---

# CS-05 — Process Production Integration

**Status:** BLOCKED pending CS-04 acceptance.

First production natural-composition capability only:

- Process `sequence` / `cycle`;
- 2–8 stages;
- approved art handles;
- focus/reveal/trace;
- object/relation `REQUEST_EXPLANATION`;
- additive production Process contract/profile; do not mutate the accepted awareness-only proof into production silently;
- semantic-support + capability + Safety/permission + causal/stale validation;
- atomic supersede → accept → activate → Event/Snapshot/run-link transaction;
- strict production adapter/Host entry reusing the **existing accepted ProcessView**;
- existing `process_sequence_workspace` filtration activity remains separate;
- existing Studio feed/snapshot/reload remains delivery authority;
- no automatic Tutor call on Specialist completion.

Documentation: `docs/reviews/CS-05/IMPLEMENTATION_RECORD.md` plus sanitized browser screenshots.

---

# CS-06 — Real Daily End-to-End Trial

**Status:** BLOCKED pending CS-05 acceptance.

Purpose is product proof, not another architecture task.

Minimum journey set:

- grounded Process cycle;
- non-cycle sequence;
- Arabic/mixed-direction case;
- Chat-only zero-Specialist case;
- reuse/update zero-composition case;
- controlled failure/stale case;
- useful optional Personal-Fact visual personalization case;
- case where available personalization is deliberately not used because it adds no learning value.

**Acceptance order:** Quality first; then latency; then cost. Quality review is blocking. Record Tutor first text/terminal, queue, Specialist generation, Scene validation/commit, first useful Canvas, Tutor/Specialist tokens/cost and call counts. Do not invent a latency/cost pass threshold before this baseline exists.

Documentation: `docs/reviews/CS-06/IMPLEMENTATION_RECORD.md` is the real-trial closure report with scenario matrix, screenshots, timing/cost and explicit mock/live/browser distinctions.

---

# CS-07 — Visual Specialist Lab

**Status:** BLOCKED pending CS-06 acceptance.

Controlled post-proof experiments using the installed Toolbelt:

- Motion Lab;
- Konva spatial-interaction Lab;
- JSXGraph math-construction Lab;
- MathLive editable-math-input Lab.

Each engine receives a KILL / MODIFY / KEEP recommendation before any later production promotion. CS-07 does not automatically enable any engine-backed learning activity in production.

Documentation: one `docs/reviews/CS-07/IMPLEMENTATION_RECORD.md` with bounded sub-sections/evidence; do not create competing canonical specs.

---

## Documentation / transition rule for all CS tasks

1. Create `docs/reviews/<TASK-ID>/IMPLEMENTATION_RECORD.md` before code with baseline SHA, purpose, non-scope, protected boundaries, expected changed paths and verification plan.
2. Record meaningful implementation decisions/deviations only; not a diary.
3. Before claiming completion, record actual paths, tests/build/Postgres/mock/live/browser evidence, model-call counts, quality findings, latency/tokens/cost where applicable, unverified evidence and independent review.
4. Submit for Product Owner review and add/update the row in `docs/reviews/README.md`.
5. Only Product Owner acceptance changes status to DONE / ACCEPTED.
6. Update `project-state/PROJECT_STATE.md` and this file after acceptance; promote the next task only with explicit authorization.
7. `TASKS.md` is not rewritten merely to duplicate this current overlay.

## Execution boundary

Only **CS-04** is currently executable. All later CS tasks and all unrelated blocked work remain blocked until explicitly promoted.
