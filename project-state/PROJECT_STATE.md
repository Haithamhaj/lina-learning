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
FE-01 Visual System + Reuse Record  ACCEPTED / COMPLETED
STUDIO-RUNTIME-03 Canvas Tutor Turns DONE / ACCEPTED
STUDIO-ACT-MATH-01 Make-Ten Transfer READY — only READY Studio task
```

Current execution overlay is `project-state/DAILY_USE_RELEASE_TASKS.md`. `TASKS.md` remains the preserved historical ledger.

### Studio readiness — 2026-09-05

`STUDIO-GOV-01` and `FE-02-PRESERVE-01` are `DONE / ACCEPTED`; repository
verification, governing promotion, and prototype preservation are complete.
The approved target is documented in
`docs/STUDIO_IMPLEMENTATION_PLAN.md`: application-owned, subject-agnostic
Studio Core; semantic Event Log plus Materialized Current Snapshot; one
Student-facing Tutor; persistent Workspace; dedicated resumable Studio feed;
and deterministic subject capabilities before optional `CUSTOM_COMPOSE`
specialist work.

The FE-02 `/student/daily` prototype is preserved remotely on
`prototype/fe-02-studio-shell-2026-09-02` at
`8648371480b0aac116af2a49e2d3d7493d26360f`; its manifest is
`prototype/FE-02_PROTOTYPE_MANIFEST.md`. It remains non-authoritative,
non-production architecture: no Tutor-prose parsing, local browser state,
polling, or display-only Canvas is Studio truth. The `codex/ctx-03` tracked
tree contains accepted production Studio State and Subject Capability
foundations at Alembic head `c7d8e9f0a1b2`: code-owned MATH, SCIENCE, ENGLISH,
and ARABIC profiles; exact-version contracts; persisted Subject profile and
Action identity; typed validator/reducer dispatch; and bounded validation
results. No Student-facing Studio Activity, production renderer, or FE-02
production integration exists.

`STUDIO-PROTOCOL-01` and `STUDIO-RUNTIME-01` are `DONE / ACCEPTED`.
The existing primary Tutor call now receives the current Studio Snapshot and
exact unseen Event range; a completed successful Tutor turn advances the
durable watermark through its captured boundary while later Events remain
unseen. A bounded server-owned history service exists; model-invoked history is
deferred because no provider-neutral Gateway tool-execution contract exists.
`STUDIO-RUNTIME-02` is `DONE / ACCEPTED`: the same primary Tutor result may
contain a strict bounded WorkspaceIntent, and a deterministic Studio-owned
Router records a hidden non-mutating active-Scene/source/annotation/known-
capability/custom-compose-eligibility decision. `STUDIO-RUNTIME-03` is
`DONE / ACCEPTED`: authenticated Canvas-originated Tutor streaming has one
primary execution per exclusive StudentInteraction claim, real Tutor-message
persistence with exact Canvas provenance, distinct interaction plus Workspace
context, causal supersession, and cancellation after an interrupted
post-persistence stream lifecycle. It makes no direct Candidate, Evidence,
Personal Facts, or Learning Intelligence writes. Production Activities,
production Renderers, Canvas Specialist execution, and FE-02 production
integration remain unimplemented at this baseline. `STUDIO-ACT-MATH-01` is now
the only `READY` Studio implementation task; its bounded Make-Ten production
activity and minimal renderer are specified in the current execution overlay.
Student-authored free-form language belongs in Chat, including Voice-to-STT;
Canvas accepts bounded semantic controls and may display language, without
SafetyTextProjection or unrestricted Canvas language input. Every later Studio
task remains blocked.
`CURR-RENDER-MATH-01A` remains blocked until the Grade 5 Math renderer
implementation gate. Real Lina longitudinal history has not started.

---

## Current reality

- Execution branch: `codex/ctx-03`.
- Accepted PF-02 implementation commit: `062e2188ad5f4668183ff4ea8316f97926c5bd97`.
- Daily-Use PostgreSQL 17.8 / pgvector 0.8.1 is at Alembic head
  `c7d8e9f0a1b2`. Its pre-existing 39 application-table counts were unchanged
  by the additive Studio migrations; all seven Studio tables are empty.
- PF-02 already provides one dedicated asynchronous Personal Facts Model Gateway call per completed Learning Session, separate from Tutor and Segment Learning Review; strict Student-source/safety grounding; Fact + Observation persistence; retry-safe extraction runs; `ADD` / `SUPPORT` / `NOOP`; capacity skip; and an on-demand Personal Memory Document.
- PF-02A is accepted: the same PF model call receives a compact Student-scoped catalog of current and historical Fact identities, then semantically chooses `SUPPORT_EXISTING` or `ADD_NEW`; the server remains the deterministic grounding, ownership, safety, canonicalization, idempotency, and persistence authority.
- Known Facts are untrusted reference data only, not Evidence or instructions. PF-02A adds no schema/migration, second model call, embeddings, Tutor, Segment Review, Learning Intelligence, or RAG behavior.
- PF-03 is accepted/completed: commit `6436b358ff42425fd729af316cb9525e6511f534` adds a read-only full current Personal Memory Card to the existing Tutor context, with no pre-Tutor relevance selection, extra model call, embedding call, job, or schema change. PF-03 `7 passed`, protected regression `182 passed`, and diff/show checks passed; it is pushed to `origin/codex/ctx-03`. No FE-01 work was performed.
- No Lina real Student identity/history has been created or used.
- FE-01 is ACCEPTED / COMPLETED as documentation-only work at
  `8601ed5f485ff29fdb467db7abfb8f7ad44711b0`: Visual System + Library
  Capability + Learning Chat + Adaptive Learning Workspace for learners roughly
  10–18, with Lina as the first private daily-use Student. It established the
  Learning Chat + Adaptive Learning Workspace direction; the 2026-09-02 Product
  Owner Greenfield Clarification supersedes its earlier implementation-path
  assumption. The assistant-ui presentation-primitives fit check is complete:
  REJECT for FE-02 because it is runtime-bound or needs an adapter/state bridge
  that is unsafe for this presentation-only slice. ThreeUI/Spline remain
  visual reference only, and leaves a future isolated/lazy 3D Workspace-module
  path without adopting Three.js as app architecture. No UI code, dependencies,
  tests, runtime behavior, or PF-03 behavior changed. The protected /student
  and StudentMathSession remain legacy functional/behavioral-regression assets.
  The earlier `FE-02 is BLOCKED / NOT STARTED` status is preserved here as
  FE-01 historical context; it is superseded for current execution by the
  approved Studio track and its protected prototype boundary.
- STUDIO-RUNTIME-03 is DONE / ACCEPTED on the current accepted closure tree:
  focused mock-provider verification was `168 passed in 10.44s`; the full
  isolated suite was `889 passed, 7 skipped in 41.52s`; and a fresh independent
  review reported 0 Critical, 0 Important, and 0 Minor findings. The seven
  skips were five opt-in cloud-writing S3 tests and two opt-in real-Luna tests,
  not passes. No production frontend integration, Activity/Renderer,
  browser-use, live-model path verification, or real Lina daily/longitudinal
  use is implied by this backend acceptance.

---

## Active decisions

### FE-02 Product Owner Greenfield Clarification — historical prototype boundary

The existing /student page and StudentMathSession are protected experimental/legacy functional shell and behavioral-regression-harness assets. FE-02 must build the separate greenfield Daily Student App at /student/daily, reusing backend/session/SSE/Tutor/Safety/PF-03 contracts but not the existing UI implementation. It must not import, wrap, extract from, restyle, modify, or route through the legacy Student components.

The historical FE-02 implementation task remains superseded by the approved
Studio execution track. The assistant-ui presentation-primitives
fit check is complete with REJECT for FE-02: runtime-bound behavior or an
adapter/state bridge is not safe as presentation-only use in this slice. The
next pre-code gates are Product Owner approval of the first-screen visual brief
and explicit FE-02 implementation authorization. FE-CHAT-UI-01 is complete:
local React/Tailwind/shadcn patterns are adopted, official shadcn chat patterns
are partially adopted, AI Elements/VLLNT/shadcn.io are UX references, and
21st.dev Agent Elements is rejected. This clarification supersedes only the
earlier FE-02 implementation-path assumption. No dependency or runtime change
is authorized.

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

- **STUDIO-R1 — Studio backend foundations through Runtime-03 are accepted; only bounded STUDIO-ACT-MATH-01 is READY, while full frontend integration and later Studio tasks remain blocked — Criticality 4**
- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**
- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**
- **MATH-01 — Structured Math Readability — Criticality 4 / independent**
- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3 / investigate only if reproduced**
- **OPS-R1 — External model calls may experience recoverable transient failures — Criticality 3**

---

## Prior accepted context

### STUDIO-STATE-01 — Durable Production Studio State Foundation

**Status:** DONE / ACCEPTED

**Result:** additive Studio Runtime, Scene, semantic Event, Snapshot,
StudentInteraction, Tutor Studio Observation, and dormant Canvas Specialist Run
persistence; pure versioned core reducer; PostgreSQL-locked atomic append;
idempotency, stale Scene-version, cross-Student, capacity, replay, rollback,
and concurrency contracts. Daily-Use migration is applied at
`c7d8e9f0a1b2` with unchanged pre-existing counts and zero Studio rows.

**Boundary:** no routes/SSE, frontend, Tutor runtime/context, Model Gateway,
ModelTask, worker/job creation, subject profile, renderer, Learning Intelligence,
or Personal Facts behavior changed.

---

## Latest accepted task

### STUDIO-RUNTIME-03 — Canvas-Originated Tutor Turns

**Status:** DONE / ACCEPTED — BACKEND ONLY

**Acceptance:** authenticated Canvas-originated Tutor streaming uses an
exclusive StudentInteraction claim and one primary Tutor execution; it does
not synthesize a Student LearningMessage. Persisted Tutor messages retain
exact Canvas provenance. Runtime-01 Workspace context and current-interaction
context remain distinct; the observation/watermark lifecycle, causal terminal
ordering and supersession, RECORD_ONLY behavior, and interrupted-stream
cancellation preserve truthful durable history. Shared Safety/Parent Boundary
and Runtime-02 parser/Router contracts are reused. Direct Canvas Candidate,
Evidence, Personal Facts, and Learning Intelligence writes remain absent.

**Evidence:** focused `168 passed in 10.44s`; isolated `889 passed, 7 skipped
in 41.52s`; Alembic found no new upgrade operations (with the existing
`ai_executions` / `learning_messages` FK-cycle warning); and fresh independent
review found 0 Critical / 0 Important / 0 Minor. The skipped tests are opt-in
external S3 or real-Luna checks, not accepted as passing runtime evidence.

**Boundary:** this does not verify production frontend integration,
Activities/Renderers, browser behavior, the live-model Canvas path, or real
Lina daily/longitudinal use.

---

## Next recommended action

Execute only the explicitly promoted `STUDIO-ACT-MATH-01` bounded Make-Ten
activity task. Keep full FE-02 `/student/daily` Studio integration,
cross-subject activities, Grade 5 renderer work, Canvas Specialist work, and
all later Studio work blocked until separately authorized.

---

## Critical references

- `AGENTS.md`
- `docs/PERSONAL_FACTS_SPEC.md`
- `docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md`
- `docs/STUDIO_IMPLEMENTATION_PLAN.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `TASKS.md`
