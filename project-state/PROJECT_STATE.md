# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **IN PROGRESS / BLOCKED ON TUTOR STREAM TRANSACTION LOCK**

Current execution overlay: `project-state/DAILY_USE_RELEASE_TASKS.md`.  
`TASKS.md` remains the preserved historical ledger.

---

## Current reality

- `codex/ctx-03` is the accepted execution branch.
- Fresh shared local Daily-Use PostgreSQL 17.8 + pgvector 0.8.1 was created from zero and migrated to Alembic head `f5a1c2d3e4b6`; no historical experimental interaction data was imported.
- Web, API, and Worker run from the aligned `ctx03` worktree against the same fresh shared application database.
- Test/validation Students and Lina may coexist in the same DB under isolated Student identities. Lina's real longitudinal baseline is Student-scoped, not database-scoped.
- OpenAI operational verification is **VERIFIED** through the existing Model Gateway:
  - Tutor: OpenAI / `gpt-5.6-luna`.
  - Segment Review transport: OpenAI / `gpt-5.6-luna` with strict structured output and no durable activation during transport-only verification.
  - Embedding: OpenAI / `text-embedding-3-small`, 1536 dimensions.
  - AI execution ledger records provider/model/task, success, latency, and usage lineage.
- Real Clerk browser sign-in is verified for launch-test Student and Parent identities.
- Clerk session-token customization carries signed role authority from user public metadata.
- Backend JWT/JWKS verification is verified: Parent resolves to `PARENT_ADMIN`; Student resolves to `STUDENT`.
- Launch-test Parent exists locally as application `User(role=PARENT_ADMIN)` and is explicitly linked to the Sandbox Test Student.
- **REAL-AUTH CROSS-STUDENT ISOLATION = VERIFIED** for implemented auth/session paths. Browser-supplied Student/session identifiers are locators only; authorization remains anchored to verified Clerk subject and server-owned Student ownership.
- RL-01D has partially proven the integrated Learning Intelligence path on the fresh runtime: natural Session closure, real Segment Learning Review, deterministic Session Finalization, one validated Event/Evidence path, Current State materialization, Candidate Patterns, Decision Views, job health, and cross-Student scoping all executed successfully. Pattern non-promotion after one Session was correctly insufficient evidence.
- RL-01D later-personalization acceptance is not yet complete because the controlled multi-turn Tutor scenario has not completed reliably through the normal FastAPI/SSE path.
- The earlier suspected OpenAI/provider timeout was not reproducible. Instrumented provider and TutorRuntime calls completed well within the existing 30-second blocking-operation timeout.
- A reproducible application blocker is now identified before OpenAI is reached: the request-scoped DB session resolves the authenticated Student using a `SELECT ... FOR UPDATE` lock, then the `StreamingResponse` generator opens a second DB session. That stream session attempts to insert `safety_audits` for the same Student and waits on the outer request transaction's Student-row lock / FK check. The observed wait is PostgreSQL `Lock / transactionid`; no Model Gateway call begins.
- The blocker is therefore a **stream transaction-boundary bug**, not an OpenAI reliability problem. No timeout/retry change is approved.
- Future Personal Facts isolation remains unimplemented/unverified until PF tasks.
- No Lina real Student identity/history has been created or used.

---

## Active decisions

1. Launch-first: finish the smallest reliable Daily-Use product, then expand from real Lina use.
2. Use one fresh shared application DB; test data and Lina may coexist only under isolated Student identities.
3. Lina's real Student identity starts with zero prior learning history.
4. Cross-Student isolation is a **Criticality-5 launch invariant**.
5. Personal Facts are a separate Student-asserted context layer, not Learning Intelligence or Parent Core Profile.
6. Renderer-first is the primary teaching-visual strategy; image generation is optional/deferred illustrative output.
7. Student original images remain raw source; annotation is default derived feedback; clean reconstruction is fallback.
8. Frontend visual improvement is launch scope.
9. Initial Voice is Audio → STT → transcript → normal Tutor; raw audio is not retained after successful STT.
10. AI capabilities remain behind Model Gateway; OpenAI is an operational provider, not permanent architecture.
11. Replit is a candidate private host after local proof, not product architecture.
12. Backend role authority comes from signed Clerk session-token claims; frontend-readable metadata alone is not backend authorization.
13. RL-01D stream correction must fix the request/stream transaction boundary without adding model retries, changing provider timeout, weakening Student ownership locks globally, or redesigning Safety/DB architecture.

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

- **RL-R5 — Tutor Streaming Request/Stream Transaction Lock — Criticality 5**  
  The normal FastAPI streaming route can self-block before OpenAI: the request-scoped transaction holds a Student row lock while the separate stream-session transaction tries to persist a `SafetyAudit` FK to the same Student. This must be corrected and regression-tested before RL-01D can resume.

- **RL-R4 — Later Relevant/Irrelevant Intelligence Selection Not Yet Proven — Criticality 5**  
  The downstream intelligence materialization path is partially proven, but RL-01D still requires a completed meaningful multi-turn Session followed by relevant later intelligence selection and an unrelated-context exclusion control.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01D — Controlled Full Intelligence Loop

**Status:** IN PROGRESS / BLOCKED ON TUTOR STREAM TRANSACTION LOCK  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01C **DONE / ACCEPTED**

**Verified within RL-01D so far:**
- natural Session/Segment lifecycle closure;
- real Segment Learning Review;
- deterministic Session Finalization with zero semantic Session model calls;
- Event/Evidence/Current State/Decision View materialization;
- correctly insufficient Pattern evidence;
- Worker/job health;
- cross-Student scoping;
- provider-level and TutorRuntime streaming can complete normally when bypassing the blocking FastAPI request/stream transaction boundary.

**Current blocker:** release the request-scoped Student lock before the independent stream-owned transaction begins, while preserving authenticated ownership and first-identity behavior. Add a deterministic PostgreSQL regression test for the safety-audit/stream path. Do not change OpenAI timeout or add hidden retries.

**Remaining RL-01D acceptance after the correction:** complete a meaningful three-turn Tutor Session through the real route, allow normal lifecycle/Review/Finalization, verify relevant Learner Intelligence selection in a later Session, and verify unrelated fraction intelligence is excluded from an unrelated Math question.

**Boundary:** Do not start TASK-027A, Personal Facts, frontend redesign, Voice, Vision, RAG changes, Artifacts, deployment, Science, or Parent Insights in this task.

---

## Next recommended action

Execute a bounded RL-01D transaction-boundary correction and regression verification only. Return the diff/results for review before resuming the final RL-01D acceptance journey. Do not start TASK-027A.

---

## Critical references

- `AGENTS.md`
- `docs/DAILY_USE_RELEASE_PLAN.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `TASKS.md`
