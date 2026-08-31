# Lina Personal Learning System

## IMPLEMENTATION_PLAN.md

**Status:** Approved implementation direction; synchronized with accepted Learning Intelligence architecture under `DOC-SYNC-01` pending Product Owner review  
**Authority:** Governing execution map for technical architecture, sequencing principles, dependencies, decision gates, and implementation boundaries  
**Audience:** Product owner, ChatGPT, Codex, AI agents, developers, reviewers  
**Governing references:** `PROJECT_REFERENCE.md`, `LEARNING_INTELLIGENCE_SPEC.md`, `LEARNING_PRODUCT_ROADMAP.md`  
**Safety authority:** `CHILD_SAFETY_POLICY.md`  
**Current operational state / next action:** `project-state/PROJECT_STATE.md`  
**Execution/task state:** `TASKS.md`

---

# 1. Purpose

This plan defines **how approved Lina Learning product direction should be implemented** without becoming the current task queue or a historical diary.

It provides:

- architecture direction,
- domain/module boundaries,
- integration principles,
- sequencing/gating rules,
- verification expectations,
- what complexity to delay,
- and technical invariants Codex/AI agents must preserve.

It does **not** decide which task is next today. `PROJECT_STATE.md` and `TASKS.md` own that.

Historical phases/tasks remain provenance in task history and Git. A historical “next” instruction does not remain executable after its task is accepted or superseded.

---

# 2. Implementation Objective

The project is no longer at a Phase-0 shell. The accepted current core already includes a Math-first Tutor, optional grounding, Segment-based conversation context, child-safety enforcement, Segment Learning Review, deterministic Session Finalization, Event/Evidence materialization, Current State/Patterns, Card selection, and technical later-personalization paths.

The current implementation objective is therefore not “build the first Learning Intelligence architecture.” It is to preserve that accepted core, operate it reliably, learn from real Lina use, and promote broader product capabilities deliberately.

The protected learning loop is:

```text
Student can enter Tutor with zero content
        ↓
Safety / Parent Boundary enforcement
        ↓
optional question-driven grounding
+ relevant current-Segment conversation context
+ relevant Session-authorized learner intelligence
        ↓
ONE primary Tutor model call
        ↓
response + bounded provisional metadata
        ↓
completed Segment semantic Review in background
        ↓
Session closes / complete compatible Reviews available
        ↓
deterministic Session Intelligence Finalization
        ↓
Session-authorized Event/Evidence
        ↓
Current State / Patterns / Decision Views
        ↓
on-demand Learner Intelligence Card
        ↓
relevant later Tutor personalization
```

The system should optimize for:

1. educational usefulness,
2. source/evidence traceability,
3. current-behavior-first personalization,
4. operational simplicity,
5. modifiability/rebuildability,
6. cost/latency visibility,
7. child-appropriate natural interaction,
8. extensibility without premature platform complexity.

---

# 3. Sources of Truth

## 3.1 Stable Product Truth

`docs/PROJECT_REFERENCE.md`

Controls product purpose, boundaries, roles, learning philosophy, Tutor/product principles, approved deferred capabilities, Grade/content/multimodal/artifact direction, and system invariants.

## 3.2 Learning Intelligence Truth

`docs/LEARNING_INTELLIGENCE_SPEC.md`

Controls Event/Evidence rubrics, Current State, Pattern rules, Segment Review, Session authority, Card, Decision Views, traceability, and reprocessing.

## 3.3 Product Evolution

`docs/LEARNING_PRODUCT_ROADMAP.md`

Controls approved capability sequencing/gates but does not make a capability executable by itself.

## 3.4 Safety Truth

`docs/CHILD_SAFETY_POLICY.md`

Controls the non-overridable child-safety baseline and Parent Learning Boundary semantics.

## 3.5 Current Reality

`project-state/PROJECT_STATE.md`

Controls current operational goal/reality/risks/next action.

## 3.6 Task State

`TASKS.md`

Contains durable task history and executable/current task records.

---

# 4. Architecture Strategy

## 4.1 Modular Monolith

Use a **Modular Monolith**.

```text
┌───────────────────────────┐
│        Next.js Web        │
│   Student + Parent/Admin  │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│      FastAPI Backend      │
│ Tutor                     │
│ Intelligence              │
│ Content                   │
│ Retrieval                 │
│ Learning Artifacts*       │
│ Model Gateway             │
│ Grade*                    │
│ Platform                  │
└─────────────┬─────────────┘
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
 PostgreSQL  Storage  Worker
 + pgvector
```

`*` Approved domain direction does not imply current production capability is un-frozen.

Do not create microservices merely because logical domains exist.

## 4.2 Simplicity Rule

Prefer the simpler implementation unless abstraction clearly improves maintainability, recoverability, testing, rebuildability, or future extension.

Do not introduce Docker/Kubernetes/new hosts/queues/databases/observability platforms merely because the current operational environment needs wiring. Deployment is an operational choice, not product architecture.

---

# 5. Current Technology Direction

## Frontend

- Next.js
- TypeScript
- responsive web application
- Clerk client/session integration
- SSE Tutor streaming
- child-friendly component system

## Backend

- Python
- FastAPI
- typed service/domain boundaries

## Database

- PostgreSQL
- pgvector
- JSONB where evolving payloads benefit from flexibility
- Alembic migrations

## File/Object Storage

- provider-neutral storage abstraction
- S3-compatible persistent storage when the selected production-style environment requires durable private assets

Storage is important for books/images/assets, but zero-book Text Tutor + Learning Intelligence must not be blocked on content upload.

## Background Work

```text
PostgreSQL jobs table
+
separate Worker process
```

The Worker entrypoint and job system already exist. Do not introduce Redis/Celery unless real workload proves need.

## Streaming

- Server-Sent Events (SSE)

## Model Access

- task-based Model Gateway
- current implemented real provider support includes OpenAI
- provider/model is replaceable and not permanent domain architecture

---

# 6. Domain Boundaries

## 6.1 Tutor Domain

Owns:

- Student Tutor runtime,
- current authenticated Session ownership path,
- session-local Segment relation/context,
- Hybrid Segment Context assembly,
- teaching Mode/Strategy/Method decisions inside the same primary Tutor call,
- response streaming,
- bounded Candidate metadata,
- provisional Broad Subject hint,
- persisted teaching/segment lineage,
- consumption of relevant Card intelligence.

Must not:

- directly declare stable learner Patterns,
- own durable Evidence activation,
- bypass Model Gateway,
- own document parsing,
- own deterministic Pattern weighting,
- create a second conversation/learner-memory subsystem.

## 6.2 Learning Intelligence Domain

Owns the **implemented accepted** path:

- Segment structural reviewability,
- Segment Learning Review,
- staged findings,
- deterministic Session Finalization,
- Session authority generation,
- Event/Evidence materialization,
- Current State,
- Learner Patterns,
- deterministic weighting/lifecycle,
- Decision Views,
- Learner Intelligence Card projection/selection,
- bounded/versioned reprocessing.

Historical legacy `session_evidence` data/routes remain compatibility/audit concerns, not the primary current semantic architecture.

## 6.3 Content Domain

Owns:

- original educational sources,
- document/processing versions,
- Docling structural processing,
- normalized structural representation,
- optional educational semantic enrichment,
- source/page/figure/formula provenance,
- reprocessing state.

Must not own Tutor behavior or learning-path authority.

## 6.4 Retrieval Domain

Owns:

- structural/metadata filtering,
- lexical retrieval,
- vector retrieval,
- deterministic/hybrid fusion,
- relevant context selection,
- provenance/source refs,
- bounded retrieval budgets.

It answers “what source material is useful for this current question?” not “what must Lina study now?”

## 6.5 Learning Artifacts Domain — Approved but Frozen

When explicitly promoted, owns:

- typed Artifact Specifications,
- registry/renderer selection,
- reusable visual/interactive representations,
- inline/Learning Canvas contracts,
- semantic interaction events,
- sandboxed fallback rendering where approved.

Do not build it merely to solve one bounded Math text-alignment defect.

## 6.6 Model Gateway Domain

Owns:

- task routing,
- provider adapters,
- structured output/stream handling,
- fallback where approved,
- usage/cost/latency lineage.

Current task categories include:

```text
tutor
segment_evidence
embedding
curriculum_semantics
session_evidence  # legacy/historical compatibility when required
```

Future/gated categories may include:

```text
speech_to_text
vision_student_work
vision_content_enrichment
grade_transition
image_generation / external verification when approved
```

`segment_evidence` is **implemented current architecture**, not an “approved future target.”

## 6.7 Grade Domain — Approved Future Production Work

Owns active Grade/GradePeriod lifecycle, future Parent activation, compact transition intelligence, and prior Grade archive linkage when that capability is promoted.

## 6.8 Platform Domain

Owns shared infrastructure:

- auth/roles,
- Parent ↔ Student authorization,
- DB/session/migrations,
- storage,
- jobs/Worker,
- settings,
- Safety/Parent Boundary persistence,
- AI execution ledger,
- observability/health.

---

# 7. Content Processing Architecture

## 7.1 Source Preservation

Original sources remain durable where product policy allows. Derived representations are versioned/rebuildable.

## 7.2 Structural-First Pipeline

```text
Learning Source
  ↓
Preserve Original + Provenance
  ↓
Processing Run
  ↓
Docling structural processing / normalization
  ↓
Retrieval blocks / index
  ↓
Retrieval-ready

Optional:
Structural representation
  ↓
Educational semantic enrichment
```

Educational semantics are not a permission gate for Tutor/basic RAG.

## 7.3 Structural Chunking

Preserve document structure first. Apply token-aware splitting only when structural units exceed practical limits. Avoid blind fixed-size token chunking as primary strategy.

## 7.4 Figures/Formulas

Keep page/source/caption/provenance and relevant relationships. Use expensive visual enrichment selectively.

---

# 8. Retrieval Architecture

Retrieval is optional and question-driven.

```text
Current Student question
   ↓
Grade / Broad Subject when known
   ↓
structural / metadata candidates
   ↓
lexical + vector retrieval
   ↓
context ranking / bounded result
```

Recent conversation context is advisory. Current School Focus is not an authority. Optional semantic metadata may improve ranking but cannot exclude otherwise relevant structural candidates merely because enrichment is missing.

---

# 9. Tutor Runtime Architecture

## 9.1 Primary Path

```text
Authenticated Student Turn
     ↓
hard Safety baseline
     ↓
Session / current Segment resolution
     ↓
Hybrid Segment Context
├── Current Turn
├── Full Immediate Exchange
├── Structured Segment State
└── relevant complete current-Segment Exchanges
     ↓
separate optional RAG
+ relevant Learner Intelligence
+ effective Parent Boundary configuration
     ↓
final capacity guardrail
     ↓
ONE primary Tutor model call
     ↓
response stream
+ teaching Mode / Strategy / Method / prior relation
+ Segment relation / provisional Broad Subject
+ optional Candidate metadata
+ Parent Boundary semantic applicability
     ↓
deterministic validation / policy enforcement / persistence
```

## 9.2 Teaching Decisions

TeachingMode, TeachingStrategy, and TeachingMethod remain distinct. The same primary Tutor call semantically selects values; runtime validates canonical IDs/lineage rather than keyword-routing meaning.

Selecting a TeachingMethod is not Evidence that it helped. Observable Student outcome + Segment Review + Session authorization is required for effectiveness Evidence.

## 9.3 Tutor Call Count

Normal Student turn = one primary Tutor model call. Do not add critic/evaluator/profile/classifier chains by default.

## 9.4 Conversation Context

A Learning Thread is the session-local contiguous Segment. Returning after an intervening Segment creates a new Segment. Normal raw context recall remains Current-Segment-only.

Structured Segment State is conversational metadata, not Evidence. Historical archive retrieval remains gated future work.

---

# 10. Learning Intelligence Runtime

## 10.1 Segment Review

A Segment is structurally reviewable only when safely closed, properly owned/linked, and containing at least one persisted raw Student interaction.

Structural reviewability is not a semantic learning gate. Do not require Candidate, Guided Check, TeachingMethod, Tutor response, concept, keyword, or minimum exchange count.

## 10.2 Review → Finalization

```text
closed structurally reviewable Segment
→ SEGMENT_LEARNING_REVIEW job
→ complete raw Segment semantic review
→ staged findings

Session closed
+ complete compatible required Review set
→ SESSION_INTELLIGENCE_FINALIZE job
→ deterministic finalization
→ Event/Evidence
→ Current State / Patterns / Decision Views
```

No ordinary broad semantic Session call is required after Segment Reviews. No partial Session intelligence activation is allowed.

## 10.3 Card and Later Personalization

The Card is an on-demand compact projection of active/relevant State/Patterns. It is not a persisted source of truth or transcript summary.

A later Tutor receives only relevant Card entries. Current behavior remains higher authority than historical intelligence.

## 10.4 Reprocessing

Reprocessing is bounded, versioned, and authority-safe. Preserve previous coherent authority until the selected new scope can activate atomically. Raw source and prior generations remain auditable.

---

# 11. Session Lifecycle and Worker

Sessions close automatically after configured inactivity/grace without requiring Lina to press an End button.

The separate Worker process is responsible for recurring lifecycle polling and background job handling. Current repository code already contains the Worker entrypoint and intelligence/content handler registration.

If a selected real-use environment does not start the Worker, treat that as **operational wiring**, not missing Learning Intelligence implementation. Do not redesign queues/services before proving the actual gap.

---

# 12. Multimodal Input — Approved, Frozen Until Promotion

The intended product is not text-only.

## Voice

```text
Audio
→ STT
→ transcript
→ normal Tutor pipeline
```

Current approved direction retains transcript and does not retain raw audio after successful transcription unless a later policy changes that.

## Student Work Images

Future approved flow:

```text
Original image
→ Vision interpretation
→ clarify if material ambiguity
→ Tutor response
→ annotate original first when useful
→ clean reconstruction if annotation insufficient
```

Original Student work remains source authority. Derived Vision/annotation/reconstruction cannot replace it.

No Voice/Vision implementation is authorized merely by this plan.

---

# 13. Interactive Learning Artifacts — Approved, Frozen Until Promotion

Approved architecture:

```text
Tutor identifies representation need
→ typed Artifact Specification
→ registry
→ tested renderer
→ inline visual or Learning Canvas
→ meaningful interaction event when educationally relevant
```

Prefer reusable deterministic renderers over arbitrary generated code. Arbitrary unsandboxed AI JavaScript is rejected. Artifact failure must not block Tutor conversation.

A bounded Math readability correction does not automatically unfreeze the Artifact Engine.

---

# 14. Child Safety and Parent Learning Boundaries

Hard child-safety baseline is product/runtime policy and cannot be weakened by Parent settings.

Normal Tutor flow preserves same-primary-call semantic applicability for configurable Parent Boundaries while server-owned Parent configuration remains final authority. The server enforces the final visible response.

Parent Boundary categories/actions remain separate from Learner Intelligence. Detailed semantics belong in `CHILD_SAFETY_POLICY.md`.

---

# 15. Cross-Subject Architecture

`SCOPE-01` / `SUBJ-01` are accepted.

- one technical Session may contain multiple Subjects through Segments;
- one Segment has one primary Broad Subject;
- meaningful Subject switch → new Segment;
- no extra normal-turn Subject classifier;
- Segment Review is durable semantic Subject authority;
- Broad Subject and school relationship are separate;
- school relationship is `SCHOOL_ALIGNED / EXTENDED / UNKNOWN`;
- absent school source → `UNKNOWN`, not automatic `EXTENDED`;
- unresolved/conflicting durable attribution fails closed.

Do not keep language describing cross-subject attribution as future/unimplemented current architecture.

---

# 16. Extensibility Rules

## Adding a Subject

Subject expansion should reuse Tutor/Intelligence core and add bounded subject guidance/evidence/artifact/retrieval differences without scattered core rewrites or a generic plugin framework.

## Adding a Provider

Implement a Model Gateway provider adapter; do not alter Tutor/Intelligence business logic merely to change provider.

## Adding an Artifact Type

When the capability is promoted: typed spec + registry entry + renderer + semantic interaction mapping + tests.

## Adding an Evidence Dimension

Requires a versioned Learning Intelligence contract change and must not silently reinterpret historical Evidence.

---

# 17. Repository / Code Organization

Logical domains remain:

```text
apps/web
apps/api
services/tutor
services/intelligence
services/content
services/retrieval
services/model_gateway
services/platform
workers
tests
docs
project-state
```

Learning Artifacts/Grade modules should be added/expanded only when their approved capability work is actually promoted; do not scaffold large frozen subsystems preemptively.

API routes remain thin; avoid combining provider calls, SQL, and business rules directly in endpoint handlers where a domain/service boundary already exists or clearly helps.

---

# 18. Observability

AI execution ledger should expose, where applicable:

- execution ID,
- task,
- provider/model,
- input/output usage,
- latency,
- estimated cost,
- success/failure,
- fallback,
- prompt/schema/policy lineage.

Learner traceability should support:

```text
Pattern / Current State / Decision View
→ Evidence
→ Event
→ Segment Review / Finding
→ Raw interaction / original Student asset
```

Operational verification should observe failures/retries without creating a new observability platform by default.

---

# 19. Rebuildability and Migration

Use migrations for schema change. Prefer additive/versioned evolution. Avoid destructive changes to original books, Student work, raw text/transcript history, provenance, or intelligence generations.

Content reprocesses from original sources. Intelligence reprocesses from retained raw interactions under selected versions.

Changes to deterministic Pattern/Decision policy should permit downstream recalculation without unnecessary AI re-read when semantic Evidence has not changed.

---

# 20. Testing and Verification Strategy

Prioritize behavioral contracts over superficial coverage.

## Deterministic tests

Examples: lifecycle, Pattern rules, Card compaction, auth/authorization, Safety state resolution, job idempotency/retry, context selection, finalization authority, reprocessing activation.

## AI contract/real-model tests

Examples: structured Tutor output, Segment Review output, teaching/subject semantics, bounded real provider scenarios.

## Browser / real-use evidence

Browser acceptance, limited Real-Lina use, stable daily Lina use, and longitudinal Lina validation are **different evidence categories**. Never imply one from another.

The existing project has limited Real-Lina interaction history, but recurring daily and longitudinal validation remain separate work.

---

# 21. Product Sequencing Principle

Do not attempt to finish the complete intended product before learning from Lina.

Equally, do not mistake an early Math/Text proving ground for the final product.

Approved broader capabilities remain visible but frozen:

- Science,
- Voice/STT,
- Vision/photo/homework,
- handwriting/drawing Evidence,
- annotation/reconstruction,
- visual/interactive learning artifacts,
- Learning Canvas,
- broader Parent Intelligence UX,
- Grade-transition production.

Real use should help order promotion among these approved directions.

---

# 22. First Product Loop Completion

The first product loop is broader than “Lina can chat with Tutor.” It should ultimately demonstrate:

## Student

- safe useful natural learning,
- current-question authority,
- optional grounding,
- adaptive teaching,
- sufficient child-usable input/representation for recurring use.

## Intelligence

- completed Segment Review,
- Session-authorized Event/Evidence,
- State/Patterns,
- compact relevant Card,
- later personalization that helps without fighting current behavior,
- audit/reprocessing.

## Parent

- meaningful learning state,
- Evidence behind important conclusions,
- useful content/Grade controls,
- AI usage/cost visibility,
- safety/boundary controls,
- enough explanation to understand important personalization changes.

## Operations

- one reliable real-use environment,
- durable data,
- running background lifecycle,
- failure/retry/recovery visibility,
- provider replaceability through Model Gateway.

The exact current task to reach the next gate belongs in `PROJECT_STATE.md` / `TASKS.md`.

---

# 23. Deferred Architecture

Do not introduce without demonstrated need and Product Owner approval:

- microservices,
- Kubernetes/distributed orchestration,
- graph DB / universal knowledge graph,
- Redis/Celery,
- dedicated vector DB,
- native mobile app,
- multi-family SaaS/billing,
- teacher/classroom tooling,
- generic autonomous-agent framework,
- chains of AI evaluators on every Tutor turn,
- second normal-turn Subject/Topic/Candidate classifier,
- ordinary semantic Session summarizer after Segment Reviews,
- archive vector memory / automatic prior-session semantic injection,
- advanced ML/clustering,
- large generic artifact marketplace,
- deployment redesign merely to activate an existing process.

Any proposal for one must identify the concrete current problem, evidence current architecture is insufficient, operational cost/complexity, migration path, and why a simpler option fails.

---

# 24. Change Rules

Explicit Product Owner approval is required before changing:

- product/learning philosophy,
- Evidence rubric meanings,
- Pattern lifecycle semantics,
- Segment Review / Session authority boundary,
- child-safety / Parent Boundary semantics,
- current-behavior-over-history principle,
- source/rebuildability principle,
- Student vs Parent UX separation,
- Modular Monolith direction,
- frozen capability execution status.

---

# 25. Operational Definition of Success

The project moves correctly when new work improves one or more of:

- Lina understands better,
- Lina interacts more naturally,
- Tutor uses relevant context more effectively,
- Learner Intelligence becomes more useful/auditable,
- Parent gains clearer understanding/control,
- code remains easier to evolve,
- operations remain reliable,
- cost/latency stay visible/manageable,

without damaging protected boundaries.

It is not progress merely because more AI calls, dashboards, agents, data, or dependencies exist.

---

# 26. Final Implementation Principle

> **Preserve the accepted smallest complete learning-intelligence loop. Operate it reliably. Learn from real Lina use. Promote approved broader capabilities only when sequencing/evidence justifies them.**

The correct implementation is not the one that builds the largest number of approved ideas fastest. It is the one that keeps learning coherent, traceable, child-usable, rebuildable, operationally simple, and easy to evolve.
