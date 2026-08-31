# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

`DOC-SYNC-01` is **DONE / ACCEPTED**.  
`RL-01A — Accepted Runtime Alignment` is **DONE / ACCEPTED**.  
`RL-01B — Fresh Shared Application DB & Runtime Composition` is **DONE / ACCEPTED**.  
`RL-01C — Clerk + OpenAI Operational Verification` is **IN PROGRESS / BLOCKED ON CLERK SESSION-TOKEN ROLE CLAIM**.

Current execution overlay: `project-state/DAILY_USE_RELEASE_TASKS.md`.  
`TASKS.md` remains the preserved historical ledger.

---

## Current reality

- `codex/ctx-03` is the accepted execution branch.
- Fresh shared local Daily-Use PostgreSQL 17.8 + pgvector 0.8.1 was created from zero and migrated to Alembic head `f5a1c2d3e4b6`; no historical experimental interaction data was imported.
- Web, API, and Worker run from the aligned `ctx03` worktree against the same fresh shared application database.
- Test/validation Students and Lina may coexist in the same DB under isolated Student identities. Lina's real longitudinal baseline is Student-scoped, not database-scoped.
- OpenAI operational verification on the fresh runtime is **VERIFIED** through the existing Model Gateway:
  - Tutor: OpenAI / `gpt-5.6-luna` — verified real execution.
  - Segment Review transport: OpenAI / `gpt-5.6-luna` — verified strict structured transport without durable intelligence activation.
  - Embedding: OpenAI / `text-embedding-3-small` — verified 1536-dimensional execution.
  - AI execution ledger recorded success, latency, provider/model/task lineage.
- Real local-browser Clerk sign-in has now been completed successfully for both a launch-test Student identity and a second launch-test Parent identity.
- The launch-test Parent has Clerk `publicMetadata.role = PARENT_ADMIN`, and the Lina Web `/parent` surface recognizes that role correctly.
- A direct authenticated browser call to `GET /api/v1/auth/me` succeeded with HTTP `200`, proving Clerk JWT/JWKS transport and backend token verification are operational.
- That same backend response reported `role = STUDENT`, while the frontend reported `PARENT_ADMIN`. Root cause is now identified: `public_metadata.role` is not currently included in the Clerk session token claims consumed by the backend.
- This is a Clerk session-token configuration gap, not a database/authorization redesign requirement. The preferred fix is to add a compact custom session claim for `role`, sourced from `user.public_metadata.role`, then refresh/re-sign-in and re-run the backend role check.
- Real-auth Parent→Student authorization and cross-Student isolation remain pending until the backend JWT sees `PARENT_ADMIN`.
- `REAL-AUTH CROSS-STUDENT ISOLATION = NOT VERIFIED — CLERK ROLE CLAIM BLOCKER`.
- No tracked source/schema/dependency changes were made during RL-01C verification so far.
- RL-01D has not started and remains blocked until RL-01C closes.

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
12. Clerk role authority for backend requests must come from a verified session-token claim or another explicitly approved backend authority; frontend-readable metadata alone is not sufficient backend authorization.

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

- one primary Tutor model call per normal turn;
- current behavior outranks historical personalization;
- deterministic Session Finalization and no partial activation;
- Candidate metadata remains provisional;
- Student Core Profile, Personal Facts, conversation context, Safety, RAG, and Learner Intelligence remain separate authorities;
- cross-Student isolation across conversation, assets, future Personal Facts, Learning Intelligence, and authorization;
- original Student work remains source; annotations/reconstructions are derived;
- no Redis/Celery, graph database, second learner-memory system, microservice split, or deployment redesign without demonstrated need.

---

## Active risks

- **AUTH-R2 — Clerk Role Missing From Backend Session Token — Criticality 5**  
  Real browser login works and JWT verification returns `200`, but the backend still sees `STUDENT` because the Parent role currently exists only in Clerk public metadata / frontend-visible user data, not the signed session-token claims consumed by the API.

- **ISO-R1 — Cross-Student Runtime Isolation Under Real Auth — Criticality 5**  
  Structural/synthetic isolation and contract tests pass, but real Clerk-authenticated Parent/Student isolation cannot close until backend role authority is corrected and re-verified.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01C — Clerk + OpenAI Operational Verification

**Status:** IN PROGRESS / BLOCKED ON CLERK SESSION-TOKEN ROLE CLAIM  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01B **DONE / ACCEPTED**

### Verified within RL-01C

- OpenAI Tutor route — VERIFIED.
- OpenAI Segment Review transport — VERIFIED.
- OpenAI embedding route — VERIFIED.
- AI execution ledger / secret boundaries — VERIFIED.
- Clerk JWKS reachability and unauthenticated denial — VERIFIED.
- Real browser Clerk sign-in — VERIFIED.
- Frontend Parent-role recognition from Clerk public metadata — VERIFIED.
- Backend authenticated JWT/JWKS transport — VERIFIED (`/api/v1/auth/me` returns `200`).

### Remaining closure gate

1. Add a compact Clerk custom session-token claim that exposes the backend role from `user.public_metadata.role` (prefer direct `role` claim rather than embedding all public metadata).
2. Refresh/re-sign-in so a new session token is minted.
3. Confirm `/api/v1/auth/me` returns `PARENT_ADMIN` for the launch-test Parent.
4. Bootstrap/verify the corresponding local Parent User and explicit Parent→Sandbox Test Student relationship.
5. Verify linked Parent access, unrelated Student denial, Student→Parent denial, and no browser-supplied identity override under real Clerk auth.

Do not execute RL-01D until this gate is closed.

---

## Next recommended action

Update the Clerk development instance session-token customization to include a direct role claim from the user's public metadata, refresh the Parent session, and re-run the authenticated backend role check.

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
