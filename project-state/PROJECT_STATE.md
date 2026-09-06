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
STUDIO-ACT-MATH-01 Make-Ten Transfer DONE / ACCEPTED
STUDIO-ACT-SCI-01 Process Sequence DONE / ACCEPTED
STUDIO-ACT-EN-01 English Sentence Ordering DONE / ACCEPTED
FE-02-STUDIO-01 Real Studio + Daily App DONE / ACCEPTED
STUDIO-ACT-AR-01 Arabic Academic Activity DONE / ACCEPTED
CURR-RENDER-MATH-01A            DONE / ACCEPTED
MATH-RENDER-NUMBER-LINE-01      DONE / ACCEPTED
STUDIO-ACCEPT-01                BLOCKED
```

Current execution overlay is `project-state/DAILY_USE_RELEASE_TASKS.md`. `TASKS.md` remains the preserved historical ledger.

### Studio readiness — 2026-09-06

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
results. The historical foundation baseline had no Student-facing Studio
Activity or production renderer. `STUDIO-ACT-MATH-01` now adds the accepted
exact-version Make-Ten activity and minimal React/SVG renderer; the accepted
FE-02 production integration is separate at `/student/daily`.

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
Personal Facts, or Learning Intelligence writes. Canvas Specialist execution
remains unimplemented. `STUDIO-ACT-MATH-01`
is `DONE / ACCEPTED`: its bounded exact-version Make-Ten Activity, durable
typed operations/validation/rebuild, minimal React/SVG renderer, and Runtime-03
submit continuation are accepted. `TRANSFER_ITEM` remains `RECORD_ONLY`;
submit creates one Runtime-03 Tutor continuation without a fake Student message
or direct learning-intelligence writes. The isolated mock-labelled review mount
is not `/student/daily`.
Student-authored free-form language belongs in Chat, including Voice-to-STT;
Canvas accepts bounded semantic controls and may display language, without
SafetyTextProjection or unrestricted Canvas language input.
`STUDIO-ACT-SCI-01` is `DONE / ACCEPTED`: it adds one bounded Science
`process_sequence_workspace` activity, not a generic Artifact Engine or
Science curriculum. `STUDIO-ACT-EN-01` is `DONE / ACCEPTED`: exact-version
`ENGLISH / subject-profile-v2` preserves historical English profiles and adds
the bounded `sentence_ordering_workspace`. Its project-authored
`english_sentence_ordering_fixture_slate /
english-sentence-ordering-fixture-slate-v1` uses stable opaque identities,
server-owned deterministic validation, record-only reorder, and one
submit-only Runtime-03 continuation. It does not authorize free-form Canvas
language, a generic text/artifact system, or `/student/daily` integration.
`STUDIO-ACT-AR-01` is **DONE / ACCEPTED**. Its intentional post-FE-02 deferral
is retained as history. The accepted bounded Arabic sentence-ordering activity
uses `ARABIC / subject-profile-v2`,
`arabic-sentence-ordering-workspace-activity-v1`,
`arabic-sentence-ordering-workspace-renderer-v1`, and
`arabic-sentence-ordering-workspace-scene-v1`, while preserving historical
Arabic profiles. Its project-authored case-marked fixture has opaque token IDs,
preserves Arabic words/diacritics, strictly parses browser-safe catalog/state,
and keeps deterministic academic validation server-owned. The accepted answers
are `تكتبُ الطالبةُ الدرسَ` and `تكتبُ الدرسَ الطالبةُ`; this bounded policy
does not classify other Arabic constructions generally. Reordering is
`RECORD_ONLY`; explicit submission alone triggers one Runtime-03 continuation.
The exact activation extends the accepted `/student/daily` Renderer Host without
reopening FE-02 or modifying protected `/student`/`StudentMathSession`.
`FE-02-STUDIO-01` is **DONE / ACCEPTED**. The real authenticated greenfield
`/student/daily` route retains one Student-owned LearningSession across Chat
and Studio, with exact `?session=` resume; it uses server-authoritative active
Scene/seed, exact Math/Science/English Renderer Host dispatch, reconciled
operations/feed/reload, and the accepted Runtime-03/admission boundary. The
accepted Arabic activity makes the smallest exact-contract extension to that
same host; it does not reopen FE-02 or alter legacy `/student` or
`StudentMathSession`. `STUDIO-ACCEPT-01` remains blocked because full-system
acceptance has not been performed or separately authorized; all other later
Studio and deployment work remains blocked.
`CURR-RENDER-MATH-01A` is DONE / ACCEPTED as a bounded planning correction,
not renderer implementation. The accepted pack at
`research/curr-render-math-01/` records the seven Section 14.2 corrections,
the reproducible 36-node coverage calculation, retained provenance limits, and
an independent review with 0 Critical / 0 Important / 0 new Minor findings.
The corrected planning basis has 11 proposed families, 9 Core and the same
four-family initial recommendation; actual implemented Grade 5 capability
coverage remains 0/36. `MATH-RENDER-BATCH-01` is an unaccepted umbrella, not
a blanket authorization: its only promoted child is
`MATH-RENDER-NUMBER-LINE-01`, now **DONE / ACCEPTED** for its bounded decimal
comparison and rounding slice; its sanitized closure record is
`docs/MATH_RENDER_NUMBER_LINE_01_ACCEPTANCE_CLOSURE.md`. Powers-of-ten,
estimation, fraction modes, and every other number-line or batch family
capability remain NOT PROMOTED. This acceptance does not change the research
coverage calculation or accept the umbrella.
`STUDIO-ACCEPT-01` is also BLOCKED / NOT PROMOTED. Real Lina longitudinal
history has not started.

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
- STUDIO-ACT-MATH-01 is DONE / ACCEPTED: the exact `9 + 6 → 10 + 5`
  Make-Ten flow has durable Event/Snapshot state, exact reload/rebuild,
  truthful invalid/stale handling, and bounded exact-Scene activation. The
  known activity makes no additional Canvas-model call. Final browser evidence
  covers mouse, emulated touch, keyboard, cancellation, rejection, RTL/narrow
  layout, and reduced motion; detailed commands, skips, and review evidence
  are in `project-state/DAILY_USE_RELEASE_TASKS.md`.
- STUDIO-ACT-SCI-01 is DONE / ACCEPTED: the exact-version Science v2
  `process_sequence_workspace` preserves historical empty Science v1, keeps
  the deterministic sand/water filtration answer order server-owned, and
  retains the submitted configuration independently from later record-only
  reorders. One Runtime-03 continuation occurs only on submit; no fake Student
  message, direct intelligence write, or additional Canvas model call exists.
  The isolated mock-labelled renderer is not `/student/daily`. Detailed
  verification, provenance, and independent-review evidence are retained in
  `project-state/DAILY_USE_RELEASE_TASKS.md`.
- STUDIO-ACT-EN-01 is DONE / ACCEPTED: exact `ENGLISH /
  subject-profile-v2` keeps historical English profiles unchanged and resolves
  the bounded `sentence_ordering_workspace` fixture
  `english_sentence_ordering_fixture_slate /
  english-sentence-ordering-fixture-slate-v1`. The server-only canonical order
  is `tok-c820 → tok-43bd → tok-7f2c → tok-a91e`; the browser catalogue is
  `tok-7f2c → tok-a91e → tok-43bd → tok-c820` and its deterministic initial
  order is `tok-a91e → tok-c820 → tok-7f2c → tok-43bd`. Opaque fixture IDs do
  not encode labels or canonical positions; duplicate visible labels remain
  separately representable. `REORDER_TOKEN` remains record-only; only submit
  creates one Runtime-03 continuation. The submitted configuration remains
  source truth after later reorders. No fake Student message, direct Candidate,
  Evidence, Personal Facts, or Learning Intelligence write, extra
  Canvas/Specialist call, free-form Canvas language channel, or FE-02
  integration was accepted. Detailed verification and final review evidence are
  in `project-state/DAILY_USE_RELEASE_TASKS.md`.
- `STUDIO-ACT-AR-01` is **DONE / ACCEPTED**. The accepted Arabic activity
  preserves Student ownership, rejection/idempotency, Event/Scene/Snapshot
  persistence and rebuild, and the original submitted configuration/validation
  separately from later Workspace state in configured mock-Gateway input. Each
  accepted submission has one interaction and Tutor continuation, with no fake
  Student message or direct Canvas intelligence/Personal-Facts write. ARABIC →
  LANGUAGE_ARTS and LiveSubjectContext remain unchanged. Authenticated evidence
  covers pointer, browser-emulated touch, keyboard/focus, RTL, reconciliation,
  reload, narrow layout and reduced motion; it is not live-provider, physical
  device, natural activity-selection, deployment, or real-Lina proof.
- `FE-02-STUDIO-01` is **DONE / ACCEPTED**. The tracked greenfield
  `/student/daily` integration reuses real Studio Runtime/Snapshot/Event and
  Tutor authorities; the preserved prototype remains reference-only. Its final
  matrix is 37 PASS: one new Chromium/CDP-emulated touch case and 36 applicable
  reused cases. `STUDIO-ACCEPT-01` remains blocked pending a separately
  authorized full-system acceptance run.

---

## Active decisions

### FE-02 Product Owner Greenfield Clarification — historical prototype boundary

The existing /student page and StudentMathSession are protected experimental/legacy functional shell and behavioral-regression-harness assets. FE-02 must build the separate greenfield Daily Student App at /student/daily, reusing backend/session/SSE/Tutor/Safety/PF-03 contracts but not the existing UI implementation. It must not import, wrap, extract from, restyle, modify, or route through the legacy Student components.

The historical FE-02 implementation task remains superseded by the approved
Studio execution track. `FE-02-STUDIO-01` is DONE / ACCEPTED; this closure does
not authorize a later Studio task. The
assistant-ui presentation-primitives
fit check is complete with REJECT for FE-02: runtime-bound behavior or an
adapter/state bridge is not safe as presentation-only use in this slice. The
first-screen visual brief remains mandatory implementation input; if the real
Studio composition needs a material change to it, return to the Product Owner
before implementation. Separate Product Owner authorization is required for
later Studio work. FE-CHAT-UI-01 is complete:
local React/Tailwind/shadcn patterns are adopted, official shadcn chat patterns
are partially adopted, AI Elements/VLLNT/shadcn.io are UX references, and
21st.dev Agent Elements is rejected. This clarification supersedes only the
earlier FE-02 implementation-path assumption. No dependency or runtime change
is authorized.

**Release order:** finish the approved bounded Arabic activity and full Studio
acceptance before any Replit experiment or deployment work. Replit remains
blocked; no early experiment or deployment is authorized.

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

- **STUDIO-R1 — Studio foundations plus bounded Make-Ten, Science process,
  English and Arabic sentence-ordering, and FE-02 integration are accepted;
  final Studio acceptance remains BLOCKED / NOT PROMOTED until separately
  authorized and performed — Criticality 4**
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

### STUDIO-ACT-EN-01 — English Sentence Ordering

**Status:** DONE / ACCEPTED

**Acceptance:** exact-version `ENGLISH / subject-profile-v2` preserves
historical English profile versions and adds the bounded
`sentence_ordering_workspace`. The project-authored fixture is
`english_sentence_ordering_fixture_slate`
(`english-sentence-ordering-fixture-slate-v1`): `tok-c820 = Birds`,
`tok-43bd = fly`, `tok-7f2c = over`, and `tok-a91e = clouds`. The canonical
answer remains server-only (`tok-c820 → tok-43bd → tok-7f2c → tok-a91e`), while
the browser receives a noncanonical catalogue and deterministic noncanonical
current order. Token identity is opaque and independent of visible text and
canonical position; duplicate labels remain distinct semantic objects.

`REORDER_TOKEN` is `RECORD_ONLY`; `SUBMIT_CONFIGURATION` alone is
`TUTOR_TRIGGERING`. Durable Event/Snapshot state retains exact activation,
idempotency, rebuild/reload, stale and ownership rejection, and the submitted
configuration as source truth after later record-only reorders. Submit creates
one Runtime-03 Tutor execution and one real Tutor LearningMessage, without a
fake Student message, direct Candidate/Evidence/Personal Facts/Learning
Intelligence write, or extra Canvas/Specialist model call. The isolated review
mount is not FE-02 `/student/daily`.

**Language boundary:** academic English tokens remain LTR inside Arabic RTL or
mixed-direction surrounding UI. Visible keyboard focus and mouse,
Chromium-emulated touch, and keyboard/button paths emit equivalent bounded
semantic reorder intent. Canvas has no contenteditable, sentence-composition,
explanation, reasoning, or other unrestricted Student language channel;
Student-authored free-form language remains Chat or Voice-to-STT-to-Chat.

**Evidence:** 6 focused English PostgreSQL/activation/rebuild/Runtime-03 tests
passed; 4 renderer/model tests passed; the isolated Chromium matrix passed
16/16 cases; the full isolated Python suite passed 906 with 7 skipped; web
typecheck and production build passed; Alembic found no new upgrade operations;
and tracked/relevant-untracked whitespace checks passed. The final independent
source/evidence review reported 0 Critical / 0 Important / 0 Minor and did not
independently re-execute tests. The seven skips remain the documented opt-in
cloud-writing S3 and real-Luna checks, not passes.

**Boundary:** generated browser screenshots, traces, and `results.json` remain
local evidence; its historical descriptive label was intentionally not rewritten.
No Arabic or FE-02 promotion occurred.

---

### STUDIO-ACT-SCI-01 — Process Sequence Workspace

**Status:** DONE / ACCEPTED

**Acceptance:** exact-version `SCIENCE / subject-profile-v2` adds the bounded
`sand_water_filtration` fixture (`sand-water-filtration-fixture-v1`) while
preserving empty `SCIENCE / subject-profile-v1` for replay. Its one
server-owned accepted order models only the narrow sand-and-water filtration
sequence; it does not claim filtration alone makes arbitrary water safe or
potable, and it makes no Grade 5 Science coverage claim. Reorder is
`RECORD_ONLY`; submit persists the exact configuration and creates one
Runtime-03 Tutor continuation without a fake Student message, direct
Candidate/Evidence/Personal Facts/Learning Intelligence write, or an
additional Canvas model call.

**Boundary:** the reviewed route is a mock-labelled isolated renderer, not
FE-02 `/student/daily`; no later Studio task is promoted.

---

### STUDIO-ACT-MATH-01 — Make-Ten Group Transfer

**Status:** DONE / ACCEPTED

**Acceptance:** exact-version `ten_frame_group_transfer` implements the
bounded `9 + 6 → 10 + 5` flow with exact Scene-identity activation, durable
typed operations and Snapshot rebuild, truthful validation, and a minimal
React/SVG renderer. `TRANSFER_ITEM` is `RECORD_ONLY`; only the declared submit
uses one accepted Runtime-03 Tutor continuation, with no fake Student message,
direct Candidate/Evidence/Personal Facts/Learning Intelligence write, Canvas
Specialist, or additional Canvas model call.

**Boundary:** the mock-labelled isolated review mount is not FE-02
`/student/daily`; no other activity, Grade 5 coverage claim, deployment,
live-model validation, or real-Lina use is accepted. Make-Ten remains outside
the Grade 5 denominator. Detailed verification and independent-review evidence
are retained in `project-state/DAILY_USE_RELEASE_TASKS.md`.

---

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

Do not infer a next implementation task from this child acceptance. The
umbrella's remaining families/modes, `STUDIO-ACCEPT-01`, Replit, deployment,
real-Lina, and all other later Studio work remain unpromoted. Any next action
requires separate Product Owner promotion.

---

## Critical references

- `AGENTS.md`
- `docs/PERSONAL_FACTS_SPEC.md`
- `docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md`
- `docs/STUDIO_IMPLEMENTATION_PLAN.md`
- `research/curr-render-math-01/10_CORRECTION_RECORD.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `TASKS.md`
