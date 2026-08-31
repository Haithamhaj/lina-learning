# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating map for Codex/AI agents working in this repository. Do not duplicate the full product specification here. Read the governing documents needed for the task before changing code.

## Governing References

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — stable product purpose, boundaries, approved architecture, Tutor behavior, multimodal/artifact principles, Grade rules, and system invariants.
2. `docs/LEARNING_INTELLIGENCE_SPEC.md` — canonical Events, Evidence, Current State, Patterns, Intelligence Card, Segment Review, Session authority, and reprocessing semantics.
3. `docs/CHILD_SAFETY_POLICY.md` — non-overridable child safety and Parent Learning Boundaries.
4. `docs/LEARNING_PRODUCT_ROADMAP.md` — approved product-evolution direction, capability sequencing, dependencies, and validation gates. Roadmap presence is not execution approval.
5. `docs/IMPLEMENTATION_PLAN.md` — implementation architecture, sequencing principles, dependencies, gates, and deferred complexity.
6. `docs/TECHNOLOGY_REUSE_CATALOG.md` — approved reusable technology/component candidates and mandatory pre-build evaluation rules.
7. `docs/SUBJECT_SCOPE_POLICY.md` — governing cross-subject, Broad Subject, optional school-context, and future School-Focused policy when subject scope is relevant.
8. `project-state/PROJECT_STATE.md` — **current operational reality and current next action**.
9. `TASKS.md` — durable task history and executable/current task state, subject to an explicit newer Product Owner-approved task-specific transition recorded in Project State.

Task-specific implementation specs may govern an explicitly active bounded task when they are named by `PROJECT_STATE.md` / `TASKS.md`. Historical task-specific specs do not remain current merely because they exist.

### Document authority rule

Different documents own different truth:

- `PROJECT_REFERENCE.md` owns stable product truth.
- `LEARNING_INTELLIGENCE_SPEC.md` owns Learning Intelligence semantics.
- `LEARNING_PRODUCT_ROADMAP.md` owns approved future sequencing, not current execution.
- `IMPLEMENTATION_PLAN.md` owns technical direction, not current next-task status.
- `PROJECT_STATE.md` owns current operational truth.
- `TASKS.md` owns durable task/execution state.

Historical phase/task text is provenance. It must not override a newer accepted governing decision or current Product Owner-approved state.

### Current transition discipline

Do **not** hardcode a historical “next task” in this file. `SCOPE-01`, `SUBJ-01`, `DEC-01`, `DEC-02`, `REP-01`, `LANG-01`, `CAND-03`, and `CAND-02` are accepted at the current baseline. Their former transitions are historical.

The current action must be read from `project-state/PROJECT_STATE.md` and the current task record. During `DOC-SYNC-01`, documentation synchronization is the only approved active work. If that review is accepted, Project State may then promote `RL-01`; do not infer that promotion before acceptance.

No existing record automatically promotes `MATH-01`, `ID-01`, `EDU-ERR-01`, `REC-25`, `LR-D04B`, Voice, Vision, Science production, Learning Canvas, Artifact Engine, or Parent Dashboard expansion.

If current governing documents conflict outside an explicit Product Owner-approved override, stop and surface the conflict rather than silently choosing a product direction.

## Execution Rules

- Execute only an explicitly approved/ready task from the governing current state/task queue, normally one task or one tightly related group at a time.
- A Roadmap item is **not executable** merely because it is approved or ordered.
- Do not skip dependencies or mandatory gates.
- Prefer the simplest implementation that preserves approved boundaries and rebuildability.
- **Reuse-first, not dependency-first:** before custom-building a substantial UI, chat, retrieval, or Learning Artifact subsystem, inspect applicable candidates in `docs/TECHNOLOGY_REUSE_CATALOG.md`.
- For any catalog item marked `EVALUATE BEFORE CUSTOM BUILD`, record `ADOPT / PARTIAL ADOPT / REJECT` with rationale before equivalent custom infrastructure is considered complete.
- Reuse package/component-level capabilities when useful; do not adopt an entire platform to obtain one feature.
- Keep UX simple even when internals are modular.
- Do not introduce a new infrastructure service, generic agent framework, graph database, dedicated vector DB, Redis/Celery, microservice architecture, or deployment redesign without explicit approval and demonstrated need.
- Do not implement future phases merely because interfaces are easy to scaffold.
- Math is the current production proving ground; Math + Science and multimodal/visual capabilities remain approved product direction but frozen until explicitly promoted.
- Replit configuration is an environment convenience, not product architecture.

## Protected Architectural Areas

The following require Product Owner approval before changing their meaning:

- **Raw Interaction → completed Segment semantic review → Session-authorized Evidence → Current State / Patterns → Learner Intelligence Card → relevant later personalization.** Segment is the semantic review unit; Session is the durable intelligence-authority boundary. Staged Segment findings are not Learner Intelligence, Candidate metadata is provisional, and no second learner-memory system is authorized.
- Learning Intelligence Rubric semantics and deterministic Pattern Rules.
- Mastery/confidence as derived decision views, not source truth.
- Current behavior outranking historical personalization.
- Raw interaction and original Student work preservation.
- One primary Tutor call per normal Student turn.
- No second normal-turn Candidate/Subject/Topic classifier, broad semantic Session summarizer, Evidence evaluator, or agent chain without measured need and Product Owner approval.
- A Learning Thread is the session-local contiguous Segment; there is no third Thread entity.
- One technical Session may contain multiple session-local Segments with different Subjects; one Learning Segment has one primary Broad Subject for durable attribution.
- `LEARNING` and `NON_LEARNING / CASUAL` Segment semantics are distinct. Casual conversation is not academic Evidence.
- Broad Subject classification is controlled/versioned and separate from actual Grade/school Subject registry.
- School relationship is `SCHOOL_ALIGNED`, `EXTENDED`, or `UNKNOWN`; missing school material must not become `EXTENDED` automatically.
- Durable Event/Evidence Subject authority comes from reviewed Segment/Finding lineage, not blindly from a Session-level default.
- Subject conflict/unresolved attribution fails closed rather than contaminating another Subject.
- Future Adaptive/Open and School-Focused/Book-Led Parent policies share the same Learning Intelligence core; no second memory architecture is authorized.
- A Durable Conversation Topic is optional Grade-scoped navigation metadata, never Learner Intelligence, Evidence, curriculum authority, or Safety authority.
- Hybrid Segment Context is conversational continuity only: Current Turn, Full Immediate Exchange, compact Structured Segment State, and relevance-selected complete raw Exchanges from the Current Segment remain separate from Learner Intelligence, pedagogy, Safety, and RAG authority.
- A blind shared character window is not conversation-selection authority. Capacity/token limits are final guardrails, not relevance algorithms.
- Do not inject full Session or prior-session raw transcripts into normal Tutor input.
- Structured Segment State is compact, source-linked, rebuildable conversational metadata only. It cannot become Evidence, Learner Intelligence, personalization, curriculum authority, or Safety decision.
- Parent-owned Student Core Profile facts remain separate from Evidence-derived Learner Intelligence and conversation context.
- Tutor availability is independent of curriculum/book availability.
- Retrieval is driven by the current question; school plans/curriculum position do not control what Lina may ask now.
- Book/trusted references are grounding sources, not Teaching Authority.
- Curriculum semantic extraction is optional enrichment and is not a prerequisite for Tutor/basic RAG/Learning Intelligence.
- **Current School Focus is superseded as a learning-path authority. Do not recreate it.**
- Parent/Admin-controlled Grade activation and compact transition intelligence rather than full prior-Grade runtime transfer.
- Multimodal Student input and separation of originals from AI-derived interpretation/annotation/reconstruction.
- A photographed page is context/source material, not learner Evidence by identity alone. A photographed Student solution may support Evidence only through an explicitly authorized Vision + Segment Review path.
- Child-safety baseline and Parent Learning Boundary semantics, including runtime enforcement rather than prompt-only enforcement.
- TeachingStrategy and TeachingMethod are distinct.
- TeachingMethod selection/use is not effectiveness Evidence; observable Lina outcome plus persisted method lineage is required.
- Teaching Methods remain a small, project-owned, versioned registry rather than a mutable Tutor persona.
- Same-primary-call semantic decisions may include Mode, Strategy, Method, prior-method relation, Segment relation, provisional Broad Subject, and Parent Boundary applicability; runtime validates/persists canonical values rather than replacing semantic understanding with keyword routing.
- Historical method ranking belongs only to an explicitly promoted evidence-dependent track; do not create a new profile subsystem for it.
- Modular Monolith architecture unless scaling evidence justifies change.
- Approved Voice, Vision, Science, visual artifact, Parent expansion, and Grade-production directions remain frozen until their sequencing/evidence gates explicitly promote them.

## AI / Model Rules

- Services request AI by task through Model Gateway; do not call provider SDKs from arbitrary routes/services.
- Normal Tutor turns use one primary Tutor call.
- Tutor may emit hidden Candidate metadata; it does not directly write stable learner conclusions.
- Closed structurally reviewable Segments may be reviewed asynchronously outside Tutor latency. Structural reviewability does not determine educational meaning.
- Segment Review is semantic authority for completed learning episodes and reviewed Broad Subject/school relationship.
- Session Finalization is the deterministic durable activation boundary and requires no ordinary semantic Session model call after Segment Reviews.
- AI handles semantic/cognitive work. Deterministic code handles allowed-value validation, safety enforcement, counts, recency, lifecycle, weights, persistence, authority, and state transitions where practical.
- Safety/boundary enforcement consumes explicit system/Parent policy; prompt text alone is not enforcement.
- For strategy/method effectiveness, only observable Lina outcome may support/challenge Evidence; selecting the strategy/method is not self-confirmation.
- Log task, provider, model, usage, latency, estimated cost, success/failure, fallback where applicable, and safe lineage identifiers.
- Current implemented real provider support may use OpenAI, but provider/model selection must remain behind Model Gateway and must not be hardwired as permanent product architecture.

## Content Rules

- Preserve approved native Docling + PostgreSQL/pgvector structural/hybrid retrieval direction; do not restart RAG design without a concrete blocker.
- Preserve original uploaded books/documents and provenance.
- Docling is baseline structural processing; educational semantics are separate optional enrichment.
- Basic retrieval-ready content does not require semantic taxonomy completion.
- Prefer structural/hierarchical retrieval; do not make blind fixed-token chunking primary.
- Reprocessing must be possible from original source.
- Future trusted references and Student-captured pages enter through the existing Learning Source/Retrieval boundary rather than a parallel RAG stack.

## Learning Artifact Rules

- Learning Artifacts are approved product direction but **not currently executable unless explicitly promoted**.
- Before building a generic custom Artifact DSL/renderer layer, evaluate approved package-level candidates when the active task requires it.
- Prefer typed Artifact Specifications and reusable renderers.
- AI-generated custom HTML/SVG is fallback-only and must be sandboxed/sanitized under the approved capability.
- Arbitrary unsandboxed AI JavaScript is rejected.
- Artifact failure must never block Tutor conversation.
- Motion/interaction must serve a learning objective.

## UI / Experience Reuse Rules

- Use shadcn/ui as the baseline functional component layer unless a concrete task-level conflict is documented.
- Before hand-building a large new chat/attachment/artifact subsystem, evaluate applicable reuse candidates in the catalog.
- Preserve a coherent child-appropriate visual system suitable around Grade 5 rather than preschool/corporate styling.
- Motion is purposeful: orientation, feedback, explanation, celebration, or interaction — not noise.

## Verification Rules

A task is not complete because code or documents exist. Before claiming completion:

1. run the task's required verification,
2. run relevant unit/contract/integration checks,
3. verify no protected invariant changed accidentally,
4. inspect changed runtime/output when applicable,
5. update task state when appropriate,
6. update `project-state/PROJECT_STATE.md` when current reality/next action changes,
7. distinguish independent code review, Codex-reported automated execution, real-model verification, browser verification, limited Real-Lina use, stable daily Real-Lina use, and longitudinal Real-Lina validation rather than collapsing them into one label.

When a test cannot be run, state exactly why and leave that evidence category unverified.

### Real-model environment discovery and protected local work

Implementation work belongs in the isolated worktree:

`/Users/haitham/development/lina-learning-ctx03`

The original checkout may be inspected **read-only** for existing local environment/provider configuration when required for real-model verification. Never stash, reset, clean, overwrite, refactor incidentally, or otherwise disturb protected local work.

Known protected Eureka-related dirty files in the original checkout include:

- `scripts/verify_eureka_semantic_representation.py`
- `services/content/semantics.py`
- `tests/test_eureka_semantic_verifier.py`
- `tests/test_semantic_batch_planning.py`

Never print, echo, display, copy, commit, or hardcode secret values. Do not copy an original checkout `.env` into the isolated worktree. Report only whether required approved configuration was available.

## Data / Migration Rules

- Use migrations for schema changes.
- Avoid destructive migrations unless explicitly approved with rebuild/migration path.
- Derived Learning Intelligence stays versioned and rebuildable.
- Preserve provenance from derived data to raw source/processing run.

## Approval Required Before

- changing governing product/architecture meaning or protected invariants,
- weakening child-safety behavior,
- changing rubric meanings,
- bypassing Model Gateway,
- adding core infrastructure/deployment complexity not already approved,
- changing Modular Monolith architecture,
- continuing past a mandatory decision gate without approval,
- deleting raw learner history or original source files,
- promoting a deferred approved capability into implementation.

## Project-State Discipline

`project-state/PROJECT_STATE.md` is a short operational snapshot, not a diary/changelog. Keep only:

- current goal,
- current reality,
- active decisions,
- protected areas,
- active risks,
- next recommended action,
- critical references.
