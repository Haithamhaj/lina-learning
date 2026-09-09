# SEG-EVID-01F Math Learning Intelligence Acceptance Execution Plan

> **For Codex:** Execute each task in order with test-first evidence. This plan
> deliberately excludes SCOPE-01, SUBJ-01, Science production routing, and
> browser/Real-Lina verification.

**Goal:** Verify the approved Math-only Learning Intelligence path using a clean
isolated database and real `openai / gpt-5.6-luna`, including safe bounded
retention anchors, multi-Session authority, pattern lifecycle, reprocessing,
and later Tutor personalization.

**Architecture:** Raw Math conversation remains source authority. Closed
Segments are interpreted by a versioned strict Segment Review; deterministic
Session Finalization is the only activation boundary. When retention is
logically evaluated, the reviewer receives only prior authoritative Evidence
anchors—never transcript, Card, Pattern conclusion, or free-form profile.

**Tech Stack:** Python, SQLAlchemy/PostgreSQL, Pydantic strict structured
output, existing Model Gateway, pytest, project acceptance tooling.

---

### Task 1: Prove the missing bounded-retention contract with a red test

**Files:**
- Modify: `tests/test_segment_semantic_review_postgres.py`
- Modify: `services/intelligence/segment_reviews.py`

**Step 1: Write the failing test**

Create prior Session-authorized Evidence for the same Math Student and a new
closed Segment. Assert the model request contains only the six approved anchor
fields, and that a grounded delayed `retention_check` can validate only against
that anchor.

**Step 2: Run test to verify it fails**

Run the single PostgreSQL test. Expected RED: the current request supplies an
empty anchor list and the validator rejects the retention Finding.

**Step 3: Implement minimal correction**

Select only authoritative prior Evidence for the same Student and subject;
serialize bounded anchor fields; validate anchor provenance, same concept,
meaningful elapsed time, retention event/context, and `retention_failure` only
where grounded. Version schema/prompt/policy identities so incompatible old
Reviews remain unavailable for new-contract semantic reuse.

**Step 4: Run focused tests**

Run the Segment Review PostgreSQL suite and finalization/reprocessing suites.
Expected GREEN: ordinary C-v1 findings remain unaffected; malformed, foreign,
or absent anchors fail closed.

### Task 2: Build repeatable Math-only acceptance tooling

**Files:**
- Create: `scripts/run_seg_evid_01f_acceptance.py`
- Create or modify: focused tooling tests under `tests/`

**Step 1: Write the failing test**

Add a focused contract test for an acceptance configuration validator: it must
require an isolated database, require `openai / gpt-5.6-luna`, reject source
database targeting, and report only sanitized identifiers/counts.

**Step 2: Run test to verify it fails**

Run the targeted test and confirm the script/module is not yet present.

**Step 3: Implement minimal tooling**

Use existing public Tutor runtime, session lifecycle, queued Review handler,
Session Finalization, and E reprocess path. Create one new Student and run only
normal Tutor/session operations; do not insert semantic outputs, Review rows,
Events, Evidence, States, Patterns, Decisions, or memory rows. Persist a
sanitized report below the ignored acceptance-artifact directory.

**Step 4: Run focused tests**

Run the acceptance-tooling test and relevant lifecycle/finalization tests.

### Task 3: Execute real-Luna multi-Session acceptance

**Files:**
- Create: ignored `.acceptance-artifacts/.../seg-evid-01f-report.json`

**Step 1: Create fresh isolated database**

Clone the local demo database inside the PostgreSQL container to a new uniquely
named acceptance database. Never write the source database or copy/create env
files. Load existing project environment read-only only for this execution.

**Step 2: Execute Math scenarios through normal runtime**

Run multiple Sessions covering confusion, bare wrong answer, explicit reasoning,
correction, TeachingMethod outcome, meaningful transfer, a later retention
check with authoritative anchors, pattern support/counter/weakening/resolution,
current behavior above history, and a later personalizing Tutor turn. Keep any
incidental non-Math content fail-closed and un-attributed.

**Step 3: Validate deterministic downstream and reprocess**

Confirm Review completion, Session-authorized Event/Evidence activation,
State/Pattern/Decision/Card results, negative-memory exclusion, atomicity, and
one E-path reprocess that reuses current-contract Reviews without a new semantic
call when eligible.

**Step 4: Record sanitized outcomes**

Record provider/model, IDs, counts, status assertions, policy/version lineage,
and sanitized context-debug selection. Do not store secrets or raw transcript
content in the report.

### Task 4: Final verification and governing record

**Files:**
- Modify: governed historical acceptance report
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`

**Step 1: Run verification**

Run focused PostgreSQL suites, canonical Python suite, and `git diff --check`.

**Step 2: Update state accurately**

Only after all gates pass, set SEG-EVID-01F and Full-System Acceptance to
`REVIEW`, retain `EDU-ERR-01` blocked pending independent F acceptance, and
keep Real-Lina/browser `NOT VERIFIED`. Record all automated/model/database
results as Codex-reported.

**Step 3: Commit and push**

Commit focused implementation/tests/tooling/docs without ignored acceptance
artifacts or local env files. Push `codex/ctx-03` without merge, rebase, or
scope expansion.
