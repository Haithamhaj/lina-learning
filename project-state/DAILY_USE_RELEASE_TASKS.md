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
→ TASK-027A Student Core Profile — DONE / ACCEPTED
→ PF-01 Personal Facts Contract — READY
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

---

## RL-01B — Fresh Shared Application DB & Runtime Composition

**Status:** DONE / ACCEPTED  
**Accepted commit:** `dc76195bcb9ba7577b5f6dbbf0804f5bff6c43ff`

**Accepted result:** fresh shared PostgreSQL/pgvector DB, aligned Web/API/Worker runtime, standard Worker command, Worker recovery smoke, and Student-scoped shared-DB isolation.

---

## RL-01C — Clerk + OpenAI Operational Verification

**Status:** DONE / ACCEPTED

**Accepted result:** real Clerk Student/Parent auth and signed backend roles, explicit Parent→Student authorization, real OpenAI Tutor/Segment Review/embedding routes through Model Gateway, AI execution lineage, and real-auth cross-Student isolation.

---

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

**Status:** READY  
**Dependencies:** TASK-027A accepted

**Purpose:** Define the durable Student-scoped contract for factual context the Student tells the system about herself/her world. This is the semantic/data boundary for personal memory, not extraction or Tutor use yet.

### Approved source authority

- Personal Facts are **Student-asserted**.
- They come from what the Student tells the system about herself/her world.
- Parent claims do not automatically become Student Personal Facts.
- The system does not need to establish objective external truth before preserving a Student assertion as personal context.

### Required contract output

PF-01 must define:

1. **Qualification boundary**
   - what is a durable Personal Fact;
   - what is merely ephemeral/current-conversation context;
   - what must never be stored as a Personal Fact.

2. **Fact representation**
   - stable fact identity/key/category;
   - normalized value/statement;
   - current lifecycle status;
   - source Student message/interaction lineage;
   - first-observed / last-observed timestamps;
   - support/repetition metadata where useful.

3. **Temporal/reconciliation semantics**
   - repeated support;
   - contradiction;
   - invalidation;
   - supersession;
   - current vs historical/superseded facts;
   - history preserved rather than silently overwritten/deleted.

4. **Safety/privacy boundaries**
   - do not store unsafe sensitive personal information merely because the child said it;
   - comply with `docs/CHILD_SAFETY_POLICY.md`;
   - no hidden broad child-surveillance profile.

5. **Semantic exclusions**
   - no personality analysis;
   - no psychological interpretations/diagnosis;
   - no intelligence labels;
   - no learning-style labels;
   - no global character judgments;
   - no transcript summaries masquerading as facts;
   - no Learner Intelligence/Evidence copied into Personal Facts;
   - no Student Core Profile duplication merely to create a second memory.

6. **Authority separation**

```text
Student Core Profile = Parent/System-authoritative application facts
Personal Facts       = Student-asserted factual personal context
Learner Intelligence = learning-derived evidence-backed state
Conversation Context = current/raw conversational continuity
```

7. **Parent inspection**
   - Parent may inspect stored Personal Facts for the linked Student;
   - inspection does not make Parent a Personal-Fact source;
   - no separate hidden child-facts store is required under the current approved decision.

8. **Isolation/rebuildability**
   - every Personal Fact is Student-scoped;
   - source lineage is sufficient to audit/rebuild derived current state;
   - Student A facts can never enter Student B context.

### Important product examples to resolve in the contract

The contract should classify examples such as:

- “I like drawing.”
- “My cat is called Luna.”
- “Sara is my best friend.”
- “I’m going to Jeddah next weekend.”
- “I’m tired today.”
- repeated mentions of football without an explicit “I like football.”
- “I’m bad at math.”
- “I’m shy.”
- “I’m 14 / I’m in Grade 8” when Parent/System Core Profile says otherwise.

The contract must distinguish literal Student assertions from derived interest/personality inference. Repetition alone must not silently become a psychological or personality conclusion.

### Verification

- contract clearly distinguishes durable vs ephemeral vs prohibited memory;
- temporal/supersession examples are deterministic enough for PF-02 to implement ADD / UPDATE / SUPERSEDE / NOOP;
- no Personal Fact can become Learning Evidence merely through existence;
- Parent inspection and Student-scoped authorization are specified;
- child-safety/private-information storage boundaries are explicit;
- no second memory/profile platform is introduced.

### Explicit exclusions

PF-01 does **not** implement:
- LLM/model extraction;
- Worker jobs;
- ADD/UPDATE/SUPERSEDE/NOOP execution;
- Tutor Personal Facts selection/injection;
- Parent Insights;
- frontend memory UI;
- graph/Graphiti or generic memory frameworks;
- PF-02 or PF-03.

**Stop condition:** Stop after the Personal Facts contract/design is produced for Product Owner review. Do not start PF-02.

---

## PF-02 — Personal Facts Extraction & Reconciliation

**Status:** BLOCKED  
**Dependencies:** PF-01 accepted  
**Purpose:** Async Worker + Model Gateway extraction/reconciliation using ADD / UPDATE / SUPERSEDE / NOOP; no extra normal Tutor-turn call.

---

## PF-03 — Relevant Personal Facts in Tutor Context

**Status:** BLOCKED  
**Dependencies:** PF-02 accepted  
**Purpose:** Relevance-bounded Personal Facts as a separate Tutor input beside Conversation Context, Student Core Context, Learner Intelligence, optional RAG, and Safety; preserve one primary Tutor call.

---

# Lina Frontend — Daily-Use Launch UX

## FE-01 — Lina Visual System & Reuse Decision
**Status:** BLOCKED  
**Dependencies:** PF-03 accepted

## FE-02 — Daily Student Experience
**Status:** BLOCKED  
**Dependencies:** FE-01 accepted

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
