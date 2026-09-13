# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating guide for AI implementation agents working in Lina. Read the governing references needed for the task, preserve approved product boundaries, and use engineering judgment rather than mechanically following checklists.

## Authority map

Read in this order when relevant:

1. `docs/PROJECT_REFERENCE.md` — durable product truth and cross-domain boundaries.
2. `docs/LEARNING_INTELLIGENCE_SPEC.md` — Evidence / Intelligence semantics.
3. `docs/CHILD_SAFETY_POLICY.md` — child-safety and Parent Boundary authority.
4. `docs/IMPLEMENTATION_PLAN.md` — current technical architecture and execution direction.
5. `docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md` — approved Full-Power Canvas architecture and acceptance authority.
6. `research/repository/TECHNOLOGY_REUSE_CATALOG.md` — reusable technology/capability reference.
7. `project-state/PROJECT_STATE.md` — current operational snapshot.
8. `TASKS.md` — executable queue and dependencies.

If two governing documents conflict, the most recently approved Product Owner decision controls only where the conflict is explicit. Surface any unresolved protected-area contradiction rather than silently inventing a new product direction.

## Current implementation mode

The approved current execution direction is `FULL-POWER-CANVAS-01`.

Use **native Codex capabilities only** for this work. Do not use Superpowers or any `superpowers:*` workflow/skill. Native reasoning, repository inspection, editing, debugging, browser work, testing, and native subagents are allowed.

Do not stop for ordinary implementation choices, test failures, layout problems, library selection, or reversible refactors. Stop only for:

- a protected-area change requiring Product Owner approval;
- contradictory governing requirements that cannot be reconciled from repository truth;
- missing credentials when no safe useful work remains;
- an irreversible/destructive external action requiring consent.

Do not merge to `main`, force-push, delete branches, or rewrite unrelated history without explicit approval.

## Engineering rules

- Prefer the smallest robust implementation that satisfies the approved behavior.
- Preserve the modular monolith.
- Reuse current Tutor, Studio, filtering, generated-asset ownership, Model Gateway, browser harness, and Agentic Canvas foundations.
- Do not rebuild working infrastructure merely because FULL-POWER-CANVAS-01 expands capability.
- Add new abstractions only when they materially improve correctness, safety, reuse, visual quality, recoverability, or maintainability.
- Generated visual code is never application authority.
- Exact Math/Science truth comes from typed data or deterministic tools, not renderer guesswork.
- Route application AI through approved model/provider boundaries and preserve usage/latency/cost lineage.
- Use migrations for schema changes.
- Preserve raw learner/source provenance and rebuildability.

## Tutor / Canvas authority

The invariant is:

```text
Tutor teaches.
Canvas Agent composes.
Tools establish exact truth.
Code validates and executes.
Studio persists.
Tutor understands the Canvas.
```

The Primary Tutor owns:

- educational objective;
- facts and grounding;
- pedagogical strategy;
- student-facing explanation;
- interpretation of meaningful learner actions.

The Full-Power Canvas Agent owns bounded visual composition. It may choose REUSE, ADAPT, or CREATE and may use approved visual/runtime capabilities, but it does not gain learner-state, safety, storage, database, or Tutor authority.

## Full-Power Canvas rules

Typed renderers are a **fast path, not a capability ceiling**.

The Canvas Agent may use the strongest approved route for the educational representation:

- existing typed visual tools/renderers;
- reusable visual artifacts;
- parameter adaptation;
- React/SVG/Motion;
- JSXGraph;
- Konva;
- MathLive;
- approved chart/simulation capabilities;
- generated project-owned images;
- custom visual code inside the approved isolated sandbox.

Use:

```text
REUSE when fit is strong
REUSE also for parameters/presentation expressible by the existing schema
ADAPT only when generalized capability must change
CREATE when reuse/adaptation would compromise the learning representation
```

Do not force reuse merely to reduce cost.

### Custom visual security boundary

Generated custom code must execute only inside the approved visual sandbox. It must not receive:

- cookies or browser identity;
- application secrets;
- database access;
- unrestricted filesystem access;
- arbitrary network access;
- raw Personal Memory or Learning Intelligence;
- raw student-source bytes unless a separately approved safe path explicitly requires them;
- direct Studio writes.

Only allowlisted dependencies/capabilities and a bounded semantic event bridge are permitted.

### Semantic Manifest

Every finalized Canvas runtime kind must expose a validated implementation-independent Semantic Manifest with stable semantic IDs sufficient for the same Primary Tutor to understand what the learner sees and does.

The Tutor should normally consume semantic state/events, not generated code. A visual snapshot may be used only when genuinely useful.

### Reusable Visual Registry

Separate:

- build history: every generated visual attempt/version needed for provenance;
- reusable registry: only parameterizable, validated, safe, high-quality reusable artifacts.

Never promote student-specific private information into reusable artifact definitions.

## Verification rules

Use lightweight behavior-first TDD on meaningful new boundaries when practical:

```text
define behavior → RED for intended reason → implement → GREEN
```

Do not build exhaustive upfront test matrices.

During implementation use focused verification. Do not repeatedly rerun the entire Python/PostgreSQL/browser/live-provider suite after small changes.

The primary release gate is one final integrated acceptance wave that includes real-provider and real-browser proof for representative REUSE, ADAPT, CREATE, Tutor round-trip, and sandbox-negative behavior, followed by one broad regression near closure.

A task is not complete because unit tests pass. Visual completion requires actual rendered evidence.

Always run `git diff --check` before closure and report any unrun gate exactly.

## Project-state discipline

`project-state/PROJECT_STATE.md` is a short operational snapshot, not a diary. Keep only:

- current goal;
- current reality;
- active decisions;
- protected areas;
- active risks;
- next recommended action;
- critical references.
