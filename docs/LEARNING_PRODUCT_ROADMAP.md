# LEARNING_PRODUCT_ROADMAP.md — Lina Personal Learning System

**Status:** Approved repository roadmap and product-evolution reference  
**Approved direction:** Option A — Simplify the critical path, preserve the valuable learning-intelligence architecture  
**Baseline reviewed:** `6bdd5dda7b795256cf2d51b15d123567758516f9`  
**Approved:** 2026-08-23

---

## 1. Purpose

This document is the central roadmap for **what Lina Learning should build next, in what order, and why**.

It is intentionally separate from the implementation task queue.

The product goal is simple:

> A capable Tutor should work as easily as a normal GPT conversation, while Lina Learning adds the value that a normal chat does not provide well: trusted grounding when available, persistent learning history, evidence-based personalization, longitudinal learner intelligence, source provenance, child safety, and a child-appropriate experience.

The system must not make basic tutoring harder merely because a curriculum source, semantic extraction layer, or school document is unavailable.

---

## 2. Document Governance

Each project document has a distinct responsibility.

| Document | Authority / purpose |
|---|---|
| `docs/PROJECT_REFERENCE.md` | Approved product principles, scope, boundaries, permanent decisions |
| `docs/LEARNING_PRODUCT_ROADMAP.md` | **This document:** ordered product capabilities, approved product-evolution decisions, dependencies, and validation gates |
| `TASKS.md` | Only work that has been promoted into executable implementation tasks |
| `docs/IMPLEMENTATION_PLAN.md` | Technical implementation direction for work that has been approved for execution |
| `project-state/PROJECT_STATE.md` | Short operational snapshot of the project **now** |
| `project-state/SYSTEM_MAP.html` | Visual map of the current approved system |
| `AGENTS.md` | Rules and source-of-truth map for AI/Codex work inside the repository |

### Roadmap rule

A capability being present in this roadmap does **not** authorize implementation.

A roadmap item becomes executable only when:

1. its dependencies are satisfied,
2. its validation gate is clear,
3. the Product Owner approves promotion,
4. it is added to `TASKS.md` with a concrete implementation scope.

### Approved supersession rule

The decisions in Sections 3, 4, 12, and 13 are newly approved product decisions. Where an older statement in `PROJECT_REFERENCE.md`, `IMPLEMENTATION_PLAN.md`, `TASKS.md`, `LEARNING_INTELLIGENCE_SPEC.md`, or `SYSTEM_MAP.html` directly contradicts one of these explicitly approved decisions, the older statement is **superseded pending LR-A01 governing-document reconciliation**.

This rule exists only to prevent Codex or another AI agent from implementing known-obsolete assumptions before the governing documents are reconciled. It is not permission to invent additional product changes.

---

# 3. Approved Product Principles

## 3.1 Tutor availability is independent of curriculum availability

The Tutor must remain usable when:

- no school book has been uploaded,
- the exact school book cannot be found,
- content processing is incomplete,
- semantic enrichment fails,
- RAG returns no useful result,
- no external reference exists.

The model may answer from its own general educational knowledge.

> **Content improves the answer; it does not authorize the answer.**

## 3.2 The current question drives the interaction

The current Student question is authoritative.

Retrieval is **question-driven**, not curriculum-position-driven.

The system does not need to determine where Lina currently is in the school curriculum or what the school says she should study now before helping her.

Lina may return to an old topic, ask about a future topic, ask outside the current school sequence, revisit something she previously misunderstood, or ask an exploratory question.

## 3.3 Current School Focus is not a product authority

`Current School Focus` as a controlling product concept is removed.

School plans, weekly tables, monthly plans, and similar documents may be useful **references**, but they do not determine the Tutor path.

Useful recent conversational/topic continuity remains allowed.

> **Recent context rule: Relevance first; recency second.**

Recent learning context should enter a new interaction only when it is genuinely useful to the current question.

## 3.4 Grounding is optional and multi-source

The Tutor may use any useful source available for the current question.

Approved source types include:

1. current Student-captured page/image,
2. exact uploaded school book or exact school material,
3. previously captured Student learning pages/homework,
4. trusted aligned curriculum/educational references,
5. trusted general educational references,
6. model general knowledge.

This is **grounding priority**, not teaching-method priority.

The Tutor may use a different explanation, example, analogy, or representation if it helps Lina understand better.

## 3.5 Concept belongs primarily to the learning interaction

Concept identity should normally be inferred from the interaction using:

- Lina's question,
- the current conversation,
- the current image/page when available,
- retrieved context when useful,
- the model's understanding.

A whole book does not need to be pre-classified into a large educational taxonomy before the system can understand what Lina is learning.

Typical examples:

- Division
- Decimal place value
- Multiplication by powers of ten
- Adding unlike fractions
- Area of rectangles

A conversation may have one primary concept and related concepts when useful, but this is an interaction-intelligence concern rather than a prerequisite for content ingestion.

## 3.6 Learning Intelligence remains a core differentiator

The retained core learning path is:

```text
Raw Interaction
→ Candidate Event
→ Validated Learning Event / Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ Relevant later personalization
```

The system should preserve the distinction between raw interaction, candidate interpretation, validated evidence, current state, historical patterns, and runtime personalization.

The Learner Intelligence Card remains a compact runtime projection rather than a new source of truth.

## 3.7 Semantic curriculum extraction is optional enrichment

The current curriculum semantic taxonomy may include UNIT, LESSON, CONCEPT, OBJECTIVE, DEFINITION, EXPLANATION, EXAMPLE, EXERCISE, VOCABULARY, FIGURE, TABLE, and FORMULA.

These may be useful for navigation, analysis, source organization, or future curriculum intelligence.

They are **not required** for:

- Tutor availability,
- basic RAG availability,
- concept identification from the conversation,
- Candidate Events,
- Evidence,
- Learner Intelligence.

The semantic layer should be retained initially as optional, rebuildable enrichment and evaluated later on demonstrated value.

---

# 4. Approved Core Architecture Correction — Option A

## 4.1 Current incorrect critical path

```text
Source / Book
→ Structural extraction
→ Mandatory semantic extraction
→ Semantic-derived index
→ Content READY
→ Student allowed to enter Tutor
```

This creates an unnecessary dependency: failure or absence of semantic curriculum processing can prevent a capable Tutor from helping the Student.

## 4.2 Target critical path

### Tutor runtime

```text
Student question
→ Auth / ownership
→ Safety
→ Optional question-driven retrieval
→ Relevant Learner Intelligence
→ One primary Tutor model call
→ Tutor response
→ Candidate Event
→ Evidence / State / Patterns
→ Later personalization
```

### Content grounding

```text
Learning Source
→ Preserve original + provenance
→ Structural extraction / normalization
→ Retrieval-ready representation
→ Existing hybrid retrieval

Optional:
Structural representation
→ Semantic enrichment
```

### No source available

```text
Question
→ Retrieval returns no useful context
→ Tutor continues using model knowledge
```

---

# 5. What Must Be Preserved

The architecture correction is a **decoupling/simplification**, not a rewrite.

Keep unless implementation evidence proves otherwise:

- modular monolith,
- Clerk role/ownership boundary,
- child-safety boundary,
- object-storage abstraction,
- PostgreSQL/Alembic,
- pgvector,
- DB-backed jobs/worker foundation,
- Model Gateway,
- AI execution ledger,
- one primary Tutor model call,
- Docling structural representation,
- page/source provenance,
- structural hierarchy and reading order,
- non-blind fixed-token-first content handling,
- PostgreSQL lexical retrieval,
- vector retrieval,
- deterministic RRF/hybrid fusion,
- context budgets,
- exact source lineage,
- Candidate Event contract,
- Evidence pipeline,
- Current State,
- Patterns,
- Learner Intelligence Card,
- rebuildability and versioning.

---

# 6. Grounding Source Model

The retrieval system should evolve toward the general concept of a **Learning Source**, without requiring a parallel RAG stack.

| Source type | Role |
|---|---|
| Exact uploaded book | Strongest persistent curriculum anchor |
| Exact school handout/material | Strong exact/near-exact curriculum reference |
| Student-captured current page | Highest context for the current turn |
| Student-captured historical page | Learning-history reference |
| Trusted aligned web source | Curriculum/grade/topic alignment support |
| Trusted general educational source | Explanation/example/representation support |
| School plan/table | Supplementary reference only; never learning authority |

The existing content/retrieval infrastructure should remain extensible enough to accept additional source types without creating a second retrieval subsystem.

---

# 7. Trusted Educational Reference Builder

## 7.1 Product decision

When a Subject is added or configured, the system may automatically build a **Trusted Educational Reference Pack** even if the exact school book is unavailable.

This capability is approved for future implementation and should be tested first as a bounded **Grade 5 Math pilot**.

It is not required for the current core architecture correction.

## 7.2 Inputs available during setup

Required:

- Grade
- Subject

Useful when known:

- Country
- School
- Curriculum
- Book title
- Publisher
- language
- other parent-provided identifying details

The Parent is **not required** to locate the exact book.

If the Parent has the real book, it can be uploaded. If not, the system proceeds normally and may discover aligned references.

## 7.3 Trusted source tiers

### Tier 1 — highest reference authority

- Ministry/curriculum authority
- official government education sites
- official publisher material
- official curriculum repositories

### Tier 2 — established educational institutions

- recognized educational organizations
- major established learning platforms
- high-quality curriculum support organizations

### Tier 3 — reputable academic/school sources

- universities
- schools
- academic institutions
- reputable teacher/curriculum resources with clear institutional ownership

### Excluded by default

- anonymous forums
- unknown blogs
- SEO-content farms
- unclear-source worksheets
- low-trust scraped material
- sources whose authority cannot be established

Parent approval is not required for each trusted source.

## 7.4 Source alignment classification

### `EXACT_CURRICULUM`

The exact uploaded/verified school book or exact official material.

### `ALIGNED_CURRICULUM`

Trusted material demonstrably covering the same grade/curriculum/topic, but not the exact school source.

### `GENERAL_EDUCATION`

Trusted educational material useful for explanation, examples, or representation but not tied to the exact curriculum.

Do not label an aligned/general source as the exact school book.

## 7.5 Why trusted references matter

Trusted web references are intended to improve:

- terminology alignment,
- grade-appropriate depth,
- curriculum proximity,
- additional examples,
- alternative explanations,
- visual/representational diversity,
- explanation variety when one teaching method does not work,
- support when the exact book is unavailable,
- support for topics not represented in the current uploaded material.

The purpose is **not** to make the Tutor dependent on web search.

## 7.6 Reference-pack refresh

Initial reference discovery should be allowed to run automatically when a Subject is configured.

Later, the Parent/Admin may request refresh, re-search, or source metadata updates without forcing a manual approval workflow for every source.

---

# 8. Student-Captured Learning Sources — Approved Future Behavior

Vision implementation remains frozen until its later gate, but the intended behavior is already approved.

```text
Current page
→ understand the immediate question
→ highest context for this turn
→ preserve original
→ extract useful content when reliable
→ optionally persist as Student-Captured Learning Source
```

Rules:

- do not treat one captured page as a full book,
- do not treat it automatically as official curriculum authority,
- preserve the original image,
- persistent extracted content requires sufficient reliability,
- if ambiguity can change the answer, do not guess,
- ask Lina to clarify or capture a clearer image,
- ambiguity that does not affect the answer need not block the conversation.

---

# 9. Capability Roadmap

Stable roadmap IDs are used so decisions can be referenced consistently across ChatGPT, Codex, project documents, and implementation reviews.

When a roadmap item is approved for execution, `TASKS.md` should reference the Roadmap ID and assign the repository's normal TASK/REC execution ID.

## Track A — Core Simplification

**Goal:** Make Tutor availability as frictionless as normal GPT while preserving grounding, intelligence, provenance, and safety.

| Roadmap ID | Capability / task | Dependency | Expected output | Gate |
|---|---|---|---|---|
| **LR-A01** | Governing decision correction | Option A approval | Permanent decisions reconciled across governing docs before code changes | Docs no longer instruct Codex to preserve old blocking architecture |
| **LR-A02** | Tutor always available | LR-A01 | Remove Student API/UI book-readiness gate from Tutor availability | Authenticated Student can open Tutor with zero content |
| **LR-A03** | Decouple index identity from mandatory semantics | LR-A01 | Non-destructive DB/index contract allowing structural-first indexes | Existing semantic index history remains valid |
| **LR-A04** | Structural-first index builder | LR-A03 | Existing indexing machinery can build source-linked blocks from completed structural representation | Structural source is searchable without semantic run |
| **LR-A05** | Semantic retrieval behavior becomes advisory | LR-A04 | Null semantic metadata cannot exclude otherwise relevant structural candidates | Example/exercise-style queries still retrieve structural content |
| **LR-A06** | Source processing lifecycle | LR-A04 | New upload can progress through preserve → structural → retrieval index using existing worker foundation | One real source reaches retrieval-ready without manual semantic scripts |
| **LR-A07** | Parent content-status decoupling | LR-A03/LR-A04 | Parent sees grounding/index status separately from optional semantic enrichment | Semantic failure does not report Tutor/content as globally unusable |
| **LR-A08** | Deprecate school-focus authority residue | LR-A01 | Stop producing obsolete `current_school_focus` authority while preserving conversational continuity | No school-position signal controls Tutor/retrieval |
| **LR-A09** | Simplification acceptance suite | LR-A02–A08 | Automated proof of zero-book Tutor + optional grounding + intelligence behavior | All required acceptance scenarios pass |
| **LR-A10** | Real Lina calibration resumes | LR-A09 | REC-25 calibration begins only after corrected architecture is proven | Real interactions confirm Tutor usability and context quality |

### Required acceptance scenarios for LR-A09

1. Zero book → session opens and Tutor answers.
2. Zero retrieval match → Tutor still answers.
3. Structural/indexed content → relevant grounding enters Tutor context.
4. Semantic enrichment failure → Tutor/RAG remain usable.
5. Relevant Learner Intelligence → enters context.
6. Irrelevant/stale intelligence → does not enter context.
7. Conversation continuation can use relevant recent topic context.
8. No school-plan/current-school-position authority is required.

## Track B — Grade 5 Math Trusted Reference Pilot

**Goal:** Prove whether trusted external references improve grounding and explanation diversity before building a large discovery subsystem.

**Starts only after:** LR-A09; preferably after first real Lina observations from LR-A10.

| Roadmap ID | Capability / task | Dependency | Expected output | Gate |
|---|---|---|---|---|
| **LR-B01** | Trusted-source contract | Track A | Source trust tiers, provenance fields, alignment classification, rejection rules | Contract is small and auditable |
| **LR-B02** | Grade 5 Math discovery pilot | LR-B01 | Bounded search for trusted Grade 5 Math references using known curriculum/publisher metadata when available | Useful trusted sources can be discovered without exact book |
| **LR-B03** | Reference ingestion through existing source/RAG boundary | LR-B02 | Selected trusted references normalized and indexed without a parallel RAG stack | Existing RetrievalService can use them |
| **LR-B04** | Grounding-source priority | LR-B03 | Exact/current sources and aligned/general references coexist with explicit provenance/authority | Aligned sources never impersonate exact curriculum |
| **LR-B05** | Grounding-value evaluation | LR-B04 | Compare Tutor output across model-only, exact-source when available, and trusted-reference grounding | Evidence shows whether references improve usefulness |
| **LR-B06** | Refresh/research control | LR-B05 | Parent/Admin can trigger later refresh/research without per-source approval | Refresh is bounded and provenance-preserving |

### LR-B05 evaluation dimensions

Evaluate practical value rather than benchmark theater:

- correctness,
- closeness to Grade 5 terminology,
- appropriateness of depth,
- usefulness of examples,
- explanation diversity,
- ability to explain the same concept differently after Lina remains stuck,
- source relevance,
- avoidance of unnecessary context,
- latency/cost impact.

Possible judgment:

- **KEEP** — material value demonstrated.
- **MODIFY** — useful but source selection/ranking needs correction.
- **STOP** — little value over the model alone; do not expand the subsystem.

## Track C — Student-Captured Page Context

**Goal:** Let a page Lina is holding become immediate learning context without requiring the full book.

**Status:** Approved future capability; implementation frozen until Vision gate.

| Roadmap ID | Capability / task | Dependency | Expected output |
|---|---|---|---|
| **LR-C01** | Current-turn image/page context | Vision gate | Page becomes highest-priority context for the immediate question |
| **LR-C02** | Captured-source persistence | LR-C01 | Original preserved and reliable extraction can become a reusable learning source |
| **LR-C03** | Ambiguity/confidence handling | LR-C01 | Tutor asks for clarification when uncertain extraction can change the answer |
| **LR-C04** | Historical captured-page retrieval | LR-C02 | Relevant prior captured pages may support later questions |

## Track D — Personalization Calibration & Evolution

**Goal:** Improve the system's differentiating value: understanding how Lina learns over time.

| Roadmap ID | Capability / task | Dependency | Expected output |
|---|---|---|---|
| **LR-D01** | Real Evidence calibration | LR-A10 | Validate Candidate → Evidence behavior on real interactions |
| **LR-D02** | Concept quality calibration | LR-D01 | Confirm interaction-derived concept labels are useful and stable enough for evidence grouping |
| **LR-D03** | Card relevance calibration | LR-D01 | Confirm relevant personalization helps and irrelevant history stays out |
| **LR-D04** | Strategy outcome learning | sufficient real evidence | Improve how prior successful/unsuccessful teaching strategies influence later Tutor behavior |
| **LR-D05** | Retention/generalization views | sufficient longitudinal evidence | Validate whether existing derived views meaningfully help Parent/Tutor decisions |

No new learner-profile subsystem should be introduced unless the current Evidence/State/Pattern/Card path proves insufficient.

## Track E — Later Product Expansion

These remain deferred until their relevant gates:

- Science production support
- Voice / STT
- production Vision / handwriting / drawing
- Learning Canvas
- Interactive Artifact Engine
- advanced motion/gamification
- Grade transition production
- broader Parent Dashboard

They must not expand the current simplification scope.

---

# 10. Ordered Build Sequence

```text
1. Correct governing architecture decisions
2. Make Tutor work with zero book/content
3. Make structural content directly retrieval-ready
4. Prove existing Hybrid RAG still works
5. Resume Real Lina calibration
6. Run Grade 5 Math Trusted Reference Pilot
7. Compare real grounding value
8. Improve trusted-source discovery/ranking only if value is proven
9. Open Student-captured page work when Vision is authorized
10. Expand personalization based on real evidence
11. Expand subjects/channels/artifacts only after their gates
```

---

# 11. What Must NOT Be Built During Core Simplification

Track A does **not** authorize:

- a new RAG framework,
- a second vector database,
- a parallel generic-source retrieval subsystem,
- web-search agent implementation,
- curriculum planner,
- curriculum-position tracker,
- concept graph,
- new concept-classifier service,
- multi-agent Tutor orchestration,
- Vision,
- Voice,
- Science expansion,
- Learning Canvas,
- Artifact Engine,
- Parent Dashboard expansion.

Track A is a simplification and decoupling effort.

---

# 12. Validation Gates

## Gate A — Tutor Independence

Pass when:

> An authenticated Student can learn with the Tutor using zero uploaded curriculum content.

## Gate B — Structural Grounding

Pass when:

> A structurally processed source can be indexed and retrieved without mandatory semantic curriculum extraction.

## Gate C — Optional Enrichment

Pass when:

> Semantic enrichment may succeed or fail without blocking Tutor availability or basic RAG.

## Gate D — Real Lina Calibration

Pass when:

> Real interactions demonstrate that the corrected Tutor/context/intelligence path is usable enough to justify further product expansion.

## Gate E — Trusted Reference Value

Pass when:

> The bounded Grade 5 Math reference pilot demonstrates practical improvement in grounding and/or explanation diversity sufficient to justify automating and expanding the capability.

---

# 13. Superseded Assumptions

The following earlier assumptions are superseded and must not be used as active implementation requirements:

1. A real Grade 5 book must be READY before Lina may use the Tutor.
2. Semantic extraction is mandatory before retrieval indexing.
3. UNIT/LESSON/EXAMPLE/etc. classification is required for basic Tutor operation.
4. Current School Focus should direct the main learning path.
5. School weekly/monthly plans determine what Lina should study now.
6. Curriculum-derived Concept rows are required for learner intelligence.
7. Failure in optional semantic enrichment should make the learning experience unavailable.

Historical implementation/data may remain for auditability; superseded product assumptions should not remain active architecture requirements.

---

# 14. Treatment of Existing Semantic Work

The current Semantic Layer should be:

**DECOUPLED, NOT DELETED.**

Current uncommitted Prompt-v5 / Eureka verifier work should remain parked until the core architecture correction is complete.

After real usage, evaluate semantic enrichment by direct value:

- Does it improve retrieval?
- Does it improve navigation?
- Does it help Parent understanding?
- Does it reduce Tutor ambiguity?
- Is the cost/latency/maintenance justified?

If not, it may later be deprecated or deleted through a separately approved cleanup task.

---

# 15. Repository Integration Plan

## `docs/PROJECT_REFERENCE.md`

Reconcile durable decisions during **LR-A01**:

- Tutor always available,
- question-driven optional grounding,
- no Current School Focus authority,
- interaction-derived concept,
- semantics optional,
- multi-source Learning Source model,
- trusted web reference principle,
- grounding priority vs teaching-method freedom.

Do not copy the full roadmap.

## `TASKS.md`

Add only the next executable Track A tasks when the Product Owner promotes them.

Each execution task should include:

- Roadmap ID,
- purpose,
- dependencies,
- files/areas,
- expected output,
- verification,
- blocked-by-approval/proof status.

Track B/C/D future items remain here until promoted.

REC-25 Early Lina Calibration must not proceed until the Track A correction gate is passed.

## `docs/IMPLEMENTATION_PLAN.md`

During LR-A01, update the technical critical path to:

```text
source → structural → retrieval index
                  ↘ optional semantics
```

and:

```text
question → safety → optional retrieval + relevant intelligence → Tutor
```

## `project-state/PROJECT_STATE.md`

During LR-A01, record only:

- Option A approved,
- Track A is next,
- semantic Prompt-v5 work parked,
- REC-25 calibration waiting for Track A,
- next approved action.

Do not copy the entire roadmap.

## `project-state/SYSTEM_MAP.html`

On the next authorized map update, visually distinguish:

- Tutor critical path,
- optional grounding,
- optional semantic enrichment,
- learner-intelligence path,
- future trusted references / captured pages as non-active source types.

## `AGENTS.md`

`docs/LEARNING_PRODUCT_ROADMAP.md` is a governing reference. Agents must not implement roadmap items unless they are promoted to `TASKS.md`.

---

# 16. Live Roadmap Status

| Track | Status | Current decision |
|---|---|---|
| Track A — Core Simplification | **APPROVED DIRECTION** | LR-A01 is the next promotion target |
| Track B — Trusted Grade 5 Math References | **APPROVED FUTURE PILOT** | Do not build until Track A gate / promotion |
| Track C — Student-Captured Pages | **APPROVED FUTURE BEHAVIOR / FROZEN** | Wait for Vision gate |
| Track D — Personalization Calibration | **ACTIVE DESIGN / REAL DATA DEPENDENT** | Continue after corrected real-Lina flow |
| Track E — Broader Expansion | **FROZEN** | Later gates only |

---

# 17. Next Recommended Action

Promote **LR-A01 — Governing decision correction** into the executable repository plan.

The first implementation-facing work after LR-A01 should be the small, test-driven Track A architecture correction.

Do not begin the Trusted Reference Builder implementation in the same Track A change.

After Track A passes and the Tutor works naturally with zero content and with optional structural grounding, start the bounded **Grade 5 Math Trusted Reference Pilot** and judge its value from actual Tutor behavior before expanding it.
