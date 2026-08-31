# TASKS.md — Lina Personal Learning System

## How to Use This File

- Codex should execute only tasks marked `READY`.
- Normally complete one task at a time.
- A task becomes `DONE` only after its verification passes.
- Future-phase tasks may remain `BLOCKED` until dependencies and decision gates are satisfied.
- If implementation reality invalidates a task, update this file and `project-state/PROJECT_STATE.md`; do not silently improvise a new roadmap.

### Status Values

`READY` · `IN_PROGRESS` · `REVIEW` · `BLOCKED` · `DONE`

---

# Historical Task Ledger

The detailed historical task ledger up to the Product Owner-approved Daily-Use Lina Release transition remains preserved in Git history at commit `af7264cd05e1bb9f6e794005802758521c57d509` and earlier accepted commits.

This file is now the current execution ledger for the approved **Daily-Use Lina Release 1** sequence. Historical accepted architecture and completion evidence remain authoritative through the governing documents and Git history; this current ledger must not be used to reopen completed historical work.

The Product Owner explicitly approved this execution-plan transition on 2026-08-31 after `RL-01` Current Reality Audit.

---

# Daily-Use Lina Release 1 — Current Execution Sequence

## Release rule

Only one task is `READY` at a time unless the current task explicitly authorizes a tightly bounded group. Completion of one task does not automatically start the next: verify, update `PROJECT_STATE.md`, return for review/promotion, then continue.

The approved order is:

```text
RL-01A Accepted Runtime Alignment
→ RL-01B Fresh DB + Runtime Composition
→ RL-01C Clerk + OpenAI Operational Verification
→ RL-01D Controlled Full Intelligence Loop
→ TASK-027A Student Core Profile
→ PF-01 Personal Facts Contract
→ PF-02 Personal Facts Extraction/Reconciliation
→ PF-03 Relevant Facts in Tutor Context
→ FE-01 Lina Visual System & Reuse Decision
→ FE-02 Daily Student Experience
→ TASK-032 Voice / STT
→ TASK-033 Vision / Student Work
→ TASK-034 Original-Image Annotation
→ DEPLOY-01 Private Daily Environment
→ LINA-R1 Clean Real-Use Baseline
```

Post-launch work remains blocked: measured RAG evaluation, selected learning artifacts, Science production, Grade transition expansion, advanced Parent Insights, clustering/ML, and optional image generation.

---

## RL-01A — Accepted Runtime Alignment

**Status:** READY  
**Dependencies:** Product Owner-approved RL-01 Current Reality Audit; `DOC-SYNC-01` accepted  
**Purpose:** Align the isolated implementation worktree and runtime reference to the accepted `codex/ctx-03` revision before any database/runtime/feature activation.

**Expected output:**

- resolve/fetch the accepted remote `codex/ctx-03` HEAD;
- safely align `/Users/haitham/development/lina-learning-ctx03` to that revision;
- preserve protected dirty files in the original checkout and make no implementation changes there;
- verify tracked worktree state and remote relationship;
- identify stale runtime/process/config references still pointing at the older original checkout/runtime;
- confirm whether the acceptance commits after the previously audited local revision are documentation/governance-only or expose any unexpected runtime change;
- run appropriate baseline automated verification on the aligned revision;
- report exact resulting HEAD and blockers to RL-01B.

**Likely areas:** Git/worktree only; read-only runtime/config discovery where required.

**Verification:**

- isolated worktree is on the accepted branch/HEAD or a clearly documented newer accepted fast-forward;
- original protected checkout remains untouched;
- no secrets printed/copied/committed;
- no feature/runtime/schema change introduced;
- baseline verification result recorded;
- exact stale/current runtime references classified.

**Explicit exclusions:** fresh DB creation, migrations against the historical DB, Worker activation against real data, Clerk changes, OpenAI configuration changes, Personal Facts, Frontend work, Voice, Vision, deployment, RAG changes, Artifacts, MATH-01, ID-01.

**Stop condition:** Stop after report/verification. Do not start RL-01B.

---

## RL-01B — Fresh Real-Use Database & Runtime Composition

**Status:** BLOCKED  
**Dependencies:** RL-01A accepted  
**Purpose:** Establish the clean current-schema database and one aligned local runtime composition that will become the technical baseline for real Lina use.

**Expected output:**

- fresh PostgreSQL/pgvector database created from current migrations from zero;
- no import/migration of experimental historical interaction data;
- current Web + API + Worker configured to use the same current revision/configuration;
- standard local run composition includes the Worker or has an equally explicit reliable process-start contract;
- database/job/session lifecycle smoke checks.

**Verification:**

- migration head matches current repository;
- database contains no historical/test Lina interaction rows beyond required bootstrap/configuration;
- Web/API/Worker use the same DB/revision;
- Worker can start/stop safely and access the jobs table;
- restart does not invalidate durable DB state;
- no architecture redesign, Redis/Celery, new queue, or second database introduced.

**Stop condition:** Do not configure/verify real Clerk/OpenAI interaction or run the full intelligence proof until RL-01B review.

---

## RL-01C — Clerk + OpenAI Operational Verification

**Status:** BLOCKED  
**Dependencies:** RL-01B accepted  
**Purpose:** Make the aligned runtime usable by real Parent/Student identities and existing real Model Gateway routes without creating parallel auth/provider integrations.

**Expected output:**

- real Clerk configuration verified for Parent/Admin and Lina Student use;
- Parent ↔ Student ownership/authorization proven through existing boundaries;
- browser origin/JWT/JWKS flow verified;
- OpenAI project/API configuration available server-side through existing Model Gateway;
- real routes verified for Tutor, Segment Review, and embeddings;
- usage/execution lineage remains recorded without secret exposure.

**Verification:**

- real browser login/logout for Student and Parent as applicable;
- Student cannot cross Parent/other-Student boundaries;
- one controlled real Tutor execution succeeds;
- Segment Review and embedding routes are operationally available through Model Gateway;
- no provider API key reaches browser or Git;
- no direct arbitrary OpenAI SDK calls are added outside provider adapters.

**Stop condition:** Do not run the full lifecycle/finalization proof until review.

---

## RL-01D — Controlled Full Intelligence Loop

**Status:** BLOCKED  
**Dependencies:** RL-01C accepted  
**Purpose:** Prove the accepted architecture on the clean current environment before Lina's real baseline begins.

**Expected flow:**

```text
controlled Student Session
→ real Tutor
→ Segment persistence
→ inactivity / Session closure
→ Worker
→ Segment Learning Review
→ deterministic Session Finalization
→ Event / Evidence
→ Current State / Patterns / Decision Views
→ Learner Intelligence Card
→ later Session
→ relevant Card entry reaches Tutor context
```

**Verification:**

- no manual DB mutation is needed to advance the flow;
- no stuck unrecoverable jobs;
- all required Reviews/finalization lineage is source-linked;
- relevant intelligence is selected in a later Session without full transcript injection;
- unrelated later question does not receive stale intelligence;
- one primary Tutor call remains protected;
- Session Finalization remains deterministic;
- controlled proof data is clearly distinguishable from the later real Lina baseline.

**Completion effect:** RL-01 becomes eligible for Product Owner technical closure. Do not start Student Core/Profile/Facts work in the same execution.

---

# User Knowledge Foundation

## TASK-027A — Student Core Profile & Tutor Student Context

**Status:** BLOCKED  
**Dependencies:** RL-01D accepted  
**Purpose:** Provide Parent/System-authoritative core application facts separately from Personal Facts and Learning Intelligence.

**Expected output:**

- authorized Parent-managed child display identity;
- date of birth when supplied and runtime-derived age;
- active Grade / GradePeriod linkage;
- compact Student Core Context consumed by Tutor;
- removal of hardcoded approximately-10-year-old identity assumption where applicable.

**Boundaries:** no Personal Fact extraction; no Learner Intelligence/Evidence editing; no personality/learning-style claims; Parent Core Profile facts do not become learning conclusions.

**Verification:** ownership isolation, correct derived age/Grade, no cross-child leakage, no mutation of Evidence/Learner Intelligence.

---

## PF-01 — Personal Facts Contract

**Status:** BLOCKED  
**Dependencies:** TASK-027A accepted  
**Purpose:** Add a separate durable Personal Facts domain representing facts the Student tells the system about herself.

**Product definition:**

> Personal Facts answer: "What durable factual things has this Student told the system about herself or her world?"

Examples may include interests, likes/dislikes, relationships/names as asserted by the Student, pets, goals, preferences, activities, fears or dislikes when explicitly asserted, and other durable self-reported facts.

**Expected output:**

- versioned Personal Fact persistence contract;
- Student/source-message lineage;
- current/invalidated/superseded lifecycle;
- first/last observation;
- repeated-support and contradiction metadata where justified;
- categories/types only as needed for retrieval/UI, without psychological ontology;
- migration/tests.

**Protected boundaries:**

- Student assertions are the source for Personal Facts; Parent claims do not automatically become the Student's Personal Facts;
- no requirement for external objective verification;
- no personality/psychological/intelligence/learning-style inference;
- no transcript-summary memory;
- no Learning Evidence/Current State/Pattern mutation;
- no second Learner Intelligence system;
- Parent may inspect the stored Personal Facts;
- future Parent insights cannot write back derived conclusions as facts.

**Verification:** facts remain auditable to source messages; invalid/superseded facts leave current retrieval; Learning Intelligence remains unchanged.

---

## PF-02 — Personal Facts Extraction & Reconciliation

**Status:** BLOCKED  
**Dependencies:** PF-01 accepted; existing Worker + Model Gateway  
**Purpose:** Extract durable Personal Facts from Student interaction asynchronously and reconcile them against current facts.

**Approved conceptual flow:**

```text
Student interaction / completed processing unit
→ fact extraction
→ retrieve/compare relevant current facts
→ ADD / UPDATE / SUPERSEDE / NOOP
→ persist source-linked fact generation
```

**Expected output:** background extraction/reconciliation path behind Model Gateway; idempotent/retry-safe job handling; no additional normal Tutor-turn model call.

**Verification scenarios:** new fact, repeated same fact, explicit change of preference, contradiction, no durable fact, malformed model output, job retry/idempotency.

**Boundary:** fact extraction does not determine learning ability, teaching effectiveness, personality, or psychological state.

---

## PF-03 — Relevant Personal Facts in Tutor Context

**Status:** BLOCKED  
**Dependencies:** PF-02 accepted  
**Purpose:** Make Personal Facts useful in future conversation without dumping the complete fact store into every Tutor request.

**Expected flow:**

```text
Current Student turn
+ Current Segment conversation context
+ compact Student Core Context
+ relevant Personal Facts
+ relevant Learner Intelligence
+ optional question-driven RAG
+ effective Safety decision
→ ONE primary Tutor call
```

**Expected output:** relevance-bounded Personal Fact selection with source/debug identifiers; clear Tutor-context section separate from Learner Intelligence.

**Verification:** relevant fact can naturally inform a response; irrelevant facts are excluded; stale/superseded facts do not enter current context; facts never appear as Learning Evidence; one-primary-call invariant preserved.

---

# Lina Frontend — Daily-Use Launch UX

## FE-01 — Lina Visual System & Reuse Decision

**Status:** BLOCKED  
**Dependencies:** PF-03 accepted  
**Purpose:** Establish one coherent age-appropriate visual/component direction before broader Student UI implementation.

**Required reuse evaluation:** inspect applicable candidates from `docs/TECHNOLOGY_REUSE_CATALOG.md`, including shadcn/ui baseline, existing assistant-ui decision, Motion/Motion Primitives, ThreeUI/Three.js, Magic UI, React Bits, 21st.dev, Aceternity UI, and Cult UI where relevant.

Classify each relevant candidate as:

`ADOPT / PARTIAL ADOPT / VISUAL REFERENCE / REJECT`

**Target:** playful + intelligent + polished + personal; appropriate for roughly age 10; not preschool and not a corporate chatbot.

**Expected output:** visual system/reuse decision, key UI primitives, typography/spacing/motion/3D performance boundaries, Lina avatar/photo readiness, accessibility/readability constraints.

**Boundary:** do not stack libraries for novelty; ThreeUI/Three.js is selective visual capability, not application architecture.

---

## FE-02 — Daily Student Experience

**Status:** BLOCKED  
**Dependencies:** FE-01 accepted  
**Purpose:** Turn the proving Student surface into the Daily-Use Lina launch experience before multimodal controls become active.

**Expected output:**

- Lina home/entry experience;
- polished Tutor thread/composer;
- clear empty/thinking/error/retry states;
- suggested actions/guided checks integrated cleanly;
- microphone/photo/attachment affordance locations ready for their promoted tasks;
- bilingual RTL/LTR behavior;
- responsive desktop/tablet/mobile-browser layouts;
- purposeful motion and visual warmth.

**Verification:** child usability/browser review, responsive screenshots, no internal analytics/debug exposure, SSE/persistence behavior unchanged, performance acceptable with selected visual layers.

---

# Multimodal Launch Capabilities

## TASK-032 — Voice Input / STT

**Status:** BLOCKED  
**Dependencies:** FE-02 accepted; RL-01C Model Gateway configuration  
**Purpose:** Let Lina speak naturally instead of typing while preserving the normal Tutor architecture.

**Approved flow:**

```text
record short audio
→ speech_to_text Model Gateway task
→ transcript
→ normal Student/Tutor message path
```

**Expected output:** record/cancel/retry UI, Arabic/English transcription, visible transcript, normal Tutor submission, transcript/source metadata persistence.

**Policy:** raw audio is not retained after successful STT under the current version.

**Boundary:** no speech-to-speech/realtime architecture required for Release 1 unless measured interaction evidence later justifies it.

**Verification:** transcript fidelity on representative Arabic/English/mixed samples, no raw-audio persistence after success, no bypass of Safety/session/persistence boundaries.

---

## TASK-033 — Student Image / Handwriting / Drawing Understanding

**Status:** BLOCKED  
**Dependencies:** TASK-032 accepted; durable/private object storage available; RL-01C Model Gateway  
**Purpose:** Let Lina photograph/upload homework, handwritten work, drawings, diagrams, or textbook/worksheet content and continue in the same Tutor session.

**Expected output:** camera/file upload, original private asset persistence, Multimodal Turn linkage, `vision_student_work` task through Model Gateway, ambiguity/clarification behavior, derived interpretation provenance.

**Boundary:** original image remains source authority; Vision interpretation does not replace it and does not become Evidence without the governed Segment Review path.

**Verification:** representative homework/handwriting/drawing cases, ambiguous case asks clarification, ownership/privacy isolation, source-vs-derived lineage preserved.

---

## TASK-034 — Annotate Original Image First

**Status:** BLOCKED  
**Dependencies:** TASK-033 accepted  
**Purpose:** Provide educational correction/feedback directly on a derived copy of Lina's original work before reconstructing a clean visual.

**Approved default:** circles, arrows, highlights, check/cross marks, and short explanatory labels anchored to the original.

**Fallback:** when annotation is insufficient, produce a clean React/SVG/interactive reconstruction linked to the original and interpretation.

**Expected output:** annotation data/artifact contract, renderer, provenance links, UI presentation, clean-reconstruction fallback seam.

**Verification:** original object unchanged; annotations align to the intended region; derived copy clearly distinguished from source; annotations/reconstruction are never misclassified as Student Evidence.

---

# Private Daily-Use Deployment

## DEPLOY-01 — Lina Private Daily Environment

**Status:** BLOCKED  
**Dependencies:** TASK-034 accepted  
**Purpose:** Move the proven current composition into one stable private daily-use environment for Lina without changing product architecture.

**Preferred candidate:** Replit may be used after a fit check; the old Phase-0 Replit application is not the source baseline.

**Required composition:** current proven Web + API + Worker + fresh persistent PostgreSQL/pgvector + Clerk + Model Gateway/OpenAI configuration + durable/private object storage + health/restart procedures.

**Verification:** browser login, Tutor/Voice/Vision paths, persistence across restart, Worker remains operational, jobs recover, private assets remain accessible/authorized, secrets remain server-side, no architecture redesign required.

---

## LINA-R1 — Clean Real-Use Baseline

**Status:** BLOCKED  
**Dependencies:** DEPLOY-01 accepted  
**Purpose:** Begin the actual longitudinal Lina baseline from a clean database after the launch environment is proven.

**Boundary:** experimental historical database/conversation data is not imported as real-use history.

**Expected output:** natural Lina Session 1+ usage accumulating Personal Facts and Learning Intelligence under the current architecture.

**Verification / review:** confirm Lina can use the product naturally; inspect first real Session lifecycle, Personal Facts, Learning Intelligence activation, later-session personalization, Voice/Vision usability, cost/latency, and any launch-blocking defect. Do not overfit from one interaction.

---

# Post-Launch — Not Release 1 Blockers

## RAG-EVAL-01 — Measured Retrieval Evaluation

**Status:** BLOCKED  
**Dependencies:** LINA-R1 underway with representative real Grade-5 sources/questions  
**Purpose:** Evaluate whether the current native Docling + PostgreSQL/pgvector Hybrid Retrieval should remain unchanged or whether an alternative materially improves total quality/complexity.

**Compare only if practical:** current native path vs official LlamaIndex+Docling integration vs OpenAI retrieval/file-search capability.

**Measure:** correct source/page/concept retrieval, provenance, Arabic/English behavior, latency, cost, dependency/custom-code complexity, rebuildability, filtering/control.

**Rule:** no replacement without measured advantage. Keep behind existing Retrieval boundary.

---

## TASK-035 — Interactive Learning Artifacts

**Status:** BLOCKED  
**Dependencies:** LINA-R1 / explicit Product Owner promotion based on real use  
**Purpose:** Add visual/interactive teaching representations using the approved renderer-first strategy.

**Renderer baseline:** React/SVG + Motion + JSXGraph + React Konva + MathLive. Evaluate OpenMAIC package-level reuse before custom generic renderer/DSL infrastructure where applicable.

**Image generation:** optional/deferred illustrative capability only; not the default learning renderer.

**Initial scope:** only high-value artifacts supported by observed Math/Science use; do not build a large generic catalog.

---

## PARENT-INSIGHT-01 — Facts × Learning Exploration

**Status:** BLOCKED / FUTURE / DATA-DEPENDENT  
**Dependencies:** sufficient real Lina Personal Facts + Learning Intelligence history  
**Purpose:** Explore what useful Parent-facing insights can be derived from the intersection of Student-asserted facts/interests and evidence-grounded learning behavior.

**No implementation choice is approved yet.** Begin later with descriptive/temporal/cross-analysis. Use SQL/analytics/LLM/clustering/ML only if the data and a concrete question justify them.

**Prohibited:** psychological/personality diagnosis, unsupported talent labeling, derived insights writing themselves back as Personal Facts or Learning Intelligence authority.

---

# Still Deferred / Independent

The following are not promoted by this launch plan unless separately approved:

- `MATH-01` beyond bounded fixes justified by its own task;
- `ID-01` unless reproduced during real auth verification;
- `EDU-ERR-01`;
- `REC-25` historical calibration record;
- `LR-D04B` longitudinal TeachingMethod learning;
- Science production (`TASK-036` historical ID) until explicit promotion;
- retention/proactive learning;
- Grade transition production;
- advanced gamification;
- graph database / Graphiti;
- Redis/Celery;
- advanced ML/clustering before real data;
- broad Parent Dashboard expansion beyond specifically promoted launch needs.
