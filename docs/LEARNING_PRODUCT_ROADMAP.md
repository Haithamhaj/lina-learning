# LEARNING_PRODUCT_ROADMAP.md — Lina Personal Learning System

**Status:** Approved repository roadmap and product-evolution reference  
**Approved direction:** Option A — simplify the critical path while preserving the Learning Intelligence differentiator  
**Original approval:** 2026-08-23  
**Current execution state:** Always read from `project-state/PROJECT_STATE.md` and `TASKS.md`; this roadmap does not hardcode the current next task.

---

# 1. Purpose

This document records **approved product evolution, capability sequencing, dependencies, and validation gates**.

It is intentionally separate from the executable task queue.

The product goal is:

> A capable Tutor should work as naturally as a normal GPT conversation while Lina Learning adds what general chat does not provide reliably over time: evidence-grounded learner intelligence, relevant personalization, source provenance, optional trusted grounding, child safety, Parent inspectability, and a child-appropriate multimodal/visual experience.

Basic tutoring must not become harder because curriculum content, semantic extraction, school plans, or exact book material is unavailable.

---

# 2. Document Governance

| Document | Authority / purpose |
|---|---|
| `docs/PROJECT_REFERENCE.md` | Stable approved product truth and durable decisions |
| `docs/LEARNING_PRODUCT_ROADMAP.md` | **This document:** approved capability evolution, sequencing, and gates |
| `docs/LEARNING_INTELLIGENCE_SPEC.md` | Learning Intelligence semantics and authority contracts |
| `docs/IMPLEMENTATION_PLAN.md` | Technical implementation direction for approved work |
| `project-state/PROJECT_STATE.md` | Current operational truth and current next action |
| `TASKS.md` | Executable/current task state plus durable task history |
| `AGENTS.md` | Agent operating rules and protected areas |
| `project-state/SYSTEM_MAP.html` | Visual architecture + operational-readiness overlay |

### Roadmap rule

A capability being approved or present here does **not** authorize implementation.

A roadmap capability becomes executable only when:

1. dependencies/gates are sufficiently satisfied,
2. the Product Owner explicitly promotes it,
3. a bounded implementation task/spec is defined,
4. current state/task records reflect that promotion.

### Historical sequencing rule

Track IDs and old ordering remain useful provenance. A completed historical transition does not remain the current next action forever. `PROJECT_STATE.md` is the current operational authority.

---

# 3. Approved Product Principles

## 3.1 Tutor availability is independent of curriculum availability

The Tutor remains usable when:

- no book is uploaded,
- an exact book cannot be found,
- processing is incomplete,
- semantic enrichment fails,
- retrieval returns no useful result,
- no external reference exists.

The model may answer from general educational knowledge.

> **Content improves the answer; it does not authorize the answer.**

## 3.2 Current question drives the interaction

The current Student question is authoritative. Retrieval is question-driven, not curriculum-position-driven.

Lina may revisit an old topic, ask ahead, explore outside school sequence, switch subject, or ask something unrelated to the current book.

## 3.3 Current School Focus is not product authority

School plans/tables/outlines are references, not learning-path authority.

> **Relevance first; recency second; current Student intent above both.**

## 3.4 Grounding is optional and multi-source

When useful, grounding may come from:

1. current Student-captured page/image,
2. exact uploaded school book/material,
3. historical captured learning pages,
4. trusted aligned educational references,
5. trusted general educational references,
6. model general knowledge.

This is grounding priority, not teaching-method priority.

## 3.5 Concept belongs primarily to the interaction

Concept/topic identity normally comes from Lina's question, current conversation, current image/page when available, useful retrieved context, and model understanding.

A whole book does not need preclassification into a giant taxonomy before the system can understand what Lina is learning.

## 3.6 Learning Intelligence is the core differentiator

Current accepted path:

```text
Raw Interaction
→ optional Candidate hint
→ completed Segment
→ Segment Learning Review
→ staged findings
→ deterministic Session Intelligence Finalization
→ Session-authorized Event/Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ relevant later personalization
```

Candidate ≠ Evidence. Current State ≠ Pattern. Card ≠ source truth. Current behavior outranks history.

## 3.7 Curriculum semantics are optional enrichment

Unit/Lesson/Concept/Objective/Example/Exercise/etc. semantics may improve navigation, analysis, and source organization.

They are not required for Tutor availability, basic RAG, interaction concept identification, Evidence, or Learner Intelligence.

---

# 4. Option A — Corrected Critical Path

## Tutor runtime

```text
Student question
→ Auth / ownership
→ Safety
→ optional question-driven retrieval
+ relevant Learner Intelligence
→ ONE primary Tutor model call
→ response + bounded provisional metadata
→ completed Segment Review in background
→ Session-authorized intelligence
→ relevant later personalization
```

## Content grounding

```text
Learning Source
→ preserve original + provenance
→ structural extraction / normalization
→ retrieval-ready representation
→ hybrid retrieval

Optional:
structural representation
→ educational semantic enrichment
```

## No source

```text
Question
→ no useful retrieval
→ Tutor continues using model knowledge
```

This is a decoupling/simplification, not a replacement of the Learning Intelligence core.

---

# 5. What Must Be Preserved

Unless implementation evidence proves otherwise, preserve:

- Modular Monolith,
- Clerk role/ownership boundary,
- child-safety boundary,
- object-storage abstraction,
- PostgreSQL/Alembic,
- pgvector,
- DB-backed jobs/Worker,
- Model Gateway,
- AI execution ledger,
- one primary Tutor call,
- Docling structural representation,
- source/page provenance,
- structural-first content handling,
- PostgreSQL lexical + vector retrieval and deterministic fusion,
- bounded context,
- Candidate contract as provisional observation only,
- Segment Review + Session authority,
- Current State / Patterns / Card,
- rebuildability/versioning.

---

# 6. Grounding Source Model

The system evolves around a general **Learning Source** concept without creating a parallel RAG stack.

| Source type | Role |
|---|---|
| Exact uploaded book | Strong persistent curriculum anchor |
| Exact school material | Strong exact/near-exact school reference |
| Current Student-captured page | Highest immediate grounding when relevant |
| Historical captured page | Optional learning-history reference |
| Trusted aligned source | Grade/curriculum/topic alignment support |
| Trusted general educational source | Explanation/example/representation support |
| School plan/table | Supplementary reference only; never path authority |

---

# 7. Trusted Educational Reference Builder — Approved Future Pilot

A Subject may later have a bounded Trusted Educational Reference Pack even if exact school material is unavailable.

Useful setup inputs include Grade/Subject and, when known, Country, School, Curriculum, Book, Publisher, and language.

Source trust tiers should favor official authorities/publishers, established educational institutions, then reputable academic/school sources. Anonymous forums, unknown blogs, SEO farms, unclear-source worksheets, and low-trust scraped material are excluded by default.

Alignment classifications:

- `EXACT_CURRICULUM`
- `ALIGNED_CURRICULUM`
- `GENERAL_EDUCATION`

Aligned/general material must never impersonate exact school material.

The future pilot should be kept only if it materially improves correctness, Grade terminology, useful depth, explanation diversity, or representational variety at acceptable cost/latency.

---

# 8. Student-Captured Learning Sources — Approved Future Behavior

Vision implementation remains frozen until explicitly promoted.

Intended behavior:

```text
Current page/photo
→ understand immediate question
→ preserve original
→ use as high-priority current context
→ optionally persist reliable extracted learning source
```

Rules:

- one page is not a whole book,
- image identity does not establish learner Evidence,
- original is preserved,
- uncertain extraction that can change the answer should trigger clarification,
- derived interpretation remains separate from source.

---

# 9. Capability Roadmap

Stable IDs are preserved for cross-document provenance. Completed IDs are historical state; they do not remain current execution tasks.

## Track A — Core Simplification

**Goal:** Tutor availability as frictionless as normal GPT while preserving grounding, intelligence, provenance, and safety.

Historical IDs `LR-A01`–`LR-A10` are **COMPLETE / ACCEPTED**. Their governing outcomes remain:

- zero-book Tutor,
- structural-first content path,
- semantic enrichment optional,
- Current School Focus authority removed,
- optional grounding and Learning Intelligence preserved,
- real-use calibration seam preserved.

Track A completion does not automatically authorize later tracks.

## Track B — Grade 5 Math Trusted Reference Pilot

**Status:** **APPROVED FUTURE PILOT / FROZEN until explicit promotion.**

Preserved IDs:

- `LR-B01` Trusted-source contract
- `LR-B02` Grade 5 Math discovery pilot
- `LR-B03` ingestion through existing source/RAG boundary
- `LR-B04` source-priority/provenance
- `LR-B05` grounding-value evaluation
- `LR-B06` refresh/research control

Keep/expand only if measured value over model-only/exact-source baselines is material.

## Track C — Student-Captured Page Context

**Status:** **APPROVED CORE DIRECTION / FROZEN behind Vision promotion.**

Preserved IDs:

- `LR-C01` current-turn image/page context
- `LR-C02` captured-source persistence
- `LR-C03` ambiguity/confidence handling
- `LR-C04` historical captured-page retrieval

## Track D — Personalization Calibration & Evolution

**Goal:** improve the differentiating value—understanding how Lina learns over time—without creating a second learner-memory subsystem.

Historical/current IDs:

- `LR-D00` Segment Evidence Authority Foundation — **completed through accepted SEG-EVID architecture/implementation**.
- `LR-D01` real Evidence calibration — evidence/real-use dependent.
- `LR-D02` concept-quality calibration — evidence dependent.
- `LR-D03` Card relevance calibration — evidence dependent.
- `LR-D04A` Teaching Method Foundation & Observability — historical accepted foundation work.
- `LR-D04B` Method Outcome Learning — **deferred / requires sufficient trustworthy real Evidence and explicit promotion**.
- `LR-D05` retention/generalization views — longitudinal-evidence dependent.

Do not create a new learner profile/memory subsystem unless the accepted Evidence/State/Pattern/Card path proves insufficient and Product Owner approves a change.

## Track E — Intended Product Expansion

These are not random nice-to-haves; they remain **approved product direction but frozen by sequencing**:

- Science production support,
- Voice / STT,
- Vision / handwriting / drawing,
- original-image annotation / reconstruction,
- visual and interactive learning artifacts,
- Learning Canvas,
- broader Parent Intelligence UX,
- Grade-transition production,
- later retention/proactive learning,
- later additional subjects/languages.

Real Lina behavior should help decide **which approved capability is promoted first**, not whether the broader product direction exists.

---

# 10. Two Product Gates After Limited Real Use

Limited real Lina interaction has already occurred. Therefore the product no longer uses “Has Lina ever tried it?” as a binary gate.

## Gate A — Daily-Use Lina Baseline

Goal: one reliable recurring private Lina experience in which the existing Tutor/intelligence system can operate naturally enough to learn from real use.

Operational verification belongs in the current task/state process, not in this roadmap.

## Gate B — First Product Loop Complete

The first product loop is broader than Student Tutor. It ultimately needs:

- a useful Student learning experience,
- credible recurring Learning Intelligence / personalization,
- enough Parent visibility to inspect important state/evidence,
- useful content/grounding management where it adds value,
- operational traceability/recovery,
- AI usage/cost visibility sufficient for product operation.

## Gate C — Intended Product Expansion

After the core loop proves itself, promote approved deferred capabilities deliberately according to real behavior and product need.

---

# 11. Product Learning Signals for Capability Promotion

Real use should order approved capabilities with evidence such as:

- repeated desire to show homework/page/work → raise Vision/photo priority;
- keyboard/text friction → raise Voice/STT priority;
- repeated spatial/visual learning need → raise bounded Artifact/Canvas priority;
- natural Science demand → raise Science production priority;
- Parent inability to understand personalization → raise Parent Evidence/Intelligence UX priority;
- exact-source/model-only comparison showing real grounding gap → raise Trusted Reference priority.

This is prioritization, not reactive product discovery from zero.

---

# 12. Validation Gates

## Tutor Independence

Pass when an authenticated Student can learn with zero uploaded curriculum.

## Structural Grounding

Pass when structural content can be indexed/retrieved without mandatory curriculum semantics.

## Optional Enrichment

Pass when semantic enrichment can succeed/fail without blocking Tutor/basic RAG.

## Learning Intelligence Traceability

Pass when Segment Review → Session-authorized Evidence → State/Patterns/Card remains auditable, rebuildable, and current-behavior-first.

## Daily Real-Use Reliability

Pass only when the current operational track verifies a reliable recurring real-use environment and cross-session loop. Limited Real-Lina interaction does not by itself satisfy this.

## Deferred Capability Value

Promote a frozen capability only after explicit Product Owner decision, informed by real learning/product evidence and the approved broader direction.

---

# 13. Superseded Assumptions — Do Not Resurrect

1. A real Grade 5 book must be READY before Lina may use Tutor.
2. Semantic extraction is mandatory before retrieval indexing.
3. UNIT/LESSON/EXAMPLE taxonomy is required for basic Tutor operation.
4. Current School Focus directs the learning path.
5. Weekly/monthly school plans determine what Lina should study now.
6. Curriculum-derived Concept rows are required for Learner Intelligence.
7. Failure of optional semantic enrichment makes learning unavailable.
8. Candidate metadata is durable Evidence.
9. A second normal-turn Candidate/Subject/Topic classifier is required.
10. A semantic Session LLM summarizer is the current primary learning-review architecture.
11. Replit or any particular host is product architecture.

Historical code/data may remain auditable; these assumptions are not active requirements.

---

# 14. Treatment of Existing Semantic Work

Educational semantic work is:

> **DECOUPLED, NOT DELETED.**

Protected local Eureka work must not be stashed, reset, cleaned, overwritten, or incidentally refactored.

Future value should be judged from evidence: retrieval, navigation, Parent understanding, Tutor ambiguity reduction, cost, and maintenance value.

---

# 15. Live Roadmap Status

| Track | Status | Current meaning |
|---|---|---|
| Track A — Core Simplification | **COMPLETE / ACCEPTED** | Governing corrected critical path remains protected |
| Track B — Trusted References | **APPROVED FUTURE PILOT / FROZEN** | Do not implement without promotion |
| Track C — Student-Captured Pages | **APPROVED CORE DIRECTION / FROZEN** | Requires Vision promotion |
| Track D — Personalization Evolution | **EVIDENCE-GOVERNED** | Core authority implemented; later calibration tracks require real evidence/promotion |
| Track E — Broader Product Expansion | **APPROVED DIRECTION / FROZEN** | Science, Voice, Vision, Artifacts, Parent expansion, Grade production remain visible but gated |

---

# 16. Current Execution Rule

This roadmap intentionally does **not** name the current next executable task.

Always read:

1. `project-state/PROJECT_STATE.md`
2. `TASKS.md`
3. any explicitly named Product Owner-approved current task specification

before starting work.

No roadmap item should be promoted merely because earlier historical sequencing once placed it “next.”

---

# 17. Governing Summary

Lina Learning is not being reduced to a Text Math chatbot. Math/Text is the proving ground for the Learning Intelligence core.

The approved long-term direction remains a natural child learning product across Math + Science initially, with Voice, Vision, original-work understanding, visual/interactive representations, Parent inspectability, and later Grade/subject expansion. Those capabilities remain intentionally visible while frozen so early real use can determine sequencing without erasing the product vision.

Current operational next action is deliberately external to this roadmap.
