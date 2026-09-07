# CS-03 — Tutor ↔ Specialist Runtime Alignment — Implementation Record

**Status:** DONE / ACCEPTED
**Prepared:** 2026-09-07
**Execution branch:** `codex/ctx-03`
**Implementation baseline:** `c59b9b29149f68f71514e753905dafb53daa23dc`

## Purpose

Add the bounded Primary Tutor → admitted Visual Order → Semantic Alignment
Envelope → Frozen Composition Pack → Visual Learner Context boundary. CS-03
stops before any Canvas Specialist execution, Job, Worker dispatch, run, or
Scene composition.

## Governing references

- `AGENTS.md`; Canvas Specialist execution contract, plan and acceptance spec.
- Current project state/task overlay and Product Owner decisions 39–41.
- `runtime/tutor/visual-guidance-v1.md`; Canvas Specialist Skill/capability
  pack (not loaded into Tutor); Personal Facts specification.

## Scope and protected boundaries

The current Tutor contract advances additively from `tutor_turn_v9` to a new
required-nullable visual-order sibling, preserving v8/v9 readers and
`workspace_intent-v1` meaning. Primary Tutor remains sole Student-facing
teacher; Studio/application retains execution, renderer, persistence, Safety,
Evidence/PF/LI authority. Core Profile remains age/Grade authority; selected
current safe Personal Facts are bounded read-only presentation input.

No database/schema/migration, Gateway/Worker/ModelTask/Specialist call, Job,
CanvasSpecialistRun, Scene/ProcessView/production routing, dependency, or
Student-visible protocol change is authorized.

## Pre-implementation governance correction

The plan status labels and task-overlay final execution boundary were stale
after accepted CS-01/CS-02 closure. Before source changes they were aligned to
CS-01/02 DONE / ACCEPTED, CS-03 READY, and CS-04–07 BLOCKED; no substantive
accepted CS content was changed.

## Implementation decisions

Changes are Tutor strict schema/provider normalization/runtime/context
capacity seams; a dedicated Studio-owned visual-order admission/pack helper;
focused tests; Tutor visual guidance; and this record. The new current schema
is `tutor_turn_v10` with required-nullable `workspace_visual_order`; v8/v9
remain explicit compatible readers with their historical field shapes. The
current local Tutor provider returns null.

`workspace-visual-order-v1` is an exact extra-forbidden raw order: COMPOSE,
PROCESS, SEQUENCE/CYCLE, objective, 2–8 ordered semantic facts, bounded
relations and must-not-imply constraints, 0–6 authorized source references,
0–3 exact Personal Fact keys, locale/direction, and display-name request.
Educational fields reject implementation/renderer/code terms. Admission occurs
only after full primary-Tutor parse and Parent Boundary handling; rejection is
hidden metadata and never fails the Chat response.

Application admission assigns stable `F1…F8` fact and `R1…R8` relation
identities in `semantic-alignment-envelope-v1`. It creates
`frozen-composition-pack-v1` containing the admitted order, alignment, exact
retrieved excerpts (or explicit `ADMITTED_TUTOR_ORDER` origin when no source is
requested), locale/direction, Specialist Capability Pack identity,
PROCESS 2–8 bound, allowed affordance names, and
`visual-learner-context-v1`.

The Visual Learner Context is transient input then frozen metadata: only Core
Profile age/Grade and, only when requested, display name; plus at most three
facts selected by the Primary Tutor from the current safe catalogue. The
catalogue resolves one latest value per Student-scoped eligible fact key
(PREFERENCE/FAVORITE/ACTIVITY/PET), then includes all current entries only when
the complete compact catalogue fits `12` facts and `1200` entry characters
(fact key + category + display statement). It is deterministically ordered by
fact key only after current-value resolution; it does not rank relevance.
Overflow returns no catalogue and `CATALOG_CAPACITY_EXCEEDED`, while the Tutor
may still admit a non-personalized visual. Under final request capacity
pressure, the guard drops the whole optional catalogue with
`CATALOG_OMITTED_CONTEXT_CAPACITY`, never individual facts. The Tutor may
select zero through three exact supplied keys; only those selected facts enter
the Visual Learner Context/Frozen Pack. It cannot set age/Grade or inject
Personal Fact history. SHA-256 is computed over canonical UTF-8 JSON (sorted
keys, compact separators) of the frozen pack. The resulting admitted order,
alignment, frozen pack, digest, and rejection code persist only under the
hidden Tutor `LearningMessage.payload.workspace_visual` audit boundary.

WorkspaceIntent v1 and router semantics are untouched. A Parent Boundary
server redirect bypasses visual admission; the persisted audit remains
`NOT_REQUESTED`. No Candidate Event, Evidence, PF, LI, Scene, Job, Worker,
Gateway, ModelTask, Specialist call, or Student-visible protocol is created by
the visual order.

## Changed paths

- `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md` and
  `project-state/DAILY_USE_RELEASE_TASKS.md`: narrow stale-status correction
  before source work.
- `runtime/tutor/visual-guidance-v1.md`: nullable bounded Process-order
  instruction only; explicit no-render/no-second-Tutor boundary.
- `services/studio/visual_order.py`: application-owned raw order, admission,
  semantic alignment, frozen pack, and digest contract.
- `services/tutor/candidate_events.py`, `services/model_gateway/openai_provider.py`,
  `services/tutor/context.py`, `services/tutor/capacity.py`, and
  `services/tutor/runtime.py`: v10 output, provider strictness/legacy
  recognition, all-or-nothing current catalogue/capacity handling, and hidden
  persistence.
- Focused contract/regression tests listed below.

## Verification results

- RED: `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_visual_order_admission.py` initially failed at collection with `ModuleNotFoundError: services.studio.visual_order`.
- GREEN: the same focused admission command: **6 passed, 0 failed, 0 skipped**.
- Final focused contract suite:
  `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_visual_order_admission.py tests/test_tutor_runtime_contract.py tests/test_tutor_runtime_scenarios.py tests/test_model_gateway_streaming.py tests/test_openai_provider.py tests/test_studio_workspace_intent.py tests/test_studio_workspace_router.py tests/test_process_visual_awareness.py`: **144 passed, 0 failed, 0 skipped**.
- Adjacent Core Profile/context/WorkspaceIntent/Process regression:
  `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_tutor_context_contract.py tests/test_tutor_context_capacity.py tests/test_student_core_profile.py tests/test_studio_workspace_router.py tests/test_process_visual_awareness.py`: **36 passed, 0 failed, 17 skipped** (pre-existing PostgreSQL-marked cases).
- PostgreSQL collection:
  `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_tutor_context_postgres.py tests/test_pf03_personal_memory_tutor_context_postgres.py tests/test_personal_facts_postgres.py tests/test_studio_tutor_context_postgres.py tests/test_process_visual_awareness_postgres.py tests/test_studio_state_postgres.py`: **0 passed, 0 failed, 117 skipped**. `-rs` confirms: `PostgreSQL DATABASE_URL is required for Tutor context tests`.
- Post-fix affected suite:
  `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_visual_order_admission.py tests/test_tutor_runtime_contract.py tests/test_tutor_context_contract.py tests/test_tutor_context_capacity.py tests/test_tutor_runtime_scenarios.py tests/test_model_gateway_streaming.py tests/test_openai_provider.py tests/test_studio_workspace_intent.py tests/test_studio_workspace_router.py tests/test_process_visual_awareness.py`: **159 passed, 0 failed, 0 skipped**.
- `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest python -m compileall -q services/tutor/context.py services/tutor/capacity.py services/tutor/runtime.py services/studio/visual_order.py`: passed.
- `git diff --check`: passed.
- Canonical disposable PostgreSQL proof:
  `uv run --with-requirements apps/api/requirements.txt --with pytest python scripts/test_postgres.py reset`, then
  `DATABASE_URL='postgresql+psycopg://lina_test:lina_test@127.0.0.1:55434/lina_learning_test' LINA_TEST_DATABASE=1 MODEL_PROVIDER=mock PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_canvas_specialist_alignment_postgres.py`, then
  `uv run --with-requirements apps/api/requirements.txt --with pytest python scripts/test_postgres.py down`: initial **2 passed, 0 failed, 0 skipped**; post-fix **5 passed, 0 failed, 0 skipped**. The named disposable container and volume were removed after each proof.
- Canonical broader regression diagnostic:
  `npm run test:python`: **575 passed, 25 failed, 486 errors, 7 skipped, 1 warning**. Migrations completed; the first distinct error class is a PostgreSQL `DeadlockDetected` during concurrent fixture `TRUNCATE ... CASCADE` setup (for example `tests/test_content_index_identity_postgres.py:46`), before affected test bodies. This environment/test-fixture failure is not attributable to a CS-03 path.

## Call-count and isolation evidence

The focused runtime proof records exactly one `ModelTask.TUTOR` AI execution
and the ordinary Learning Segment; it admits a source-grounded Process order
as hidden metadata with no Job, Specialist run, Scene, or Candidate Event.
The null Chat proof persists `workspace_visual.status = NOT_REQUESTED`. Parent
Boundary redirect proof likewise persists `NOT_REQUESTED`. No Specialist task
or provider route exists in this change.

## Known unverified evidence

The full canonical PostgreSQL regression does not complete cleanly because of
concurrent fixture TRUNCATE deadlocks; its aggregate is retained above and is
not represented as a pass. The focused CS-03 PostgreSQL proof passed. No live
Luna/Specialist call, browser evidence, Worker/Job execution, or Scene
rendering is required or claimed by CS-03. A read-only `git fetch origin` was
blocked by protected worktree `FETCH_HEAD` permissions; starting HEAD and
baseline ancestry were verified locally.

## Independent scope review

Product Owner review found one Important issue: recency-based catalogue
preselection could hide a relevant fourth current safe fact. The required fix
replaced it with complete-current-or-unavailable catalogue behavior and added
unit/PostgreSQL coverage for fourth-fact selection, no selection, overflow,
current-value transitions, and all-or-nothing final capacity handling.

Post-fix read-only review of the changed source and tests found no contradiction with
Primary Tutor authority, WorkspaceIntent v1, router semantics, Core Profile
authority, or Parent Boundary enforcement. No executable-code/renderer,
persistence/Safety/Evidence/PF/LI, Specialist, Gateway, Worker, Job, Scene,
ProcessView, schema/migration, routing, dependency, or CS-04 leakage was
found. Final findings: **Critical 0; Important 0; Minor 0**.

## Disposition

Product Owner accepted CS-03 on 2026-09-07 with **Critical 0; Important 0;
Minor 0**. The historical catalogue-preselection finding and its accepted
complete-current-or-unavailable correction remain recorded above. CS-03 is
**DONE / ACCEPTED**; CS-04 is **READY** but has not been started.
