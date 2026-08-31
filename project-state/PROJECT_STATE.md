# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **DONE / ACCEPTED**
- `TASK-027A — Student Core Profile & Tutor Student Context` — **DONE / ACCEPTED**
- `PF-01 — Personal Facts Contract` — **ONLY READY TASK / CONTRACT REVISION IN REVIEW**

Current execution overlay: `project-state/DAILY_USE_RELEASE_TASKS.md`.  
`TASKS.md` remains the preserved historical ledger.

---

## Current reality

- `codex/ctx-03` is the accepted execution branch.
- Fresh shared PostgreSQL/pgvector Daily-Use DB, aligned Web/API/Worker, real Clerk auth, real OpenAI Model Gateway routes, real-auth cross-Student isolation, and the complete Learning Intelligence loop are verified.
- `RL-01D` proved real Tutor → Segment Review → deterministic Session Finalization → Event/Evidence → Current State/Patterns/Decision Views → compact relevant later Tutor personalization, with irrelevant historical intelligence excluded when unrelated.
- `TASK-027A` is accepted and committed as `57a763bbd538157c6503c10f64d0010a91dc2c46`.
- Student Core Profile now reuses the existing Student/GradePeriod foundation, adds nullable `Student.date_of_birth`, derives age deterministically rather than storing it, exposes a linked-Parent Core Profile boundary, and injects only compact `display_name`, `age_years`, and effective `grade_level` into Tutor context.
- GradePeriod lifecycle is accepted: a scheduled future Grade does not blank today's Grade; the current effective period remains valid through the day before the transition, and conflicting active overlaps are rejected rather than arbitrarily selected.
- Daily-Use Alembic head is `f9b1c2d3e4f5`.
- Student Core Profile remains Parent/System-authoritative and separate from Student-asserted Personal Facts and learning-derived Learner Intelligence.
- Personal Facts are **not implemented yet**. `PF-01` is currently being revised to the Product Owner-approved simple memory model: durable explicit Student Fact + source-linked Observation history/count. Extraction/reconciliation begins in `PF-02`; Tutor-context use begins in `PF-03`.
- The generic `Haithamhaj/personalization` repo and the earlier Customer Intelligence Card were reviewed for reusable ideas. We reuse the principles of facts, evidence/counts, recency, and separate memory/card projections; we do not import its event-sourcing, Redis/BullMQ, graph, vector-memory, replay, or multi-tenant architecture into Lina Release 1.
- No Lina real Student identity/history has been created or used. Lina's clean longitudinal baseline remains Student-scoped and unstarted.

---

## Active decisions

1. Launch-first: finish the smallest reliable Daily-Use product, then expand from real Lina use.
2. Use one shared application DB with strict Student-scoped isolation; Lina's real identity starts with zero prior test history.
3. Student Core Profile is Parent/System-authoritative application context.
4. Personal Facts are a separate **Student-asserted** context layer derived only from explicit safe durable statements the Student makes about herself/her ordinary world.
5. Release-1 Personal Facts use a simple **Fact + Observation History** model. Repeating the same explicit Fact adds an Observation, increases support count, and updates first/last-observed history. No arbitrary confidence percentage is stored.
6. A Fact is identified by Student + stable `fact_key` + normalized value. A different explicit value for the same `fact_key` is stored as a separate historical Fact; current state is derived at read time from the most recently observed explicit Fact for that key.
7. Count preserves strength/history but does not override a newer explicit contrary Fact. Recency decides the current value; prior counts remain useful context for future personalization/recommendation analysis.
8. Future plans, one-off events, and temporary states are Conversation Context, not Personal Facts. `TEMPORAL_EVENT` is excluded from Release 1.
9. Repeated discussion without an explicit assertion does not silently become an interest, preference, personality trait, or talent.
10. Personal Facts do not create Learning Evidence and must not contain personality/psychology conclusions, intelligence labels, learning-style labels, inferred talents, or academic judgments.
11. Parent may inspect stored Personal Facts and their support/history, but Parent claims do not become Student Personal Facts.
12. Student Core Profile, Personal Facts, Conversation Context, Safety, curriculum RAG, and Learner Intelligence remain separate authorities.
13. PF-03 retrieval must remain optional, cheap, bounded, and non-blocking. Use Student-scoped PostgreSQL indexes plus deterministic relevance/recency/count selection first; do not add a vector-memory platform or mix Personal Facts into curriculum RAG unless later measured need justifies it.
14. Current demonstrated behavior outranks historical personalization.
15. One primary Tutor model call per normal Student turn remains protected.
16. Renderer-first is the primary teaching-visual strategy; image generation remains optional/deferred illustrative output.
17. Initial Voice is Audio → STT → transcript → normal Tutor; raw audio is not retained after successful STT.
18. AI capabilities remain behind Model Gateway; OpenAI is an operational provider, not permanent architecture.
19. Replit is a candidate private host after local proof, not product architecture.

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

Separate from that learning path:

```text
Parent/System facts → Student Core Profile
Student explicit assertions → Personal Facts
```

Protected invariants:

- **Segment interprets; Session commits.**
- Candidate ≠ Evidence.
- Student Core Profile ≠ Personal Facts ≠ Learner Intelligence.
- Personal Facts never become Learning Evidence merely because they exist.
- Personal Facts store explicit factual assertions/context, not personality or psychological interpretation.
- Personal Facts retrieval must not become a second RAG/memory platform by default.
- no second learner-memory system;
- cross-Student isolation across conversation, assets, Personal Facts, Learning Intelligence, and authorization;
- no Redis/Celery, graph database, microservice split, or generic memory framework without demonstrated need.

---

## Active risks

- **PF-R2 — Personal Facts Contract Revision Not Yet Accepted — Criticality 5**  
  The simplified Fact + Observation model is Product Owner-approved in direction, but PF-01 still needs one clean final contract proposal before PF-02 implementation can begin.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**

---

## Current executable task

### PF-01 — Personal Facts Contract

**Status:** READY / REVISE CONTRACT ONLY  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** TASK-027A **DONE / ACCEPTED**

**Goal:** finalize the simple durable Student-scoped contract for explicit safe factual context the Student tells the system about herself/her ordinary world, without implementing extraction or Tutor use yet.

Required contract areas now are:
- durable explicit Fact vs conversation-only vs prohibited/sensitive statement;
- controlled category + stable `fact_key` + normalized value representation;
- source-linked Observation history;
- support count + first/last observed timestamps;
- different values for one `fact_key` preserved as history, with latest explicit Fact determining current state at read time;
- no future/agenda event storage;
- Parent inspection;
- strict separation from Core Profile, Safety, curriculum RAG, Conversation Context, and Learner Intelligence;
- cross-Student isolation;
- cheap optional PF-03 retrieval direction using PostgreSQL indexes and deterministic bounded relevance rather than vector Personal Facts retrieval.

**Boundary:** PF-01 does **not** implement database models/migration, model extraction, Worker reconciliation, Tutor-context selection, Parent Insights, frontend memory UI, or a second memory platform. Do not start `PF-02` in the same run.

---

## Next recommended action

Have Codex revise the PF-01 contract proposal to the approved simplified model and remove the supersession/invalidation/temporal-event complexity. Review that final contract once, then either accept PF-01 and promote PF-02 or correct only any remaining concrete contract gap.

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
