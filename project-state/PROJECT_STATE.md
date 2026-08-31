# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **ONLY READY TASK**

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
- Parent real-auth verification passed:
  - `/api/v1/auth/me` → 200 `PARENT_ADMIN`;
  - Parent admin shell → 200;
  - Student shell → 403;
  - linked Student summary → 200;
  - unrelated Student summary → 404.
- Student real-auth verification passed:
  - `/api/v1/auth/me` → 200 `STUDENT`;
  - Student shell → 200;
  - Parent admin shell → 403;
  - supplying an unrelated `student_id` did not change server-owned Student identity;
  - foreign Session GET → 404;
  - foreign Session message POST → 404.
- **REAL-AUTH CROSS-STUDENT ISOLATION = VERIFIED** for implemented auth/session paths.
- Browser-supplied Student/session identifiers are locators only; authorization remains anchored to verified Clerk subject and server-owned Student ownership.
- Future Personal Facts isolation remains unimplemented/unverified until PF tasks.
- No Lina real Student identity/history was created or used during RL-01C.
- RL-01D has not started.

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

- **RL-R4 — Full Integrated Intelligence Loop Not Yet Proven on Fresh Runtime — Criticality 5**  
  Individual runtime/auth/model components are verified, but the natural controlled path from real Tutor interaction through Segment Review, deterministic Session Finalization, durable intelligence, and later relevant personalization still requires RL-01D verification.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01D — Controlled Full Intelligence Loop

**Status:** READY  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01C **DONE / ACCEPTED**

**Goal:** Prove on a controlled launch-test Student that the already-accepted architecture operates end-to-end on the fresh aligned runtime:

```text
real Tutor interaction
→ Segment lifecycle
→ Worker Segment Learning Review
→ deterministic Session Finalization
→ Event / Evidence
→ Current State / Patterns / Decision Views
→ Learner Intelligence Card
→ later relevant Tutor personalization
```

The proof must use normal application/Worker behavior rather than manual DB mutation, preserve one primary Tutor call, preserve deterministic Session finalization, and keep all validation data separate from Lina's future real longitudinal history.

**Boundary:** Do not start TASK-027A, Personal Facts, frontend redesign, Voice, Vision, RAG changes, Artifacts, deployment, Science, or Parent Insights in this task.

---

## Next recommended action

Execute **RL-01D only** and return its report for review. Do not start TASK-027A in the same run.

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
