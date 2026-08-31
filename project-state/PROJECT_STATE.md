# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **IN PROGRESS / FINAL ACCEPTANCE JOURNEY READY**

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
- RL-01D has partially proven the integrated Learning Intelligence path on the fresh runtime: natural Session closure, real Segment Learning Review, deterministic Session Finalization, validated Event/Evidence materialization, Current State, Candidate Patterns, Decision Views, Worker/job health, and cross-Student scoping all executed successfully. Pattern non-promotion after one Session was correctly insufficient evidence.
- The earlier suspected OpenAI/provider timeout was not reproduced and is not the accepted cause of the Tutor stream failure.
- The actual application blocker was confirmed as a FastAPI/SSE transaction-boundary lock: the request-scoped transaction held a Student `FOR UPDATE` lock while the independent stream Session attempted to flush `SafetyAudit(student_id FK)`.
- `RL-01D-R3` corrected that boundary by completing request-side auth/ownership/action validation, copying plain stream inputs, and committing the request Session before the independent stream transaction begins. The correction preserves Student ownership and first-identity persistence without removing `FOR UPDATE`, weakening Safety, changing model timeout, or adding retries.
- `RL-01D-R3 FIX = ACCEPTED` and is committed/pushed as `3af613484266e2c21d9e91a20d09ef217b05c16e`.
- Regression verification passed for the previous PostgreSQL lock, first-identity creation, provider-failure ledger/recovery, and Student streaming/session behavior.
- Real post-fix smoke passed for three consecutive Tutor turns through FastAPI/SSE + real OpenAI: three `StreamComplete`, exactly one primary Tutor call per turn, three persisted SafetyAudits, six alternating Student/Tutor messages, three successful AIExecution rows, and zero observed PostgreSQL lock waits.
- The final RL-01D acceptance journey has **not** yet been run after this accepted correction.
- Remaining RL-01D proof is limited to one fresh meaningful multi-turn Session through normal lifecycle/Review/Finalization, followed by relevant later Learner Intelligence selection and an unrelated-context exclusion control.
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
13. The accepted Tutor-stream correction is a transaction-lifetime fix only. Do not reintroduce the previous lock, remove ownership locking globally, change provider timeout, or add hidden Tutor retries without a new demonstrated requirement.

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

- **RL-R4 — Later Relevant/Irrelevant Intelligence Selection Not Yet Proven — Criticality 5**  
  The materialization path is proven on controlled data, but RL-01D still requires one final post-fix acceptance journey showing meaningful multi-turn learning → normal finalization → relevant later intelligence selection, plus exclusion of stale fraction intelligence from an unrelated Math question.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01D — Controlled Full Intelligence Loop

**Status:** IN PROGRESS / FINAL ACCEPTANCE JOURNEY READY  
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
- normal provider/Tutor streaming;
- FastAPI/SSE request/stream transaction lock root cause and accepted correction;
- post-fix real three-turn Tutor smoke with one primary Tutor call per turn and durable Safety/AI/message persistence.

**Remaining acceptance gate:**
1. Run one fresh controlled non-Lina meaningful three-turn learning Session through the real authenticated application path.
2. Allow normal Session/Segment lifecycle, real Segment Review, and deterministic Session Finalization without manual DB mutation.
3. Inspect the resulting Event/Evidence/State/Pattern/Decision View/Card delta and lineage.
4. Start a later Session for the same Student and verify relevant finalized intelligence is actually selected into compact Tutor context without full prior transcript injection.
5. Run an unrelated Math control and verify stale fraction-specific intelligence is not blindly selected.
6. Confirm one primary Tutor call per normal turn, zero semantic Session LLM calls, healthy jobs, and Student isolation.
7. Stop for Product Owner review. Do not start TASK-027A in the same run.

**Boundary:** Do not start TASK-027A, Personal Facts, frontend redesign, Voice, Vision, RAG changes, Artifacts, deployment, Science, or Parent Insights in this task.

---

## Next recommended action

Execute the **final RL-01D acceptance journey only** on one fresh controlled non-Lina Student using the accepted post-fix runtime. Do not repeat the timeout investigation, authorization audit, or transaction-lock investigation unless a new concrete failure reproduces them. Do not start TASK-027A.

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
