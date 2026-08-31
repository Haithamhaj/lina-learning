# Lina Personal Learning System — Project State

## Current goal

Execute the Product Owner-approved **Daily-Use Lina Release 1** sequence one task at a time until Lina can begin stable private daily use.

- `DOC-SYNC-01` — **DONE / ACCEPTED**
- `RL-01A — Accepted Runtime Alignment` — **DONE / ACCEPTED**
- `RL-01B — Fresh Shared Application DB & Runtime Composition` — **DONE / ACCEPTED**
- `RL-01C — Clerk + OpenAI Operational Verification` — **DONE / ACCEPTED**
- `RL-01D — Controlled Full Intelligence Loop` — **DONE / ACCEPTED**
- `TASK-027A — Student Core Profile & Tutor Student Context` — **DONE / ACCEPTED**
- `PF-01 — Personal Facts Contract` — **ONLY READY TASK**

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
- Personal Facts are **not implemented yet**. `PF-01` defines their durable semantic/data contract only; extraction/reconciliation begins in `PF-02`, and Tutor-context selection begins in `PF-03`.
- No Lina real Student identity/history has been created or used. Lina's clean longitudinal baseline remains Student-scoped and unstarted.

---

## Active decisions

1. Launch-first: finish the smallest reliable Daily-Use product, then expand from real Lina use.
2. Use one shared application DB with strict Student-scoped isolation; Lina's real identity starts with zero prior test history.
3. Student Core Profile is Parent/System-authoritative application context.
4. Personal Facts are a separate **Student-asserted** context layer derived from what the Student tells the system about herself/her world.
5. Parent claims do not automatically become Student Personal Facts.
6. Personal Facts may evolve through support, contradiction, invalidation, and supersession while preserving source-message/time lineage.
7. Personal Facts do not create Learning Evidence and must not contain personality/psychology conclusions, intelligence labels, or learning-style labels.
8. Parent may inspect stored Personal Facts.
9. Student Core Profile, Personal Facts, Conversation Context, Safety, RAG, and Learner Intelligence remain separate authorities.
10. Current demonstrated behavior outranks historical personalization.
11. One primary Tutor model call per normal Student turn remains protected.
12. Renderer-first is the primary teaching-visual strategy; image generation remains optional/deferred illustrative output.
13. Initial Voice is Audio → STT → transcript → normal Tutor; raw audio is not retained after successful STT.
14. AI capabilities remain behind Model Gateway; OpenAI is an operational provider, not permanent architecture.
15. Replit is a candidate private host after local proof, not product architecture.

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
Student assertions → Personal Facts
```

Protected invariants:

- **Segment interprets; Session commits.**
- Candidate ≠ Evidence.
- Student Core Profile ≠ Personal Facts ≠ Learner Intelligence.
- Personal Facts never become Learning Evidence merely because they exist.
- Personal Facts store factual assertions/context, not personality or psychological interpretation.
- no second learner-memory system;
- cross-Student isolation across conversation, assets, Personal Facts, Learning Intelligence, and authorization;
- no Redis/Celery, graph database, microservice split, or generic memory framework without demonstrated need.

---

## Active risks

- **PF-R2 — Personal Facts Contract Not Yet Materialized — Criticality 5**  
  The Personal Facts layer is approved conceptually but its exact durable schema, provenance, lifecycle, sensitive-data boundaries, and Parent inspection contract must be defined before extraction can safely begin.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**

---

## Current executable task

### PF-01 — Personal Facts Contract

**Status:** READY  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Dependency:** TASK-027A **DONE / ACCEPTED**

**Goal:** define the durable, Student-scoped contract for factual context the Student tells the system about herself/her world, without implementing extraction or Tutor use yet.

Required contract areas:
- what qualifies and does not qualify as a Personal Fact;
- source authority = Student assertion/interaction;
- source-message/time provenance;
- canonical fact identity/category/value representation;
- support/repetition, contradiction, invalidation, and supersession lifecycle;
- current vs superseded state without deleting history;
- bounded handling of temporary/ephemeral statements;
- sensitive/private-information storage exclusions consistent with child safety;
- Parent inspection boundary;
- strict separation from Student Core Profile, Conversation Context, Safety, and Learner Intelligence;
- cross-Student isolation and rebuildability.

**Boundary:** PF-01 does **not** implement model extraction, Worker reconciliation, Tutor-context selection, Parent Insights, frontend memory UI, or a second memory platform. Do not start `PF-02` in the same run.

---

## Next recommended action

Define and review the `PF-01` Personal Facts contract first. Because this contract determines what the system is allowed to remember about a child, do not implement extraction before Product Owner approval of the categories, lifecycle, provenance, and privacy boundaries.

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
