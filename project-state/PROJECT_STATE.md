# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

`DOC-SYNC-01` is **DONE / ACCEPTED**.  
`RL-01A — Accepted Runtime Alignment` is **DONE / ACCEPTED**.  
`RL-01B — Fresh Shared Application DB & Runtime Composition` is **DONE / ACCEPTED**.  
`RL-01C — Clerk + OpenAI Operational Verification` is **IN PROGRESS / BLOCKED ON HUMAN CLERK LOGIN**.

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
- Clerk configuration is discoverable and technically reachable: frontend publishable configuration exists, live JWKS fetch succeeded, unauthenticated routes return `401`, and authorization contracts remain covered by automated tests.
- **Real Clerk browser login is not yet verified** because Codex's in-app browser could not reach the local loopback runtime after restart.
- Therefore real-auth Student/Parent role behavior and real-auth cross-Student isolation remain unverified.
- `REAL-AUTH CROSS-STUDENT ISOLATION = NOT VERIFIED — HUMAN LOGIN BLOCKER`.
- No tracked source/schema/dependency changes were made during RL-01C verification.
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

- **AUTH-R1 — Real Clerk Browser Session Not Yet Verified — Criticality 5**  
  Human browser sign-in is required to complete the actual Clerk session/JWT path on the local aligned runtime.

- **ISO-R1 — Cross-Student Runtime Isolation Under Real Auth — Criticality 5**  
  Structural/synthetic isolation and contract tests pass, but real Clerk-authenticated Student/Parent isolation is not yet verified.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **PF-R1 — Personal Facts Not Yet Implemented — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**

---

## Current executable task

### RL-01C — Clerk + OpenAI Operational Verification

**Status:** IN PROGRESS / BLOCKED ON HUMAN CLERK LOGIN  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** RL-01B **DONE / ACCEPTED**

### Verified within RL-01C

- OpenAI Tutor route — VERIFIED.
- OpenAI Segment Review transport — VERIFIED.
- OpenAI embedding route — VERIFIED.
- AI execution ledger / secret boundaries — VERIFIED.
- Clerk JWKS reachability and unauthenticated denial — VERIFIED.

### Remaining closure gate

A human-controlled local browser must complete real Clerk sign-in, after which Codex must verify:

- authenticated Student path;
- Student vs Parent role boundary;
- Parent → Student ownership boundary;
- real-auth cross-Student isolation;
- no browser-supplied identity override.

Do not execute RL-01D until this gate is closed.

---

## Next recommended action

Complete one real local-browser Clerk sign-in on the aligned runtime, then return control to Codex to finish only the remaining RL-01C auth/isolation checks.

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
