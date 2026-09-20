# AGENTS.md — Lina Personal Learning System

## Purpose

This file is the compact operating guide for AI implementation agents working in Lina.

Read the current repository reality first. Do not implement from old conversation memory or historical plans when the current code, branch, worktree, documentation, or production state says otherwise.

## Authority map

Read in this order when relevant:

1. docs/PROJECT_REFERENCE.md — durable product truth and subsystem boundaries.
2. docs/LEARNING_INTELLIGENCE_SPEC.md — Evidence and Learning Intelligence authority.
3. docs/CHILD_SAFETY_POLICY.md — child safety and Parent Boundaries.
4. docs/IMPLEMENTATION_PLAN.md — current technical architecture.
5. docs/TUTOR_PEDAGOGY_REFERENCE.md — teaching reference.
6. docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md — detailed Canvas implementation contract.
7. research/repository/TECHNOLOGY_REUSE_CATALOG.md — reusable technology reference.
8. project-state/PROJECT_STATE.md — current operational snapshot.
9. TASKS.md — active execution queue.

Historical plans, reviews, closure documents, and tracker evidence do not override current canonical references unless the Product Owner explicitly revives a historical decision.

## Before implementation

Inspect the actual repository and, when available, the authorized local worktree:

- active branch and worktree;
- git status;
- tracked and untracked changes;
- recent commits;
- origin/main;
- relevant source and tests;
- current project-state and task authority.

Preserve unrelated dirty work. Do not silently reset or overwrite another worktree.

## Current implementation mode

The system is in controlled real-use validation.

Core Tutor, learner-context, Learning Intelligence, Student-source, Studio/Canvas, reusable visual, Worker, and live deployment foundations are implemented.

Current work should be driven by observed product need, especially teaching flow, live reliability, latency, personalization relevance, JEV decision quality, and later generated educational images.

Do not restart completed architecture programs merely because their historical plans remain in the repository.

## Engineering rules

- Prefer the smallest robust implementation that satisfies approved behavior.
- Preserve the modular monolith.
- Reuse current Tutor, Studio, Student-source, Learning Intelligence, Model Gateway, Worker, and Canvas foundations.
- Add abstractions only when they materially improve correctness, safety, recoverability, maintainability, visual quality, or real reuse.
- Use migrations for schema changes.
- Preserve raw learner and source provenance.
- Keep application authority in code and governed services.
- Keep model/provider routes observable and replaceable.
- Do not optimize away safety, ownership, lineage, or Evidence boundaries.

## Product authority model

The key invariant is:

    Tutor teaches.
    Canvas represents and composes.
    Tools establish exact truth.
    JEV makes bounded decisions only.
    Code validates and admits.
    Studio persists.
    Learning Intelligence interprets governed Evidence.
    The same Tutor continues with the learner.

### Primary Tutor

Owns educational objective, teaching strategy, explanation, source grounding, learner-facing reasoning, and interpretation of meaningful learner actions.

### Canvas

Owns bounded visual composition only. It may use REUSE, ADAPT, or CREATE but does not become a second Tutor or learner-state authority.

### JEV

JEV is used for finite bounded decisions such as:

- visual personalization fact selection;
- exact Canvas reuse selection;
- Segment rubric comparison.

JEV must not become a free-form orchestrator, teacher, generator, Safety authority, or database authority.

### Deterministic system

Owns:

- identity and ownership;
- Parent Boundary enforcement;
- executable validation;
- lineage;
- persistence;
- thresholds and finite allowed-action sets;
- stale-state admission;
- Evidence lifecycle rules;
- fallback behavior.

## Learner-context rules

Keep these authorities separate:

- Current conversation.
- Student Core Profile.
- Personal Facts / Personal Memory.
- Learning Intelligence.

Current Student behavior outranks history.

Personal Facts may personalize context but never prove mastery, ability, personality, motivation, or learning style.

Learning Intelligence may guide teaching but must remain source-linked, revisable, and scoped.

## Canvas rules

Typed renderers are a fast path, not a capability ceiling.

Use:

    REUSE when exact fit is strong
    ADAPT when generalized capability must change
    CREATE when reuse or adaptation would compromise learning

Do not force reuse merely to save cost.

Every finalized custom visual must expose bounded semantic meaning so the Primary Tutor can understand it without reading generated source code.

Generated visual code must stay inside the approved sandbox and receive no cookies, secrets, database access, unrestricted filesystem or network access, raw broad Personal Memory, raw Learning Intelligence, or direct Studio write authority.

A Student action must be truthful. Never fabricate a target, answer, interaction, or visual-delivery state.

## Learning Intelligence rules

- Raw interaction is historical source authority.
- Candidate Events are optional hints, not Evidence.
- Segment Review interprets completed learning context.
- Session Finalization governs activation.
- Evidence updates Current State and Patterns only through approved rules.
- Stable patterns require repeated support.
- Strategy use is not strategy-effectiveness Evidence.
- Canvas clicks are not automatically learning Evidence.
- No psychological/personality or permanent learning-style inference.

## Verification

Use focused behavior-first tests during implementation.

Typical closure sequence:

1. focused contract or unit tests;
2. affected PostgreSQL integration;
3. frontend tests and typecheck when relevant;
4. actual browser evidence for visual behavior;
5. repository truth;
6. git diff --check;
7. broader regression near closure when justified;
8. real provider/live proof only when the acceptance question requires it.

A task is not complete because unit tests pass.

Do not claim learning benefit from structural or synthetic tests.

## Production and external actions

Explicit Product Owner approval is required for:

- merge to main when not already authorized;
- production deployment;
- production DB migration;
- destructive data operations;
- material provider/model policy changes;
- irreversible external actions.

Routine reversible local implementation decisions do not require repeated approval.

## Project-state discipline

project-state/PROJECT_STATE.md is a short operational snapshot, not a diary.

Keep only:

- current goal;
- current reality;
- active decisions;
- protected areas;
- active risks;
- next recommended action;
- critical references.

## Documentation discipline

When product reality changes materially, update:

- README.md for orientation;
- docs/PROJECT_REFERENCE.md for durable product truth;
- docs/IMPLEMENTATION_PLAN.md for architecture;
- the relevant governing domain spec;
- TASKS.md for active execution;
- PROJECT_STATE.md for current operations.

Do not rewrite historical evidence to look current.

## Language

Write Codex prompts, implementation instructions, and handoffs in English.

Keep Product Owner discussion in Arabic unless requested otherwise.
