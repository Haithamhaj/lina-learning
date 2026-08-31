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
→ RL-01C Clerk + OpenAI Operational Verification — READY
→ RL-01D Controlled Full Intelligence Loop — BLOCKED
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
**Dependencies:** RL-01A accepted  
**Accepted commit:** `dc76195bcb9ba7577b5f6dbbf0804f5bff6c43ff`

**Accepted result:**
- fresh shared PostgreSQL 17.8 + pgvector 0.8.1 application database created from zero and migrated to Alembic head `f5a1c2d3e4b6`;
- no historical experimental interaction data imported;
- persistent local database resource `lina-learning-daily-use-postgres` established;
- aligned Web + API + Worker run from the current `codex/ctx-03` worktree against the same database;
- stale old-checkout API stopped;
- `npm run dev:worker` added as the standard Worker startup command;
- Worker claim/complete/retry/restart smoke verification passed;
- one synthetic Sandbox Test Learner exists with zero learning history; Lina's real Student identity/history has not been created;
- implemented learning paths were verified Student-scoped; future Personal Facts isolation remains to be implemented in PF tasks;
- Python suite `715 passed, 7 skipped`; web build/typecheck and `git diff --check` passed.

**Shared database invariant:** Test/validation Students and Lina may coexist in this database under separate Student identities. Cross-Student isolation is Criticality 5. Lina's real longitudinal baseline is Student-scoped, not database-scoped.

---

## RL-01C — Clerk + OpenAI Operational Verification

**Status:** READY  
**Dependencies:** RL-01B accepted  
**Purpose:** Make the aligned fresh runtime usable with real Clerk identity and real OpenAI-backed Model Gateway routes without creating parallel auth/provider integrations.

**Expected output:**
- verify the exact current Clerk configuration path and use it safely with the aligned Web/API;
- verify real browser Clerk session/JWT/JWKS flow against the fresh shared application database;
- establish/verify a controlled launch-test Parent/Student identity path without creating Lina's real longitudinal history prematurely;
- verify Parent ↔ Student authorization and cross-Student isolation through the real auth path;
- verify server-side OpenAI configuration through the existing Model Gateway;
- verify real Tutor, Segment Review, and embedding routes through the Gateway;
- verify AI execution lineage/usage logging without exposing secrets;
- preserve one primary Tutor call and all accepted Safety/Session/Segment boundaries.

**Verification:**
- real browser auth works on the aligned runtime;
- protected Student/Parent boundaries hold;
- one controlled real Tutor execution succeeds for a launch-test Student;
- a bounded real Segment Review transport check and embedding execution succeed through Model Gateway without running the full Session finalization journey;
- no provider key reaches browser/Git/log output;
- no arbitrary direct OpenAI SDK integration is added outside the provider adapter;
- Lina's real Student identity remains unused/clean unless an identity-only bootstrap is explicitly unavoidable and produces zero learning history.

**Explicit exclusions:** full Session→Review→Finalization→Evidence→Card proof (RL-01D), Personal Facts, frontend redesign, Voice, Vision, annotation, RAG changes, Artifacts, Replit deployment, MATH-01, ID-01 fixes unless reproduced as an auth blocker.

**Stop condition:** Stop after RL-01C verification/report. Do not execute RL-01D.

---

## RL-01D — Controlled Full Intelligence Loop

**Status:** BLOCKED  
**Dependencies:** RL-01C accepted  
**Purpose:** Prove on a controlled launch-test Student the complete accepted path: real Tutor → Segment → Worker Review → deterministic Session Finalization → Event/Evidence → State/Patterns/Decision Views/Card → relevant later Tutor personalization. No manual DB mutation.

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
