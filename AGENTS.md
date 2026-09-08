# Lina Personal Learning System — Operating Guide

## Purpose

Lina is a private AI learning application for a child. Build clear, useful
learning experiences while protecting safety, student data, and the meaning of
learning evidence.

## Default: BUILD MODE

An explicit Product Owner request for an implementation, fix, improvement,
feature, or refactor authorizes the work. Complete the requested working slice;
old roadmap, task, review, `READY`, or `BLOCKED` labels are history/reference,
not execution gates.

Use the smallest correct implementation. Keep the student experience simple
and internal boundaries modular. Read only the current references materially
relevant to the change: start with this file, `docs/PROJECT_REFERENCE.md`, and
`project-state/PROJECT_STATE.md`; use `TASKS.md` and specialized specs when
they help clarify the affected behavior or boundary.

## TDD default

For behavioral features and fixes, use RED → GREEN → REFACTOR:

1. Understand the intended behavior.
2. Add or update the smallest meaningful automated test first.
3. Confirm it fails for the expected reason when practical.
4. Make the smallest production change that passes it.
5. Refactor only while tests remain green, then run the affected regression
   surface.

For bugs, reproduce with a failing regression test whenever reasonably
possible. For refactors, add characterization coverage when existing coverage
does not protect the behavior. Do not invent low-signal tests for documentation
changes, pure visual polish, or conditions that cannot be reproduced locally.
For UI work, use component/contract tests where useful, then browser/visual
verification when the visual result matters.

## Proportional verification

Match verification to risk, rather than running the full repository matrix for
every change:

- Small isolated behavior: focused tests.
- Backend behavior: unit/contract and relevant integration tests.
- Durable state or database behavior: focused PostgreSQL integration proof.
- Frontend interaction: component/contract coverage and relevant browser proof.
- Cross-cutting, high-risk, or release work: broader affected regression suite.

Before committing, inspect the diff, self-review the changed behavior, fix
concrete findings, and run `git diff --check`. Use deeper independent review
only when requested, for a meaningful release, for a cross-cutting/high-risk
change, or when a protected area is materially changed.

## Five protected areas

Stop for Product Owner input only when a requested change would materially
weaken or change one of these protections:

1. Child Safety baseline.
2. Authentication, privacy, Student ownership, or data isolation.
3. Learning Evidence / Learning Intelligence write authority or meaning.
4. Destructive database, schema, or data-migration behavior.
5. Irreversible external actions, including deployment, paid effects, or
   destructive remote operations.

Existing accepted behavior near a protected area is not itself a stop signal:
preserve it and continue normally. Keep raw student work and source provenance
intact; route provider calls through the Model Gateway; do not expose, copy,
hardcode, or commit secrets.

## When to stop or ask

Stop only for a concrete blocker: conflicting product requirements, an
unresolved choice that materially changes student behavior or data meaning,
missing required credentials with no meaningful local progress, a material
protected-area change, or an irreversible/destructive action needing consent.

File count, cross-stack scope, stale documents, old task status, missing
implementation records, and multiple ordinary engineering steps are not
blockers. Do not stop for a progress report while executable work remains.

## Engineering autonomy

Make ordinary decisions independently: module placement, helper structure,
naming, test placement/number, routine refactoring, error handling, and fixes
for concrete defects found in the authorized slice. Ask only when a decision
materially changes product behavior, user experience, data meaning, or a
protected area.

Prefer existing project patterns and lightweight dependencies. Do not add a
new infrastructure service, generic agent framework, graph/vector database,
Redis/Celery, microservice, or deployment redesign without demonstrated need
and Product Owner approval.

## Versioning and documentation

Create a new durable contract version only when compatibility genuinely
matters: persisted historical data, an external/public API, deployed clients,
or a real migration boundary. Otherwise simplify internal code directly.

Documentation supports implementation. Update the minimum relevant current
documentation in the same working slice when reality changes; plans, decision
records, and review artifacts are reference material unless explicitly made
authoritative by the Product Owner.

## Local work and commits

Preserve unrelated local changes, untracked artifacts, and secrets. Never
stash, reset, clean, overwrite, or commit them. Prefer one meaningful commit
for each completed working slice, including needed documentation; do not create
separate governance, promotion, acceptance, or review-closure commits unless
explicitly requested.
