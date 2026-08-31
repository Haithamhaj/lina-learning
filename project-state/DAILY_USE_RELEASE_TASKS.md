# Daily-Use Lina Release 1 — Execution Tasks

**Status:** Product Owner approved on 2026-08-31  
**Authority:** Current bounded execution overlay for Daily-Use Lina Release 1.  
**Relationship to `TASKS.md`:** `TASKS.md` remains the preserved historical ledger.  
**Execution rule:** Only one task is `READY` at a time. After each task: verify, review, update `PROJECT_STATE.md`, then promote the next task explicitly.

---

# Approved Sequence

```text
RL-01A Accepted Runtime Alignment — DONE / ACCEPTED
→ RL-01B Fresh Shared DB + Runtime Composition — DONE / ACCEPTED
→ RL-01C Clerk + OpenAI Operational Verification — DONE / ACCEPTED
→ RL-01D Controlled Full Intelligence Loop — READY
→ TASK-027A Student Core Profile — BLOCKED
→ PF-01 Personal Facts Contract — BLOCKED
→ PF-02 Personal Facts Extraction/Reconciliation — BLOCKED
→ PF-03 Relevant Facts in Tutor Context — BLOCKED
→ FE-01 Lina Visual System & Reuse Decision — BLOCKED
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
**Accepted result:** isolated worktree aligned to accepted `codex/ctx-03`; protected original checkout untouched; baseline verification passed; stale runtime references classified.

---

## RL-01B — Fresh Shared Application DB & Runtime Composition

**Status:** DONE / ACCEPTED  
**Accepted commit:** `dc76195bcb9ba7577b5f6dbbf0804f5bff6c43ff`

**Accepted result:**
- fresh shared PostgreSQL 17.8 + pgvector 0.8.1 application database created from zero and migrated to Alembic head `f5a1c2d3e4b6`;
- no historical experimental interaction data imported;
- aligned Web + API + Worker run from current `codex/ctx-03` against the same DB;
- standard Worker command `npm run dev:worker` added and worker claim/complete/retry/restart smoke passed;
- shared DB Student isolation verified structurally/synthetically;
- Lina real longitudinal baseline remains Student-scoped and unstarted.

---

## RL-01C — Clerk + OpenAI Operational Verification

**Status:** DONE / ACCEPTED  
**Dependencies:** RL-01B accepted

**Accepted result:**
- real OpenAI Tutor route verified through Model Gateway using `gpt-5.6-luna`;
- real Segment Review transport verified through Model Gateway using `gpt-5.6-luna` without durable intelligence activation;
- real embedding route verified using `text-embedding-3-small` with 1536 dimensions;
- AI execution ledger recorded provider/model/task, success, latency, and usage lineage;
- real Clerk browser sign-in verified for launch-test Student and Parent identities;
- Clerk session-token customization now carries signed role authority from user public metadata;
- backend `/api/v1/auth/me` verifies Parent as `PARENT_ADMIN` and Student as `STUDENT`;
- launch-test Parent application User created as `PARENT_ADMIN`, with explicit Parent→Sandbox Test Student relationship;
- Parent real-auth matrix passed: `/auth/me` 200 `PARENT_ADMIN`; Parent shell 200; Student shell 403; linked Student summary 200; unrelated Student summary 404;
- Student real-auth matrix passed: `/auth/me` 200 `STUDENT`; Student shell 200; Parent shell 403; spoofed `student_id` did not grant another Student identity/session; foreign Session GET/POST both 404;
- **REAL-AUTH CROSS-STUDENT ISOLATION = VERIFIED** for implemented auth/session paths;
- browser-supplied Student/session identifiers do not override server-owned Clerk-subject → Student ownership;
- no Lina real identity/history was used, and no code/schema/dependency change was needed for Clerk role authority.

**Boundary retained:** future Personal Facts isolation is not claimed until PF tasks implement that domain.

---

## RL-01D — Controlled Full Intelligence Loop

**Status:** READY  
**Dependencies:** RL-01C accepted  
**Purpose:** Prove on a controlled launch-test Student the complete accepted path:

```text
real Tutor
→ Segment persistence/closure
→ Worker Segment Learning Review
→ deterministic Session Finalization
→ Event / Evidence
→ Current State / Patterns / Decision Views
→ Learner Intelligence Card
→ later Tutor receives relevant intelligence
```

**Expected output:**
- one controlled learning Session using real Tutor/OpenAI on the launch-test Student;
- Session/Segment lifecycle advances through normal application/Worker behavior without manual DB mutation;
- required Segment Review runs and validates;
- deterministic Session Finalization activates one coherent durable intelligence generation;
- Events/Evidence remain source-linked;
- Current State/Patterns/Decision Views/Card update only from Session-authorized intelligence;
- a later launch-test Student Session receives relevant Card/intelligence context;
- an unrelated later question does not receive stale irrelevant intelligence;
- one primary Tutor call per normal turn remains intact;
- controlled validation data remains clearly separate from Lina's future real longitudinal baseline.

**Verification:**
- no manual DB updates used to force lifecycle/intelligence progression;
- no extra semantic Session LLM call after Segment Reviews;
- no stuck unrecoverable jobs;
- Session Finalization remains deterministic and no partial activation occurs;
- source→Segment Review→Event/Evidence→State/Pattern/Card lineage is inspectable;
- relevant later personalization is observable without full transcript injection;
- cross-Student isolation remains intact.

**Explicit exclusions:** TASK-027A, Personal Facts, frontend redesign, Voice, Vision, annotation, RAG changes, Learning Artifacts, Replit deployment, MATH-01, Science, Parent Insight analysis.

**Stop condition:** Stop after RL-01D verification/report. Do not start TASK-027A in the same run.

---

# User Knowledge Foundation

## TASK-027A — Student Core Profile & Tutor Student Context
**Status:** BLOCKED  
**Dependencies:** RL-01D accepted  
**Purpose:** Parent/System-authoritative child identity, DOB-derived age, active Grade/GradePeriod, compact Student Core Context. Separate from Personal Facts and Learning Intelligence.

## PF-01 — Personal Facts Contract
**Status:** BLOCKED  
**Dependencies:** TASK-027A accepted  
**Purpose:** Durable Student-asserted factual context with source lineage, temporal lifecycle, support/contradiction/supersession; no psychological/personality/learning inference.

## PF-02 — Personal Facts Extraction & Reconciliation
**Status:** BLOCKED  
**Dependencies:** PF-01 accepted  
**Purpose:** Async Worker + Model Gateway extraction/reconciliation using ADD / UPDATE / SUPERSEDE / NOOP; no extra normal Tutor-turn call.

## PF-03 — Relevant Personal Facts in Tutor Context
**Status:** BLOCKED  
**Dependencies:** PF-02 accepted  
**Purpose:** Relevance-bounded Facts as a separate Tutor input beside conversation, Student Core Context, Learner Intelligence, optional RAG, and Safety; preserve one primary Tutor call.

---

# Lina Frontend — Daily-Use Launch UX

## FE-01 — Lina Visual System & Reuse Decision
**Status:** BLOCKED  
**Dependencies:** PF-03 accepted  
**Purpose:** One coherent age-appropriate visual system. Evaluate shadcn, existing assistant-ui decision, Motion/Motion Primitives, ThreeUI/Three.js, Magic UI, React Bits, 21st.dev, Aceternity, Cult UI as ADOPT / PARTIAL ADOPT / VISUAL REFERENCE / REJECT.

## FE-02 — Daily Student Experience
**Status:** BLOCKED  
**Dependencies:** FE-01 accepted  
**Purpose:** Polished Lina home + Tutor thread/composer, bilingual RTL/LTR, responsive UX, mic/photo affordances, purposeful motion, no internal analytics exposure.

---

# Multimodal Launch Capabilities

## TASK-032 — Voice Input / STT
**Status:** BLOCKED  
**Dependencies:** FE-02 accepted; RL-01C Model Gateway operational  
**Approved flow:** audio → STT → transcript → normal Tutor. Raw audio not retained after successful STT. No speech-to-speech requirement for Release 1.

## TASK-033 — Student Image / Handwriting / Drawing Understanding
**Status:** BLOCKED  
**Dependencies:** TASK-032 accepted; durable/private storage; RL-01C Model Gateway operational  
**Purpose:** Original private image + Multimodal Turn + Vision interpretation; ambiguity asks clarification; original remains source authority.

## TASK-034 — Annotate Original Image First
**Status:** BLOCKED  
**Dependencies:** TASK-033 accepted  
**Purpose:** Derived annotation on original first; clean React/SVG/interactive reconstruction only when annotation is insufficient. Derived output never replaces Student source Evidence.

---

# Private Daily-Use Deployment

## DEPLOY-01 — Lina Private Daily Environment
**Status:** BLOCKED  
**Dependencies:** TASK-034 accepted  
**Purpose:** Proven Web + API + Worker + shared persistent PostgreSQL/pgvector + Clerk + Model Gateway/OpenAI + durable private object storage in one stable private environment. Replit is a candidate, not architecture.

## LINA-R1 — Clean Real-Use Baseline
**Status:** BLOCKED  
**Dependencies:** DEPLOY-01 accepted  
**Purpose:** Begin Lina's actual longitudinal use under her own clean Student identity. Test Student data may coexist in the shared DB but must never enter Lina's history/context/authorization scope.

---

# Post-Launch — Not Release 1 Blockers

## RAG-EVAL-01 — Measured Retrieval Evaluation
**Status:** BLOCKED  
**Dependencies:** representative real Grade-5 use/questions  
**Rule:** current Docling + PostgreSQL/pgvector remains baseline unless measured comparison proves a material advantage for an alternative.

## TASK-035 — Interactive Learning Artifacts
**Status:** BLOCKED  
**Dependencies:** explicit Product Owner promotion after real use  
**Renderer baseline:** React/SVG + Motion + JSXGraph + React Konva + MathLive. Image generation remains optional/deferred illustrative output, not default teaching renderer.

## PARENT-INSIGHT-01 — Facts × Learning Exploration
**Status:** BLOCKED / FUTURE / DATA-DEPENDENT  
**Purpose:** Explore Parent-facing insights only after sufficient Personal Facts + Learning Intelligence history. No psychological/personality diagnosis, unsupported talent labeling, or write-back into source layers.

---

# Still Deferred / Independent

Not promoted by this launch plan unless separately approved: `MATH-01`, `ID-01` unless reproduced, `EDU-ERR-01`, `REC-25`, `LR-D04B`, Science production, retention/proactive learning, Grade transition production, advanced gamification, graph/Graphiti, Redis/Celery, advanced ML before real data, and broad Parent Dashboard expansion beyond specifically promoted needs.
