# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating map for Codex/AI agents working in this repository. Do not duplicate the full product specification here. Read the governing documents needed for the task before changing code.

## Governing References

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — product purpose, boundaries, approved architecture, Tutor behavior, multimodal/artifact principles, Grade rules, system invariants.
2. `docs/LEARNING_INTELLIGENCE_SPEC.md` — Events, Evidence, Current State, Patterns, Intelligence Card, measurement rules, reprocessing.
3. `docs/CHILD_SAFETY_POLICY.md` — non-overridable child safety and Parent Learning Boundaries.
4. `docs/IMPLEMENTATION_PLAN.md` — execution architecture, phases, dependencies, gates, deferred work.
5. `docs/TECHNOLOGY_REUSE_CATALOG.md` — approved reusable technology/component candidates and mandatory pre-build evaluation rules.
6. `project-state/PROJECT_STATE.md` — current operational reality and next action.
7. `TASKS.md` — actual executable work queue.

If documents conflict, stop and surface the conflict. Do not silently choose a new product direction.

## Execution Rules

- Execute only `READY` tasks from `TASKS.md`, normally one task or one tightly related task group at a time.
- Do not skip dependencies or mandatory gates.
- Prefer the simplest implementation that preserves approved boundaries and rebuildability.
- **Reuse-first, not dependency-first:** before custom-building a substantial UI, chat, retrieval, or Learning Artifact subsystem, inspect the applicable candidates in `docs/TECHNOLOGY_REUSE_CATALOG.md`.
- For any catalog item marked `EVALUATE BEFORE CUSTOM BUILD`, record an `ADOPT / PARTIAL ADOPT / REJECT` decision and rationale before the equivalent custom infrastructure is considered complete.
- Reuse package/component-level capabilities when useful; do not adopt an entire platform merely to obtain one feature.
- Keep the UX simple even when internals are modular.
- Do not introduce a new infrastructure service, agent framework, graph database, dedicated vector DB, Redis/Celery, or microservice without explicit approval and demonstrated need.
- Do not implement future phases merely because their interfaces are easy to scaffold.
- Do not silently expand Math/Science scope into a generic education platform.

## Protected Architectural Areas

The following require Product Owner approval before changing their meaning:

- Event → Evidence → State/Pattern → Intelligence Card architecture.
- Learning Intelligence Rubric semantics and Pattern Rules.
- Mastery/confidence as derived decision views, not source truth.
- Current behavior outranking historical personalization.
- Raw interaction and original student work preservation.
- Book as Curriculum Anchor, not Teaching Authority.
- Parent/Admin-controlled Grade activation through new Grade books.
- Compact Grade Transition Card rather than full prior-Grade runtime transfer.
- Multimodal student input and separation of student originals from AI-derived annotations/reconstructions.
- Child-safety baseline and Parent Learning Boundary semantics, including explicit runtime policy enforcement rather than prompt-only enforcement.
- Strategy-effectiveness anti-self-confirmation: Tutor strategy selection/use is not confirming Evidence without an observable Lina outcome.
- Modular Monolith architecture unless scaling evidence justifies a change.
- Early Lina Calibration Checkpoint before Phase 3 and Real Lina Decision Gate after Phase 4.

## AI/Model Rules

- Services request AI by task through the Model Gateway; do not call provider SDKs from arbitrary routes/services.
- Normal Tutor turns target one primary Tutor call.
- Tutor may emit hidden Candidate Event metadata; it does not directly write stable learner conclusions.
- Session Evidence consolidation happens at session level, not as an extra evaluator call after every message.
- AI handles semantic/cognitive work; deterministic code handles counts, recency, lifecycle, weights, effective policy routing, and state transitions where practical.
- Safety/boundary enforcement must consume the explicit policy-engine decision contract; Tutor prompt text alone is not enforcement.
- For teaching-strategy patterns, only observable Lina outcomes may confirm/challenge effectiveness; choosing the strategy because history recommended it is not Evidence.
- Log task, provider, model, tokens/usage, latency, estimated cost, success/failure, and fallback.

## Content Rules

- Before building substantial custom RAG/index plumbing, evaluate the approved native Docling/pgvector baseline against the official Docling + LlamaIndex candidate as required by the reuse catalog.
- Preserve original uploaded books/documents.
- Docling is the baseline structural document-understanding layer.
- Educational semantics are a separate derived layer.
- Prefer structural/hierarchical retrieval; do not make blind fixed-token chunking the primary strategy.
- Reprocessing must be possible from the original source.

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
5. update `TASKS.md` status,
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
