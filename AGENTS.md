# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating map for Codex/AI agents working in this repository. Do not duplicate the full product specification here. Read the governing documents needed for the task before changing code.

## Governing References

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — product purpose, boundaries, approved architecture, Tutor behavior, multimodal/artifact principles, Grade rules, system invariants.
2. `docs/LEARNING_PRODUCT_ROADMAP.md` — approved product-evolution decisions, ordered capability roadmap, superseded assumptions, dependencies, and validation gates. Roadmap items are not executable until promoted to executable task scope.
3. `docs/LEARNING_INTELLIGENCE_SPEC.md` — Events, Evidence, Current State, Patterns, Intelligence Card, measurement rules, reprocessing.
4. `docs/CHILD_SAFETY_POLICY.md` — non-overridable child safety and Parent Learning Boundaries.
5. `docs/IMPLEMENTATION_PLAN.md` — execution architecture, phases, dependencies, gates, deferred work.
6. `docs/TECHNOLOGY_REUSE_CATALOG.md` — approved reusable technology/component candidates and mandatory pre-build evaluation rules.
7. `docs/SUBJECT_SCOPE_POLICY.md` — governing SCOPE-01 cross-subject, Broad Subject, optional school-context, and future School-Focused policy when subject scope is relevant.
8. `docs/SUBJ_01_IMPLEMENTATION_SPEC.md` — approved bounded execution contract for SUBJ-01 while that task is active.
9. `project-state/PROJECT_STATE.md` — current operational reality and next action.
10. `TASKS.md` — durable task history and executable work queue, subject to an explicit newer task-specific governing spec/current-state transition approved by the Product Owner.

### Roadmap and task coordination

The Roadmap records approved product-evolution decisions, sequencing, dependencies, and validation gates. It does not by itself make work executable.

Normally an item must be `READY` in `TASKS.md`. A newer Product Owner-approved task-specific governing spec may explicitly close a prerequisite, mark its successor `READY`, and temporarily supersede a stale status line in the large historical `TASKS.md`; that override must also be reflected in `project-state/PROJECT_STATE.md` and must name the exact bounded task. Do not generalize such an override to other tasks.

**Current explicit transition:** `docs/SUBJECT_SCOPE_POLICY.md` closes `SCOPE-01` as `DONE / APPROVED`, `docs/SUBJ_01_IMPLEMENTATION_SPEC.md` makes `SUBJ-01` `READY`, and `project-state/PROJECT_STATE.md` records SUBJ-01 as the next action. Any older `TASKS.md` row still showing `SCOPE-01 = READY` or `SUBJ-01 = BLOCKED` is stale for these two task IDs only and must not block SUBJ-01 execution. Consolidate those historical task rows when safely editing `TASKS.md`; do not rewrite unrelated task history.

If governing documents conflict outside an explicit approved override like the one above, stop and surface the conflict rather than silently choosing a product direction.

## Execution Rules

- Execute only an explicitly `READY` task from the governing task queue/current approved task-specific spec, normally one task or one tightly related task group at a time.
- A Roadmap item is **not executable** merely because it is approved or ordered. It must first be promoted into an executable task with concrete scope and status.
- Do not skip dependencies or mandatory gates.
- Prefer the simplest implementation that preserves approved boundaries and rebuildability.
- **Reuse-first, not dependency-first:** before custom-building a substantial UI, chat, retrieval, or Learning Artifact subsystem, inspect the applicable candidates in `docs/TECHNOLOGY_REUSE_CATALOG.md`.
- For any catalog item marked `EVALUATE BEFORE CUSTOM BUILD`, record an `ADOPT / PARTIAL ADOPT / REJECT` decision and rationale before the equivalent custom infrastructure is considered complete.
- Reuse package/component-level capabilities when useful; do not adopt an entire platform merely to obtain one feature.
- Keep the UX simple even when internals are modular.
- Do not introduce a new infrastructure service, agent framework, graph database, dedicated vector DB, Redis/Celery, or microservice without explicit approval and demonstrated need.
- Do not implement future phases merely because their interfaces are easy to scaffold.
- Do not silently expand the current Math-first implementation into a generic education platform; implement only the approved cross-subject core boundary needed by SUBJ-01.

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
- For the new Segment Review path, durable Event/Evidence Subject authority comes from the reviewed Segment/Finding lineage, not blindly from a Session-level default Subject. Subject conflict or unresolved attribution fails closed rather than contaminating another Subject.
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
- Early Lina Calibration Checkpoint before Phase 3 and Real Lina Decision Gate after Phase 4, subject to the currently approved Roadmap sequencing corrections.

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
- Segment Review is the authoritative semantic-analysis point for `LEARNING` vs `NON_LEARNING`, primary Broad Subject, concept/topic, and optional source-grounded school alignment in the new SUBJ-01 contract.
- AI handles semantic/cognitive work, including the normal Tutor call's turn-level Mode, Strategy, Method, and prior-method-relation decision; deterministic code handles allowed-value validation, safety, counts, recency, lifecycle, weights, persistence, effective policy routing, and state transitions where practical. No extra classifier/model call is authorized for those Tutor decisions.
- Safety/boundary enforcement must consume the explicit policy-engine decision contract; Tutor prompt text alone is not enforcement.
- For teaching-strategy patterns, only observable Lina outcomes may confirm/challenge effectiveness; choosing the strategy because history recommended it is not Evidence.
- Log task, provider, model, tokens/usage, latency, estimated cost, success/failure, and fallback.

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

- Before building a generic custom Artifact DSL/renderer layer, evaluate the approved OpenMAIC package-level renderer/DSL candidate; do not adopt the OpenMAIC platform architecture by default.
- Prefer typed Artifact Specifications and reusable renderers.
- MVP renderer stack: native React/SVG, Motion, JSXGraph, React Konva, MathLive.
- Custom generated HTML/SVG is fallback-only and must be sandboxed/sanitized.
- Artifact failure must never block the Tutor conversation.
- Visual motion must serve a learning objective, not decoration alone.

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
6. update `project-state/PROJECT_STATE.md` if current reality or next action changed.

When a test cannot be run, state exactly why and leave the task unverified rather than marking it complete.

## Data / Migration Rules

- Use migrations for schema changes.
- Avoid destructive migrations unless explicitly approved and backed by a migration/rebuild path.
- Derived learning intelligence must remain versioned and rebuildable.
- Preserve provenance from derived data to raw source/processing run.

## Approval Required Before

- changing governing docs or protected invariants,
- weakening child-safety behavior,
- changing approved rubric state meanings,
- bypassing the Model Gateway,
- adding a new core infrastructure dependency not already approved/evaluated by the technology reuse process,
- changing architecture from Modular Monolith,
- continuing past a mandatory decision gate without recorded approval,
- deleting raw learner history or original source files.

## Project-State Discipline

`project-state/PROJECT_STATE.md` is a short operational snapshot, not a diary or changelog. Keep only:

- current goal,
- current reality,
- active decisions,
- protected areas,
- active risks,
- next recommended action,
- critical references.
