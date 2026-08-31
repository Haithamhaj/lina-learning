# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

`DOC-SYNC-01` is **DONE / ACCEPTED**.  
`RL-01A — Accepted Runtime Alignment` is **DONE / ACCEPTED**.  
`RL-01B — Fresh Shared Application DB & Runtime Composition` is **DONE / ACCEPTED**.  
`RL-01C — Clerk + OpenAI Operational Verification` is the **ONLY READY TASK**.

Current execution overlay: `project-state/DAILY_USE_RELEASE_TASKS.md`.
`TASKS.md` remains the preserved historical ledger.

---

## Current reality

- `codex/ctx-03` is the accepted execution branch.
- RL-01B was committed/pushed at `dc76195bcb9ba7577b5f6dbbf0804f5bff6c43ff`; subsequent commits only promote/record current task governance until new runtime work is accepted.
- Fresh shared local Daily-Use PostgreSQL 17.8 + pgvector 0.8.1 was created from zero and migrated to Alembic head `f5a1c2d3e4b6`.
- No historical experimental interaction data was imported.
- Web, API, and Worker run from the aligned `ctx03` worktree against the same fresh database.
- Standard Worker command exists: `npm run dev:worker`.
- Worker job claim/complete/retry and restart smoke verification passed.
- The stale API from the old original checkout was stopped; the original checkout itself remains protected/unmodified.
- One synthetic `Sandbox Test Learner` exists with zero learning history. Lina's real Student identity/history has not been created or used.
- Implemented learning paths are Student-scoped. Cross-Student isolation is a **Criticality-5 launch invariant**.
- Same database for test/validation Students and Lina is approved; Lina's clean longitudinal baseline is Student-scoped, not database-scoped.
- Full-System Learning Intelligence Acceptance remains **DONE / ACCEPTED** with Segment Review + deterministic Session Finalization authority.
- Current hybrid RAG remains native Docling + PostgreSQL/pgvector; no RAG redesign is authorized for launch.

---

## Active decisions

1. Launch-first: finish the smallest reliable Daily-Use product, then expand from real Lina use.
2. Use one fresh shared application DB; test data and Lina may coexist only under isolated Student identities.
3. Lina's real Student identity starts with zero prior learning history.
4. Personal Facts are a separate Student-asserted context layer, not Learning Intelligence or Parent Core Profile.
5. Personal Facts never become Learning Evidence by identity and do not contain psychological/personality/learning-style inference.
6. Renderer-first is the primary teaching-visual strategy; image generation is optional/deferred illustrative output.
7. Student original images remain raw source; annotation is default derived feedback; clean reconstruction is fallback.
8. Frontend visual improvement is launch scope.
9. Initial Voice is Audio → STT → transcript → normal Tutor; raw audio is not retained after successful STT.
10. Vision/photo input is in the launch sequence after foundation/frontend gates.
11. AI capabilities remain behind Model Gateway; OpenAI is an operational provider, not permanent architecture.
12. Replit is a candidate private host after local proof, not product architecture.

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
- deterministic Session Finalization; no partial activation;
- Candidate metadata remains provisional;
- Student Core Profile, Personal Facts, conversation context, Safety, RAG, and Learner Intelligence remain separate authorities;
- cross-Student isolation across conversation, assets, Personal Facts, Learning Intelligence, and authorization;
- original Student work remains source; annotations/reconstructions are derived;
- no Redis/Celery, graph database, second learner-memory system, microservice split, or deployment redesign without demonstrated need.

---

## Active risks

- **RL-R3 — Real Auth/Model Operations Not Yet Verified — Criticality 5**  
  Real Clerk browser identity/JWT/JWKS and OpenAI-backed Model Gateway routes have not yet been proven on the fresh aligned runtime.

- **ISO-R1 — Cross-Student Runtime Isolation Under Real Auth — Criticality 5**  
  Persistence scoping is verified structurally/synthetically; RL-01C must verify authorization/isolation through the real Clerk identity path.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**  
  Current Student UI remains a proving surface; the approved polished Lina frontend is later in the launch sequence.

- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01C — Clerk + OpenAI Operational Verification

**Status:** READY  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01B **DONE / ACCEPTED**

**Goal:** Verify real Clerk identity/authorization and real OpenAI-backed Model Gateway routes on the aligned fresh runtime, using a controlled launch-test Student and preserving Lina's own Student history as clean/unstarted.

**Boundary:** Do not execute the full Session→Review→Finalization→Evidence→Card loop; that belongs to RL-01D. Do not start Personal Facts, frontend redesign, Voice, Vision, RAG changes, Artifacts, or deployment.

---

## Next recommended action

Execute **RL-01C only**, return its report for review, and do not start RL-01D in the same run.

---

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DAILY_USE_RELEASE_PLAN.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
