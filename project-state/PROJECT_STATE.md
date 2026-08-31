# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **IN PROGRESS / FINAL AUTH-ISOLATION CHECKS REMAIN**

Current execution overlay: `project-state/DAILY_USE_RELEASE_TASKS.md`.  
`TASKS.md` remains the preserved historical ledger.

---

## Current reality

- `codex/ctx-03` is the accepted execution branch.
- Fresh shared local Daily-Use PostgreSQL 17.8 + pgvector 0.8.1 was created from zero and migrated to Alembic head `f5a1c2d3e4b6`; no historical experimental interaction data was imported.
- Web, API, and Worker run from the aligned `ctx03` worktree against the same fresh shared application database.
- Test/validation Students and Lina may coexist in the same DB under isolated Student identities. Lina's real longitudinal baseline is Student-scoped, not database-scoped.
- OpenAI operational verification is **VERIFIED** through the existing Model Gateway:
  - Tutor: OpenAI / `gpt-5.6-luna` — verified real execution.
  - Segment Review transport: OpenAI / `gpt-5.6-luna` — verified strict structured transport without durable intelligence activation.
  - Embedding: OpenAI / `text-embedding-3-small` — verified 1536-dimensional execution.
  - AI execution ledger records provider/model/task, success, latency, and usage lineage.
- Real local-browser Clerk sign-in is verified for a launch-test Student identity and a launch-test Parent identity.
- Launch-test Parent has `publicMetadata.role = PARENT_ADMIN` in Clerk.
- Clerk session-token customization now includes the user's public metadata, and after sign-out/sign-in the backend `GET /api/v1/auth/me` returns HTTP `200` with `role = PARENT_ADMIN` for the launch-test Parent.
- Therefore Clerk JWT/JWKS transport, signed backend role authority, and Parent frontend role recognition are all **VERIFIED**.
- Remaining RL-01C closure work is application-owned authorization only: bootstrap/verify the local Parent User, create the explicit Parent→Sandbox Test Student relationship, and verify linked access / unrelated-Student denial / Student→Parent denial / no browser-supplied identity override under real Clerk auth.
- `REAL-AUTH CROSS-STUDENT ISOLATION = PARTIALLY VERIFIED — FINAL RELATIONSHIP/ACCESS CHECKS PENDING`.
- No tracked source/schema/dependency change was required to fix the Clerk role issue; the fix was Clerk development-instance session-token configuration.
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
12. Backend role authority must come from signed Clerk session-token claims; frontend-readable metadata alone is not sufficient authorization.

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

Also protected: one primary Tutor model call per normal turn; current behavior outranks history; deterministic Session Finalization; separate Student Core Profile / Personal Facts / conversation context / Safety / RAG / Learner Intelligence authorities; cross-Student isolation; original Student work as source; no Redis/Celery, graph database, second learner-memory system, microservice split, or deployment redesign without demonstrated need.

---

## Active risks

- **ISO-R1 — Real-auth Parent/Student relationship isolation not fully closed — Criticality 5**  
  Parent JWT role is now verified. Final RL-01C work must prove application-owned Parent→Student linkage, denial for unrelated Students, Student→Parent denial, and no client-supplied identity override.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01C — Clerk + OpenAI Operational Verification

**Status:** IN PROGRESS — final real-auth authorization/isolation checks remain  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`

### Verified

- OpenAI Tutor route — VERIFIED.
- OpenAI Segment Review transport — VERIFIED.
- OpenAI embedding route — VERIFIED.
- AI execution ledger / secret boundaries — VERIFIED.
- Clerk JWKS reachability and unauthenticated denial — VERIFIED.
- Real browser Clerk sign-in — VERIFIED.
- Frontend Parent-role recognition — VERIFIED.
- Backend JWT/JWKS verification — VERIFIED.
- Backend signed Parent role (`PARENT_ADMIN`) — VERIFIED.

### Remaining closure gate

1. Bootstrap/verify launch-test Parent as application `User(role=PARENT_ADMIN)` using the verified Clerk subject.
2. Link that Parent explicitly to the existing Sandbox Test Student using the existing server-side relationship boundary.
3. Ensure at least one unrelated synthetic Student exists for denial testing.
4. Verify under real Clerk auth:
   - Parent admin shell allowed;
   - Student shell denied to Parent;
   - linked Student summary allowed;
   - unrelated Student summary denied without enumeration;
   - launch-test Student cannot access Parent surface;
   - browser-supplied Student/session IDs cannot cross ownership boundaries.
5. Do not execute RL-01D.

---

## Next recommended action

Return to Codex to finish only the remaining RL-01C application-owned Parent/Student bootstrap and real-auth isolation checks. No further Clerk dashboard changes are expected unless those checks reveal a new concrete blocker.

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
