# Daily-Use Lina Release 1 — Execution Tasks

**Status:** Product Owner approved on 2026-08-31  
**Authority:** Current bounded execution overlay for the Daily-Use Lina Release 1 transition.  
**Relationship to `TASKS.md`:** `TASKS.md` remains the preserved historical ledger. This file governs only the Product Owner-approved Daily-Use Release 1 sequence and must not be generalized to unrelated historical/future work.  
**Execution rule:** Only one task is `READY` at a time unless the task itself explicitly authorizes a tightly bounded group. After each task: verify, update `PROJECT_STATE.md`, return for review/promotion, then continue.

---

# Approved Sequence

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

Post-launch work is not a Release-1 blocker: measured RAG evaluation, selected renderer/artifact expansion, Science production, Grade transition, advanced Parent Insights, clustering/ML, and optional illustrative image generation.

---

## RL-01A — Accepted Runtime Alignment

**Status:** DONE / ACCEPTED  
**Dependencies:** Product Owner-approved RL-01 Current Reality Audit; `DOC-SYNC-01` accepted  
**Purpose:** Align the isolated implementation worktree and runtime reference to the accepted `codex/ctx-03` revision before any database/runtime/feature activation.

**Accepted result:**
- isolated worktree `/Users/haitham/development/lina-learning-ctx03` aligned from local `d93f104b3afb21741429229e7c2fa4584e7779ac` to remote/current `db0a7b05c6a6ec3d9e6b8914200eb6b2f80e37e9`;
- branch `codex/ctx-03`, ahead/behind `0/0`, tracked state clean;
- `.acceptance-artifacts/` preserved untracked;
- original checkout and protected Eureka-related local modifications untouched;
- baseline `af7264cd05e1bb9f6e794005802758521c57d509` → current HEAD diff verified documentation/governance-only, with no runtime/schema/migration/config implementation change;
- Python disposable-PostgreSQL verification passed `715 passed, 7 skipped`;
- web build/typecheck, migration single-head `f5a1c2d3e4b6`, and `git diff --check` passed;
- live API remains stale from old original checkout; Web/Worker not running; DB/Clerk/Model configuration remains sourced from the old checkout. These are RL-01B/RL-01C concerns, not RL-01A failures.

**Verification:** ACCEPTED on 2026-08-31 from the Codex RL-01A report. No task-authored tracked implementation files changed.

---

## RL-01B — Fresh Real-Use Database & Runtime Composition

**Status:** READY  
**Dependencies:** RL-01A accepted  
**Purpose:** Establish the clean current-schema database and one aligned local runtime composition that will become the technical baseline for real Lina use.

**Expected output:**
- fresh PostgreSQL/pgvector database created from current migrations from zero;
- no import/migration of experimental historical interaction data;
- current Web + API + Worker configured to use the same current revision/configuration;
- standard local run composition includes Worker or has an equally explicit reliable process-start contract;
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
- no direct arbitrary OpenAI SDK calls added outside provider adapters.

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
- no manual DB mutation needed to advance the flow;
- no stuck unrecoverable jobs;
- Reviews/finalization lineage is source-linked;
- relevant intelligence selected later without full transcript injection;
- unrelated later question receives no stale intelligence;
- one primary Tutor call preserved;
- Session Finalization remains deterministic;
- controlled proof data distinguishable from later real Lina baseline.

**Completion effect:** RL-01 becomes eligible for Product Owner technical closure. Do not start user-knowledge work in the same execution.

---

# User Knowledge Foundation

## TASK-027A — Student Core Profile & Tutor Student Context

**Status:** BLOCKED  
**Dependencies:** RL-01D accepted  
**Purpose:** Provide Parent/System-authoritative application facts separately from Personal Facts and Learning Intelligence.

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

**Product definition:** Personal Facts answer: **“What durable factual things has this Student told the system about herself or her world?”**

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
- Parent may inspect stored Personal Facts;
- future Parent insights cannot write back derived conclusions as facts.

**Verification:** facts auditable to source messages; invalid/superseded facts leave current retrieval; Learning Intelligence unchanged.

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

**Verification:** relevant fact naturally informs response; irrelevant facts excluded; stale/superseded facts excluded; facts never appear as Learning Evidence; one-primary-call invariant preserved.

---

# Lina Frontend — Daily-Use Launch UX

## FE-01 — Lina Visual System & Reuse Decision

**Status:** BLOCKED  
**Dependencies:** PF-03 accepted  
**Purpose:** Establish one coherent age-appropriate visual/component direction before broader Student UI implementation.

**Required reuse evaluation:** inspect applicable candidates from `docs/TECHNOLOGY_REUSE_CATALOG.md`, including shadcn/ui baseline, existing assistant-ui decision, Motion/Motion Primitives, ThreeUI/Three.js, Magic UI, React Bits, 21st.dev, Aceternity UI, and Cult UI where relevant.

Classify each relevant candidate as `ADOPT / PARTIAL ADOPT / VISUAL REFERENCE / REJECT`.

**Target:** playful + intelligent + polished + personal; appropriate for roughly age 10; not preschool and not a corporate chatbot.

**Expected output:** visual system/reuse decision, key UI primitives, typography/spacing/motion/3D performance boundaries, Lina avatar/photo readiness, accessibility/readability constraints.

**Boundary:** do not stack libraries for novelty; ThreeUI/Three.js is selective visual capability, not application architecture.

---

## FE-02 — Daily Student Experience

**Status:** BLOCKED  
**Dependencies:** FE-01 accepted  
**Purpose:** Turn the proving Student surface into the Daily-Use Lina launch experience before multimodal controls become active.

**Expected output:** Lina home/entry experience; polished Tutor thread/composer; empty/thinking/error/retry states; suggested actions/guided checks; mic/photo/attachment affordance locations ready; bilingual RTL/LTR; responsive desktop/tablet/mobile-browser; purposeful motion and visual warmth.

**Verification:** child usability/browser review, responsive screenshots, no internal analytics/debug exposure, SSE/persistence unchanged, performance acceptable with selected visual layers.

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

**Verification:** original object unchanged; annotations align to intended region; derived copy distinguished from source; annotations/reconstruction never misclassified as Student Evidence.

---

# Private Daily-Use Deployment

## DEPLOY-01 — Lina Private Daily Environment

**Status:** BLOCKED  
**Dependencies:** TASK-034 accepted  
**Purpose:** Move the proven current composition into one stable private daily-use environment for Lina without changing product architecture.

**Preferred candidate:** Replit may be used after a fit check; the old Phase-0 Replit application is not the source baseline.

**Required composition:** current proven Web + API + Worker + fresh persistent PostgreSQL/pgvector + Clerk + Model Gateway/OpenAI configuration + durable/private object storage + health/restart procedures.

**Verification:** browser login, Tutor/Voice/Vision paths, persistence across restart, Worker operational, jobs recover, private assets authorized, secrets server-side, no architecture redesign required.

---

## LINA-R1 — Clean Real-Use Baseline

**Status:** BLOCKED  
**Dependencies:** DEPLOY-01 accepted  
**Purpose:** Begin the actual longitudinal Lina baseline from a clean database after the launch environment is proven.

**Boundary:** experimental historical database/conversation data is not imported as real-use history.

**Expected output:** natural Lina Session 1+ usage accumulating Personal Facts and Learning Intelligence under the current architecture.

**Verification / review:** confirm natural use; inspect first real Session lifecycle, Personal Facts, Learning Intelligence activation, later-session personalization, Voice/Vision usability, cost/latency, and launch-blocking defects. Do not overfit from one interaction.

---

# Post-Launch — Not Release 1 Blockers

## RAG-EVAL-01 — Measured Retrieval Evaluation

**Status:** BLOCKED  
**Dependencies:** LINA-R1 underway with representative real Grade-5 sources/questions  
**Purpose:** Evaluate whether current native Docling + PostgreSQL/pgvector Hybrid Retrieval should remain unchanged or whether an alternative materially improves total quality/complexity.

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
**Purpose:** Explore useful Parent-facing insights from the intersection of Student-asserted facts/interests and evidence-grounded learning behavior.

**No implementation choice is approved yet.** Begin later with descriptive/temporal/cross-analysis. Use SQL/analytics/LLM/clustering/ML only if data and a concrete question justify them.

**Prohibited:** psychological/personality diagnosis, unsupported talent labeling, derived insights writing themselves back as Personal Facts or Learning Intelligence authority.

---

# Still Deferred / Independent

Not promoted by this launch plan unless separately approved: `MATH-01` beyond its own bounded work, `ID-01` unless reproduced, `EDU-ERR-01`, `REC-25`, `LR-D04B`, Science production until explicit promotion, retention/proactive learning, Grade transition production, advanced gamification, graph/Graphiti, Redis/Celery, advanced ML before real data, and broad Parent Dashboard expansion beyond specifically promoted needs.
