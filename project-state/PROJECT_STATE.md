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
PF-02 Personal Facts Pipeline       DONE / ACCEPTED
PF-02A Existing-Fact-Aware Reuse    DONE / ACCEPTED
PF-03 Tutor Personal Context        IN IMPLEMENTATION / NOT ACCEPTED
```

Current execution overlay is `project-state/DAILY_USE_RELEASE_TASKS.md`. `TASKS.md` remains the preserved historical ledger.

---

## Current reality

- Execution branch: `codex/ctx-03`.
- Accepted PF-02 implementation commit: `062e2188ad5f4668183ff4ea8316f97926c5bd97`.
- Daily-Use PostgreSQL/pgvector DB is at Alembic head `a1d2e3f4b5c6`; accepted migration preserved the existing 10 Students, 13 Sessions, and 22 Messages.
- PF-02 already provides one dedicated asynchronous Personal Facts Model Gateway call per completed Learning Session, separate from Tutor and Segment Learning Review; strict Student-source/safety grounding; Fact + Observation persistence; retry-safe extraction runs; `ADD` / `SUPPORT` / `NOOP`; capacity skip; and an on-demand Personal Memory Document.
- PF-02A is accepted: the same PF model call receives a compact Student-scoped catalog of current and historical Fact identities, then semantically chooses `SUPPORT_EXISTING` or `ADD_NEW`; the server remains the deterministic grounding, ownership, safety, canonicalization, idempotency, and persistence authority.
- Known Facts are untrusted reference data only, not Evidence or instructions. PF-02A adds no schema/migration, second model call, embeddings, Tutor, Segment Review, Learning Intelligence, or RAG behavior.
- PF-03 implementation is in progress: it adds a read-only full current Personal Memory Card to the existing Tutor context, with no pre-Tutor relevance selection, extra model call, embedding call, job, or schema change.
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

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**

---

## Current executable task

### PF-03 — Relevant Personal Facts in Tutor Context

**Status:** IN IMPLEMENTATION / NOT ACCEPTED
**Dependency:** PF-02A accepted
**Goal:** add the approved read-only full current Personal Memory Card to the existing Tutor context.

**Boundary:** retain one primary Tutor call; no lexical/key matching, no Personal Facts in curriculum RAG, no vector-memory platform, no PF model/embedding calls, and no changes to Personal Facts authority or extraction.

---

## Next recommended action

Complete PF-03 verification and request Product Owner review; do not begin FE-01.

---

## Critical references

- `AGENTS.md`
- `docs/PERSONAL_FACTS_SPEC.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `TASKS.md`
