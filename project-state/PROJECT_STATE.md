# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **DONE / ACCEPTED**
- `TASK-027A — Student Core Profile & Tutor Student Context` — **ONLY READY TASK**

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

- The accepted Tutor streaming transaction-lock correction is committed as `3af613484266e2c21d9e91a20d09ef217b05c16e`. It releases request-owned DB locks before the independent SSE stream transaction without removing Student ownership locking, weakening Safety, changing provider timeout, or adding hidden retries.
- The final controlled learning Session completed three real OpenAI Tutor turns with one primary Tutor call per turn, natural lifecycle closure, completed Segment Review, deterministic Session Finalization, source-linked Events/Evidence/State/Patterns/Decision Views, healthy jobs, and Student isolation.
- One first Segment Review provider attempt ended with durable `TimeoutError`; the configured automatic Worker retry succeeded. Final Review completed, no unrecoverable job remained, and no partial intelligence activation occurred. This is accepted as a recoverable provider failure, not an RL-01D correctness blocker.
- Relevant later personalization is verified: a later same-denominator-fractions question selected five compact authoritative Current State/Pattern entries from finalized prior intelligence; no full prior transcript, archived Session, or Personal Facts were injected; the Tutor still used one primary call.
- Irrelevant-context exclusion is verified: a later separate `7 × 8` Session selected no fraction-specific Learner Intelligence.
- `RELEVANT PRIOR INTELLIGENCE SELECTION = PASS`.
- `IRRELEVANT FRACTION INTELLIGENCE EXCLUSION = PASS`.
- `REAL-AUTH CROSS-STUDENT ISOLATION = VERIFIED` for implemented auth/session paths.
- Semantic Session LLM calls remain `0`; Session Finalization remains deterministic.
- No Lina real Student identity/history has been created or used. Lina's clean longitudinal baseline remains Student-scoped and unstarted.
- The next product foundation gap is Student Core Profile: Parent/System-authoritative child identity and school context must enter Tutor context as a separate compact authority before Personal Facts work begins.

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
9. Renderer-first is the primary teaching-visual strategy; image generation is optional/deferred illustrative output.
10. Student original images remain raw source; annotation is default derived feedback; clean reconstruction is fallback.
11. Frontend visual improvement is launch scope.
12. Initial Voice is Audio → STT → transcript → normal Tutor; raw audio is not retained after successful STT.
13. AI capabilities remain behind Model Gateway; OpenAI is an operational provider, not permanent architecture.
14. Replit is a candidate private host after local proof, not product architecture.
15. Backend role authority comes from signed Clerk session-token claims; frontend-readable metadata alone is not backend authorization.
16. Do not reintroduce the accepted Tutor streaming lock, remove ownership locking globally, change provider timeout, or add hidden Tutor retries without a new demonstrated requirement.

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

- **CORE-R1 — Student Core Context Not Yet Implemented — Criticality 4**  
  Tutor can use Learning Intelligence selectively, but Parent/System-authoritative child identity, DOB-derived age, active Grade, and GradePeriod are not yet a compact governed Tutor input.

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

**Status:** READY  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01D **DONE / ACCEPTED**

**Goal:** establish a compact Parent/System-authoritative Student Core Profile and inject only the relevant compact Student Core Context into Tutor requests as a separate authority from conversation, Personal Facts, RAG, Safety, and Learner Intelligence.

Expected core concepts include:
- child identity/display name under application authority;
- date of birth when supplied;
- age derived from DOB rather than independently maintained;
- active Grade / GradePeriod linkage;
- bounded Tutor Student Core Context;
- explicit provenance/authority separation from Student-asserted Personal Facts and learning-derived intelligence.

**Boundary:** Do not implement Personal Facts, frontend redesign, Voice, Vision, RAG changes, deployment, or later tasks in the same run.

---

## Next recommended action

Execute **TASK-027A only**. First audit what Student/Grade/GradePeriod identity structures already exist and reuse them where correct; implement only the missing Core Profile/context boundary. Stop for Product Owner review before promoting `PF-01`.

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
