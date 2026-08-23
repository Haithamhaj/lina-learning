# LR-A01 Governing Decision Correction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the repository's governing documents with the Product Owner-approved Option A architecture without changing runtime code, database schema, tests, or REC-25 execution.

**Architecture:** This is a documentation/governance correction only. `docs/LEARNING_PRODUCT_ROADMAP.md` is the approved product-evolution reference for the 2026-08-23 decisions. Existing historical implementation records remain intact; only active governing statements that contradict the approved direction are corrected or explicitly marked superseded.

**Tech Stack:** Markdown, existing HTML/SVG system map, repository-native governance files.

**Spec:** `docs/LEARNING_PRODUCT_ROADMAP.md` — especially Sections 3, 4, 6, 7, 9 Track A, 12, 13, and 15.

## Global Constraints

- Documentation-only change: **no application code, migrations, prompts, tests, DB operations, jobs, or runtime changes**.
- Do not start REC-25.
- Do not implement Trusted Reference Builder, Vision, Voice, Science, Learning Canvas, Artifact Engine, or Parent Dashboard expansion.
- Preserve historical task completion records and implementation evidence; do not rewrite history to pretend the old architecture never existed.
- Mark obsolete product assumptions as superseded rather than deleting historical evidence where audit value remains.
- Keep the existing Hybrid Retrieval direction: Docling structural representation + PostgreSQL lexical + pgvector + deterministic fusion + provenance + context budgets.
- Semantic curriculum extraction remains available but becomes optional enrichment, not a Tutor/RAG availability prerequisite.
- `Current School Focus` as learning authority is removed; relevant recent conversational/topic context remains allowed.
- The Tutor remains available with zero books, zero indexed content, semantic failure, or no retrieval match.
- Concept identity for Learning Intelligence primarily comes from the learning interaction; no new concept subsystem is introduced.
- Trusted educational web references are an approved future Learning Source and Grade 5 Math pilot, but **not implemented in LR-A01**.
- Student-captured page behavior remains approved future Vision work and frozen.

---

## File Map

### Modify

- `docs/PROJECT_REFERENCE.md` — durable product principles and architecture truth.
- `docs/IMPLEMENTATION_PLAN.md` — execution architecture and dependency/gate correction.
- `TASKS.md` — promote Track A into the executable queue and block REC-25 until Track A acceptance.
- `project-state/PROJECT_STATE.md` — current operational snapshot only.
- `project-state/SYSTEM_MAP.html` — visual map of the corrected critical path and future source types.

### Verify / normally no content change required

- `AGENTS.md` — already points to `docs/LEARNING_PRODUCT_ROADMAP.md` and contains the temporary supersession rule. After reconciliation, remove or simplify only the temporary wording if the five governing files are fully consistent.
- `docs/LEARNING_PRODUCT_ROADMAP.md` — approved spec; do not materially redesign it during LR-A01.
- `docs/LEARNING_INTELLIGENCE_SPEC.md` — do not rewrite the intelligence architecture in this task. Any obsolete `current_school_focus` state is implementation/deprecation work under LR-A08, not a reason to redesign the spec here unless a narrow cross-reference is required.

---

### Task 1: Correct `PROJECT_REFERENCE.md`

**Files:**
- Modify: `docs/PROJECT_REFERENCE.md`

**Produces:** Durable product truth consistent with Option A and the Roadmap.

- [ ] **Step 1: Add the Roadmap to the document relationship/authority map**

State that `docs/LEARNING_PRODUCT_ROADMAP.md` owns approved product-evolution sequencing, future capability tracks, dependencies, and validation gates; `PROJECT_REFERENCE.md` continues to own durable product principles.

- [ ] **Step 2: Correct the product definition and in-scope wording**

Replace any wording that implies school books/current school position are required to determine what Lina may learn.

The durable rule must be:

```text
The current Student question drives the interaction.
Books, school materials, trusted references, and later captured pages are optional grounding sources.
The Tutor remains usable without them.
```

Remove `Current school focus detection and correction` as an active product capability/authority.

- [ ] **Step 3: Replace the School-Led Main Path principle**

Remove/supersede statements equivalent to:

```text
The school/book context defines the main path.
```

Replace with:

```text
Question-Driven Learning, Reference-Grounded When Useful

Lina's current question/learning need is authoritative.
School/book/reference context can improve terminology, scope alignment, examples, and expected depth, but does not determine what Lina is allowed or required to study now.
The Tutor may teach prerequisites or related ideas when useful and return to the current question naturally.
```

- [ ] **Step 4: Correct Content and Book Understanding**

Keep original-source preservation and Docling structural processing.

Change Educational Semantic Layer wording to explicitly state that it is optional/rebuildable enrichment and not required for Tutor availability or basic retrieval.

Replace the mandatory pipeline with:

```text
Learning Source
    ↓
Preserve original + provenance
    ↓
Structural extraction / normalization
    ↓
Retrieval-ready representation
    ↓
Hybrid search/index

Optional:
Structural representation
    ↓
Educational semantic enrichment
```

- [ ] **Step 5: Correct school-plan behavior**

School plans/tables are supplementary references that may reveal available subjects/topics/materials. They do not determine a current learning position or steer the Tutor.

- [ ] **Step 6: Add the multi-source Learning Source principle**

Represent future source types without implementing them:

```text
Current captured page/image — highest context for the current turn
Exact uploaded school material/book — strongest persistent curriculum anchor
Historical student-captured pages — learning-history references
Trusted aligned web references
Trusted general educational references
Model general knowledge — always available
```

Clarify that this is **grounding authority**, not teaching-method authority.

- [ ] **Step 7: Add Trusted Educational Reference principle**

Record the approved future behavior:

- Grade + Subject required for setup.
- Country/School/Curriculum/Book/Publisher/language used when known.
- Parent is not required to find the exact book.
- System may automatically discover trusted references.
- Trust order: official/publisher → established educational institutions → reputable academic/school sources.
- Exclude anonymous forums, low-trust blogs, SEO junk, unclear-source content.
- No per-source Parent approval is required for trusted sources.
- Alignment classes: `EXACT_CURRICULUM`, `ALIGNED_CURRICULUM`, `GENERAL_EDUCATION`.
- Trusted references help terminology, alignment, alternative explanations/examples, and representational diversity.
- Their absence never blocks Tutor.

- [ ] **Step 8: Correct Retrieval Architecture**

Replace curriculum-position-first narrowing with question-driven retrieval.

Keep:

- Grade/Subject scoping where known,
- lexical + vector retrieval,
- structural/hierarchical boundaries,
- deterministic fusion,
- context budgets,
- provenance.

Semantic type/unit/lesson/concept metadata may improve ranking/navigation when available but must not be core candidate eligibility requirements.

- [ ] **Step 9: Correct Tutor Runtime**

The normal path should read conceptually:

```text
Student question
→ SafetyDecision
→ optional question-driven grounding
→ relevant Learner Intelligence
→ one primary Tutor model call
→ response + Candidate Event metadata
```

No book/content readiness gate belongs in the product principle.

Recent conversational/topic context may help low-information continuations (`continue`, `again`, `I don't understand`) but current-question relevance outranks recency/history.

- [ ] **Step 10: Correct Concept ownership**

Record that `concept_ref`/concept identity is primarily derived from the interaction using question, conversation, image when available, retrieved references, and model understanding. Curriculum preclassification is not required for Learning Intelligence.

- [ ] **Step 11: Correct Parent-facing current-focus wording**

Remove Parent responsibilities/views that imply manually correcting Lina's school position/current focus. Preserve Parent content/reference controls and evidence inspection.

- [ ] **Step 12: Update Approved Decisions and Validation Gate**

Mark as superseded/rejected where applicable:

- school-led main path,
- current-school-focus authority,
- real-book prerequisite for Tutor,
- mandatory semantic-before-index,
- curriculum-derived Concept prerequisite.

Add approved decisions:

- Tutor always available,
- question-driven optional RAG,
- semantic enrichment optional,
- multi-source Learning Source model,
- interaction-derived concept,
- trusted reference pilot/future source,
- relevance-first recent context.

The first meaningful validation loop must permit:

```text
no book → Tutor still works
content available → optional grounding improves the answer
```

Do not require a real book as permission to enter the Tutor.

- [ ] **Step 13: Self-check**

Search the file for these terms and inspect every remaining occurrence:

```text
Current school focus
School-Led
school-led
real Grade 5 Math book
Educational semantic extraction
current topic
main path
```

Any remaining occurrence must either be compatible with Option A or clearly historical/superseded.

---

### Task 2: Correct `IMPLEMENTATION_PLAN.md`

**Files:**
- Modify: `docs/IMPLEMENTATION_PLAN.md`

**Consumes:** Corrected product principles from Task 1.

**Produces:** Execution architecture where Tutor availability and structural RAG do not depend on semantic enrichment.

- [ ] **Step 1: Add Roadmap to the authority order**

Insert `docs/LEARNING_PRODUCT_ROADMAP.md` between product truth and detailed execution where appropriate. State that Roadmap items are not executable until promoted into `TASKS.md`.

- [ ] **Step 2: Correct the first implementation objective**

Do not define the vertical slice as beginning with mandatory real-book upload.

Use:

```text
Student can enter Tutor with zero content
→ Tutor answers safely from model knowledge
→ if structural/indexed sources exist, retrieval grounds the answer
→ interaction produces Candidate/Evidence/Intelligence
→ later Tutor uses relevant intelligence
```

Real-book and trusted-reference grounding are validation inputs, not Tutor prerequisites.

- [ ] **Step 3: Correct Content Processing Architecture**

Make the critical content path:

```text
Source
→ preserve original
→ structural processing
→ retrieval blocks/index
→ retrieval-ready

optional parallel/downstream enrichment:
→ educational semantics
```

Semantic enrichment may feed metadata/navigation/rebuildable enrichment but is not required for basic index completion.

- [ ] **Step 4: Correct Retrieval Architecture**

Question-driven retrieval is primary. Remove `Current School Focus` as a required narrowing stage.

Keep Grade/Subject, structural boundaries, lexical/vector retrieval, deterministic fusion, provenance, and budgets.

Recent conversational topic context is advisory only.

- [ ] **Step 5: Correct Tutor Runtime Architecture**

The context builder accepts empty retrieval. Tutor availability is independent of content status.

- [ ] **Step 6: Correct cost/task language**

`curriculum_semantics` remains an optional batch/occasional route. Do not imply it is required to unlock the Tutor.

Trusted web discovery remains future Roadmap Track B; do not add implementation steps to Track A.

- [ ] **Step 7: Correct Phase/Gate statements without erasing history**

Historical Phase 1/2 work can remain documented, but active gate language must be corrected so a real book/semantic READY state is no longer permission for Tutor operation.

Where old Phase 1/2 exit gates are retained for historical context, explicitly mark the old dependency as superseded by Roadmap Track A.

- [ ] **Step 8: Correct First Build Order / Definition of Done**

The active order after the 2026-08-23 correction must prioritize:

```text
Track A governance correction
→ zero-book Tutor availability
→ structural-first indexing
→ optional semantic behavior
→ acceptance suite
→ Real Lina calibration
→ Grade 5 Math Trusted Reference Pilot
```

Do not reorder frozen future capabilities into Track A.

- [ ] **Step 9: Self-check**

Search and inspect every occurrence of:

```text
Current School Focus
current focus
semantic extraction
real Grade 5 Math book
Phase 1 Exit
book reaches READY
```

---

### Task 3: Promote Track A in `TASKS.md`

**Files:**
- Modify: `TASKS.md`

**Produces:** Executable queue aligned with the Roadmap.

- [ ] **Step 1: Preserve historical TASK-001…REC records**

Do not rewrite existing DONE evidence as though it never happened.

- [ ] **Step 2: Mark obsolete active gate wording as superseded**

In the relevant Phase 1/Phase 2 notes, state that mandatory book + semantic readiness as a Tutor permission gate is superseded by Option A / Roadmap Track A.

- [ ] **Step 3: Add a new clearly named section before REC-25**

Use a section such as:

```markdown
# Roadmap Track A — Core Simplification (2026-08-23)
```

Add these entries with Roadmap IDs:

```text
LR-A01 Governing decision correction
LR-A02 Tutor always available
LR-A03 Decouple index identity from mandatory semantics
LR-A04 Structural-first index builder
LR-A05 Semantic retrieval behavior advisory
LR-A06 Source processing lifecycle
LR-A07 Parent content-status decoupling
LR-A08 Deprecate school-focus authority residue
LR-A09 Simplification acceptance suite
LR-A10 Real Lina calibration resumes
```

- [ ] **Step 4: Set statuses correctly**

At completion of this governance-only task:

- `LR-A01` / its repository TASK/REC wrapper = `DONE` only after all LR-A01 document verification passes.
- `LR-A02` = `READY`.
- `LR-A03` onward = `BLOCKED` by their explicit dependencies unless a tightly related approved task group is intentionally promoted later.
- REC-25 = `BLOCKED` or explicitly waiting on `LR-A09`; it must not remain immediately executable.

Use the repository's existing TASK/REC naming convention for execution IDs, while retaining `Roadmap: LR-Axx` inside each entry.

- [ ] **Step 5: Add Track B only as a reference, not READY work**

Do not expand `TASKS.md` with all future Roadmap items. Add at most one short note pointing to Roadmap Track B after Track A/Real Lina calibration.

---

### Task 4: Refresh `PROJECT_STATE.md`

**Files:**
- Modify: `project-state/PROJECT_STATE.md`

**Produces:** Short current-state snapshot; not a changelog.

- [ ] **Step 1: Current goal**

Set the current goal to the Track A architecture simplification, with LR-A02 next after LR-A01.

- [ ] **Step 2: Current reality**

Keep only high-value facts:

- Option A approved.
- Roadmap exists at `docs/LEARNING_PRODUCT_ROADMAP.md`.
- Existing Tutor runtime can tolerate empty retrieval, but Student API currently blocks it with content readiness.
- Existing index builder/persistence still requires semantic run and must be decoupled.
- Hybrid retrieval, Evidence/State/Patterns/Card, Safety, Model Gateway, and provenance remain protected/reusable.
- Prompt-v5/Eureka uncommitted work is parked optional semantic-enrichment work.
- REC-25 has not started and is waiting for Track A acceptance.

- [ ] **Step 3: Active decisions**

Record concise Option A principles:

- Tutor always available.
- RAG optional/question-driven.
- semantics optional enrichment.
- concept from interaction.
- no Current School Focus authority.
- relevant recent context remains allowed.
- Trusted Reference Pack is approved future Track B, not current implementation.

- [ ] **Step 4: Protected/frozen areas**

Preserve current protected core and frozen future systems.

- [ ] **Step 5: Next recommended action**

Set to `LR-A02 — Tutor always available`, after LR-A01 verification.

- [ ] **Step 6: Critical references**

Include `docs/LEARNING_PRODUCT_ROADMAP.md`.

---

### Task 5: Correct `SYSTEM_MAP.html`

**Files:**
- Modify: `project-state/SYSTEM_MAP.html`

**Produces:** Visual map reflecting the approved critical path.

- [ ] **Step 1: Update top-level target text**

Remove claims that the current target requires a real Grade 5 book before Tutor use.

- [ ] **Step 2: Update Tutor flow**

Visualize:

```text
Student question
→ Safety
→ Optional Grounding + Relevant Learner Intelligence
→ One Tutor Call
→ Candidate
→ Evidence
→ State/Patterns
→ later personalization
```

- [ ] **Step 3: Update Content/RAG lane**

Visualize:

```text
Learning Source
→ preserve original
→ Docling / structural normalization
→ retrieval-ready structural index
→ lexical + pgvector + fusion + provenance

Optional semantic enrichment
```

- [ ] **Step 4: Show future sources without presenting them as active**

Include visually muted/deferred source boxes for:

- Trusted Educational References (Roadmap Track B)
- Student-Captured Pages (Roadmap Track C / Vision frozen)

- [ ] **Step 5: Remove school-focus authority**

Do not show Parent correction of school focus as a control path. Recent conversational context may appear only as an advisory Tutor-context input.

- [ ] **Step 6: Update source-of-truth map**

Add `docs/LEARNING_PRODUCT_ROADMAP.md`.

---

### Task 6: Reconcile `AGENTS.md` temporary supersession wording

**Files:**
- Inspect/modify if necessary: `AGENTS.md`

**Produces:** Clean agent governance after LR-A01.

- [ ] **Step 1: Confirm Roadmap is still in Governing References**

Keep the Roadmap reference and the rule that Roadmap items require promotion to `TASKS.md`.

- [ ] **Step 2: Simplify temporary conflict handling if reconciliation is complete**

The temporary wording that says the Roadmap overrides older conflicting documents pending LR-A01 can be replaced with a simpler normal conflict rule once `PROJECT_REFERENCE`, `IMPLEMENTATION_PLAN`, `TASKS`, `PROJECT_STATE`, and `SYSTEM_MAP` are aligned.

Do not weaken the rule that unlisted document conflicts must be surfaced.

---

### Task 7: Documentation Verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Confirm no runtime/code scope leaked in**

Run:

```bash
git diff --name-only <LR-A01-base>..HEAD
```

Expected changed files are limited to documentation/governance files:

```text
AGENTS.md (only if temporary wording was simplified)
docs/PROJECT_REFERENCE.md
docs/IMPLEMENTATION_PLAN.md
docs/LEARNING_PRODUCT_ROADMAP.md (normally unchanged)
docs/superpowers/plans/2026-08-23-lr-a01-governing-decision-correction.md
TASKS.md
project-state/PROJECT_STATE.md
project-state/SYSTEM_MAP.html
```

No `apps/`, `services/`, `workers/`, `migrations/`, `tests/`, or prompt implementation files may change.

- [ ] **Step 2: Search for known contradictions**

Run repository searches across the governing docs for:

```text
Current School Focus
current school focus
School-Led Main Path
school-led main path
book reaches READY
real Grade 5 Math book
semantic extraction
TASK-013 — Structural content blocks and indexing
```

For every hit, classify it as:

- corrected active rule,
- historical implementation record,
- optional enrichment statement,
- or remaining contradiction.

There must be **no remaining active contradiction**.

- [ ] **Step 3: Verify Roadmap discoverability**

Confirm all of the following:

- `AGENTS.md` references `docs/LEARNING_PRODUCT_ROADMAP.md`.
- `PROJECT_REFERENCE.md` relationship map references it.
- `IMPLEMENTATION_PLAN.md` authority/execution map references it.
- `PROJECT_STATE.md` critical references includes it.
- `SYSTEM_MAP.html` source-of-truth map includes it.
- `TASKS.md` Track A items include Roadmap IDs.

- [ ] **Step 4: Verify queue state**

Confirm:

```text
LR-A01 governance reconciliation = DONE
LR-A02 Tutor always available = READY
REC-25 = not executable until LR-A09 / Track A acceptance
Track B = future, not READY
```

- [ ] **Step 5: Do not run destructive PostgreSQL tests**

LR-A01 is documentation-only. No DB/test suite is necessary to prove documentation consistency, and no development DB operation is authorized.

- [ ] **Step 6: Review the final diff manually**

Verify the diff does not silently change:

- child-safety semantics,
- Evidence/State/Pattern/Card meaning,
- Model Gateway rules,
- one-primary-Tutor-call rule,
- raw-source preservation,
- frozen Vision/Voice/Science/Artifact scopes.

- [ ] **Step 7: Commit only after verification**

Use one documentation commit, for example:

```bash
git add AGENTS.md docs/PROJECT_REFERENCE.md docs/IMPLEMENTATION_PLAN.md TASKS.md project-state/PROJECT_STATE.md project-state/SYSTEM_MAP.html docs/superpowers/plans/2026-08-23-lr-a01-governing-decision-correction.md
git commit -m "docs: reconcile learning architecture with Option A"
```

If `AGENTS.md` did not require a final change, omit it from the add list.

---

## LR-A01 Completion Gate

LR-A01 is complete only when all of the following are true:

1. The Roadmap is discoverable from the repository's main governance map.
2. No active governing document says a book or semantic extraction is required for Tutor availability.
3. No active governing document treats Current School Focus as learning authority.
4. Content architecture says structural-first retrieval; semantics are optional enrichment.
5. Retrieval architecture is question-driven and keeps the existing hybrid/provenance direction.
6. Learning Intelligence concept identity is not dependent on curriculum semantic preprocessing.
7. Trusted Educational References are recorded as an approved future Learning Source/pilot, not implemented in Track A.
8. `TASKS.md` has Track A promoted with LR-A02 as the next READY task.
9. REC-25 is waiting for Track A acceptance.
10. No runtime code, DB schema, prompts, or tests changed in LR-A01.
