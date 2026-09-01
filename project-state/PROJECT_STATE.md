# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **DONE / ACCEPTED**
- `TASK-027A — Student Core Profile & Tutor Student Context` — **DONE / ACCEPTED**
- `PF-01 — Personal Facts Contract` — **DONE / ACCEPTED**
- `PF-02 — Personal Facts Extraction/Reconciliation` — **ONLY READY TASK**

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
- `PF-01` is accepted as `docs/PERSONAL_FACTS_SPEC.md`: durable explicit Student Fact + source-linked Observation history/count, latest-explicit-current read semantics, retained historical contrary values, and one derived Personal Memory Document per Student. Personal Facts remain unimplemented.
- `PF-02` is the only ready task: one dedicated asynchronous Model Gateway call per completed Learning Session, separate from Tutor teaching and Segment Learning Review; Student-source grounding; deterministic `ADD` / `SUPPORT` / `NOOP`; and deterministic Personal Memory Document refresh. It must never write Learning Events, Evidence, Current State, or Patterns.
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
20. Personal Facts extraction is not Tutor output, Segment Review output, or a semantic Session Learning Intelligence summarizer. It is an independent asynchronous Session-level task; its failure does not block Learning Intelligence, and Learning Intelligence failure does not block it.

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
- Personal Facts extraction must remain separate from Tutor and Segment Review semantics.
- no second learner-memory system;
- cross-Student isolation across conversation, assets, Personal Facts, Learning Intelligence, and authorization;
- no Redis/Celery, graph database, microservice split, or generic memory framework without demonstrated need.

---

## Active risks

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**

---

## Current executable task

### PF-02 — Personal Facts Extraction/Reconciliation

**Status:** READY
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** PF-01 **DONE / ACCEPTED**

**Goal:** implement the accepted `docs/PERSONAL_FACTS_SPEC.md` contract only: dedicated asynchronous completed-Session Personal Facts extraction, Student-source grounding, deterministic `ADD` / `SUPPORT` / `NOOP`, and deterministic Personal Memory Document refresh. Keep it separate from Tutor and Segment Review, with no second reconciliation model call.

**Boundary:** Do not start PF-03, Tutor-context injection, vector retrieval, Parent Insights, or unrelated product work in this task.

---

## Next recommended action

Execute PF-02 against the accepted Personal Facts contract, preserving the protected separation from Tutor and Learning Intelligence.

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
