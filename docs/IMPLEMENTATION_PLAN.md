# Lina Personal Learning System

## IMPLEMENTATION_PLAN.md

**Status:** Approved implementation direction  
**Authority:** Governing execution map for architecture, sequencing, dependencies, decision gates, and implementation boundaries  
**Audience:** Product owner, ChatGPT, Codex, AI agents, developers, reviewers  
**Governing references:** `PROJECT_REFERENCE.md`, `LEARNING_PRODUCT_ROADMAP.md`, `LEARNING_INTELLIGENCE_SPEC.md`
**Required supporting policy before student-facing release:** `CHILD_SAFETY_POLICY.md`  
**Execution queue:** `TASKS.md`  
**Current operational state:** `project-state/PROJECT_STATE.md`

---

# 1. Purpose of This Plan

This document defines **how the approved Lina Personal Learning System should be implemented**, without turning the implementation plan itself into a giant task list.

It exists to provide:

- architectural direction,
- module boundaries,
- build sequence,
- dependencies,
- decision gates,
- verification expectations,
- what must be built first,
- what must explicitly be delayed,
- and the rules Codex/AI agents must preserve while implementing.

This document does **not** replace `TASKS.md`. `LEARNING_PRODUCT_ROADMAP.md`
records approved product-evolution tracks, but Roadmap items are not executable
until promoted into `TASKS.md`.

> **`IMPLEMENTATION_PLAN.md` defines the execution architecture. `TASKS.md` defines the actual work queue.**

Codex should normally execute one scoped task or one tightly related task group at a time, verify it, update project state, and then continue.

---

# 2. Implementation Objective

The first objective is not to build the entire product vision.

The first objective is to prove one real end-to-end learning loop with Lina.
Tutor availability does not depend on a book, completed processing, semantic
enrichment, or a retrieval match:

```text
Student can enter Tutor with zero content
        ↓
Tutor answers safely from model knowledge
        ↓
If structural/indexed sources exist, retrieval grounds the answer
        ↓
Interaction produces Candidate Events, Evidence, and Intelligence
        ↓
Meaningful learning events are captured
        ↓
Session evidence is produced
        ↓
Current state / patterns / intelligence are updated
        ↓
Next session uses relevant learner intelligence
```

This vertical slice must work before the project expands into its full feature set.

The implementation should optimize for:

1. correctness of the learning loop,
2. traceability,
3. modifiability,
4. real usability by Lina,
5. cost visibility,
6. extensibility without premature platform complexity.

---

# 3. Governing Sources of Truth

Implementation must follow this authority order:

## 3.1 Product and Architecture Truth

`docs/PROJECT_REFERENCE.md`

Controls:

- product purpose,
- product boundaries,
- roles,
- learning philosophy,
- tutor principles,
- Grade behavior,
- content/RAG principles,
- multimodal behavior,
- interactive artifacts,
- safety and parent-learning-boundary principles,
- implementation invariants.

## 3.2 Product-Evolution Roadmap

`docs/LEARNING_PRODUCT_ROADMAP.md`

Controls approved product-evolution sequencing, future capability tracks,
dependencies, and validation gates. It does not authorize implementation until
the relevant item is promoted to `TASKS.md`.

## 3.3 Learning Intelligence Truth

`docs/LEARNING_INTELLIGENCE_SPEC.md`

Controls:

- meaningful events,
- evidence rubrics,
- current state,
- pattern identity,
- scope,
- lifecycle,
- deterministic weighting,
- session consolidation,
- Intelligence Card,
- decision views,
- reprocessing,
- human audit.

## 3.4 Child Safety Truth

`docs/CHILD_SAFETY_POLICY.md`

Controls:

- non-overridable child-safety baseline,
- age-appropriate response behavior,
- enforcement rules,
- parent-configurable topic-boundary semantics.

This file must exist before Lina-facing production use.

## 3.5 Execution Direction

`docs/IMPLEMENTATION_PLAN.md`

This file.

## 3.6 Current Operational Reality

`project-state/PROJECT_STATE.md`

Short snapshot of:

- current goal,
- current reality,
- active decisions,
- protected areas,
- active risks,
- next recommended action.

## 3.6 Actual Work Queue

`TASKS.md`

This is what Codex should execute.

---

# 4. Codex Execution Model

The project should be implemented through a repository-native harness rather than a single giant prompt.

The intended relationship is:

```text
AGENTS.md
   ↓
   ├── PROJECT_REFERENCE.md
   ├── LEARNING_INTELLIGENCE_SPEC.md
   ├── CHILD_SAFETY_POLICY.md
   ├── IMPLEMENTATION_PLAN.md
   ├── PROJECT_STATE.md
   └── TASKS.md
```

## 4.1 `AGENTS.md` Role

`AGENTS.md` should remain compact.

It should act as:

- a map to governing documents,
- a statement of protected architectural boundaries,
- verification rules,
- change-approval rules,
- project-state update rules.

It should **not** duplicate the product documentation.

## 4.2 Task Size

Tasks should normally be small enough to:

- have one primary outcome,
- have explicit verification,
- avoid editing unrelated modules,
- be reviewed independently.

Avoid instructions such as:

> "Build the Lina learning system."

Prefer instructions such as:

> "Implement the Docling conversion adapter for uploaded Grade books, persist the source and processing metadata, and add contract tests for the normalized output. Do not implement curriculum semantic extraction yet."

## 4.3 Task Completion Rule

A task is not complete when code has merely been written.

A task is complete only when:

1. expected output exists,
2. required tests/checks pass,
3. relevant behavior is verified,
4. no protected invariant has been violated,
5. `TASKS.md` and `PROJECT_STATE.md` are updated when applicable.

---

# 5. Architecture Strategy

## 5.1 Architecture Style

Use a **Modular Monolith**.

The project should be internally modular but operationally simple.

Do not create microservices merely because domains are separated logically.

```text
┌───────────────────────────┐
│        Next.js Web        │
│   Student + Parent/Admin  │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│      FastAPI Backend      │
│                           │
│ Tutor                     │
│ Intelligence              │
│ Content                   │
│ Retrieval                 │
│ Learning Artifacts        │
│ Model Gateway             │
│ Grade                     │
│ Platform                  │
└─────────────┬─────────────┘
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
 PostgreSQL  Storage  Worker
 + pgvector
```

## 5.2 Simplicity Rule

Prefer the simpler implementation unless additional abstraction clearly improves:

- maintainability,
- recoverability,
- testing,
- extensibility,
- or long-term data durability.

Do not introduce complexity solely for architectural elegance.

---

# 6. Initial Technology Stack

## Frontend

- Next.js
- TypeScript
- responsive web application
- SSE client for tutor streaming
- child-friendly component system
- parent/admin application shell

## Backend

- Python
- FastAPI
- typed application/service boundaries

## Database

- PostgreSQL
- JSONB for evolving evidence/metadata structures
- pgvector for vector retrieval

## File/Object Storage

- S3-compatible object storage
- original books/documents
- original student images/drawings
- extracted figures
- generated/annotated learning artifacts

## Document Understanding

- Docling as the baseline structural document-processing layer

## Background Processing

Initial implementation:

```text
jobs table
+
worker process
```

Do not introduce Redis/Celery until actual workload demonstrates the need.

## Streaming

- Server-Sent Events (SSE)

## Interactive Learning Stack

Initial artifact renderers/utilities:

- React/SVG
- Motion
- JSXGraph
- React Konva
- MathLive

Optional later when justified by real use:

- Rough.js
- Recharts
- p5.js
- specialized renderers

---

# 7. Domain Boundaries

The implementation should expose clear domain boundaries without turning each domain into a separate deployment unit.

## 7.1 Tutor Domain

Owns:

- tutor runtime,
- consumption of compact Student Core Context without owning or inferring the profile,
- teaching mode resolution,
- Multimodal Turn context,
- session-local Learning Thread / Segment resolution,
- optional Grade-scoped Durable Conversation Topic resolution,
- context assembly orchestration,
- adaptive teaching strategy selection,
- one primary tutor-model call,
- tutor response streaming,
- hidden Candidate Event metadata,
- open learning loops.

Must not:

- directly create stable learner patterns,
- directly overwrite learner intelligence,
- directly manage provider-specific AI SDK calls,
- own document parsing,
- own deterministic pattern weighting.

## 7.2 Learning Intelligence Domain

Owns:

- Candidate Event consolidation,
- validated learning events,
- evidence,
- current learning state,
- learner patterns,
- deterministic weighting/lifecycle,
- session intelligence deltas,
- Intelligence Card,
- derived decision views,
- historical reprocessing.

Must follow `LEARNING_INTELLIGENCE_SPEC.md`.

## 7.3 Content Domain

Owns:

- original uploaded educational documents,
- document versions,
- Docling processing,
- normalized document representation,
- educational semantic extraction,
- Grade/subject/book metadata,
- curriculum nodes,
- figures/formulas,
- reprocessing state.

Must not own tutor behavior.

## 7.4 Retrieval Domain

Owns:

- metadata filtering,
- lexical retrieval,
- vector retrieval,
- hierarchical ranking,
- retrieval context budgets,
- provenance/source references.

Content answers:

> What educational material do we have?

Retrieval answers:

> Which educational material is relevant now?

## 7.5 Learning Artifacts Domain

Owns:

- typed Artifact Specifications,
- Artifact Registry,
- renderer selection,
- reusable visual/interactive artifacts,
- inline rendering contract,
- expanded Learning Canvas contract,
- custom sandboxed HTML/SVG fallback,
- meaningful artifact-interaction events.

## 7.6 Model Gateway Domain

Owns:

- task-based AI execution,
- provider/model routing,
- fallback,
- retry/timeout boundaries,
- structured output handling,
- AI usage logging,
- cost estimation.

Application domains request a **task**, not a provider.

Example:

```text
execute(task="tutor", ...)
execute(task="session_evidence", ...)
execute(task="vision_student_work", ...)
```

## 7.7 Grade Domain

Owns:

- active Grade period,
- Grade/book association,
- Parent/Admin activation of a new Grade,
- creation of the compact transition card,
- archival status of the previous Grade.

It must remain simple.

There is no automatic Grade-transition inference requirement.

## 7.8 Platform Domain

Owns shared infrastructure:

- authentication,
- roles/authorization,
- Parent ↔ Student ownership/authorization and durable Student Core Profile facts,
- settings,
- parent topic boundaries,
- files,
- jobs,
- AI usage/cost ledger,
- observability,
- health/status.

---

# 8. Extensibility Architecture

Extensibility is a first-class requirement.

The code must support future additions without requiring a rewrite of the Tutor or Intelligence core.

## 8.1 Adding a Subject

Initial subjects:

- Math
- Science

Future subjects should be added through subject-level configuration/adapters for:

- subject teaching guidance,
- subject-specific evidence dimensions if needed,
- artifact availability,
- retrieval defaults,
- terminology/prompt fragments.

Avoid subject conditionals scattered throughout the codebase.

Do not build a generic plugin marketplace/framework in the MVP.

## 8.2 Adding an Artifact Type

A new artifact should primarily require:

1. a typed Artifact Specification,
2. a registry entry,
3. a renderer,
4. interaction-event mapping,
5. tests.

The core Tutor interface should not need redesign.

## 8.3 Adding an AI Provider

A provider implementation should satisfy Model Gateway interfaces without changing Tutor, Content, Intelligence, or Vision business logic.

## 8.4 Adding an Evidence Dimension

A new dimension must be introduced through a versioned Learning Intelligence specification/schema change and must not silently reinterpret historical evidence.

## 8.5 Adding a Document Processor

Docling is the baseline, but the Content domain should wrap it behind a document-processing adapter so another processor can be benchmarked or added later.

---

# 9. Repository Shape

Recommended initial repository layout:

```text
lina-learning/
│
├── AGENTS.md
├── TASKS.md
│
├── apps/
│   ├── web/
│   └── api/
│
├── services/
│   ├── tutor/
│   ├── intelligence/
│   ├── content/
│   ├── retrieval/
│   ├── learning_artifacts/
│   ├── model_gateway/
│   ├── grade/
│   └── platform/
│
├── packages/
│   ├── schemas/
│   └── shared/
│
├── prompts/
│   ├── tutor/
│   ├── intelligence/
│   ├── content/
│   └── safety/
│
├── workers/
├── tests/
│
├── docs/
│   ├── PROJECT_REFERENCE.md
│   ├── LEARNING_INTELLIGENCE_SPEC.md
│   ├── CHILD_SAFETY_POLICY.md
│   └── IMPLEMENTATION_PLAN.md
│
└── project-state/
    ├── PROJECT_STATE.md
    └── SYSTEM_MAP.html
```

This is a logical organization target, not a command to create unnecessary package boundaries.

---

# 10. API and Application-Layer Rule

API routes should remain thin.

Preferred flow:

```text
Route
  ↓
Application Service
  ↓
Domain Logic
  ↓
Repository / Provider Adapter
```

Do not implement AI calls, pattern calculations, content parsing, and direct SQL in one route handler.

At the same time, avoid enterprise-style abstraction for abstraction's sake.

---

# 11. Core Data Architecture

The exact SQL schema is an implementation task, but the initial data model should preserve these conceptual groups.

## 11.1 Identity / Grade

- users
- students
- parent/student relationship
- Grade periods

Parent-owned Student Core Profile facts are a future, separately authorized
implementation seam. Grade continues to own active Grade / GradePeriod
lifecycle; Tutor consumes only compact Student Core Context.

## 11.2 Content

- documents
- document versions / processing runs
- curriculum nodes
- content blocks
- figures/assets
- embeddings

`curriculum_nodes` may initially represent Unit/Lesson/Concept hierarchy in one extensible structure if that is simpler than many rigid tables.

## 11.3 Interaction

- sessions
- messages/raw interactions and original assets
- session-local Learning Threads / Segments
- optional Grade-scoped Durable Conversation Topics

## 11.4 Learning Intelligence

- candidate-event source metadata if persisted
- learning events
- evidence
- current states
- learner patterns
- evidence/pattern links
- session intelligence deltas
- intelligence snapshots

## 11.5 Grade Transition

- compact Grade transition cards

## 11.6 AI / Operations

- model routes
- AI executions
- processing runs
- jobs

## 11.7 JSONB Use

Use JSONB where schemas are intentionally evolving, particularly:

- evidence dimension payloads,
- event metadata,
- AI usage metadata,
- processing metadata,
- artifact parameters.

Normalize later only when query requirements justify it.

---

# 12. Content Processing Architecture

## 12.1 Source Preservation

Every uploaded book/document must preserve the original source.

Derived artifacts are replaceable.

## 12.2 Learning Source Processing Pipeline

```text
Learning Source
  ↓
Preserve Original + Provenance
  ↓
Create Processing Run
  ↓
Docling Structural Processing
  ↓
Persist Versioned DoclingDocument / normalized representation
  ↓
Structural retrieval blocks/index
  ↓
Retrieval-ready

Optional parallel/downstream enrichment:
Structural representation
  ↓
Educational semantics
```

## 12.3 Docling Responsibility

Docling provides baseline document understanding:

- layout,
- reading order,
- text,
- tables,
- pictures,
- formulas where supported,
- hierarchy,
- provenance.

Docling does **not** own educational semantics.

## 12.4 Educational Semantic Extraction — Optional Enrichment

The project layer maps structured document content into educational semantics such as:

- Grade,
- subject,
- unit,
- lesson,
- topic/concept,
- learning objective,
- example,
- exercise,
- vocabulary,
- prerequisite hint,
- expected school scope.

AI should reason over the structured representation whenever possible rather
than repeatedly processing raw PDF pages. Semantic enrichment may improve
metadata, navigation, and rebuildable analysis, but it is not required for
basic index completion or Tutor availability.

## 12.5 Structural Chunking

Use document structure first.

Docling hierarchical chunking is the baseline.

Use hybrid/token-aware refinement only when structural units exceed practical retrieval/embedding limits.

Do not use blind fixed-size token chunking as the primary strategy.

## 12.6 Figures and Formula Handling

Retain:

- figure source,
- page/provenance,
- caption/description when available,
- curriculum/lesson relationships.

Use expensive visual enrichment selectively, not automatically for every image.

## 12.7 Content Validation

Minimum automated validation should cover:

- schema validity,
- page coverage,
- unit/lesson consistency,
- source-reference validity,
- catastrophic duplication,
- large missing ranges,
- figure linkage where relevant.

---

# 13. Retrieval Architecture

## 13.1 Retrieval Principle

Retrieval is optional, question-driven grounding; it is contextual, not global
by default.

Preferred narrowing sequence:

```text
Current Student question
   ↓
Grade / Subject when known
   ↓
Structural / metadata candidates
   ↓
Lexical + Vector retrieval
   ↓
Context ranking
```

## 13.2 Recent Conversational Topic Context

Recent conversational/topic context is advisory only and may help low-
information follow-ups. The current question remains authoritative; school
plans and curriculum position do not control retrieval or teaching. Semantic
unit/lesson/concept/type metadata may improve ranking or navigation when
available, but is not core candidate eligibility.

The Tutor context builder uses the current Multimodal Turn, immediate bridge,
and bounded current Learning Thread / Segment context first. Raw Exchange
recall is limited to the Current Segment: an earlier Segment never enters
normal context merely because it shares a Durable Conversation Topic. Learner
Intelligence/Open Loops, question-driven RAG, and the effective Safety decision
are separate inputs. Do not automatically load all Session history, all topic
history, a Topic Registry, prior-session transcripts, or a historical archive.

## 13.3 Retrieval Context Budget

The runtime must enforce a configurable maximum amount of retrieved content.

Prefer a few highly relevant, provenance-rich blocks over broad context.

## 13.4 Retrieval Verification

Before calling Math RAG ready, maintain a small real-book retrieval evaluation set containing:

- question,
- expected unit,
- expected lesson,
- expected page/content region,
- expected concept.

---

# 14. Tutor Runtime Architecture

## 14.1 Primary Path

```text
Student Input
     ↓
Safety & Learning Boundary Policy Engine
     ↓
Effective SafetyDecision
     ↓
Compact Student Core Context (future TASK-027A)
     ↓
Session / Segment Resolver
     ↓
Hybrid Segment Context Assembler
├── Current Multimodal Turn
├── Full Immediate Exchange
├── Structured Segment State
└── Relevant Current-Segment Raw Exchanges
     ↓
Separate question-driven RAG / Learner Intelligence / effective Safety inputs
     ↓
Final token / capacity guardrail
     ↓
ONE primary Tutor model call
     ↓
Stream Student Response
     +
Hidden Candidate Event Metadata
```

Student Core Context is a compact Parent-authoritative future input, distinct
from conversation context and Evidence-derived Learner Intelligence. TASK-027A
will supply authoritative identity, derived age, and active Grade; this plan
does not authorize schema, service, or runtime work now.

## 14.2 Tutor Identity vs Teaching Strategy and Method

Tutor identity is stable.

Teaching strategy adapts.

Do not implement a self-rewriting persona system.

TeachingMode governs the kind of learning interaction. TeachingStrategy governs support/intervention flow. TeachingMethod is a separate pedagogical representation. `prior_method_relation` is turn-level semantic routing/audit metadata for the relation to the immediately previous persisted Tutor method. The small internal, project-owned, versioned Teaching Method Registry owns canonical IDs, compact definitions, active/frozen status, and validation; it is not an MCP, agent, service, database table, giant mutable prompt, or natural-language keyword rules engine. With seven active methods, the primary call may receive all compact active definitions.

REC-35.2 owns the exact implementation. It should use existing structured/JSONB boundaries where practical, persist the selected TeachingMethod identity with the Tutor turn, and preserve enough bounded source lineage for later Session Evidence consolidation to connect method used → observable Student outcome → relevant concept/context. Evidence must never invent the method identity. No new database migration is authorized unless a blocker is separately discovered and approved.

## 14.3 Teaching Priority

The Tutor should reason in this practical priority order:

```text
What Lina demonstrates now
>
Current Learning State
>
Relevant recent patterns
>
Relevant stable patterns
>
Curriculum context
>
Generic teaching strategy
```

Historical patterns are priors, not commands.

The same priority informs the primary Tutor call's semantic decision: current demonstrated behavior outranks historical method information, and history must not remove demonstrated independence. Luna jointly determines Mode, Strategy, Method, and prior-method relation from the current message, relevant context/personalization, prior persisted method, and compact taxonomies in that one call. Runtime validates allowed values, null combinations, frozen status, source lineage, and cross-field consistency; it must not use keyword/phrase lists to infer meanings or make a separate classification call. If Luna returns `DID_NOT_HELP`, selecting the same prior method is inconsistent unless the relation is `EXPLICIT_REPEAT_REQUEST`. This immediate switching is not longitudinal method learning.

## 14.4 Tutor Call Count

The normal path should use one primary Tutor-model call per turn.

Do not add a critic/evaluator/profile-agent chain around every response.

The conceptual method path is:

```text
Current Student message + relevant context/personalization + previous persisted teaching decision + compact taxonomies / Method Registry
    ↓
ONE Luna semantic Tutor call
    ↓
Mode + Strategy + Method + prior relation + Tutor response
    ↓
Deterministic validation / persistence
    ↓
Persisted method lineage
    ↓
Later observable Student outcome
    ↓
Existing Candidate / Evidence pipeline
```

Turn-level decisions are not learner memory, and selection or use alone is not method-effectiveness Evidence. Historical method ranking is explicitly deferred to LR-D04B, after sufficient real Evidence and validation.

## 14.5 Candidate Events

The Tutor may return small hidden Candidate Event metadata in the same AI execution.

Candidate Events must not directly become stable learner intelligence.

`NAVIGATION` and pure self-report choices remain non-evidentiary merely because they were clicked. A bounded `ANSWER_CHOICE` can be an observable guided attempt and may emit only the approved bounded Candidate types; it never becomes independent success or mastery from the click alone. The Tutor prompt must not globally require `candidate_metadata = null` for every button selection.

---

## 14.6 Conversation Context v2 Direction

The Tutor Domain conceptually owns Multimodal Turn context, session-local
Segment/Learning Thread resolution, optional Grade-scoped Durable Conversation
Topic resolution, Hybrid Segment Context assembly, and the existing one primary
Tutor call. A Learning Thread is the contiguous session-local Segment
(`thread_id`), not a separate third entity. Returning to a topic after an
intervening Segment creates a new Segment; normal raw Exchange recall remains
limited to that Current Segment.

The approved Hybrid Segment Context shape is:

```text
Current Multimodal Turn
        ↓
Full Immediate Exchange
        ↓
Compact Structured Segment State
        ↓
0..N relevant complete raw Exchanges from the Current Segment
        ↓
Final token / capacity guardrail
        ↓
ONE primary Tutor call
```

Context selection is structural and relevance-first. Capacity/token budgets are
guardrails calibrated from real usage; they are not a positional character
slicing algorithm. Selected Immediate Exchange messages remain complete raw
source messages: previous Student Turn then previous Tutor Turn when both are
available, or the available Tutor Turn only. If selected conversational context
must be reduced, drop a lower-value complete selected Exchange rather than
slicing a critical raw message. Learner Intelligence/Open Loops, question-driven RAG, and the
effective Safety decision remain separate inputs. An earlier Segment is never
reopened or injected into normal context merely because it shares a topic.

Durable Conversation Topic is navigation metadata, not Learner Intelligence,
Evidence, curriculum semantics, a Safety category, or a learner-memory system.
It does not directly update personalization; that remains governed by the
Raw Interaction → Candidate → Event → Evidence → State/Pattern → Intelligence
Card path. Raw messages/assets remain source authority and all derived metadata
must remain rebuildable.

CTX-03A authorizes only durable session-local Segment identity and
LearningMessage-to-Segment lineage. CTX-03B owns same-primary-Luna Segment
relation plus compact Structured Segment State; CTX-03C owns recent raw Context
and lazy Segment-scoped semantic recall of older complete Exchanges; CTX-03D
owns the final capacity guardrail and observability; CTX-03E owns real-Luna and
targeted Gate-A verification. CTX-03 explicitly defers a separate conversation
classifier, extra summarizer model call, archive vector index, automatic
semantic prior-session retrieval, retro-link background job, memory service,
and agent chain for conversation routing. Historical lookup is an on-demand
future seam only, subject to independent validation and Product Owner approval.

# 15. Multimodal Input Architecture

Student interaction is multimodal-first rather than chat-only.

## 15.1 Text

Direct Tutor input.

## 15.2 Voice

```text
Audio
 ↓
STT
 ↓
Transcript
 ↓
Normal Tutor Pipeline
```

Current policy:

- store transcript,
- do not retain raw audio after successful STT.

## 15.3 Student Work Images

Supported examples:

- handwritten answer,
- Math working,
- drawing,
- diagram,
- homework,
- textbook page,
- experiment image.

Pipeline:

```text
Original Image
      ↓
Vision Interpretation
      ↓
Ambiguous?
├── yes → ask Lina a simple clarification
└── no  → Tutor continues
```

The original student image remains the raw source.

## 15.4 Annotated Original — Default Visual Response

When visual feedback is useful:

```text
Original student work
      ↓
Generate explanatory annotation
(arrows / circles / highlights / short notes)
      ↓
Show annotated derived artifact
```

The annotated image must never replace the original evidence source.

## 15.5 Clean Reconstruction

When annotation is insufficient:

```text
Original student work
      ↓
Interpret educational structure
      ↓
Create clean HTML/SVG/interactive reconstruction
```

The reconstruction is a teaching artifact, not evidence of what Lina originally produced.

---

# 16. Interactive Learning Artifact Architecture

Interactive educational output is a core capability.

## 16.1 UX Model

```text
Tutor Conversation
      ↓
Small inline visual / interactive card
      ↓ when more space is needed
Expanded Learning Canvas
      ↓
Return seamlessly to the same Tutor session
```

Do not force Lina into a separate workflow or new session.

## 16.2 Primary Artifact Path

```text
Tutor determines educational representation need
      ↓
Typed Artifact Specification
      ↓
Artifact Registry
      ↓
Approved Renderer
      ↓
Inline Artifact or Learning Canvas
```

## 16.3 Initial Renderer Stack

### Shared

- React/SVG
- Motion

### Math

- JSXGraph
- MathLive
- native SVG/React components

### Rich Interaction

- React Konva

## 16.4 Optional Renderers

Introduce only when a real use case needs them:

- Rough.js
- Recharts
- p5.js
- React Flow or other specialized libraries

## 16.5 Custom HTML/SVG

AI-generated custom HTML/SVG is a fallback path, not the default.

It must be:

- sandboxed,
- sanitized,
- network-restricted,
- failure-tolerant.

Artifact failure must never block the learning conversation.

## 16.6 Artifact Evidence

Track only educationally meaningful interactions.

Do not turn every click or mouse movement into learner evidence.

---

# 17. Session Intelligence Architecture

## 17.1 Session Lifecycle

Sessions close automatically after configurable inactivity and grace behavior.

Lina should not need an End Session button.

## 17.2 Session-local Learning Threads / Segments

A session may contain multiple contiguous Learning Threads / Segments.

Example:

```text
Session
├── Math / Fractions
├── Science / Free Exploration
└── Math / Homework Continuation
```

Thread/Segment separation is internal and should not complicate Lina's
experience. An optional Durable Conversation Topic may link Segments within a
Grade, but never authorizes Evidence attribution, personalization, Safety, or
curriculum interpretation.

## 17.3 End-of-Session Consolidation

```text
Candidate Events
      +
Relevant interaction excerpts
      +
Thread context
      ↓
Session Evidence Consolidation
      ↓
Validated Learning Events
      ↓
Evidence
      ↓
Deterministic Current-State / Pattern Engine
      ↓
Intelligence Card refresh
```

## 17.4 Normal AI Cost Pattern

Target runtime pattern:

```text
1 primary Tutor call per meaningful turn
+
1 consolidation call per meaningful session
```

Do not run an evidence LLM call after every message.

---

# 18. Learning Intelligence Implementation Rules

Implementation must follow `LEARNING_INTELLIGENCE_SPEC.md`.

The following rules are architectural, not optional optimizations.

## 18.1 Source and Derivation

```text
Raw Interaction
→ Candidate Event
→ Learning Event
→ Evidence
→ Current State / Pattern
→ Intelligence Card
→ Decision View
```

## 18.2 AI vs Deterministic Logic

AI:

- interprets semantic meaning,
- classifies/extracts events/evidence,
- normalizes semantic descriptions when needed.

Deterministic system:

- counts frequency,
- calculates recency,
- applies weighting rules,
- tracks counter-evidence,
- manages lifecycle,
- manages scope,
- compacts cards,
- calculates decision views.

## 18.3 Rebuildability

Events, Evidence, Patterns, Cards, and Decision Views must remain rebuildable from retained raw history where available.

## 18.4 Learning Intelligence Rubric

The approved rubric and Pattern Rules are the measurement contract.

Do not add defensive AI layers merely to avoid all possible extraction mistakes.

The validation philosophy is:

```text
Observe
→ Audit
→ Measure
→ Correct rules/prompts
→ Reprocess
→ Compare
```

---

# 19. Grade Architecture

Grade behavior should remain intentionally simple.

## 19.1 Active Grade

The currently activated books define the current Grade learning environment.

Grade 5 remains active until the Parent/Admin uploads/activates Grade 6 books.

## 19.2 Grade Transition

```text
Grade 5 active environment
      ↓
Parent/Admin activates Grade 6 books
      ↓
Generate compact Lina transition card
      ↓
Archive Grade 5 runtime state
      ↓
Grade 6 becomes active
```

## 19.3 Transition Card

Carry only compact useful learner information, for example:

- stable important patterns,
- important unresolved foundational gaps,
- successful teaching strategies,
- relevant extended capabilities,
- other validated high-value context.

Do not carry full Grade 5 mastery data or session history into Grade 6 runtime.

## 19.4 Missing Foundation in Grade 6

If Grade 6 requires a previous foundation Lina does not currently understand, the Tutor should teach/refresh it naturally and continue the Grade 6 lesson.

Do not build a complex cross-Grade prerequisite engine for the initial product.

---

# 20. Child Safety and Parent Learning Boundaries

Child safety is enforced at system level, not only through Tutor wording.

## 20.1 Non-Overridable Safety Baseline

The system must maintain mandatory child-safety rules that Parent settings cannot weaken.

The detailed taxonomy belongs in `CHILD_SAFETY_POLICY.md`.

## 20.2 Parent Learning Boundaries

The Parent Dashboard should support configurable topic categories with three states:

- `ALLOW`
- `AGE_APPROPRIATE_ONLY`
- `REDIRECT_TO_PARENT`

Potential categories include family-sensitive topics such as:

- religion,
- relationships,
- reproduction/sex education,
- politics/current affairs,
- death/grief,
- family finances.

The exact initial category list belongs in the safety policy and implementation tasks.

## 20.3 Enforcement Order

Conceptually:

```text
Student Input
      ↓
Safety & Learning Boundary Policy Engine
      ├── non-overridable child-safety baseline
      ├── Parent Learning Boundaries
      └── age-appropriate handling directive
      ↓
Versioned SafetyDecision
      ↓
Tutor / Artifact / Vision / Web tools
```

The policy engine is an explicit runtime contract. Its category-detection implementation may use deterministic routing and/or a classifier when needed, but the effective policy action is governed by versioned system/Parent policy. Do not rely on one Tutor prompt as the only enforcement mechanism.

## 20.4 Parent Redirect Audit

`REDIRECT_TO_PARENT` is a policy/audit event, not Learner Intelligence. Parent settings should expose a compact recent-redirect view with category, timestamp, effective policy source/version, and source interaction access on demand. It must not be presented as a trait or pattern in Lina's Learner Profile.

---

# 21. Model Gateway and AI Runtime

## 21.1 Core Principle

> **Use AI for cognition. Use deterministic code for state, weights, lifecycle, and plumbing.**

## 21.2 Task Routes

Initial task categories should include:

- tutor
- session_evidence
- curriculum_semantics
- vision_student_work
- speech_to_text
- embeddings
- Grade_transition
- optional external verification
- optional custom artifact generation

`curriculum_semantics` is an occasional optional enrichment route, not a
prerequisite that unlocks Tutor use. Trusted web discovery remains future
Roadmap Track B, not Track A implementation work.

## 21.3 Routing Configuration

Each task route may configure:

- primary provider/model,
- one fallback,
- timeout,
- output/token constraints,
- enabled/disabled state,
- estimated cost behavior.

## 21.4 Tutor Model Strategy

Start with a fast, cost-efficient model candidate for normal teaching and benchmark it on Lina-specific teaching scenarios.

Do not make a specific provider/model an architectural dependency.

Upgrade only tasks that demonstrate a real quality need.

## 21.5 Cost Classes

### Frequent / latency-sensitive

- Tutor
- STT
- embeddings where applicable

### Session/batch

- session evidence consolidation
- current-focus extraction
- school-plan extraction

### Rare / potentially more expensive

- full book semantic reprocessing
- Grade transition synthesis
- historical reanalysis
- specialized visual generation

---

# 22. Observability

Observability is a core implementation requirement.

## 22.1 AI Execution Ledger

Every AI execution should record at least:

- request/execution ID,
- task,
- provider,
- model,
- input usage,
- output usage,
- image/audio usage where applicable,
- latency,
- estimated cost,
- success/failure,
- fallback usage,
- processing/prompt/schema versions as relevant.

## 22.2 Learner Traceability

Important derived intelligence should remain traceable to:

```text
Pattern
 ↓
Evidence
 ↓
Learning Event
 ↓
Raw interaction / original student artifact
```

## 22.3 Human Audit

The product owner and AI collaborators must be able to inspect real:

- transcripts,
- student images,
- events,
- evidence,
- pattern changes,
- Tutor adaptations,
- AI executions.

This audit loop is how the project will improve the Learning Intelligence Rubric and prompts.

---

# 23. Reprocessing and Versioning

## 23.1 Original Source Rule

Original sources remain preserved where the approved product policy allows.

Derived data is replaceable.

## 23.2 Versioned Processing

Processing runs should preserve relevant versions for:

- model,
- provider,
- prompt,
- schema,
- policy,
- document-processing settings.

## 23.3 Content Reprocessing

A book should be reprocessable from the original uploaded source.

## 23.4 Intelligence Reprocessing

Historical learner intelligence should be reprocessable from retained raw interaction sources.

A new processing version should not silently destroy previous derived records before verification.

## 23.5 Recalculation

Changes to deterministic weighting/lifecycle policy should allow downstream state/card recalculation without requiring an AI re-read when semantic evidence has not changed.

---

# 24. Testing and Verification Strategy

Testing should prioritize real behavioral contracts over superficial implementation coverage.

## 24.1 Unit Tests

Use for deterministic behavior such as:

- pattern lifecycle,
- recency/frequency rules,
- state resolution,
- card compaction,
- Grade activation,
- parent-boundary configuration,
- authorization,
- context budgets.

## 24.2 AI Contract Tests

Use for structured AI outputs such as:

- Tutor hidden metadata,
- Candidate Events,
- evidence consolidation,
- curriculum semantic extraction,
- Vision interpretation.

Validate both schema and key semantic expectations.

## 24.3 Content/Retrieval Golden Set

Use Lina's real Math book to maintain expected retrieval cases.

## 24.4 Learning Intelligence Golden Scenarios

Use the scenarios governed by `LEARNING_INTELLIGENCE_SPEC.md`, including:

- repeated misconception,
- fast understanding,
- text fails / visual helps,
- old difficulty resolves,
- retention failure,
- drawing/handwriting evidence,
- multi-thread session,
- Grade transition.

## 24.5 Tutor Teaching Scenarios

Benchmark Tutor candidates on real or representative Grade 5 cases for:

- age-appropriate explanation,
- bilingual behavior,
- hinting,
- switching representation,
- teaching when Lina is stuck,
- avoiding excessive repetition,
- generating useful Candidate Events.

## 24.6 Real Lina Review

Real Lina usage is the decisive validation layer.

Review:

- whether Lina wants to use the system,
- whether explanations help,
- whether RAG is correctly grounded,
- whether Evidence matches transcripts/work,
- whether Patterns are useful,
- whether personalization improves interaction,
- whether interactive artifacts add learning value.

---

# 25. Implementation Phases

Phases describe outcomes and decision boundaries.

Actual executable work must be decomposed into `TASKS.md`.

---

## Phase 0 — Repository & Runtime Foundation

### Goal

Create a clean repository, runtime, storage, testing, and governance foundation without implementing learning features prematurely.

### Scope

- repository structure,
- Next.js app shell,
- FastAPI app shell,
- PostgreSQL connection/migrations,
- object-storage abstraction,
- Parent/Student roles,
- baseline auth,
- settings infrastructure,
- DB-backed job runner foundation,
- observability/logging foundation,
- test infrastructure,
- governing docs in repository,
- initial `AGENTS.md`, `PROJECT_STATE.md`, `TASKS.md`.

### Dependencies

None beyond approved project references.

### Exit Criteria

- apps run locally,
- DB migrations work,
- Parent and Student identities can be represented,
- storage is reachable,
- tests run from documented commands,
- Codex has repository-native instructions.

### Do Not Build Yet

- Tutor intelligence,
- full Parent Dashboard,
- Science,
- artifacts,
- complex Grade workflows.

---

## Phase 1 — Grade 5 Math Content Foundation

> **Historical phase record, superseded as a Tutor permission gate by Roadmap
> Track A.** A real book and semantic readiness remain valuable grounding
> validation, but neither is required for Student Tutor availability.

### Goal

Prove that a real Grade 5 Math book can be stored, structurally processed, and
reliably retrieved. Educational semantics are optional enrichment.

### Scope

- Parent book upload,
- original file preservation,
- Docling adapter,
- versioned document processing,
- normalized Docling representation,
- optional educational semantic extraction,
- curriculum nodes,
- structural content blocks,
- lexical/vector indexing,
- retrieval API/service,
- minimal Content Admin status,
- reprocess action,
- retrieval golden set.

### Dependencies

Phase 0.

### Expected Output

An available real Grade 5 Math book reaches retrieval-ready structural indexing
and relevant content can be retrieved by known test questions.

### Exit Criteria

- useful source regions are discoverable; optional units/lessons may be available,
- test questions retrieve the intended sections/pages with acceptable reliability,
- source provenance is preserved,
- reprocessing from the original source works.

### Do Not Build Yet

- Science ingestion,
- broad document-authoring UI,
- universal curriculum editor,
- universal cross-Grade concept graph.

---

## Phase 2 — Math Tutor Vertical Slice

> **Historical sequencing note.** Roadmap Track A supersedes the Phase 1
> dependency as a permission gate: the Tutor must work with zero content, and
> grounding improves rather than authorizes the interaction.

### Goal

Make the system genuinely usable by Lina for text-based Grade 5 Math learning.

### Scope

- Student Math entry point,
- session/thread basics,
- Tutor runtime,
- context builder,
- current Grade/subject context,
- Math retrieval integration,
- fixed Tutor identity,
- adaptive teaching strategy,
- Learn/Homework/Explore basic mode behavior,
- bilingual behavior,
- SSE streaming,
- Candidate Event metadata contract,
- explicit Safety & Learning Boundary Policy Engine integration before Tutor behavior,
- Model Gateway initial Tutor route,
- Tutor-model usage/cost logging.

### Dependencies

Roadmap Track A Tutor-availability and structural-index acceptance, plus the
relevant runtime foundations.

### Expected Output

Lina can ask about Grade 5 Math and receive safe, adaptive teaching responses
with optional grounding when useful sources are available.

### Exit Criteria

- zero-content Tutor availability is proven; correct curriculum context is used in representative grounded cases,
- Tutor does not simply paraphrase the book,
- Tutor can change explanation strategy,
- Tutor does not endlessly withhold answers,
- safety/boundary behavior is enforced through the explicit policy-engine contract rather than prompt-only instructions,
- Candidate Event metadata is structurally valid,
- runtime logs and usage are inspectable,
- **Early Lina Calibration Checkpoint completed:** at least one natural Grade 5 Math use cycle is reviewed for transcript, retrieval, Tutor behavior, safety routing, and Candidate Events before Phase 3 starts. This is calibration only and does not replace the Mandatory Real Lina Decision Gate after Phase 4.

### Do Not Build Yet

- stable learner patterns,
- full Parent insights,
- voice,
- student image Vision,
- advanced artifacts.

---

## Phase 3 — Learning Intelligence Core

### Goal

Prove the durable product loop: real interactions create auditable intelligence that affects later teaching.

### Scope

- session inactivity/close logic,
- multi-thread session support,
- Candidate Event persistence/buffering as needed,
- session evidence consolidation,
- validated Learning Events,
- Evidence Rubric implementation,
- Current Learning State,
- deterministic pattern engine,
- normalized pattern identity registry (`pattern_type` + stable `pattern_key`),
- pattern scope/lifecycle,
- anti-self-confirmation rule for teaching-strategy patterns: strategy selection/use alone is not confirming Evidence; observable Lina outcome is required,
- compact Learner Intelligence Card,
- runtime intelligence selector,
- derived mastery/confidence views,
- reprocessing/versioning,
- Learning Intelligence audit view/API.

### Dependencies

Phase 2 and `LEARNING_INTELLIGENCE_SPEC.md`.

### Expected Output

A meaningful Math session creates traceable Evidence and current intelligence, and a later Tutor session uses relevant intelligence without loading full history.

### Exit Criteria

- Events trace to raw interactions,
- Evidence follows the approved rubric,
- Current State and Pattern remain distinct,
- deterministic lifecycle rules and normalized pattern-key behavior are test-covered,
- strategy-effectiveness patterns cannot strengthen merely because the Tutor selected the historical strategy,
- Card remains compact,
- reprocessing can rebuild derived intelligence,
- historical patterns do not override current Lina behavior.

### Do Not Build Yet

- advanced analytics,
- ML clustering,
- graph database,
- automatic psychological/learning-style labels.

---

## Phase 4 — Parent Basic Visibility & Control

### Goal

Allow the Parent/Admin to understand what the system is doing and control core learning context without creating a surveillance dashboard.

### Scope

- Parent Overview,
- Math learning view,
- Learner Profile / Intelligence view,
- important Evidence drill-down,
- learning-history essentials,
- Content status/reprocessing,
- AI usage/cost summary,
- content/reference controls (not school-position correction),
- parent learning-boundary settings UI,
- Recent Redirects / Policy Audit visibility for `REDIRECT_TO_PARENT` events, kept separate from Learner Profile intelligence,
- basic model-route settings where appropriate.

### Dependencies

Phases 1–3.

### Expected Output

The Parent can answer:

- What is Lina learning now?
- What does the system currently think matters?
- Why does it think that?
- What changed recently?
- What content/model/settings are active?

### Exit Criteria

- insights are evidence-linked,
- no pseudo-scientific mastery precision is presented,
- raw evidence is available on demand,
- boundaries and settings are controllable,
- recent `REDIRECT_TO_PARENT` events are visible to Parent as policy/audit events without becoming Learner Profile traits,
- Lina-facing analytics remain absent.

---

# 26. Real Lina Decision Gate — Mandatory

After Phase 4, stop feature expansion and run real usage with Lina.

This is a mandatory product decision gate.

## 26.1 Required Real Inputs

- real Grade 5 Math questions/homework where possible, with a real book and/or
  trusted references as valuable grounding-validation inputs when available,
- repeated use across multiple sessions.

## 26.2 Review Questions

### Tutor

- Does Lina willingly interact with it?
- Does the language feel natural for her?
- Does it help her understand rather than merely complete?
- Does it change representation appropriately?

### Content/Retrieval

- Does the Tutor ground school-related teaching in the correct material?
- Are important examples/figures accessible?

### Learning Intelligence

- Are meaningful Events actually meaningful?
- Does Evidence match the transcript/work?
- Do Patterns make sense under the approved rules?
- Does old intelligence resolve when Lina improves?
- Does personalization improve later interactions?

### Parent Experience

- Can the Parent inspect and understand system reasoning?
- Is the information useful rather than overwhelming?

### Cost/Latency

- Is normal Tutor interaction fast enough?
- Is session consolidation acceptable?
- Which task routes consume most cost?

## 26.3 Gate Outcomes

### Continue

Core loop is useful and trustworthy enough to expand.

### Continue With Corrections

Fix Tutor, RAG, Evidence, Pattern Rules, or UX before adding new feature families.

### Do Not Expand Yet

If Lina does not want to use it or the Intelligence loop is systematically misleading, remain focused on the core until corrected.

> **Do not compensate for a weak core by adding more features.**

---

# 27. Phase 5 — Voice + Student Images

### Goal

Make natural child input multimodal.

### Scope

- microphone input,
- STT,
- transcript storage,
- raw-audio deletion after successful STT,
- student-image upload/capture flow,
- Vision interpretation,
- ambiguity/clarification behavior,
- original student artifact preservation,
- annotated-original output,
- clean reconstruction path when needed,
- multimodal Evidence rules.

### Dependencies

Decision Gate approval/corrections and stable Phase 3 intelligence contracts.

### Exit Criteria

- Lina can speak instead of typing,
- handwriting/drawing can contribute to learning,
- ambiguous Vision interpretation triggers clarification,
- original vs derived artifacts remain separated,
- meaningful multimodal evidence is traceable.

---

# 28. Phase 6 — Interactive Learning Artifacts

### Goal

Allow the Tutor to choose visual/interactive representations when they add educational value.

### Scope

- Artifact Specification schema,
- Artifact Registry,
- inline artifact container,
- expanded Learning Canvas,
- React/SVG + Motion baseline,
- Math artifact components using JSXGraph/MathLive/Konva where valuable,
- artifact interaction events,
- safe fallback behavior,
- custom sandboxed HTML/SVG fallback only if required.

### Initial Artifact Priority

Build from real Math need, likely including a small subset such as:

- fraction visualizer,
- number line,
- bar model,
- geometry explorer,
- equation-step visualizer.

Do not build a large generic artifact catalog before real usage indicates demand.

### Exit Criteria

- Tutor can request a typed artifact,
- artifact renders reliably,
- simple artifact stays inline,
- richer artifact expands without breaking session continuity,
- educationally meaningful interaction can return to Tutor/Evidence,
- artifact failure does not block the conversation.

---

# 29. Phase 7 — Science

### Goal

Extend the validated architecture to Science without duplicating the system.

### Scope

- Science book ingestion,
- Science semantic extraction,
- Science retrieval,
- Science Tutor guidance,
- Science Evidence dimensions where specified,
- diagrams/figures,
- safe home-experiment support where allowed,
- Science-specific artifact types as real use requires.

### Dependencies

Validated Math core.

### Extensibility Test

Adding Science should validate that the architecture supports new subjects through subject-specific adapters/configuration rather than scattered core rewrites.

### Exit Criteria

- Science integrates without duplicating Tutor/Intelligence foundations,
- diagrams and scientific explanations work,
- Science factual uncertainty can be handled correctly,
- subject-specific needs remain modular.

---

# 30. Phase 8 — Retention & Proactive Learning

### Goal

Use accumulated evidence to support retention naturally without turning the system into a schedule-pressure tool.

### Scope

- retention state/views,
- review-due logic,
- gentle in-app review suggestions,
- proactive mode configuration,
- retention evidence integration.

### Exit Criteria

- review suggestions are grounded in real evidence,
- no exam-like pressure is introduced,
- successful delayed recall updates retention intelligence,
- Lina can ignore suggestions without penalty.

---

# 31. Phase 9 — Grade Transition

### Goal

Implement the already-approved simple Grade transition.

### Scope

- Parent/Admin Grade activation,
- compact transition-card synthesis,
- Grade archive state,
- initialize next Grade books/environment,
- preserve prior raw/history data,
- new Grade runtime uses only compact useful transition context by default.

### Exit Criteria

- Grade changes only when Parent/Admin activates new Grade content,
- Grade 6 begins from Grade 6 books,
- compact transition intelligence is available,
- old Grade runtime detail is not automatically injected.

---

# 32. Phase 10 — Refinement, Gamification & Expansion

This phase is deliberately open-ended and should only be planned from real evidence.

Possible work:

- child-friendly celebrations/badges,
- richer artifact library,
- refined Parent insights,
- additional subjects,
- improved accessibility,
- better proactive experiences,
- performance/cost tuning.

Do not pre-commit to all of these.

---

# 33. Cost Strategy

Cost should be observed before aggressively optimized.

## 33.1 Core Runtime Target

Normal learning:

```text
One Tutor call per turn
+
One consolidation call per meaningful session
```

## 33.2 Content

Use Docling structural processing first to avoid unnecessary VLM processing across full books.

## 33.3 Vision

Use Vision when Lina provides a relevant image or when educational value requires it.

## 33.4 Artifacts

Prefer reusable deterministic renderers over generating new HTML/JS from a model every time.

## 33.5 Optimization Rule

No additional AI call should be introduced unless it has a clear learning or system-quality benefit that cannot reasonably be achieved by deterministic code or existing context.

---

# 34. Deferred Architecture

The following must remain deferred unless real evidence creates a clear requirement:

- microservices,
- Kubernetes-style distributed architecture,
- Graphiti,
- graph database,
- universal Knowledge Graph,
- cross-Grade concept-mapping engine,
- Redis/Celery,
- native mobile application,
- multi-family SaaS,
- billing,
- teacher portal,
- classroom tooling,
- dedicated vector database,
- generic autonomous-agent framework,
- chains of AI evaluators per Tutor turn,
- separate conversation classifier/model call in the normal path,
- archive vector or automatic semantic prior-session retrieval,
- mandatory compact Segment summaries or retro-link background job,
- conversation memory service or agent chain for conversation routing,
- advanced ML/clustering,
- complex event-stream infrastructure,
- large generic artifact marketplace.

A future implementation proposal that introduces one of these must state:

1. the specific problem it solves,
2. evidence that the current architecture is insufficient,
3. added operational complexity,
4. migration path,
5. why a simpler solution is inadequate.

---

# 35. Change & Migration Rules

## 35.1 Protect Durable Data

Do not make schema changes that destroy:

- original books,
- original student work,
- raw text/transcript history,
- source provenance,
- processing-version traceability.

## 35.2 Prefer Additive Evolution

Use:

- migrations,
- versioned schemas,
- feature flags,
- adapters,
- registry extension,
- processing-version changes.

Avoid silent reinterpretation of existing intelligence.

## 35.3 Core Contract Changes

Changes to the following require explicit project-owner approval:

- learning philosophy,
- evidence rubric semantics,
- Pattern lifecycle semantics,
- child-safety policy semantics,
- Parent-learning-boundary semantics,
- Grade-transition principle,
- source-of-truth/rebuildability principle,
- Student vs Parent UX separation.

---

# 36. Definition of Done — First Product Loop

The first product loop is complete only when all of the following are true.

## Content

- Lina can enter Tutor and receive a safe answer with zero content.
- A real Grade 5 Math book can be uploaded when available.
- Original source is preserved.
- Structural processing and retrieval-ready indexing succeed for an available source.
- Relevant content can be reliably retrieved when a useful source exists.
- Educational semantic enrichment is optional and rebuildable.

## Student

- Lina can enter Math and interact with the Tutor.
- Tutor uses optional question-driven grounding when available; empty retrieval does not block it.
- Tutor can teach rather than merely answer.
- Tutor can change strategy when she is stuck.

## Intelligence

- meaningful Candidate Events are produced.
- session consolidation creates traceable Events/Evidence.
- Current State can update.
- Patterns can evolve under deterministic rules.
- Intelligence Card remains compact.
- later Tutor interaction can use relevant intelligence.

## Parent

- Parent can see important learning state.
- Parent can open evidence behind important conclusions.
- Parent can manage content/current Grade context.
- Parent can inspect AI usage/cost.

## Architecture

- Model provider can be changed by task without changing domain logic.
- derived intelligence is rebuildable.
- document processing is reprocessable.
- logs expose AI execution and downstream intelligence traceability.
- subject/artifact extension points are not hardcoded into one monolithic Tutor route.

## Validation

- real Lina use has been reviewed at the mandatory decision gate.

---

# 37. First Build Order for Codex

This sequence is directional. `TASKS.md` must decompose it into small executable units.

```text
1. Roadmap Track A governance correction
2. Zero-book Tutor availability
3. Structural-first indexing
4. Optional semantic behavior
5. Simplification acceptance suite
6. Real Lina calibration
7. Grade 5 Math Trusted Reference Pilot

Historical implementation records above remain evidence of prior work; they do
not authorize bypassing the active Track A order.

STOP
→ Run Real Lina Decision Gate

Only after gate approval/corrections:

17. Voice
18. Student images + annotation
19. Interactive artifacts
20. Science
21. Retention/proactive learning
22. Grade transition
23. Refinement/expansion
```

---

# 38. Execution Gate Rules

Codex must not infer that completion of one phase authorizes all later phases.

The following are explicit gates:

## Gate A — Content Reliability

Before the Tutor relies on school RAG, real-book retrieval must be demonstrably useful.

## Gate B — Intelligence Traceability

Before historical personalization is considered stable, Events/Evidence/Patterns must be inspectable and rebuildable.

## Gate C — Real Lina Decision Gate

Before Voice/Artifacts/Science expansion, run the real Lina review after Phase 4.

## Gate D — Grade Transition

Do not build elaborate Grade transition behavior before the current Grade product is proven.

---

# 39. Operational Definition of Success

The project is moving correctly when each new capability improves one of these without damaging the others:

- Lina understands better,
- Lina can interact more naturally,
- Tutor uses relevant context more effectively,
- Learner Intelligence becomes more useful and auditable,
- Parent gains clearer understanding/control,
- the code remains easier to extend,
- cost and latency remain visible and manageable.

The project is **not** moving correctly merely because:

- more AI calls were added,
- more dashboards were built,
- more agents exist,
- more data is stored,
- more features are available.

---

# 40. Final Implementation Principle

> **Build the smallest complete learning loop first. Preserve the evidence and architecture needed to improve it. Expand only after real Lina usage demonstrates where additional complexity creates value.**

The correct implementation is not the one that implements the largest number of approved ideas fastest.

It is the one that keeps the core learning loop coherent, observable, rebuildable, and easy to evolve.
