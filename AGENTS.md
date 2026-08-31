# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating map for Codex/AI agents working in this repository. It does not duplicate the full product specification. Read the governing documents relevant to the current task before changing code.

## Governing References

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — stable approved product truth and protected product boundaries.
2. `docs/LEARNING_PRODUCT_ROADMAP.md` — approved product-evolution direction; roadmap presence alone is not execution approval.
3. `docs/LEARNING_INTELLIGENCE_SPEC.md` — canonical Learning Intelligence semantics and authority.
4. `docs/CHILD_SAFETY_POLICY.md` — non-overridable child safety and Parent Learning Boundaries.
5. `docs/IMPLEMENTATION_PLAN.md` — technical implementation direction, sequencing, gates, and deferred architecture.
6. `docs/DAILY_USE_RELEASE_PLAN.md` — Product Owner-approved launch-first implementation addendum for Daily-Use Lina Release 1.
7. `docs/DAILY_USE_RELEASE_DECISIONS.md` — compact Product Owner-approved decision register introduced by the Daily-Use transition.
8. `docs/TECHNOLOGY_REUSE_CATALOG.md` — approved reuse candidates and mandatory fit checks.
9. `docs/SUBJECT_SCOPE_POLICY.md` — accepted cross-subject policy when relevant.
10. `project-state/PROJECT_STATE.md` — **current operational reality and current next action**.
11. `project-state/DAILY_USE_RELEASE_TASKS.md` — current bounded Daily-Use Release 1 executable-task overlay.
12. `TASKS.md` — preserved durable historical task ledger.

### Document authority and task coordination

- `PROJECT_REFERENCE.md` owns stable product truth.
- `LEARNING_INTELLIGENCE_SPEC.md` owns Learning Intelligence semantics.
- `LEARNING_PRODUCT_ROADMAP.md` owns approved evolution direction, not current execution.
- `IMPLEMENTATION_PLAN.md` owns technical implementation direction.
- `docs/DAILY_USE_RELEASE_PLAN.md` is the approved current launch implementation addendum where historical sequencing is stale.
- `docs/DAILY_USE_RELEASE_DECISIONS.md` records approved product decisions introduced by this launch transition pending later routine consolidation into the stable reference.
- `PROJECT_STATE.md` owns current operational truth and next action.
- `project-state/DAILY_USE_RELEASE_TASKS.md` owns the bounded executable Daily-Use Release 1 task sequence.
- `TASKS.md` remains the preserved historical task/execution ledger and must not be rewritten merely to mirror the current launch overlay.

Normally Codex executes only a task explicitly marked `READY` in the current bounded task source. A newer Product Owner-approved bounded transition recorded in `PROJECT_STATE.md` may override stale historical sequencing for that bounded task and must not be generalized.

## Current Product Owner Transition — Daily-Use Lina Release 1

`DOC-SYNC-01` is **DONE / ACCEPTED**.

`RL-01 — Real-Use Environment & Integrated Intelligence Loop Verification` completed its Current Reality Audit and the launch-first transition is now being executed sequentially.

The Product Owner clarified that the existing historical database is experimental/test data. It is not a production baseline to preserve or migrate as Lina's longitudinal real-use history. Daily-Use Release 1 uses one fresh shared current-schema application database; Lina's longitudinal baseline is Student-scoped, not database-scoped.

The Product Owner approved a **launch-first Daily-Use Lina Release 1** sequence. The sequence is recorded in `PROJECT_STATE.md`, `docs/DAILY_USE_RELEASE_PLAN.md`, `docs/DAILY_USE_RELEASE_DECISIONS.md`, and `project-state/DAILY_USE_RELEASE_TASKS.md`. It deliberately promotes capabilities in order, not simultaneously.

**Only the task that `PROJECT_STATE.md` and `project-state/DAILY_USE_RELEASE_TASKS.md` jointly mark `READY` is executable. Do not rely on a hardcoded task name in this file.**

Do not start any later Daily-Use task, Personal Facts, Frontend redesign, Voice, Vision, deployment, RAG evaluation, Artifacts, Science, Parent Insight analysis, MATH-01, ID-01, EDU-ERR-01, REC-25, or LR-D04B unless explicitly promoted.

## Daily-Use Release 1 Sequence

```text
RL-01A Accepted Runtime Alignment
→ RL-01B Fresh Shared DB + Runtime Composition
→ RL-01C Clerk + OpenAI Operational Verification
→ RL-01D Controlled Full Intelligence Loop
→ TASK-027A Student Core Profile
→ PF-01 Personal Facts Contract
→ PF-02 Personal Facts Extraction/Reconciliation
→ PF-03 Relevant Facts in Tutor Context
→ FE-01 Lina Visual System & Reuse Decision
→ FE-02 Daily Student Experience
→ TASK-032 Voice / STT
→ TASK-033 Vision / Student Work
→ TASK-034 Original-Image Annotation
→ DEPLOY-01 Private Daily Environment
→ LINA-R1 Clean Real-Use Baseline
```

Post-launch work includes measured RAG evaluation, selected learning artifacts, Science expansion when promoted, and future Parent Facts × Learning insight exploration after sufficient real data exists.

## Execution Rules

- Execute one `READY` task at a time unless a task explicitly defines a tightly related bounded group.
- Do not skip dependencies or promote later tasks because they appear easy.
- Do not silently revive historical phase gates that have been superseded by the current approved release sequence.
- Prefer the simplest implementation that preserves approved boundaries, provenance, and rebuildability.
- **Reuse-first, not dependency-first:** inspect applicable candidates in `docs/TECHNOLOGY_REUSE_CATALOG.md` before custom-building substantial UI/chat/RAG/artifact infrastructure.
- For any candidate marked `EVALUATE BEFORE CUSTOM BUILD`, record `ADOPT / PARTIAL ADOPT / REJECT` with rationale.
- Do not introduce microservices, Redis/Celery, a graph database, dedicated vector DB, new memory platform, generic agent framework, or deployment redesign without explicit approval and demonstrated need.
- Replit is an environment convenience/candidate host, not product architecture.
- Current hybrid Retrieval remains the launch baseline. Do not redesign RAG during foundation tasks.
- Current production proving ground remains Math-first until another Subject task is explicitly promoted.

## Protected Architecture — Learning Intelligence

The accepted learning path is:

```text
Raw learning interaction
→ optional provisional Candidate hints
→ completed structurally reviewable Segment
→ Segment Learning Review / staged findings
→ deterministic Session Intelligence Finalization
→ Session-authorized Event/Evidence
→ Current Learning State / Patterns
→ Learner Intelligence Card
→ relevant later learning personalization
```

Protect these invariants:

- **Segment interprets; Session commits.**
- Candidate ≠ Evidence.
- One primary Tutor model call per normal Student turn.
- No second normal-turn classifier, summarizer, critic, profile agent, or evidence evaluator.
- Current demonstrated behavior outranks historical personalization.
- Never personalize away demonstrated independence.
- Selecting/using a TeachingMethod is not evidence that it worked.
- TeachingStrategy and TeachingMethod remain separate.
- Luna/primary Tutor call semantically determines allowed turn-level Mode/Strategy/Method/prior relation; deterministic runtime validates/persists canonical values and lineage.
- Current School Focus is superseded as learning-path authority and must not be recreated.
- Book/content availability improves grounding but is never Tutor permission.
- Curriculum semantics are optional enrichment, not a prerequisite for Tutor or Learning Intelligence.
- Full prior-session transcripts are not injected into normal Tutor context.
- A Learning Thread is the session-local contiguous Segment; no third Thread entity.
- Durable Conversation Topic is optional navigation metadata, not Learner Intelligence, Evidence, Safety, or curriculum authority.
- Hybrid Segment Context uses Current Multimodal Turn + Full Immediate Exchange + compact Structured Segment State + relevance-selected complete current-Segment Exchanges; capacity is a guardrail, not a relevance algorithm.

## Personal Facts — Approved Separate Context Layer

Personal Facts are a new approved Daily-Use Release 1 capability, but are not executable until PF-01 is `READY`.

Purpose:

> Preserve durable facts the Student tells the system about herself so future interactions know the person they are speaking with.

Protected boundaries:

- Personal Facts are **separate from Learner Intelligence**, Evidence, Student Core Profile, Conversation Context, Safety, and curriculum grounding.
- The source is the Student's own assertions/interactions. Parent-supplied claims do not automatically become the Student's Personal Facts.
- A Personal Fact is not required to be externally verified objective truth; it represents what the Student has asserted about herself/world for personalization continuity.
- Store facts, not personality analysis, psychological interpretations, intelligence labels, learning-style labels, transcript summaries, or global character judgments.
- Personal Facts may be temporal/revisable: support, contradiction, invalidation, supersession, first/last observation, and source-message provenance should remain available.
- Relevant Personal Facts may later enter Tutor context as a separate bounded input.
- Personal Facts never become Learning Evidence merely because they exist.
- Learning Intelligence does not copy itself into Personal Facts merely to create a second memory.
- Future Parent Insights may combine Personal Facts and Learning Intelligence for analysis, but derived insights must not write back as facts or learning truth without their own governed evidence.
- Parent may inspect stored Personal Facts; no separate hidden-child-facts store is required under the current Product Owner decision.

## Student Core Profile

Student Core Profile remains separate from Personal Facts and Learner Intelligence.

It owns Parent/System-authoritative application facts such as child identity, date of birth when supplied, derived age, and active Grade/Grade Period linkage. Age should be derived from date of birth rather than manually maintained.

Parent facts in Core Profile must not be transformed into learning conclusions.

## Multimodal / Visual Decisions

The following are approved for the Daily-Use Release sequence but remain blocked until their task is promoted.

### Voice

```text
Audio
→ Speech-to-Text
→ Transcript
→ normal Tutor pipeline
```

Current policy: retain transcript; do not retain raw audio after successful STT. No speech-to-speech requirement for Release 1.

### Student Images / Vision

- Preserve the original Student image/work as the raw source.
- Vision interpretation is derived and may be uncertain.
- If a critical region is ambiguous, ask Lina a simple clarification rather than inventing certainty.
- Default visual correction path is **annotation on a derived copy of the original image**.
- Clean React/SVG/interactive reconstruction is fallback when annotation is insufficient.
- Annotation/reconstruction never replaces the original source and is not evidence of what Lina originally produced.

### Teaching Visuals — Renderer First

The primary teaching-visual strategy is deterministic/reusable renderers, not image generation:

- React/SVG
- Motion
- JSXGraph
- React Konva
- MathLive

Optional later: Rough.js, Recharts, p5.js, React Flow when a real use case requires them.

OpenAI or other image generation is **optional/deferred/illustrative**, not the default teaching renderer. Artifact failure must never block learning.

## UI / Frontend Direction

Frontend improvement is part of the approved launch sequence, but begins only when FE-01 is promoted.

Target Student experience:

> playful + intelligent + polished + personal, suitable for approximately age 10; not preschool and not a corporate chatbot.

Reuse candidates include shadcn/ui, assistant-ui fit assessment, Motion/Motion Primitives, ThreeUI/Three.js selective use, Magic UI, React Bits, 21st.dev, Aceternity UI, and Cult UI. Do not stack them indiscriminately. FE-01 must classify relevant candidates as `ADOPT / PARTIAL ADOPT / VISUAL REFERENCE / REJECT` and establish one coherent design system.

ThreeUI/Three.js may be used selectively for high-value visual moments/background/3D experiences when performance and readability remain acceptable; they do not become application architecture.

## Retrieval / RAG Rules

- Keep the current native Docling + PostgreSQL/pgvector Hybrid Retrieval path for launch.
- Preserve metadata filtering, lexical + vector retrieval, ranking/context budgets, and source provenance.
- Do not replace it with OpenAI File Search, LlamaIndex, or another framework by assumption.
- A post-launch evaluation may compare alternatives on a real Grade-5 golden set for retrieval quality, provenance, Arabic/English behavior, latency, cost, dependency complexity, and rebuildability.
- Adopt a replacement only if measured evidence shows a material advantage behind the existing Retrieval boundary.

## AI / Model Rules

- Application domains request AI tasks through Model Gateway; do not call provider SDKs arbitrarily from routes/services.
- Current operational provider may be OpenAI, but provider/model is replaceable architecture.
- Daily-Use Release tasks may add future task routes such as `personal_fact_extraction`, `speech_to_text`, and `vision_student_work` when their task is promoted.
- Keep AI usage/cost lineage observable.
- Use deterministic code for state, counts, lifecycle, reconciliation validation, and plumbing where practical.
- Do not introduce an additional AI call without identifiable product value.

## Child Safety

All Student-facing paths — Tutor, Voice, Vision, annotations, artifacts, future web/reference tools — remain subject to `docs/CHILD_SAFETY_POLICY.md`.

Parent settings may restrict family-sensitive topics further but may never weaken the non-overridable system safety baseline.

Personal Facts must not become a route for storing unsafe sensitive information beyond the approved product/safety policy.

## Verification Rules

A task is not complete because code exists. Before claiming completion:

1. run the task's listed verification;
2. run relevant unit/contract/integration tests;
3. verify protected invariants remain intact;
4. inspect changed-path runtime/log behavior when applicable;
5. update the current bounded task overlay and/or historical `TASKS.md` only when appropriate;
6. update `project-state/PROJECT_STATE.md` if current reality/next action changes;
7. distinguish code review, automated execution, real-model verification, browser verification, limited historical Real-Lina use, stable daily Real-Lina use, and longitudinal validation;
8. stop at the task boundary and return for Product Owner review before promoting the next task.

When verification cannot be run, state exactly why and keep that evidence category unverified.

## Protected Local Work / Secrets

Implementation work belongs in the isolated worktree:

`/Users/haitham/development/lina-learning-ctx03`

The original checkout may be inspected **read only** for existing local configuration when the isolated worktree lacks it. Never implement changes in the original checkout.

Known protected original-checkout Eureka-related dirty files must not be stashed, reset, cleaned, overwritten, formatted, or modified.

Never print, echo, copy, expose, commit, or hardcode secret values. Do not copy an original `.env` into the isolated worktree. Report only whether required configuration is present/absent/invalid when auditing configuration.

## Current Next Action

Read `project-state/PROJECT_STATE.md` and `project-state/DAILY_USE_RELEASE_TASKS.md`, then execute **only the single task marked `READY` there**.

Stop after that task's verification/report. Do not execute or promote the next task in the same run unless the Product Owner explicitly authorizes it.
