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
→ RL-01D Controlled Full Intelligence Loop — DONE / ACCEPTED
→ TASK-027A Student Core Profile — READY
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
- real OpenAI Tutor, Segment Review transport, and embedding routes verified through Model Gateway;
- AI execution lineage/usage ledger verified;
- real Clerk Student/Parent browser auth and signed backend role authority verified;
- explicit Parent→Sandbox Test Student relationship established;
- linked Parent access, unrelated Student denial, Student→Parent denial, and client-supplied identity override denial verified;
- **REAL-AUTH CROSS-STUDENT ISOLATION = VERIFIED** for implemented auth/session paths;
- no Lina real identity/history used.

---

## RL-01D — Controlled Full Intelligence Loop

**Status:** DONE / ACCEPTED  
**Dependencies:** RL-01C accepted

**Accepted result:**
- real multi-turn Tutor interaction completed with exactly one primary Tutor model call per normal turn;
- FastAPI/SSE request/stream transaction-lock defect was identified, minimally corrected, regression-tested, and committed as `3af613484266e2c21d9e91a20d09ef217b05c16e`;
- natural Session/Segment closure, real Segment Learning Review, and deterministic Session Intelligence Finalization completed without manual DB mutation;
- semantic Session LLM calls remained `0`;
- source-linked Events, Evidence, Current State, Patterns, and Decision Views materialized from the finalized Session;
- one first Segment Review provider attempt ended in a durable `TimeoutError`, then the configured automatic Worker retry succeeded; final Review completed with no unrecoverable job and no partial intelligence activation;
- recoverable provider failure is accepted as operational behavior, not a correctness failure;
- a later same-denominator-fractions Session selected five compact relevant Current State/Pattern intelligence entries from prior finalized learning; no full prior transcript, archived Session, or Personal Facts were injected;
- a separate later `7 × 8` Session selected no fraction-specific Learner Intelligence;
- `RELEVANT PRIOR INTELLIGENCE SELECTION = PASS`;
- `IRRELEVANT FRACTION INTELLIGENCE EXCLUSION = PASS`;
- cross-Student scoping remained intact and no Lina real identity/history was used.

---

# User Knowledge Foundation

## TASK-027A — Student Core Profile & Tutor Student Context

**Status:** READY  
**Dependencies:** RL-01D accepted  
**Purpose:** Establish Parent/System-authoritative Student identity/context and provide a compact governed Student Core Context to the Tutor, separate from Personal Facts and Learner Intelligence.

**Expected output:**
- audit and reuse existing Student / Grade / GradePeriod structures rather than creating a second identity/profile model unnecessarily;
- define the canonical Parent/System-authoritative Student Core Profile boundary;
- support child identity/display name and date of birth when supplied;
- derive age from date of birth rather than independently maintaining age;
- resolve active Grade / GradePeriod from application-owned records;
- build a compact Student Core Context for normal Tutor requests;
- keep Student Core Context separate from Conversation Context, Safety, RAG, Personal Facts, and Learner Intelligence;
- preserve one primary Tutor model call per normal turn;
- preserve cross-Student isolation and source/authority boundaries.

**Verification:**
- existing Student/Grade structures are reused where fit;
- DOB-derived age behavior is deterministic and date-boundary tested;
- active Grade/GradePeriod selection is deterministic and Student-scoped;
- Tutor payload/context contains only bounded Student Core fields and no unrelated Parent/internal metadata;
- Student Core Context is distinguishable from Personal Facts and learning-derived intelligence;
- current Tutor, auth, Session, Safety, Retrieval, and Learning Intelligence tests remain green;
- no second learner-memory/profile authority is introduced.

**Explicit exclusions:** Personal Facts implementation (`PF-01+`), frontend redesign, Voice, Vision, annotation, RAG redesign, Artifacts, deployment, Science expansion, Parent Insights, and unrelated deferred tasks.

**Stop condition:** Stop after TASK-027A verification/report. Do not start `PF-01` in the same run.

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
