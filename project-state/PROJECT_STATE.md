# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **DONE / ACCEPTED**
- `TASK-027A — Student Core Profile & Tutor Student Context` — **IN PROGRESS / BLOCKED ON FUTURE GRADEPERIOD WRITE LIFECYCLE**

Current execution overlay: `project-state/DAILY_USE_RELEASE_TASKS.md`.  
`TASKS.md` remains the preserved historical ledger.

---

## Current reality

- `codex/ctx-03` is the accepted execution branch.
- Fresh shared PostgreSQL/pgvector Daily-Use DB, aligned Web/API/Worker, real Clerk auth, real OpenAI Model Gateway routes, and real-auth cross-Student isolation are verified.
- RL-01D proved the accepted Learning Intelligence architecture end to end on controlled non-Lina data:

```text
real Tutor interaction
→ Segment lifecycle
→ real Segment Learning Review
→ deterministic Session Finalization
→ Event / Evidence
→ Current State / Patterns / Decision Views
→ compact Learner Intelligence selection
→ relevant later Tutor personalization
```

- The accepted Tutor streaming transaction-lock correction is committed as `3af613484266e2c21d9e91a20d09ef217b05c16e`.
- Relevant later personalization and irrelevant-context exclusion are verified; semantic Session LLM calls remain `0`; one primary Tutor call remains protected.
- No Lina real Student identity/history has been created or used. Lina's clean longitudinal baseline remains Student-scoped and unstarted.
- TASK-027A implementation is present locally for review and has not been committed/pushed. The design correctly reuses `Student` and `GradePeriod`, adds nullable DOB with derived age, preserves Parent/System authority, adds compact Tutor Core Context, and does not mix Personal Facts or Learner Intelligence into Core Profile.
- TASK-027A review found one Criticality-5 implementation defect in GradePeriod write lifecycle: saving a future GradePeriod currently deactivates the effective current GradePeriod immediately. This creates a gap where Tutor Core Context has no grade until the future period starts.
- Correct lifecycle direction: scheduling a future GradePeriod must not remove today's effective grade. The current effective period must remain effective through the day before the future period begins; future scheduling must not create overlapping effective periods or arbitrary resolution.
- Migration `f9b1c2d3e4f5` itself passed review: it only adds nullable `students.date_of_birth DATE`, preserves existing Students, and has no data rewrite.
- Parent authority, compact Tutor context, DOB-derived age, retrieval caller reuse, and cross-Student Core Profile isolation passed review.
- PF-01 remains blocked until TASK-027A is corrected and accepted.

---

## Active decisions

1. Launch-first: finish the smallest reliable Daily-Use product, then expand from real Lina use.
2. Use one fresh shared application DB; test data and Lina may coexist only under isolated Student identities.
3. Lina's real Student identity starts with zero prior learning history.
4. Cross-Student isolation is a **Criticality-5 launch invariant**.
5. Student Core Profile is Parent/System-authoritative application context and remains separate from Personal Facts and Learner Intelligence.
6. Age should be derived from date of birth rather than maintained independently when DOB is available.
7. Personal Facts are a separate Student-asserted context layer, not Learning Intelligence or Student Core Profile.
8. Current behavior outranks historical personalization.
9. A future GradePeriod is a scheduled future school state, not permission to erase the currently effective GradePeriod immediately.
10. When a future GradePeriod supersedes the current open-ended period, the current period should remain effective through `future.starts_on - 1 day`; effective overlaps must be rejected or resolved explicitly, never selected arbitrarily.
11. Renderer-first is the primary teaching-visual strategy; image generation is optional/deferred illustrative output.
12. Student original images remain raw source; annotation is default derived feedback; clean reconstruction is fallback.
13. Frontend visual improvement is launch scope.
14. Initial Voice is Audio → STT → transcript → normal Tutor; raw audio is not retained after successful STT.
15. AI capabilities remain behind Model Gateway; OpenAI is an operational provider, not permanent architecture.
16. Replit is a candidate private host after local proof, not product architecture.
17. Backend role authority comes from signed Clerk session-token claims; frontend-readable metadata alone is not backend authorization.
18. Do not reintroduce the accepted Tutor streaming lock, remove ownership locking globally, change provider timeout, or add hidden Tutor retries without a new demonstrated requirement.

---

## Protected areas

```text
Raw learning interaction
→ completed Segment semantic interpretation
→ Session-authorized Event/Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ relevant later learning personalization
```

Also protected:

- **Segment interprets; Session commits.**
- one primary Tutor model call per normal Student turn;
- current behavior outranks historical personalization;
- deterministic Session Finalization and no partial activation;
- Candidate metadata remains provisional;
- Student Core Profile, Personal Facts, conversation context, Safety, RAG, and Learner Intelligence remain separate authorities;
- cross-Student isolation across conversation, assets, future Personal Facts, Learning Intelligence, and authorization;
- original Student work remains source; annotations/reconstructions are derived;
- no Redis/Celery, graph database, second learner-memory system, microservice split, or deployment redesign without demonstrated need.

---

## Active risks

- **CORE-R2 — Future GradePeriod Scheduling Can Blank Current Tutor Grade — Criticality 5**  
  Current TASK-027A write behavior deactivates today's effective GradePeriod when a future GradePeriod is saved. Until corrected, Tutor Core Context may incorrectly lose `grade_level` before the future period starts.

- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**  
  Existing durable execution ledger and Worker retry/recovery behavior are operational controls; do not treat every recovered provider failure as a correctness failure.

---

## Current executable task

### TASK-027A — Student Core Profile & Tutor Student Context

**Status:** IN PROGRESS / BLOCKED ON FUTURE GRADEPERIOD WRITE LIFECYCLE  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01D **DONE / ACCEPTED**

**Implemented and review-passed areas:**
- existing Student identity reused; nullable `date_of_birth` extension only;
- deterministic DOB-derived age; no stored age;
- existing GradePeriod read resolver reused and Student-scoped;
- Parent/System-authorized linked-Student Core Profile boundary;
- compact Tutor Core Context containing only display name, derived age, and effective grade;
- raw DOB/IDs/Parent metadata/Personal Facts/Learner Intelligence excluded from Core Context;
- existing retrieval `grade_level` caller uses effective GradePeriod when available without RAG redesign;
- one primary Tutor model call preserved;
- cross-Student Core Profile isolation verified.

**Blocking defect:**
- creating/saving a future GradePeriod must not deactivate the currently effective period immediately;
- the correction must preserve current grade until the scheduled transition date and prevent overlapping effective periods;
- add regression coverage for current Grade 5 + scheduled future Grade 6, including the boundary date.

**Boundary:** Do not start PF-01, Personal Facts extraction/reconciliation, frontend redesign, Voice, Vision, RAG redesign, deployment, or later tasks while this blocker remains.

---

## Next recommended action

Correct only the TASK-027A GradePeriod write lifecycle and add focused regression coverage. Re-run the accepted TASK-027A verification suite, remove process-only Superpowers documents before commit, and return for Product Owner acceptance. Do not start PF-01.

---

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DAILY_USE_RELEASE_PLAN.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `TASKS.md`
