# Persisted Retention Provenance Repair Plan

> **For Codex:** Execute this plan in order. The existing `codex/ctx-03` worktree is the approved isolated workspace.

**Goal:** Preserve validation of a completed retention Segment Review when its exact historical Evidence was later superseded by an accepted reprocess, without allowing un-authorized historical Evidence into either persisted validation or fresh model input.

**Architecture:** Keep `_historical_anchors` as the current-authority-only selector for new Segment Review input. Add a separate persisted-review validator helper that admits only the review's exact stored anchor IDs after proving their source Session/run was authoritative either currently or in a completed, later reprocess activation audit. Reuse that helper in finalization and downstream Finding provenance resolution.

**Tech Stack:** Python, SQLAlchemy, PostgreSQL, pytest.

---

### Task 1: Add red integration coverage for historical authority replacement

**Files:**
- Modify: `tests/test_segment_semantic_review_postgres.py`
- Modify: `tests/test_intelligence_reprocess_postgres.py`

1. Build a source Session with authorized demonstrated Evidence E1 and a later delayed-retention Review anchored to E1.
2. Reprocess the source Session to E1-prime while retaining E1 rows; assert the persisted Review is no longer resolvable/finalizable before the repair.
3. Add fail-closed cases for arbitrary old Evidence, wrong student/session/run/delay, and a fresh review input that only contains E1-prime.
4. Run the narrow tests and confirm the new historical-replacement assertion fails before implementation.

### Task 2: Restore persisted-review validation from durable authority audit lineage

**Files:**
- Modify: `services/intelligence/segment_reviews.py`
- Modify: `services/intelligence/session_finalization.py`
- Modify: `services/intelligence/segment_review_provenance.py`

1. Derive requested anchor IDs only from persisted Review output.
2. Resolve those exact IDs only when their source Event/run satisfies the existing subject, student, closure, demonstrated/strong, and meaningful-delay checks, and their run is proven current or superseded by a completed reprocess activation after the Review existed.
3. Use this new persisted-only resolver in finalization and exact Finding provenance resolution; leave fresh model input on `_historical_anchors` unchanged.
4. Run the focused tests until green.

### Task 3: Verify reprocess continuation and update governed state

**Files:**
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`
- Modify: approved historical acceptance report, if it contains the previous blocker

1. Verify reprocessing a later Session with a valid historically anchored Review completes without dead-ending.
2. Run focused PostgreSQL tests, affected F regression tests, the canonical Python suite, and `git diff --check`.
3. Update the historical acceptance record and governing state with exact Codex-reported results; preserve SEG-EVID-01F and full-system acceptance as `REVIEW`, and all real-Lina/browser limitations.
4. Inspect the final diff, commit the focused correction, and push `codex/ctx-03` without staging `.acceptance-artifacts/`.
