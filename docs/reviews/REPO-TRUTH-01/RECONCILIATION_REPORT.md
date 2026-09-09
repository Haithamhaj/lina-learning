# REPO-TRUTH-01 — Reconciliation Report

> **Review evidence only. This is not a product or architecture source of
> truth.** Current truth is owned by the canonical documents identified below
> and by the accepted code at the recorded baseline.

## 1. Exact baseline

- Reconciliation candidate: `7ce6bcba41a6df92ff7862718a5d340925546415`
  (`origin/codex/ctx-03`, 2026-09-09 fetch).
- Known accepted baseline: the same SHA.
- Remote `main`: `b213e66f5e2505879610c0056f4bc5e576a01edc`.
- GitHub default branch reported by `origin`: `main`.
- The candidate descends from the known accepted baseline and from
  `origin/main`; `origin/main` has no commits absent from the candidate.
- Cleanup branch: `repo/truth-reset-01`, created directly from the candidate.
- The original `main` worktree was dirty (runtime and Daily Student changes);
  it was neither stashed nor changed. All reset work is isolated here.

## 2. Branch matrix

Ahead/behind is relative to the candidate. “Unique” means commits present on
the branch and absent from the candidate.

| Branch | SHA | Ahead / behind | Merge base | Ancestor? | Classification | Proposed action |
| --- | --- | --- | --- | --- | --- | --- |
| `origin/main` / `codex/safe-01` | `b213e66` | 0 / 222 | `b213e66` | yes | REDUNDANT_ANCESTOR | Promote the cleanup result to `main` only after approval; retire `codex/safe-01`. |
| local `main` | `6d5b7c2` | 0 / 232 | `6d5b7c2` | yes | REDUNDANT_ANCESTOR | Preserve its unrelated working-tree state; update it only through normal post-approval promotion. |
| `origin/codex/ctx-02` / `codex/ctx-02` | `8cb87b8` | 0 / 226 | `8cb87b8` | yes | REDUNDANT_ANCESTOR | Retire after approved main promotion. |
| `origin/task/004-parent-student-auth` / local branch | `96e8b77` | 0 / 325 | `96e8b77` | yes | REDUNDANT_ANCESTOR | Retire after approved main promotion. |
| `origin/codex/ctx-03` / `codex/ctx-03` | `7ce6bcb` | 0 / 0 | `7ce6bcb` | yes | CANONICAL_CANDIDATE | Use as the exact reconciliation source; retire only after main promotion. |
| `repo/truth-reset-01` | `7ce6bcb` at audit start | 0 / 0 | `7ce6bcb` | yes | TEMPORARY_CLEANUP_BRANCH | Push for review; retire after a verified main promotion. |
| `prototype/fe-02-studio-shell-2026-09-02` (local/remote) | `8648371` | 1 / 70 | `059ff3a` | no | PRESERVED_PROTOTYPE | Preserve unchanged. Its unique commit is `8648371 prototype: preserve FE-02 studio shell`. |
| `task/006-db-jobs-worker` (local only) | `10ae3b4` | 0 / 315 | `10ae3b4` | yes | REDUNDANT_ANCESTOR | Not a remote-retirement target; retain or remove its local ref only when its linked worktree is intentionally retired. |

No remote branch diverges from the candidate except the explicitly preserved
prototype. Remote branch protection was not inspectable during this audit.

## 3. Code-grounded current capability reality

The following is an implementation-anchor inventory, not a claim of new
acceptance. It establishes what current documentation must describe:

| Domain | Code anchors | Current reality to retain |
| --- | --- | --- |
| Student ownership and auth | `apps/api/routes/student.py`, `services/platform/db/models.py` | Clerk-backed Student/Parent boundaries and persisted ownership exist. |
| Safety and Parent Boundary | `services/tutor/parent_boundaries.py`, `services/student_sources/safety.py`, `services/tutor/runtime.py` | Explicit safety/boundary enforcement covers normal and multimodal paths. |
| Tutor and pedagogy | `services/tutor/runtime.py`, `teaching_decisions.py`, `teaching_methods.py` | One primary Tutor call determines semantic mode, strategy, method, and prior-method relation; code validates/persists the result. |
| Continuity and intelligence | `services/tutor/session_lifecycle.py`, `services/intelligence/{segment_reviews,consolidation,current_state,patterns,card}.py` | Session-local segments, review, evidence, state/patterns, and card foundations exist. |
| Personal Facts | `services/personal_facts/{extraction,reconciliation,memory_document}.py` | Personal Facts and Core Profile have a dedicated bounded subsystem. |
| Content and RAG | `services/content/{docling_adapter,indexing,semantics}.py`, `services/retrieval/service.py` | Original-source preservation, structural processing, optional semantics, and retrieval exist. |
| Voice and sources | `services/voice/transcription.py`, `services/student_sources/{service,docx,safety}.py` | Voice/STT and owned image/PDF/DOCX input are implemented paths. |
| Studio and Canvas | `services/studio/{service,canvas_specialist,workspace_capabilities}.py`, `apps/api/routes/studio.py` | Durable Studio state, Canvas Specialist admission, and Chat–Canvas–same-Tutor continuity exist. |
| Subject and visual surfaces | `services/studio/subjects/`, `apps/web/components/studio/` | MATH, SCIENCE, ENGLISH, and ARABIC Studio subjects exist; ordinary Chat remains available for general/unknown requests. The current Cartesian plane supports `[-10, 10]` on both axes. |
| Daily Student surface | `apps/web/components/daily-student/`, `apps/web/app/student/daily/` | A current Daily Student surface exists; authenticated end-to-end acceptance remains a separate next gate. |

## 4. Document classification matrix

| Current area / documents | Real role | Classification | Cleanup target |
| --- | --- | --- | --- |
| `README.md`, `AGENTS.md` | orientation; agent operating rules | CANONICAL | rewrite in place, concise |
| `docs/PROJECT_REFERENCE.md`, `LEARNING_INTELLIGENCE_SPEC.md`, `CHILD_SAFETY_POLICY.md` | durable product, intelligence, safety contracts | CANONICAL | reconcile in place |
| `docs/IMPLEMENTATION_PLAN.md`, `LEARNING_PRODUCT_ROADMAP.md` | technical direction; capability sequencing | CANONICAL | rewrite in place; remove historical-only conflict |
| `TASKS.md`, `project-state/{PROJECT_STATE.md,SYSTEM_MAP.html}` | execution queue; live operational state | CURRENT_STATE | compact/rewrite in place |
| `docs/domains/*` (new) | complex-domain supplements | CURRENT_DOMAIN_REFERENCE | create only Studio, Frontend, Personal Facts, Educational Visuals |
| `docs/README.md` (new) | documentation navigation | NAVIGATION | create |
| `docs/reviews/**`, `docs/acceptance-reports/**`, closure/checklist records | verification provenance | REVIEW_EVIDENCE | retain under `docs/reviews/` |
| `research/**`, reuse catalogue, post-launch backlog | investigation and candidates | RESEARCH_NON_AUTHORITATIVE | retain under `research/` |
| `docs/DAILY_USE_RELEASE_PLAN.md`, `STUDIO_IMPLEMENTATION_PLAN.md`, FE plans, Canvas execution/acceptance records, `docs/superpowers/plans/**` | completed or superseded implementation chronology | HISTORICAL_PLAN / HISTORICAL_DECISION | move under `docs/history/` after durable extraction |
| `project-state/DAILY_USE_RELEASE_TASKS.md`, existing `TASKS.md` | historical task overlay / long task history | HISTORICAL_TASK | archive under `docs/history/task-history/` |
| `output/**` | browser scripts, screenshots, generated result files | GENERATED_OUTPUT except review evidence explicitly moved | remove from current tracked tree or relocate durable proof beside review record |
| `.agents/memory/**`, `runtime/**`, `scripts/**` | local agent notes, runtime guidance, executable tooling | CURRENT_DOMAIN_REFERENCE / UNKNOWN_REQUIRES_REVIEW | retain in place; do not rewrite as product authority |
| `docs/DEVELOPMENT_DEMO.md`, `OBJECT_STORAGE.md`, `REUSE_DECISIONS.md`, `SUBJECT_SCOPE_POLICY.md`, `SUBJ_01_IMPLEMENTATION_SPEC.md`, `STUDIO_VISUAL_EXPLANATION_SPEC.md` | mixed operational and historical supplemental detail | UNKNOWN_REQUIRES_REVIEW | classify during physical cleanup; preserve rather than silently delete |

## 5. Contradiction register

| Contradiction | Files | Code/current-state evidence | Canonical owner | Cleanup action |
| --- | --- | --- | --- | --- |
| Voice, Vision, and Canvas are described as deferred despite implemented paths. | `README.md`, `TASKS.md`, old phase text | voice, student-source, Studio, Canvas, and Daily code anchors above | README; Project Reference; Roadmap | rewrite current documents; archive phase chronology |
| `IMPLEMENTATION_PLAN.md` declares itself historical/reference-only while AGENTS calls it current direction. | implementation plan; `AGENTS.md` | current architecture code spans API, worker, gateway, persistence, Studio | Implementation Plan | make it current architecture; move history out |
| `TASKS.md` is both a 131 KB history ledger and nominal current queue. | `TASKS.md` | completed capabilities now exist in code | TASKS | archive exact pre-reset file; replace with compact queue |
| `project-state/` carries a historical release-task overlay. | `project-state/DAILY_USE_RELEASE_TASKS.md` | project-state must be a live snapshot only | Project State | move overlay to history |
| Studio plans/readiness records duplicate durable architecture truth. | old Studio/Canvas/FE plans | durable Studio code exists | domain docs + Project Reference | extract current contract to `docs/domains/`; move records to history/reviews |
| Generated `output/` is mixed with repository knowledge. | tracked `output/**` | artifacts are scripts/screenshots/results, not product contracts | reviews only for durable evidence | relocate selected proof; untrack generated output and ignore directory |

## 6. Proposed canonical authority map

`AGENTS.md` owns operating rules; `README.md` orientation; `PROJECT_REFERENCE.md`
durable product truth; `LEARNING_INTELLIGENCE_SPEC.md` intelligence semantics;
`CHILD_SAFETY_POLICY.md` safety policy; `IMPLEMENTATION_PLAN.md` current technical
architecture; `LEARNING_PRODUCT_ROADMAP.md` evolution; `TASKS.md` executable
queue; `project-state/PROJECT_STATE.md` live operational state; and
`project-state/SYSTEM_MAP.html` the visual current map. `docs/domains/` provides
supplementary current detail. History, reviews, and research are non-authoritative.

## 7. Risks and unresolved findings

- Main protection could not be inspected from the local Git remote metadata.
- The original `main` working tree contains unrelated changes; it remains
  intentionally untouched outside this cleanup worktree.
- Existing historical documents may retain old links/branch names when that is
  provenance; only current canonical links must be made current.

## 8. Cleanup outcome

The canonical rewrite is followed by a physical separation: the exact old
`TASKS.md` is retained in `docs/history/task-history/`; historical plans,
decisions, supplemental specifications, and acceptance reports move beneath
`docs/history/`; technology/research material moves beneath `research/`; and
the tracked generated `output/` tree is removed from the current checkout and
ignored. The final hygiene commit records the exact file-level moves.
