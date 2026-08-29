# Lina Full-System Learning Intelligence Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver and prove the governed path from raw conversation through real Segment Review, Session-authorized intelligence, and later real Tutor personalization on an isolated acceptance database.

**Architecture:** Preserve raw messages as authority. A closed, structurally-reviewable Segment obtains one staged semantic Review; a closed Session deterministically finalizes only a complete compatible Review set into a single authoritative processing run, Events/Evidence, and existing downstream projections. The acceptance harness is separate tooling: it clones the source database, migrates only the clone, reconstructs historical Segment boundaries through the Model Gateway, and records non-secret evidence.

**Tech Stack:** FastAPI services, SQLAlchemy/PostgreSQL, Alembic, database jobs/worker registry, OpenAI Model Gateway (`openai / gpt-5.6-luna`), pytest, existing Tutor context/runtime.

**Spec:** `docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md` (Task 1 materializes the approved user spec before any runtime work).

## Global Constraints

- Work only on `codex/ctx-03`; preserve unrelated changes and never write to the source conversation database.
- AI-powered acceptance calls use the configured real `openai / gpt-5.6-luna` route through Model Gateway; no mocks, LocalTutorProvider, fabricated findings, or fallback count as acceptance evidence.
- Do not expose `DATABASE_URL`, API keys, environment contents, or source-DB credentials.
- `LearningEvent + LearningEvidence` are downstream authority; Candidate and Segment Review are provenance only.
- Add `LearningEvent.segment_review_finding_index` but never add `LearningEvent.semantic_context`.
- `IntelligenceSessionAuthority.reprocess_run_id` is nullable for live finalization; it selects a complete authoritative processing run.
- New `segment-finalization-v1` Sessions never enqueue or execute legacy `SESSION_CONSOLIDATION`; historical Sessions retain legacy compatibility.
- Finalization is deterministic, atomic, idempotent, requires every structurally-reviewable Segment Review, and rejects missing/pending/running/failed/incompatible Reviews.
- Provider/model is Review execution provenance, not Review compatibility. Required compatibility is schema, prompt, rubric, and policy version.
- `findings=[]` is a successful finalization with zero new learner-memory changes. `POSSIBLE_CROSS_SUBJECT` and `UNCERTAIN` remain withheld and never erase valid `SAME_AS_SESSION` findings.
- No full historical transcript in normal Tutor context; current behavior continues to outrank historical intelligence.
- Do not expand Voice, Vision, UI, dashboards, artifacts, REC-25, unrelated retrieval, or frozen capabilities.

---

### Task 1: Acceptance governance and execution artifacts

**Files:**
- Create: `docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md`
- Create: `docs/superpowers/plans/2026-08-29-lina-full-system-acceptance.md` (this plan)
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`

**Produces:** The durable approved acceptance spec, active objective, acceptance evidence taxonomy, and explicit statement that D/E/F are implementation stages of this governed acceptance.

- [ ] **Step 1: Write a documentation assertion test.**

Run:
```bash
rg -n 'segment-finalization-v1|REAL LUNA|source database untouched|fresh-start' docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md
```

Expected before implementation: the file is absent.

- [ ] **Step 2: Materialize the approved spec.**

Transcribe the approved execution requirements: isolated copied DB, fixed Session ID, real-Luna-only semantic operations, historical reconstruction audit, deterministic D cutover, Candidate-optional authority, later Tutor and negative-memory proof, clean fresh-start proof, evidence labels, and completion gates.

- [ ] **Step 3: Mark the governing queue.**

Set Full-System Acceptance as the active execution objective without reopening A/B/C. Keep D/E/F ordered beneath it and preserve all deferred items.

- [ ] **Step 4: Verify documentation.**

Run:
```bash
git diff --check
rg -n 'Full-System Acceptance|segment-finalization-v1|REAL LUNA' TASKS.md project-state/PROJECT_STATE.md docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md
```

- [ ] **Step 5: Commit.**

```bash
git add docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md docs/superpowers/plans/2026-08-29-lina-full-system-acceptance.md TASKS.md project-state/PROJECT_STATE.md
git commit -m "docs: start full-system intelligence acceptance"
```

### Task 2: Finalization persistence contract and migration

**Files:**
- Modify: `services/platform/db/models.py`
- Create: `migrations/versions/<revision>_add_segment_finalization_contract.py`
- Modify: `tests/test_segment_learning_review_postgres.py`
- Create: `tests/test_session_finalization_postgres.py`

**Consumes:** Completed `SegmentLearningReview` rows and existing `IntelligenceProcessingRun`, `IntelligenceSessionAuthority`, `LearningEvent` and `LearningEvidence` models.

**Produces:** Nullable authority reprocess lineage, Event Finding-index provenance, Session pipeline identity, and database-enforced/tested migration upgrade/downgrade behavior.

- [ ] **Step 1: Write failing PostgreSQL tests.**

Cover: normal authority with `reprocess_run_id=None`; unique authority still enforced; Candidate-free Event with `candidate_event_id=None`; nullable `segment_review_finding_index`; Session pipeline identity defaults/backfills legacy safely; migration head supplies all fields.

- [ ] **Step 2: Run the focused RED tests.**

Run:
```bash
uv run --with-requirements apps/api/requirements.txt python -m pytest tests/test_session_finalization_postgres.py -q
```

Expected: failures proving the missing contract.

- [ ] **Step 3: Add the minimal model and Alembic migration.**

Use nullable foreign/provenance fields only where the spec requires them. Add a non-secret, explicit Session pipeline field that distinguishes `legacy-session-evidence-v1` from `segment-finalization-v1`; backfill existing rows as legacy and never rewrite source messages.

- [ ] **Step 4: Verify GREEN and migration reversibility.**

Run focused tests, `alembic upgrade head`, `alembic current`, and a downgrade/upgrade cycle against disposable PostgreSQL.

- [ ] **Step 5: Commit.**

```bash
git add services/platform/db/models.py migrations/versions tests/test_session_finalization_postgres.py tests/test_segment_learning_review_postgres.py
git commit -m "feat(intelligence): add segment finalization contract"
```

### Task 3: Deterministic Session Finalization service

**Files:**
- Create: `services/intelligence/session_finalization.py`
- Modify: `services/intelligence/current_state.py`
- Modify: `services/intelligence/authority.py`
- Modify: `services/intelligence/patterns.py`
- Modify: `services/intelligence/decisions.py`
- Modify: `services/intelligence/card.py`
- Modify: `tests/test_session_finalization_postgres.py`
- Modify: `tests/test_pattern_engine_postgres.py`
- Modify: `tests/test_decision_views_postgres.py`
- Modify: `tests/test_intelligence_card_postgres.py`

**Consumes:** A closed Session, structurally-reviewable closed Segments, compatible completed Review outputs, and compiled `EvidenceDimensions`/relationship contracts.

**Produces:** `finalize_closed_session(...)` that atomically creates an authoritative processing run, Events/Evidence only from eligible `SAME_AS_SESSION` Findings, authority, and existing deterministic projections.

- [ ] **Step 1: Write failing contract tests.**

Test missing/pending/running/failed/incompatible Reviews refuse all activation; provider/model differences remain compatible; candidate-free Finding survives; cross-subject/uncertain Findings are withheld without suppressing safe Math; `findings=[]` succeeds with no derived rows; idempotent retry returns the same authoritative run; every Event carries Segment Review and Finding index provenance.

- [ ] **Step 2: Run RED tests.**

Run the focused finalization test module and confirm each failing expectation is about absent finalization behavior rather than fixture setup.

- [ ] **Step 3: Implement deterministic materialization.**

Read Review output through the strict existing envelope. Validate Review/session/segment/message/Candidate lineage; create no semantic call; materialize only activation-eligible Findings; create `LearningEvent` and `LearningEvidence`; create/update unified authority; call existing Current State, Pattern, Decision View, and Card production services from the single transaction boundary.

- [ ] **Step 4: Remove Candidate-only downstream assumptions.**

Replace authority's Candidate-only selection with complete authoritative-processing-run selection. Where a deterministic projection requires optional historical Candidate metadata, use Event/Review finding provenance (`segment_review_id` plus `segment_review_finding_index`) when safely available; otherwise conservatively skip only that Pattern inference. Do not fabricate metadata or duplicate Finding content.

- [ ] **Step 5: Run GREEN coverage.**

Run finalization, pattern, decision, card, legacy Session Evidence, and segment-review PostgreSQL suites.

- [ ] **Step 6: Commit.**

```bash
git add services/intelligence services/platform/db/models.py tests
git commit -m "feat(intelligence): finalize reviewed sessions"
```

### Task 4: Job orchestration and live-pipeline cutover

**Files:**
- Modify: `services/tutor/session_lifecycle.py`
- Modify: `services/tutor/segment_lifecycle.py`
- Modify: `workers/intelligence_handlers.py`
- Modify: `workers/job_worker.py` if the registry requires the new handler
- Modify: `tests/test_session_lifecycle_postgres.py`
- Modify: `tests/test_segment_review_jobs_postgres.py`
- Modify: `tests/test_session_finalization_postgres.py`

**Consumes:** Task 3 finalizer and existing Segment Review job semantics.

**Produces:** Idempotent `SESSION_INTELLIGENCE_FINALIZE`, queued when a Segment-pipeline Session closes and again when its last required Review settles; no polling and no legacy consolidation for new Sessions.

- [ ] **Step 1: Write failing lifecycle tests.**

Assert a new Session is marked `segment-finalization-v1`; closing it reconciles segments but does not enqueue `SESSION_CONSOLIDATION`; exactly one finalization job is present only once all required reviews are complete; repeated closure/review completion cannot duplicate it; legacy Session close retains its legacy job.

- [ ] **Step 2: Run RED tests.**

Run only affected lifecycle/job/finalization tests.

- [ ] **Step 3: Implement explicit routing.**

Add the job constant and payload contract, route new Sessions to Segment finalization, preserve legacy behavior based on persisted pipeline identity, and make the worker handler lock the Session and invoke deterministic finalization. Segment Review completion must call the same idempotent enqueue helper after commit-safe state is present.

- [ ] **Step 4: Run GREEN integration tests.**

Run lifecycle, Segment-job, worker, and finalization PostgreSQL tests.

- [ ] **Step 5: Commit.**

```bash
git add services/tutor workers tests
git commit -m "feat(intelligence): orchestrate session finalization"
```

### Task 5: Isolated acceptance database and reconstruction tooling

**Files:**
- Create: `scripts/run_full_system_acceptance.py`
- Create: `tests/test_full_system_acceptance_tooling.py`
- Modify: `docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md`

**Consumes:** A source database URL loaded read-only from existing local configuration, Alembic head, Model Gateway factories, and the fixed source Session ID.

**Produces:** A deliberately explicit operator tool that creates a uniquely named acceptance database, copies the source without source writes, migrates the copy, validates preservation counts, reconstructs Segment boundaries only through a dedicated real-Luna Model Gateway task, and records non-secret JSON/Markdown evidence outside source data.

- [ ] **Step 1: Write failing pure/tooling tests.**

Test source URL is never used as a write target; required environment variables are presence-checked without printing; acceptance database name is unique and refusal occurs if source/target identity matches; reconstruction audit records source Message IDs and method/model lineage; no keyword boundary classifier is used.

- [ ] **Step 2: Run RED tests.**

Run the tooling test module with no provider call mode.

- [ ] **Step 3: Implement isolation and migration safeguards.**

Use PostgreSQL dump/restore or database-template operations only after source/target identity validation. Run Alembic on the target, assert migration head and 145/73/72/38 source counts, and create an audit report without credentials or secrets.

- [ ] **Step 4: Implement real-Luna reconstruction.**

Define a strict reconstruction envelope that returns ordered message-boundary assignments and reasons. Submit the complete chronological message list to a Model Gateway task; validate all 145 Message IDs appear once and in order; persist only reconstructed Segment rows and an acceptance-run audit artifact on the isolated DB/tool report. Never alter raw message fields.

- [ ] **Step 5: Run GREEN tooling tests.**

Run the tooling tests and Alembic smoke against disposable PostgreSQL; real provider execution is deferred to Task 6 and cannot be faked.

- [ ] **Step 6: Commit.**

```bash
git add scripts/run_full_system_acceptance.py tests/test_full_system_acceptance_tooling.py docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md
git commit -m "feat(acceptance): add isolated intelligence journey runner"
```

### Task 6: Historical real-Luna acceptance journey

**Files:**
- Modify: `scripts/run_full_system_acceptance.py`
- Create: `docs/acceptance-reports/2026-08-29-full-system-historical.md`

**Consumes:** Tasks 2–5 and the copied legacy 145-message Session.

**Produces:** Non-secret actual evidence of copied source preservation, reconstructed Segments, real Review AI execution IDs/counts, finalization results, source-grounded durable Event/Evidence counts, projections, withheld Findings, and a later real Tutor turn with context-debug provenance.

- [ ] **Step 1: Preflight the isolated database.**

Confirm the source receives no writes, the copy is distinct, Alembic is at head, and the fixed Session has 145/73/72/38 preserved records before reconstruction.

- [ ] **Step 2: Execute real-Luna reconstruction and Segment Reviews.**

Use the configured `openai / gpt-5.6-luna` route. Store AI execution ledger IDs, provider/model/task/status without secrets. Run required review jobs once; validate every persisted Finding against cited raw Student Message IDs.

- [ ] **Step 3: Execute real deterministic finalization.**

Close/reconcile the acceptance Session only in the acceptance DB, run the sole finalization job, inspect Event/Evidence/authority/state/pattern/decision/card rows, and distinguish durable outcomes from withheld/empty Findings.

- [ ] **Step 4: Execute the real personalization and negative proof.**

Open a new Math Session for the same acceptance Student through production Tutor runtime. Capture context-debug selection IDs, prove no full historical transcript was loaded, identify selected relevant state/pattern/card material, and prove listed unrelated social/religious/pregnancy/science/interpersonal content was excluded. Persist the real Tutor response and its AI execution ledger entry.

- [ ] **Step 5: Write the historical evidence report.**

State only observed facts; label this `REAL LUNA VERIFIED`, `DATABASE END-TO-END VERIFIED`, and `TUTOR PERSONALIZATION VERIFIED` only if the matching ledger/DB/context evidence exists. Always state `REAL-LINA VERIFIED = NO`.

- [ ] **Step 6: Commit evidence artifacts.**

```bash
git add scripts/run_full_system_acceptance.py docs/acceptance-reports/2026-08-29-full-system-historical.md
git commit -m "test(acceptance): record historical intelligence journey"
```

### Task 7: Fresh-start real-Luna journey and regression verification

**Files:**
- Modify: `scripts/run_full_system_acceptance.py`
- Create: `docs/acceptance-reports/2026-08-29-full-system-fresh-start.md`
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`

**Consumes:** The live Segment pipeline and all prior Tasks.

**Produces:** Separate clean-student proof from real Tutor turn through Segment decisions, Reviews, finalization, projections, later personalization, and concise governed completion state.

- [ ] **Step 1: Execute clean-state journey.**

Create a new acceptance-only Student/session in the isolated DB. Use real Tutor Runtime/Luna for a Math exchange with no fabricated Candidate or Review findings; ensure Segment creation/closure uses live runtime behavior; run its real Review and deterministic finalization; open a later real Tutor Session and inspect context provenance.

- [ ] **Step 2: Run full verification.**

Run focused RED/GREEN modules, relevant PostgreSQL integration suites, `npm run test:python`, applicable web typecheck/build, `alembic upgrade head`, `alembic current`, and `git diff --check`.

- [ ] **Step 3: Verify against the acceptance checklist.**

Read the spec line-by-line and record: source untouched, schema current, real reconstruction/reviews, Candidate-free path, no partial activation, projections, later personalization, negative exclusion, fresh start, and every remaining unverified item.

- [ ] **Step 4: Update operational documentation and commit.**

Keep only current operational state in `PROJECT_STATE.md`; mark exact verification taxonomy without calling Real-Lina validation complete.

```bash
git add scripts/run_full_system_acceptance.py docs/acceptance-reports TASKS.md project-state/PROJECT_STATE.md
git commit -m "test(acceptance): verify full intelligence journey"
```

### Task 8: Whole-branch review and delivery

**Files:**
- Review: all changes since `e5a12340c6ea8478bcaff10fdf0ed29281a9a3fc`

- [ ] **Step 1: Independently review code, migration, isolation, and evidence boundaries.**
- [ ] **Step 2: Run fresh verification commands for any reviewed fix.**
- [ ] **Step 3: Push `codex/ctx-03` only after all claims have corresponding fresh evidence.**

## Self-review

- Spec coverage: Tasks 1–8 cover governance, isolated source preservation, migration, deterministic finalization, Candidate-optional activation, orchestration, real-Luna historical/fresh journeys, personalization, negative exclusion, verification, and delivery.
- Placeholder scan: no `TODO`/`TBD` implementation placeholders are used.
- Type consistency: the central interfaces are `finalize_closed_session`, `SESSION_INTELLIGENCE_FINALIZE`, the persisted Session pipeline identity, and `LearningEvent.segment_review_finding_index`; later tasks consume these exact names.
