# AGENTS.md — Lina Personal Learning System

## Purpose

Compact operating map for Codex/AI agents working in this repository. Read the governing documents relevant to the current task before changing code. Do not infer execution authorization from roadmap/design presence alone.

## Governing references

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — stable approved product truth and protected product boundaries.
2. `docs/LEARNING_PRODUCT_ROADMAP.md` — approved evolution direction; roadmap presence is not execution approval.
3. `docs/LEARNING_INTELLIGENCE_SPEC.md` — canonical Learning Intelligence semantics/authority.
4. `docs/CHILD_SAFETY_POLICY.md` — non-overridable child safety and Parent Learning Boundaries.
5. `docs/IMPLEMENTATION_PLAN.md` — broad technical implementation direction.
6. `docs/STUDIO_IMPLEMENTATION_PLAN.md` — accepted Learning Studio subsystem direction.
7. `docs/DAILY_USE_RELEASE_PLAN.md` — launch-first Daily-Use addendum.
8. `docs/DAILY_USE_RELEASE_DECISIONS.md` — Product Owner decision register.
9. `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md` — accepted bounded Tutor↔Canvas-Specialist authority/behavior contract for the active track.
10. `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md` — active CS-01→CS-07 sequencing/task boundaries.
11. `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md` — evidence, quality/speed/cost and documentation gates for CS tasks.
12. `docs/TECHNOLOGY_REUSE_CATALOG.md` — approved reuse/dependency candidates and fit-check rules.
13. `docs/SUBJECT_SCOPE_POLICY.md` — accepted cross-subject policy when relevant.
14. `project-state/PROJECT_STATE.md` — **current operational reality and next action**.
15. `project-state/DAILY_USE_RELEASE_TASKS.md` — **current bounded executable task overlay**.
16. `TASKS.md` — preserved historical task ledger; do not rewrite merely to mirror the current overlay.

### Authority/coordination

- Stable product truth → `PROJECT_REFERENCE.md` and specialist accepted decision documents where explicitly scoped.
- Learning semantics → `LEARNING_INTELLIGENCE_SPEC.md`.
- Safety → `CHILD_SAFETY_POLICY.md`.
- Studio Core sequencing/contracts → `STUDIO_IMPLEMENTATION_PLAN.md`.
- Current Canvas Specialist execution contract → `CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`.
- Current executable task/status → `PROJECT_STATE.md` + `DAILY_USE_RELEASE_TASKS.md` jointly.
- Historical detail → `TASKS.md`, accepted closure records and `docs/reviews/`.

Normally execute only the single task explicitly marked `READY` in the current overlay/state. Stop after verification/review. Never promote the next task in the same run unless the Product Owner explicitly authorizes it.

## Current active task

**CS-05 — Process Production Integration: IMPLEMENTED / UNDER PRODUCT OWNER AUDIT.**

CS-01 through CS-04 are **DONE / ACCEPTED**. **CS-05M — Semantic Motion
Intelligence is READY / EXPLICITLY AUTHORIZED** as a bounded corrective subtask
inside CS-05. CS-06 through CS-07 remain BLOCKED.

Do not start CS-06 without Product Owner acceptance of CS-05.

## Core execution rules

- Execute one READY task at a time.
- Do not skip dependencies because a later task appears easy.
- Prefer the simplest implementation that preserves accepted authorities, provenance, rebuildability and real failure behavior.
- Reuse-first, not dependency-first: inspect `TECHNOLOGY_REUSE_CATALOG.md`; record ADOPT/PARTIAL ADOPT/REJECT when a fit check is required.
- Do not introduce microservices, Redis/Celery, graph DB, dedicated vector DB, new memory platform, generic agent framework or deployment redesign without explicit approval and demonstrated need.
- AI tasks use Model Gateway; do not call provider SDKs arbitrarily from routes/services/components.
- Use deterministic code for durable state, counts, permissions, validation, lifecycle, reconciliation and plumbing where practical.
- An additional AI call requires identifiable product value and explicit task authorization.
- Keep current RAG architecture unless a separately promoted task changes it.
- Preserve secret/privacy boundaries. Never print, expose, copy, hardcode or commit secret values.

## Protected Learning Intelligence

Accepted path:

```text
Raw learning interaction
→ optional Candidate hints
→ completed reviewable Segment
→ Segment Learning Review
→ deterministic Session Intelligence Finalization
→ Session-authorized Event/Evidence
→ Current Learning State / Patterns
→ Learner Intelligence Card
→ relevant later personalization
```

Protect:

- Segment interprets; Session commits.
- Candidate ≠ Evidence.
- One Primary Tutor model call per normal Student turn.
- No second normal-turn classifier/critic/profile/evidence model.
- Current demonstrated behavior outranks historical personalization.
- Teaching Strategy/Method selection is not evidence it worked.
- Canvas/Specialist actions do not directly create Candidate/Evidence/State/Patterns/PF/LI.
- Book/content availability improves grounding but is never Tutor permission.

## Student Core Profile / Personal Facts

These authorities remain separate:

```text
Student Core Profile = Parent/System-authoritative identity/age/Grade
Personal Facts       = explicit safe durable Student-asserted context
Learner Intelligence = evidence-backed learning-derived state
Conversation Context = current/raw continuity
RAG                  = curriculum/reference grounding
Safety               = safety authority
```

Canvas Specialist work may build only the bounded transient **Visual Learner Context** defined by the accepted Specialist contract:

- authoritative Core Profile fields when useful;
- a small relevant current safe Personal Fact subset for optional visual personalization.

Never copy age/Grade into Personal Facts, pass full Personal-Fact history/support counts by default, infer personality/learning style/talent, or let personalization change instructional truth. Absence of Personal Facts never blocks learning/visual composition.

## Learning Studio / Tutor↔Canvas Specialist protected architecture

Studio Core remains application-owned and subject-agnostic. Durable truth is semantic Event Log + rebuildable Materialized Snapshot. Browser state is not durable authority. Existing Tutor SSE remains Chat authority and the authenticated Studio feed remains Workspace state-delivery authority.

### Primary Tutor

Primary Tutor is the **sole Student-facing teacher**. It owns teaching objective, explanation/scaffolding/dialogue and the educational decision whether a visual helps.

### WorkspaceIntent

`workspace_intent-v1` is protected as a bounded educational Workspace need. Do not add renderer/engine/Scene body/specialist execution meaning to existing fields. The active Canvas Specialist track uses an additive sibling visual-order contract in CS-03.

### Canvas Specialist

Canvas Specialist is a bounded **Visual Learning Composer**, not a second Tutor. It may propose semantic visual composition only after application admission. It has no direct renderer/engine, persistence, Safety, Evidence, Personal Facts, Learner Intelligence or grading authority.

For registered-pattern new content, the accepted hybrid direction is:

```text
complete Primary Tutor result
→ admitted compact visual order
→ committed Tutor lineage + frozen composition pack
→ one bounded asynchronous Specialist generation
→ application validation/stale checks
→ atomic Studio Scene acceptance/activation
→ same Tutor awareness/Runtime-03 later interaction
```

This is **not** the same as generic `CUSTOM_COMPOSE`. Broader custom composition remains separately bounded/blocked.

### Call policy

- Chat-only = 0 Specialist calls.
- Compatible reuse = 0.
- Supported update = 0.
- New admitted composition = max 1 Specialist generation.
- No automatic critic/repair/hidden inference retry.
- Specialist Job route must explicitly avoid inheriting generic three-attempt generation behavior when CS-04 is promoted.

### First production slice

Process sequence/cycle, 2–8 stages, existing accepted ProcessView. Do not conflate it with the older deterministic `process_sequence_workspace` filtration activity. Process natural composition is not implemented until CS-05.

## Visual Toolbelt

Renderer-first remains the approved strategy:

- React/DOM/SVG — baseline;
- Motion — semantic animation;
- React Konva/Konva — spatial manipulation;
- JSXGraph — mathematical visualization/construction;
- MathLive — editable math input.

CS-02 is the accepted installation/proof foundation. Presence in the
technology catalog or lockfile never production-enables a learning capability.
Models request semantic capabilities; application-owned Registry/adapters select
the engine. CS-01 through CS-04 are DONE / ACCEPTED; CS-05 is READY; CS-06 through CS-07 remain BLOCKED.

Avoid arbitrary model-authored HTML/JS/SVG/code for routine visuals when typed renderers fit.

## Model direction

Current Product Owner decision for the active Tutor/Specialist track is **GPT-5.6 Luna**, behind Model Gateway. Provider/model remains replaceable architecture. Keep AIExecution tokens/latency/cost lineage observable. No direct provider coupling in domain code.

## Optimization order

For Canvas Specialist work:

1. **Quality** — semantic fidelity, pedagogical usefulness, clarity, age/Grade appropriateness, Arabic/English correctness, natural personalization.
2. **Speed** — measure Tutor/queue/Specialist/Scene/render latency after quality is acceptable.
3. **Cost** — optimize context/calls/reuse/configuration without lowering accepted quality.

Do not invent latency/cost pass thresholds before CS-06 establishes a real baseline.

## Child Safety

All Student-facing Tutor/Canvas/Voice/Vision/artifact paths remain subject to `docs/CHILD_SAFETY_POLICY.md`. Parent settings may restrict further but never weaken the system baseline. Specialist output is untrusted semantic data until application validation; it never overrides Safety or Parent Boundaries.

## Verification / documentation rules

A task is not complete because code exists or tests pass.

For every CS task follow `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`:

1. create `docs/reviews/<TASK-ID>/IMPLEMENTATION_RECORD.md` before code;
2. record baseline, scope/non-scope, protected boundaries, expected paths and verification;
3. distinguish static/unit/Postgres/mock/live-Luna/build/browser/controlled-Student/real-Lina/longitudinal evidence;
4. record actual changed paths, exact test results, model call counts, browser/visual evidence and quality findings where applicable;
5. record latency/tokens/cost when the task executes AI;
6. state exactly what remains unverified;
7. perform scope/protected-area review;
8. submit for Product Owner review and update `docs/reviews/README.md`;
9. only Product Owner acceptance marks DONE / ACCEPTED;
10. update Project State/task overlay after acceptance and stop before the next task unless separately authorized.

Private raw evidence remains local; publish sanitized review artifacts only.

## Protected local work / worktree

Implementation work belongs in the isolated worktree:

`/Users/haitham/development/lina-learning-ctx03`

Original checkout may be inspected read-only for existing configuration when needed. Do not stash/reset/clean/overwrite protected unrelated work. Do not copy `.env`; report required configuration only as present/absent/invalid.

## Current next action

Read:

1. `project-state/PROJECT_STATE.md`
2. `project-state/DAILY_USE_RELEASE_TASKS.md`
3. `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`
4. `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md`
5. `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`

The current next action is **CS-05M implementation and Product Owner audit**. CS-06 through CS-07 remain BLOCKED;
do not start CS-06 without Product Owner acceptance of CS-05.
