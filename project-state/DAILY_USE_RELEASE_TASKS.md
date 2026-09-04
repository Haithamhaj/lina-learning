# Daily-Use Lina Release 1 — Execution Tasks

**Status:** Product Owner approved on 2026-08-31  
**Authority:** Current bounded execution overlay for Daily-Use Lina Release 1.  
**Relationship to `TASKS.md`:** `TASKS.md` remains the preserved historical ledger.  
**Execution rule:** Only one task is `READY` at a time. After each task: verify, review, update `PROJECT_STATE.md`, then promote the next task explicitly.

---

# Learning Studio — Approved Execution Track

**Authority:** `docs/STUDIO_IMPLEMENTATION_PLAN.md` is the approved detailed
direction. This track controls Studio readiness and supersedes only earlier
FE-02/display-only Canvas execution assumptions. It does not rewrite the
preserved Daily-Use history below.

```text
STUDIO-GOV-01 — DONE / ACCEPTED
→ FE-02-PRESERVE-01 — DONE / ACCEPTED
→ STUDIO-STATE-01 — DONE / ACCEPTED
→ STUDIO-SUBJECT-01 — DONE / ACCEPTED
→ STUDIO-PROTOCOL-01 — DONE / ACCEPTED
→ STUDIO-RUNTIME-01 — DONE / ACCEPTED
→ STUDIO-RUNTIME-02 — DONE / ACCEPTED
→ STUDIO-RUNTIME-03 — ONLY READY TASK
→ STUDIO-ACT-MATH-01 — BLOCKED
→ STUDIO-ACT-SCI-01 — BLOCKED
→ STUDIO-ACT-EN-01 — BLOCKED
→ STUDIO-ACT-AR-01 — BLOCKED
→ FE-02-STUDIO-01 — BLOCKED
→ CURR-RENDER-MATH-01A — BLOCKED UNTIL THE GRADE 5 MATH RENDERER IMPLEMENTATION GATE
→ independently reviewed Grade 5 renderer tasks — BLOCKED
→ STUDIO-ACCEPT-01 — BLOCKED
→ optional STUDIO-SPECIALIST-01 / STUDIO-REUSE-01 — BLOCKED
→ production deployment gate — BLOCKED
```

## STUDIO-GOV-01 — Verify and Promote Approved Studio Direction

**Status:** DONE / ACCEPTED
**Scope:** governance documentation only; no runtime, schema, API, renderer,
dependency, or frontend behavior change.

## FE-02-PRESERVE-01 — Preserve Prototype Shell

**Status:** DONE / ACCEPTED
**Purpose:** create a recoverable isolated prototype artifact without accepting
the FE-02 browser implementation as production Studio architecture.

**Accepted output:** branch `prototype/fe-02-studio-shell-2026-09-02`, commit
`8648371480b0aac116af2a49e2d3d7493d26360f`, parent
`059ff3aa6bfb983507470f484596bf05eae3b9b3`, and manifest
`prototype/FE-02_PROTOTYPE_MANIFEST.md`.

**Accepted verification:** seven focused Node tests, TypeScript typecheck,
production build, and SHA-256 identity passed. The prototype remains
non-production.

## STUDIO-STATE-01 — Durable Studio State

**Status:** DONE / ACCEPTED
**Dependencies:** accepted `STUDIO-GOV-01` and `FE-02-PRESERVE-01` only.

**Accepted result:** durable Runtime, Scene, semantic Event Log, Materialized
Snapshot, and persistence seams are at Alembic head `b6e4c2a9d7f1`; focused
Studio PostgreSQL verification and the accepted full isolated suite passed.

`STUDIO-SUBJECT-01` is `DONE / ACCEPTED` at Alembic head `c7d8e9f0a1b2`.
It provides the code-owned Subject Capability Registry, exact capability
versions, persisted Scene profile/action identity, bounded validation results,
and Student-only Activity-owned Tutor triggering. Production profiles have no
Student-facing Activities. `STUDIO-PROTOCOL-01` is `DONE / ACCEPTED`: its
authenticated open/snapshot/operation/feed boundary, resumable Event Log
recovery, PostgreSQL wake-up seam, and web protocol/controller are implemented.
`STUDIO-RUNTIME-01` is `DONE / ACCEPTED`: the existing Tutor call receives the
current Studio Snapshot and exact unseen Event range, and successful completed
Tutor consumption advances the durable Studio watermark. `STUDIO-RUNTIME-02`
is `DONE / ACCEPTED`: its strict WorkspaceIntent and deterministic,
non-mutating Workspace Router are implemented. `STUDIO-RUNTIME-03` is the only
ready Studio task; all later Studio tasks remain blocked.
`CURR-RENDER-MATH-01A` is **BLOCKED UNTIL THE GRADE 5 MATH RENDERER
IMPLEMENTATION GATE**: it does not block Studio state, protocol, runtime,
cross-subject foundation activities, or FE-02 Studio integration.

---

# Approved Sequence

```text
RL-01A Accepted Runtime Alignment — DONE / ACCEPTED
→ RL-01B Fresh Shared DB + Runtime Composition — DONE / ACCEPTED
→ RL-01C Clerk + OpenAI Operational Verification — DONE / ACCEPTED
→ RL-01D Controlled Full Intelligence Loop — DONE / ACCEPTED
→ TASK-027A Student Core Profile — DONE / ACCEPTED
→ PF-01 Personal Facts Contract — DONE / ACCEPTED
→ PF-02 Personal Facts Extraction/Reconciliation — DONE / ACCEPTED
→ PF-02A Existing-Fact-Aware Personal Facts Extraction — DONE / ACCEPTED
→ PF-03 Relevant Facts in Tutor Context — ACCEPTED / COMPLETED
→ FE-01 Visual System + Library Capability + Reuse Decision Record — ACCEPTED / COMPLETED
→ FE-02 Daily Student Experience — BLOCKED
→ TASK-032 Voice / STT — BLOCKED
→ TASK-033 Vision / Student Work — BLOCKED
→ TASK-034 Original-Image Annotation — BLOCKED
→ DEPLOY-01 Private Daily Environment — BLOCKED
→ LINA-R1 Clean Real-Use Baseline — BLOCKED
```

Post-launch work is not a Release-1 blocker: measured RAG evaluation, selected renderer/artifact expansion, Science production, Grade transition, advanced Parent Insights, clustering/ML, and optional illustrative image generation.

---

## RL-01A — Accepted Runtime Alignment
**Status:** DONE / ACCEPTED

## RL-01B — Fresh Shared Application DB & Runtime Composition
**Status:** DONE / ACCEPTED  
**Accepted commit:** `dc76195bcb9ba7577b5f6dbbf0804f5bff6c43ff`

**Accepted result:** fresh shared PostgreSQL/pgvector DB, aligned Web/API/Worker runtime, standard Worker command, Worker recovery smoke, and Student-scoped shared-DB isolation.

## RL-01C — Clerk + OpenAI Operational Verification
**Status:** DONE / ACCEPTED

**Accepted result:** real Clerk Student/Parent auth and signed backend roles, explicit Parent→Student authorization, real OpenAI Tutor/Segment Review/embedding routes through Model Gateway, AI execution lineage, and real-auth cross-Student isolation.

## RL-01D — Controlled Full Intelligence Loop
**Status:** DONE / ACCEPTED

**Accepted result:** real multi-turn Tutor interaction with one primary call per normal turn; natural Session/Segment lifecycle; real Segment Learning Review; deterministic Session Finalization with zero semantic Session LLM calls; source-linked Event/Evidence/State/Pattern/Decision materialization; relevant later intelligence selection without full historical transcript; irrelevant fraction intelligence excluded from an unrelated Math question; healthy recovery from a transient review-provider failure; cross-Student scoping preserved.

**Accepted streaming fix:** `3af613484266e2c21d9e91a20d09ef217b05c16e`.

---

# User Knowledge Foundation

## TASK-027A — Student Core Profile & Tutor Student Context

**Status:** DONE / ACCEPTED  
**Dependencies:** RL-01D accepted  
**Accepted commit:** `57a763bbd538157c6503c10f64d0010a91dc2c46`  
**Alembic head:** `f9b1c2d3e4f5`

**Accepted result:**
- existing Student identity reused; nullable `date_of_birth` added;
- age derived deterministically and never stored independently;
- GradePeriod reused with Student-scoped deterministic effective-period resolution;
- future Grade scheduling preserves the current effective Grade through the day before transition and rejects conflicting overlaps;
- linked Parent/System Core Profile GET/PUT boundary established;
- Tutor receives only compact `display_name`, `age_years`, and effective `grade_level`;
- raw DOB/IDs/Parent metadata excluded from model-facing Core Context;
- Personal Facts and Learner Intelligence remain separate;
- existing Retrieval caller uses resolved effective grade without RAG redesign;
- one primary Tutor model call remains unchanged;
- cross-Student Core Profile isolation verified.

---

## PF-01 — Personal Facts Contract

**Status:** DONE / ACCEPTED
**Dependencies:** TASK-027A accepted

**Accepted contract:** `docs/PERSONAL_FACTS_SPEC.md`.

### Approved source authority

- Personal Facts are **Student-asserted**.
- They come from explicit Student statements about herself/her ordinary world.
- Parent claims do not automatically become Student Personal Facts.
- Repeated topic discussion without an explicit assertion does not become an inferred preference, interest, personality trait, or talent.

### Approved simple model

Release 1 uses:

```text
Personal Fact
+
Personal Fact Observations
```

A Fact is identified by:
- `student_id`;
- controlled category;
- stable `fact_key` representing the topic/semantic slot;
- normalized value representing the explicit assertion.

Example:

```text
fact_key = preference:drawing
value = LIKE
```

A different explicit value for the same key is a separate Fact, not an overwrite:

```text
preference:drawing = LIKE
preference:drawing = DISLIKE
```

The current value for a `fact_key` is determined at read time from the most recently observed explicit Fact. Older Facts remain historical context.

### Observation / count contract

Every explicit support for an exact Fact creates a source-linked Observation.

The Fact exposes or can cheaply derive:
- `support_count`;
- `first_observed_at`;
- `last_observed_at`.

Repeated explicit support strengthens the historical relationship by increasing count and refreshing recency. Do **not** store arbitrary confidence percentages.

Observation rows/source lineage remain the trustworthy basis for count/history; a cached count is allowed only if it remains rebuildable from observations.

### Qualification boundary

Good Release-1 Personal Facts include ordinary durable personal context such as:
- explicit preferences/favorites/interests;
- recurring activities;
- pets;
- ordinary non-sensitive relationships;
- other safe durable personal context that can make later conversation naturally personalized.

Not Personal Facts:
- one-off future plans or calendar events;
- temporary daily states;
- inferred interests from repetition alone;
- transcript summaries;
- Core Profile competitors such as authoritative age/Grade;
- Learning Intelligence/Evidence or academic judgments;
- personality/psychology/diagnosis/intelligence/learning-style/talent conclusions;
- unsafe sensitive personal information.

Examples:
- “I like drawing.” → Personal Fact.
- “I play basketball every Thursday.” → Personal Fact.
- “I’m going to Jeddah next weekend.” → Conversation Context only.
- “I’m tired today.” → Conversation Context only.
- repeated football discussion without “I like football.” → no Personal Fact.
- “I’m bad at math.” → not Personal Fact; current conversation may respond naturally, while learning conclusions require the Learning Intelligence evidence path.
- “I’m shy.” → conversation-only; no personality memory.

`TEMPORAL_EVENT` is not part of the Release-1 Personal Facts taxonomy.

### Safety/privacy boundary

Do not persist sensitive child information into Personal Facts merely because it appears in conversation, including credentials, precise address/live location, contact details, financial/account information, highly sensitive medical/private information, sexual/private information, or safety-risk secrets. Existing raw-history and Safety policies remain separate authorities.

### Authority separation

```text
Student Core Profile = Parent/System-authoritative application facts
Personal Facts       = Student-asserted factual personal context
Learner Intelligence = learning-derived evidence-backed state
Conversation Context = current/raw conversational continuity
Safety               = safety authority
RAG                  = curriculum/reference grounding
```

Personal Facts never become Learning Evidence merely because they exist.

### Parent inspection

- Parent may inspect stored Personal Facts for the linked Student.
- Parent may see the Fact plus count/first/last-observed support/history where useful.
- Inspection does not make Parent a Personal-Fact source.
- No separate hidden child-facts database is required.

### Isolation/rebuildability

- every Fact and Observation is Student-scoped;
- every Observation traces to a Student-authored source message/interaction;
- Student A Facts can never be selected/reconciled/displayed for Student B;
- Fact counts/current state remain reconstructable from source-linked observations/history.

### PF-03 direction — SUPERSEDED / REQUIRES NEW PF-03 DESIGN

Personal Facts are optional Tutor assistance, not a teaching dependency.

Do **not** add a vector-memory platform and do **not** mix Personal Facts into curriculum RAG.

The previous deterministic lexical/key-matching direction is superseded and is **not** an approved semantic-relevance implementation decision. PF-03 requires a new bounded design decision before implementation. Retain the protected constraints: Student scoping, latest-explicit current-state semantics, bounded optional context, no extra normal-turn model call, and no vector-memory platform by default.

### PF-02 handoff direction

Keep reconciliation simple:
- new `(student_id, fact_key, value)` → `ADD` Fact + first Observation;
- same exact Fact asserted again → `SUPPORT` existing Fact with another Observation;
- same `fact_key` with a different explicit value → `ADD` a new historical Fact for that key; latest explicit Fact becomes current at read time;
- ineligible/sensitive/inferred/authority-conflicting statement → `NOOP`.

Do not require a complex supersession/invalidation state machine for Release 1.

### Verification

PF-01 is complete only when the contract unambiguously defines:
- explicit durable vs conversation-only vs prohibited memory;
- `fact_key` + normalized value identity;
- observation/source lineage;
- support count + first/last observed history;
- latest-explicit-current behavior for conflicting values;
- child-sensitive storage exclusions;
- Parent inspection;
- cross-Student isolation;
- cheap optional retrieval direction that remains separate from RAG and Learning Intelligence.

### Explicit exclusions

PF-01 does **not** implement:
- LLM/model extraction;
- Worker jobs;
- Fact/Observation database models or migration;
- Tutor Personal Facts selection/injection;
- vector Personal Facts retrieval;
- Parent Insights;
- frontend memory UI;
- graph/Graphiti or generic memory frameworks;
- PF-02 or PF-03.

**Completion:** Product Owner accepted the concise Release-1 Fact + Observation History contract, including latest-explicit-current read semantics, child privacy exclusions, a derived Personal Memory Document, and the separate PF-02 Session-level extraction boundary.

---

## PF-02 — Personal Facts Extraction & Reconciliation

**Status:** DONE / ACCEPTED
**Dependencies:** PF-01 accepted  
**Purpose:** One dedicated asynchronous Personal Facts Model Gateway call per completed Learning Session, separate from Tutor teaching and Segment Learning Review. Candidates must cite Student-authored source messages; deterministic reconciliation performs only `ADD` / `SUPPORT` / `NOOP`, with no second reconciliation model call. Refresh the derived Personal Memory Document deterministically after reconciliation. This path does not write Learning Events, Evidence, Current State, or Patterns.

**Accepted result:** additive migration `a1d2e3f4b5c6`; dedicated `PERSONAL_FACTS_EXTRACTION` job/handler through the existing Worker and `ModelTask.PERSONAL_FACTS`; strict Student-source/safety validation; canonical fact-key/value validation; deterministic `ADD` / `SUPPORT` / `NOOP`; Fact plus Observation persistence; retry-safe extraction runs; capacity-skip semantics; and an on-demand latest-fact document projection. There is no Tutor, Segment Review, or RAG coupling. Fresh-migration full Python verification: `770 passed, 7 skipped`. The Daily-Use DB remains at this head with its pre-existing Student/Session/Message rows preserved. No PF-03 behavior is included.

---

## PF-02A — Existing-Fact-Aware Personal Facts Extraction

**Status:** DONE / ACCEPTED
**Dependencies:** PF-02 accepted
**Purpose:** Extend the existing single completed-Session Personal Facts model request with a compact, Student-scoped catalog of all known Fact identities, including historical contrary values. The same call chooses `SUPPORT_EXISTING` for a supplied Fact ID or `ADD_NEW` for a genuinely new canonical identity; server validation and deterministic Observation reconciliation remain authoritative. No new model call, schema, Worker architecture, Tutor, Segment Review, Learning Intelligence, or RAG behavior is added.

**Accepted result:** the existing PF model call receives all target-Student Fact identities, including historical contrary values, and semantically chooses `SUPPORT_EXISTING` versus `ADD_NEW`. The server deterministically validates grounding, ownership, safety, canonical structure, and idempotent persistence. Known Facts are untrusted reference data only; there is no extra model call, embedding/vector matching, schema/migration change, or cross-Student leakage.

---

## PF-03 — Relevant Personal Facts in Tutor Context

**Status:** ACCEPTED / COMPLETED
**Dependencies:** PF-02A accepted
**Purpose:** Read-only injection of the full compact current Personal Memory Card as a separate optional Tutor context block beside Conversation Context, Student Core Context, Learner Intelligence, optional curriculum RAG, and Safety. The Tutor decides semantic usefulness inside the existing primary call; there is no pre-Tutor lexical/key matching, retrieval, PF model call, embedding call, or vector-memory platform.

**Acceptance:** Product Owner accepted commit `6436b358ff42425fd729af316cb9525e6511f534`; PF-03 `7 passed`, protected regression `182 passed`, and diff/show checks passed. Pushed to `origin/codex/ctx-03`. No FE-01 work was performed.

---

# Lina Frontend — Daily-Use Launch UX

## FE-01 — Visual System + Library Capability + Reuse Decision Record
**Status:** ACCEPTED / COMPLETED — DOCUMENTATION ONLY
**Dependencies:** PF-03 accepted

**Scope:** Code-grounded documentation only. Define Learning Chat + Adaptive
Learning Workspace, classify reusable UI/library candidates, map FE-02's
present and future-ready Workspace capabilities, and preserve current Student
session/SSE contracts. No UI code, dependency, API, Tutor, Personal Facts,
migration, Voice, Vision, attachment, generated-image, video, 3D, artifact,
or deployment implementation is in scope.

**Decision record:** `docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md`.

**Acceptance:** Product Owner accepted documentation commit
`8601ed5f485ff29fdb467db7abfb8f7ad44711b0`. Scope: Visual System + Library
Capability + Learning Chat + Adaptive Learning Workspace for learners roughly
10–18, with Lina as the first private daily-use Student. This task changed no
UI code, dependencies, tests, runtime behavior, or PF-03 behavior. Its
`FE-02 remains BLOCKED / NOT STARTED` statement is historical; current Studio
readiness is governed by the Studio track at the top of this file.

## FE-02 — Daily Student Experience
**Status:** BLOCKED  
**Dependencies:** FE-01 accepted

**2026-09-02 Product Owner scope clarification:** The existing /student page and StudentMathSession are protected experimental/legacy functional shell and behavioral regression-harness assets. FE-02 is no longer an evolution of that UI. The Daily Student App must be a separate greenfield surface at /student/daily, reusing accepted backend/session/SSE/Tutor/Safety/PF-03 contracts rather than the existing UI implementation. Do not import, wrap, extract from, restyle, modify, or route through the legacy Student components.

**Completed fit check:** assistant-ui presentation primitives are REJECTED for
FE-02. Its runtime-bound behavior or required adapter/state bridge is not safe
as presentation-only use for this slice; it cannot own runtime, backend,
transport, session, safety, or stream lifecycle. The local path remains a new
React/Tailwind/shadcn surface with a project-owned SSE controller.

**Completed FE-CHAT-UI-01:** Existing local React/Tailwind/shadcn primitives
are ADOPT PATTERN; official shadcn chat patterns are PARTIAL ADOPT PATTERN; AI
Elements, VLLNT, and shadcn.io are UX REFERENCE ONLY; 21st.dev Agent Elements
is REJECT. FE-02 needs no chat-library installation and retains project-owned
SSE/controller/message/composer/action/guided-check/direction/error/rollback/
lifecycle behavior.

**Next pre-code gates:** Product Owner approval of the first-screen visual
brief and explicit FE-02 implementation authorization.

**Deferred by this task:** Three.js/React Three Fiber, attachments, image/PDF handling, generated images, video, Artifact Engine, MathLive, JSXGraph, Konva, and all backend/API/SSE schema changes remain out of scope unless separately approved.

---

# Multimodal Launch Capabilities

## TASK-032 — Voice Input / STT
**Status:** BLOCKED  
**Dependencies:** FE-02 accepted; RL-01C Model Gateway operational

## TASK-033 — Student Image / Handwriting / Drawing Understanding
**Status:** BLOCKED  
**Dependencies:** TASK-032 accepted; durable/private storage; RL-01C Model Gateway operational

## TASK-034 — Annotate Original Image First
**Status:** BLOCKED  
**Dependencies:** TASK-033 accepted

---

# Private Daily-Use Deployment

## DEPLOY-01 — Lina Private Daily Environment
**Status:** BLOCKED  
**Dependencies:** TASK-034 accepted

## LINA-R1 — Clean Real-Use Baseline
**Status:** BLOCKED  
**Dependencies:** DEPLOY-01 accepted

---

# Post-Launch — Not Release 1 Blockers

## RAG-EVAL-01 — Measured Retrieval Evaluation
**Status:** BLOCKED

## TASK-035 — Interactive Learning Artifacts
**Status:** BLOCKED

## PARENT-INSIGHT-01 — Facts × Learning Exploration
**Status:** BLOCKED / FUTURE / DATA-DEPENDENT

---

# Still Deferred / Independent

Not promoted by this launch plan unless separately approved: `MATH-01`, `ID-01` unless reproduced, `EDU-ERR-01`, `REC-25`, `LR-D04B`, Science production, retention/proactive learning, Grade transition production, advanced gamification, graph/Graphiti, Redis/Celery, advanced ML before real data, and broad Parent Dashboard expansion beyond specifically promoted needs.
