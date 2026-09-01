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
PF-03 Tutor Personal Context        ACCEPTED / COMPLETED
FE-01 Visual System + Reuse Record  IN REVIEW / DOCUMENTATION ONLY
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
- PF-03 is accepted/completed: commit `6436b358ff42425fd729af316cb9525e6511f534` adds a read-only full current Personal Memory Card to the existing Tutor context, with no pre-Tutor relevance selection, extra model call, embedding call, job, or schema change. PF-03 `7 passed`, protected regression `182 passed`, and diff/show checks passed; it is pushed to `origin/codex/ctx-03`. No FE-01 work was performed.
- No Lina real Student identity/history has been created or used.
- FE-01 has a documentation-only proposed decision record at
  `docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md`. It directs FE-02 to evolve
  the local shell into Learning Chat + Adaptive Learning Workspace,
  conditionally evaluates assistant-ui presentation primitives while rejecting
  it as a runtime replacement, treats ThreeUI/Spline as visual reference only,
  and leaves a future isolated/lazy 3D Workspace-module path without adopting
  Three.js as app architecture. No UI code, dependency, or Tutor/Personal
  Facts behavior changed.

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

### FE-01 — Visual System + Library Capability + Reuse Decision Record

**Status:** IN REVIEW / DOCUMENTATION ONLY
**Dependency:** PF-03 accepted
**Goal:** establish the code-grounded visual-system, library-capability, and
reuse record that constrains FE-02 without implementing UI.

**Boundary:** preserve the local Student session/SSE lifecycle, shadcn/Tailwind
baseline, safety, Tutor, Personal Facts/PF-03, and all backend authorities. No
UI code, dependencies, Voice, Vision, attachments, artifacts, or FE-02 work.

---

## Next recommended action

Review and accept the FE-01 documentation record. Only then update FE-01 to
accepted and promote FE-02 separately; do not begin FE-02 in this task.

---

## Critical references

- `AGENTS.md`
- `docs/PERSONAL_FACTS_SPEC.md`
- `docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `TASKS.md`
