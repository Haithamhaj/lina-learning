# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating map for Codex/AI agents working in this repository. Do not duplicate the full product specification here. Read the governing documents needed for the task before changing code.

## Governing References

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — stable approved product purpose, boundaries, architecture, Tutor behavior, multimodal/artifact principles, Grade rules, system invariants.
2. `docs/LEARNING_PRODUCT_ROADMAP.md` — approved product-evolution decisions, ordered capability roadmap, superseded assumptions, dependencies, and validation gates. Roadmap items are not executable until promoted to executable task scope.
3. `docs/LEARNING_INTELLIGENCE_SPEC.md` — canonical Events, Evidence, Current State, Patterns, Segment Review, Session authority, Intelligence Card, measurement rules, reprocessing.
4. `docs/CHILD_SAFETY_POLICY.md` — non-overridable child safety and Parent Learning Boundaries.
5. `docs/IMPLEMENTATION_PLAN.md` — execution architecture, phases, dependencies, gates, deferred work.
6. `docs/TECHNOLOGY_REUSE_CATALOG.md` — approved reusable technology/component candidates and mandatory pre-build evaluation rules.
7. `docs/SUBJECT_SCOPE_POLICY.md` — governing SCOPE-01 cross-subject, Broad Subject, optional school-context, and future School-Focused policy when subject scope is relevant.
8. `docs/SUBJ_01_IMPLEMENTATION_SPEC.md` — historical bounded execution contract for accepted SUBJ-01; do not treat its former transition as current work.
9. `project-state/PROJECT_STATE.md` — **current operational reality and current next action**.
10. `TASKS.md` — durable task history and executable/current task state, subject to an explicit newer Product Owner-approved task-specific governing transition recorded in Project State.

### Document authority and task coordination

Different documents own different truth:

- `PROJECT_REFERENCE.md` owns stable product truth.
- `LEARNING_INTELLIGENCE_SPEC.md` owns Learning Intelligence semantics.
- `LEARNING_PRODUCT_ROADMAP.md` owns approved product evolution/sequencing, not current execution.
- `IMPLEMENTATION_PLAN.md` owns technical implementation direction, not current next-task status.
- `PROJECT_STATE.md` owns current operational truth and current next action.
- `TASKS.md` owns durable task/execution state.

The Roadmap records approved product-evolution decisions, sequencing, dependencies, and validation gates. It does not by itself make work executable.

Normally an item must be `READY` in `TASKS.md`. A newer Product Owner-approved task-specific governing spec/current-state transition may explicitly override a stale historical row for one bounded task; that override must be reflected in `PROJECT_STATE.md` and must not be generalized.

**Current transition rule:** do not hardcode a historical next task here. `SCOPE-01`, `SUBJ-01`, `DEC-01`, `DEC-02`, `REP-01`, `LANG-01`, `CAND-03`, and `CAND-02` are accepted at the current baseline. Read the current action from `project-state/PROJECT_STATE.md` and `TASKS.md` / the current Product Owner-approved bounded task spec. During `DOC-SYNC-01`, documentation synchronization is the only approved active work. If the Product Owner later accepts it, Project State may promote `RL-01`; do not infer that promotion before acceptance.

No existing historical record automatically promotes `MATH-01`, `ID-01`, `EDU-ERR-01`, `REC-25`, `LR-D04B`, Voice, Vision, Science production, Learning Canvas, Artifact Engine, Parent Dashboard expansion, or a deployment redesign.

If governing documents conflict outside an explicit approved override, stop and surface the conflict rather than silently choosing a product direction.

## Execution Rules

- Execute only an explicitly `READY` task or the exact Product Owner-approved current bounded task from the governing task/state records, normally one task or one tightly related task group at a time.
- A Roadmap item is **not executable** merely because it is approved or ordered. It must first be promoted into executable scope.
- Do not skip dependencies or mandatory gates.
- Prefer the simplest implementation that preserves approved boundaries and rebuildability.
- **Reuse-first, not dependency-first:** before custom-building a substantial UI, chat, retrieval, or Learning Artifact subsystem, inspect the applicable candidates in `docs/TECHNOLOGY_REUSE_CATALOG.md`.
- For any catalog item marked `EVALUATE BEFORE CUSTOM BUILD`, record an `ADOPT / PARTIAL ADOPT / REJECT` decision and rationale before the equivalent custom infrastructure is considered complete.
- Reuse package/component-level capabilities when useful; do not adopt an entire platform merely to obtain one feature.
- Keep the UX simple even when internals are modular.
- Do not introduce a new infrastructure service, agent framework, graph database, dedicated vector DB, Redis/Celery, microservice, or deployment redesign without explicit approval and demonstrated need.
- Do not implement future phases merely because their interfaces are easy to scaffold.
- The current production proving ground is Math-first. Math + Science, Voice, Vision, handwriting/drawing Evidence, visual/interactive artifacts, broader Parent UX, and Grade production remain approved product direction but frozen until explicitly promoted.
- Replit configuration is an environment convenience, not product architecture.

## Protected Architectural Areas

The following require Product Owner approval before changing their meaning:

- Raw interaction → completed Segment semantic review → Session-authorized
  Evidence → Current State / Patterns → Learner Intelligence Card →
  personalization architecture. Segment semantic review is protected;
  Session remains the durable intelligence-authority boundary. Staged Segment
  findings are not Learner Intelligence, Candidate Events are provisional
  hints rather than mandatory Evidence authority, and no second learner-memory
  system is authorized. Current behavior and the existing Pattern
  counters/lifecycle remain protected.
- Learning Intelligence Rubric semantics and Pattern Rules.
- Mastery/confidence as derived decision views, not source truth.
- Current behavior outranking historical personalization.
- Raw interaction and original student work preservation.
- A Learning Thread is the session-local contiguous Conversation Segment; there is no third Thread entity.
- One technical Session may contain multiple session-local Segments with different Subjects; one Learning Segment has one primary Broad Subject for durable Evidence attribution.
- `LEARNING` and `NON_LEARNING / CASUAL` Segment semantics are distinct. Casual conversation is not academic Evidence, and `GENERAL_KNOWLEDGE` is reserved for genuine learning that lacks a better Broad Subject.
- Broad Subject classification is controlled/versioned and separate from Lina's actual Grade/school Subject registry. School Subject, Domain Path, Unit, Lesson, Page, and curriculum-position metadata are optional/source-grounded and must not be invented when the source is absent.
- School relationship uses `SCHOOL_ALIGNED`, `EXTENDED`, or `UNKNOWN`; absence of school material must not be treated automatically as `EXTENDED`.
- For the current Segment Review path, durable Event/Evidence Subject authority comes from the reviewed Segment/Finding lineage, not blindly from a Session-level default Subject. Subject conflict or unresolved attribution fails closed rather than contaminating another Subject.
- The future Adaptive/Open and School-Focused/Book-Led Parent policies share the same Learning Intelligence Core; no second Evidence/State/Pattern memory architecture is authorized.
- A Durable Conversation Topic is optional Grade-scoped navigation metadata, never Learner Intelligence, Evidence, curriculum authority, or Safety authority.
- Hybrid Segment Context is conversational continuity only: Current Multimodal Turn, Full Immediate Exchange, compact Structured Segment State, and relevance-selected complete raw Exchanges from the current Segment are separate from Learner Intelligence, Evidence, pedagogy, Safety, and RAG authority. Raw messages and original assets remain source authority.
- A blind shared character window must not be the authority for conversation selection, and selected Immediate Exchange messages must not be positionally character-sliced. Capacity/token budgets are final guardrails calibrated from real usage, not a relevance algorithm.
- Do not inject a full Session or prior-session raw transcripts into normal Tutor input. No extra classifier or summarizer model call, archive retrieval, memory service, or CTX-03 runtime work is authorized without measured need and Product Owner approval.
- Structured Segment State is compact, source-linked, rebuildable conversational metadata only. It cannot become Evidence, Learner Intelligence, personalization, curriculum authority, or a Safety decision.
- Parent-owned Student Core Profile facts remain separate from Evidence-derived Learner Intelligence and conversation memory/context. Agents must not convert Parent factual profile fields into learning conclusions.
- Tutor availability is independent of whether curriculum/book grounding is available; grounding improves the interaction but must not become permission to learn.
- Retrieval is driven by the current question; school plans and curriculum position do not control what Lina is allowed or expected to ask now.
- Book and trusted references are grounding sources, not Teaching Authority. The Tutor may change explanation method when useful.
- Curriculum semantic extraction is optional enrichment and must not be a prerequisite for basic Tutor availability or learner-intelligence concept identification.
- **Current School Focus is superseded as a learning-path authority. Do not recreate it.**
- Parent/Admin-controlled Grade activation through new Grade books.
- Compact Grade Transition Card rather than full prior-Grade runtime transfer.
- Multimodal student input and separation of student originals from AI-derived annotations/reconstructions.
- A photographed textbook/page is learning/school context, not learner Evidence by identity alone. A photographed Student solution may support Evidence only through the governed Vision/Segment Review path after that capability is separately approved.
- Child-safety baseline and Parent Learning Boundary semantics, including explicit runtime policy enforcement rather than prompt-only enforcement.
- Strategy-effectiveness anti-self-confirmation: Tutor strategy selection/use is not confirming Evidence without an observable Lina outcome.
- TeachingStrategy (support/intervention flow) and TeachingMethod (pedagogical representation) are distinct and must not be collapsed.
- Teaching Methods remain a small, project-owned, versioned registry; they must not become a giant mutable Tutor persona or prompt.
- In the same primary Tutor call, Luna semantically determines the turn-level TeachingMode, TeachingStrategy, TeachingMethod, and relevant prior-method relation. Runtime code validates canonical values, lineage, safety, persistence, and structural consistency; it must not replace semantic understanding with keyword or phrase routing.
- Selecting a method is not Evidence of effectiveness. Any method identity used by Evidence must come from persisted, project-owned Tutor-turn state, never be invented by Evidence processing.
- Historical method ranking belongs only to LR-D04B after sufficient Evidence and approval; do not introduce MCP, agents, or infrastructure for this problem without approval.
- Do not add a separate conversation classifier, Subject classifier, Topic classifier, summarizer, archive-retrieval layer, or memory service without measured evidence and Product Owner approval.
- Modular Monolith architecture unless scaling evidence justifies a change.
- Limited Real-Lina interaction is verified; stable recurring/daily Lina use and longitudinal cross-session personalization remain separate verification horizons. Do not collapse those labels.

## AI/Model Rules

- Services request AI by task through the Model Gateway; do not call provider SDKs from arbitrary routes/services.
- Normal Tutor turns target one primary Tutor call.
- Tutor may emit hidden Candidate Event metadata; it does not directly write stable learner conclusions.
- No extra normal-turn Evidence evaluator or Subject/Topic classifier is authorized. Closed, structurally
  reviewable Segments may be reviewed asynchronously as background work, outside
  Tutor latency; deterministic reviewability does not decide educational meaning,
  and staged findings do not directly update personalization. Closed
  Session Finalization remains the durable activation boundary, is
  deterministic by default, and requires no broad semantic Session model call
  after Segment Reviews.
- Segment Review is the authoritative semantic-analysis point for `LEARNING` vs `NON_LEARNING`, primary Broad Subject, concept/topic, and optional source-grounded school alignment in the accepted SUBJ-01 contract.
- AI handles semantic/cognitive work, including the normal Tutor call's turn-level Mode, Strategy, Method, and prior-method-relation decision; deterministic code handles allowed-value validation, safety, counts, recency, lifecycle, weights, persistence, effective policy routing, and state transitions where practical. No extra classifier/model call is authorized for those Tutor decisions.
- Safety/boundary enforcement must consume the explicit policy-engine decision contract; Tutor prompt text alone is not enforcement.
- For teaching-strategy patterns, only observable Lina outcomes may confirm/challenge effectiveness; choosing the strategy because history recommended it is not Evidence.
- Log task, provider, model, tokens/usage, latency, estimated cost, success/failure, and fallback.
- Current real provider support may use OpenAI, but provider/model selection remains behind Model Gateway and must not be hardwired as permanent product architecture.

## Content Rules

- Preserve the approved native Docling + PostgreSQL/pgvector Hybrid Retrieval direction; do not restart RAG design without a concrete blocker.
- Preserve original uploaded books/documents and source provenance.
- Docling is the baseline structural document-understanding layer.
- Educational semantics are a separate, optional derived enrichment layer.
- Basic retrieval-ready content must not require semantic taxonomy completion once the Track A correction is implemented.
- Prefer structural/hierarchical retrieval; do not make blind fixed-token chunking the primary strategy.
- Reprocessing must be possible from the original source.
- Future trusted web references and Student-captured pages should enter through the existing Learning Source / Retrieval boundary rather than create a parallel RAG subsystem.

## Learning Artifact Rules

- Learning Artifacts are approved product direction but are **not currently executable unless explicitly promoted**.
- Before building a generic custom Artifact DSL/renderer layer, evaluate the approved OpenMAIC package-level renderer/DSL candidate; do not adopt the OpenMAIC platform architecture by default.
- Prefer typed Artifact Specifications and reusable renderers.
- Approved renderer direction: native React/SVG, Motion, JSXGraph, React Konva, MathLive when the capability is promoted and the concrete use case requires them.
- Custom generated HTML/SVG is fallback-only and must be sandboxed/sanitized.
- Artifact failure must never block the Tutor conversation.
- Visual motion must serve a learning objective, not decoration alone.
- A bounded Math readability fix does not automatically unfreeze the full Artifact Engine or Learning Canvas.

## UI / Experience Reuse Rules

- Use shadcn/ui as the baseline functional component layer unless a concrete task-level conflict is documented.
- Before hand-building full Student thread/composer/chat plumbing, evaluate `assistant-ui` against the FastAPI/SSE, attachment, persistence, custom message-part, and safety requirements in the reuse catalog.
- For Lina-facing visual design, inspect approved child/education visual references and component/motion sources, but preserve one coherent design system suitable for roughly age 10 rather than preschool styling.
- Motion is purposeful: orientation, feedback, explanation, celebration, or interaction — not visual noise.

## Verification Rules

A task is not complete because code exists. Before claiming completion:

1. run the task's listed verification,
2. run relevant unit/contract/integration tests,
3. verify no protected invariant was violated,
4. inspect logs/output for the changed path when applicable,
5. update `TASKS.md` status when safely modifying the historical queue, or record an explicit task-specific governing transition if the approved task spec temporarily supersedes a stale queue row,
6. update `project-state/PROJECT_STATE.md` if current reality or next action changed,
7. distinguish independent code review, Codex-reported automated execution, real-model verification, browser verification, limited Real-Lina use, stable daily Real-Lina use, and longitudinal Real-Lina validation rather than collapsing them into one label.

When a test cannot be run, state exactly why and leave that evidence category unverified rather than marking it complete.

### Real-model environment discovery and protected local work

Implementation work belongs in the isolated worktree:

`/Users/haitham/development/lina-learning-ctx03`

For real-model/provider verification, the absence of `.env` in that isolated worktree does **not** by itself mean provider configuration is unavailable. If required configuration is absent, the original repository checkout may be inspected **read only** for existing local environment/provider configuration when needed.

Never print, echo, display, copy, modify, commit, or hardcode secret values; never copy an original checkout `.env` into the isolated worktree or add environment files to Git. Report only which approved configuration locations/types were checked and whether required configuration was available.

The original checkout may not be used for implementation changes. Known protected local Eureka-related dirty files there include:

- `scripts/verify_eureka_semantic_representation.py`
- `services/content/semantics.py`
- `tests/test_eureka_semantic_verifier.py`
- `tests/test_semantic_batch_planning.py`

Never stash, reset, clean, overwrite, or incidentally refactor them.

## Data / Migration Rules

- Use migrations for schema changes.
- Avoid destructive migrations unless explicitly approved and backed by a migration/rebuild path.
- Derived learning intelligence must remain versioned and rebuildable.
- Preserve provenance from derived data to raw source/processing run.

## Approval Required Before

- changing governing product/architecture meaning or protected invariants,
- weakening child-safety behavior,
- changing approved rubric state meanings,
- bypassing the Model Gateway,
- adding a new core infrastructure dependency not already approved/evaluated by the technology reuse process,
- changing architecture from Modular Monolith,
- continuing past a mandatory decision gate without recorded approval,
- deleting raw learner history or original source files,
- promoting a deferred approved capability into implementation.

## Project-State Discipline

`project-state/PROJECT_STATE.md` is a short operational snapshot, not a diary or changelog. Keep only:

- current goal,
- current reality,
- active decisions,
- protected areas,
- active risks,
- next recommended action,
- critical references.
