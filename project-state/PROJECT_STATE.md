# Lina Personal Learning System — Project State

## Current goal

Finish Daily-Use Lina Release 1 one accepted task at a time until Lina can begin stable private daily use.

Current sequence state:

```text
DOC-SYNC-01                         DONE / ACCEPTED
RL-01A Accepted Runtime Alignment   DONE / ACCEPTED
RL-01B Shared DB/Runtime            DONE / ACCEPTED
RL-01C Clerk + OpenAI               DONE / ACCEPTED
RL-01D Full Intelligence Loop       DONE / ACCEPTED
TASK-027A Student Core Profile      DONE / ACCEPTED
PF-01 Personal Facts Contract       DONE / ACCEPTED
PF-02 Personal Facts Pipeline       DONE / ACCEPTED BASELINE
PF-02A Existing-Fact-Aware Reuse    ONLY READY TASK
PF-03 Tutor Personal Context        BLOCKED UNTIL PF-02A ACCEPTED
```

Current execution overlay remains `project-state/DAILY_USE_RELEASE_TASKS.md`; it must be aligned to this approved correction before PF-02A implementation is committed. `TASKS.md` remains the preserved historical ledger.

---

## Current reality

- Execution branch: `codex/ctx-03`.
- Accepted PF-02 implementation commit: `062e2188ad5f4668183ff4ea8316f97926c5bd97`.
- Daily-Use PostgreSQL/pgvector DB is at Alembic head `a1d2e3f4b5c6`; accepted migration preserved the existing 10 Students, 13 Sessions, and 22 Messages.
- PF-02 already provides one dedicated asynchronous Personal Facts Model Gateway call per completed Learning Session, separate from Tutor and Segment Learning Review; strict Student-source/safety grounding; Fact + Observation persistence; retry-safe extraction runs; `ADD` / `SUPPORT` / `NOOP`; capacity skip; and an on-demand Personal Memory Document.
- A post-acceptance semantic-reuse gap was found in PF-02: the extraction model currently receives the completed Session messages but **not the Student's existing Personal Fact identities**. Therefore differently worded statements can independently recreate semantically identical `fact_key`/value pairs instead of reliably supporting the existing Fact.
- Approved correction: the same existing PF background model call must receive a compact Student-scoped catalog of existing Personal Fact identities, including historical contrary values. The model decides semantic reuse (`SUPPORT_EXISTING`) versus a genuinely new Fact (`ADD_NEW`); the server continues to enforce source grounding, ownership, safety, canonical identity, idempotency, and Observation rollups. No second reconciliation model call is added.
- This is a bounded correction to PF-02, not a new memory architecture. PF-03 implementation is paused until it is accepted.
- The previously proposed simple lexical PF-03 selector is not approved as a semantic relevance solution. PF-03 selection/injection will be reconsidered after PF-02A.
- No Lina real Student identity/history has been created or used.

---

## Active decisions

1. Student Core Profile = Parent/System-authoritative context.
2. Personal Facts = explicit safe durable Student-asserted context.
3. Learner Intelligence = evidence-backed learning-derived state.
4. Personal Facts remain separate from Conversation Context, Safety, curriculum RAG, and Learner Intelligence.
5. Release-1 Personal Memory uses Fact + immutable Observation History; Observation rows are source authority and support count is rebuildable.
6. Current value for a `fact_key` is the Fact with the latest explicit Observation; older contrary values remain history.
7. The PF extraction model owns semantic equivalence across wording/language. The server must not try to infer semantic sameness with keyword matching.
8. The PF extraction input must include both the completed Session conversation and a compact catalog of existing Student Personal Fact identities so the model can reuse an existing Fact instead of inventing a duplicate slot.
9. PF semantic output is bounded to reuse/support an existing Fact or propose a new canonical Fact. Server persistence remains deterministic and idempotent; there is no second reconciliation LLM call.
10. Current raw Student conversation outranks historical Personal Facts.
11. One primary Tutor model call per normal Student turn remains protected.
12. Personal Facts must not become a second curriculum RAG or generic memory platform by default.
13. Cross-Student isolation remains Criticality 5.

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

Separate memory authority:

```text
Student explicit assertions
→ PF background semantic extraction/reuse
→ Personal Fact + Observation History
→ Personal Memory Document
```

Protected invariants:

- **Segment interprets; Session commits.**
- Candidate ≠ Evidence.
- Tutor = teaching only.
- Segment Review = Learning Intelligence only.
- Personal Facts extraction = dedicated asynchronous Session-level task only.
- Personal Facts never create Learning Evidence merely by existing.
- No Redis/Celery, graph database, microservice split, vector-memory platform, or second reconciliation model call without demonstrated need.

---

## Active risks

- **PF-R3 — Existing Fact Semantic Reuse Gap — Criticality 5**  
  PF extraction currently does not see existing Fact identities, so paraphrases/cross-language restatements may create duplicate semantic Facts instead of adding Observations to the correct existing Fact.
- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**

---

## Current executable task

### PF-02A — Existing-Fact-Aware Personal Facts Extraction

**Status:** ONLY READY TASK  
**Dependency:** PF-02 accepted baseline  
**Goal:** minimally extend the existing PF Session-level extraction request/output so the model sees existing Student Fact identities and can semantically choose `SUPPORT_EXISTING` versus `ADD_NEW`, while preserving all accepted PF-02 safety, grounding, retry, capacity, isolation, and no-second-call boundaries.

**Boundary:** no PF-03 Tutor injection, no new migration/schema unless a concrete implementation blocker is demonstrated, no Tutor/Segment Review/RAG changes, no new worker or model call.

---

## Next recommended action

Implement and verify PF-02A only. After Product Owner acceptance, update the overlay and resume PF-03 design from the corrected Personal Memory foundation.

---

## Critical references

- `AGENTS.md`
- `docs/PERSONAL_FACTS_SPEC.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `TASKS.md`
