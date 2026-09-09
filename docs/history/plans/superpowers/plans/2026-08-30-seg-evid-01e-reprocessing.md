# SEG-EVID-01E Reprocessing and Authority Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for inline task-by-task execution.

**Goal:** Reprocess a selected closed-session scope through its own legacy or
Segment-review pipeline, then atomically replace authority only after all staged
work is valid.

**Architecture:** Keep the request and authority boundary Session-scoped. Route
legacy Sessions to the existing `SESSION_EVIDENCE` consolidation path; route
`segment-finalization-v1` Sessions through validated current-contract Segment
Reviews and deterministic Event/Evidence staging without live authority writes.
Activation remains one transaction and rebuilds runtime projections only after
every selected Session stages successfully.

**Tech Stack:** Python 3.11, SQLAlchemy, PostgreSQL, Pydantic, existing Model
Gateway, pytest.

**Spec:** `/Users/haitham/.codex/attachments/02e2e753-d90f-47c1-9a17-3378375a2f05/pasted-text.txt`

## Global Constraints

- Preserve raw messages, Candidates, Reviews, and earlier processing runs.
- Never call a semantic Session model for `segment-finalization-v1`.
- Use current compiled Segment Review schema, prompt, rubric, and policy
  versions; provider/model are execution provenance only.
- Do not add `semantic_context`, synthetic Candidates, or misconception keys.
- `activate_reprocess_scope()` is the sole authority-changing path.
- Mark E `REVIEW`, leave F `BLOCKED`, and label all executions accurately.

---

### Task 1: Session-pipeline request identity and dispatch

**Files:**
- Modify: `services/intelligence/reprocess.py`
- Modify: `workers/intelligence_handlers.py`
- Test: `tests/test_intelligence_reprocess_postgres.py`

**Produces:** a request version set containing legacy Evidence identity and the
current Segment Review/finalization identity; worker dispatch with both Gateway
factories.

- [ ] Write RED tests that select one legacy and one Segment-finalization
  Session and assert the legacy Session calls only `SESSION_EVIDENCE` while the
  new Session never does.
- [ ] Run the tests and observe the current implementation incorrectly routes
  both Sessions through `consolidate_closed_session`.
- [ ] Add a `SegmentReviewVersionSelection` with schema, prompt, rubric, and
  review-policy defaults from compiled constants. Store it in `version_set` and
  validate it at enqueue and activation boundaries.
- [ ] Pass both Session-Evidence and Segment-Evidence Gateway factories to the
  reprocess worker, dispatching only from `LearningSession.intelligence_pipeline`.
- [ ] Re-run the tests and commit the green dispatch boundary.

### Task 2: Deterministic Segment-review staging without authority mutation

**Files:**
- Modify: `services/intelligence/session_finalization.py`
- Modify: `services/intelligence/reprocess.py`
- Test: `tests/test_intelligence_reprocess_postgres.py`

**Produces:** a reusable staged Segment-finalization function that validates
required Reviews, reuses exact compatible completed Reviews, materializes a new
processing run, and leaves `IntelligenceSessionAuthority` untouched.

- [ ] Write RED tests for valid Review reuse, incompatible Review rerun,
Candidate-free Finding preservation, and a zero-Finding Review producing a
completed staged run with zero Evidence.
- [ ] Run the tests and observe that the existing finalization function either
returns existing authority or writes live authority/projections.
- [ ] Extract shared Review validation and Finding materialization from normal
finalization. Add a staging entry point that builds a new processing run with
the current deterministic scope, returns withheld count, and performs no live
authority or runtime-projection write.
- [ ] For incompatible/missing Reviews, call `review_completed_segment` through
the Segment-Evidence Gateway before validating and staging; preserve completed
compatible Review rows unchanged.
- [ ] Re-run the tests and commit the green staged-finalization boundary.

### Task 3: Atomic cross-pipeline activation and retries

**Files:**
- Modify: `services/intelligence/reprocess.py`
- Modify: `workers/intelligence_handlers.py`
- Test: `tests/test_intelligence_reprocess_postgres.py`

**Produces:** coherent activation validation for mixed Session pipelines,
retry reuse of completed staged work, and rollback protection for authorities
and derived projections.

- [ ] Write RED tests for selected-scope partial failure, retry reuse,
multi-Session atomic swap, stale job rejection, and rebuild inputs limited to
newly authoritative runs.
- [ ] Run the tests and observe any missing staged-run/session/pipeline
validation or authority update before the full scope completes.
- [ ] Validate every `IntelligenceReprocessSession` against selected Session
ownership, closed status, expected pipeline, completed staged run, and coherent
version identity before changing authority. Keep all authority/projection work
inside the activation transaction.
- [ ] Preserve `previous_authority_by_session` and new run IDs in the durable
activation result; return completed staged rows unchanged on retry.
- [ ] Re-run the tests and commit the green atomic activation behavior.

### Task 4: Verification and governed state

**Files:**
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`
- Test: `tests/test_intelligence_reprocess_postgres.py`, relevant finalization,
  authority, Pattern, and Decision PostgreSQL suites

- [ ] Run focused PostgreSQL reprocessing and relevant downstream regression
  suites, then the canonical Python suite and `git diff --check`.
- [ ] If a new Review is needed for acceptance, execute it only through real
  `openai / gpt-5.6-luna`; otherwise record deterministic reuse of persisted
  real-Luna Reviews without claiming a new real-model run.
- [ ] Record E as `REVIEW`, keep F `BLOCKED` and Full-System Acceptance
  `IN_PROGRESS`, and retain `REAL-LINA = NO` and browser status accurately.
- [ ] Commit the implementation and governing state separately if that keeps
  review boundaries clearer, then push `codex/ctx-03`.
