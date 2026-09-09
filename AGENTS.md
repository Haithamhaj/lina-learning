# Lina Personal Learning System — Operating Guide

## Build mode

Execute only a concrete `READY` task in `TASKS.md`, normally one bounded task or tightly related group at a time. A roadmap item is not executable merely because it is approved. Read `docs/PROJECT_REFERENCE.md`, `project-state/PROJECT_STATE.md`, and the relevant specialized contract before changing behavior.

Use the smallest correct implementation. Preserve unrelated local work; never stash, reset, clean, overwrite, or absorb it. Use normal Git history and no force push. `main` is the canonical branch after REPO-TRUTH-01; branches are short-lived and must not become a shadow mainline.

## Authority map

- `README.md`: orientation and implemented capability.
- `docs/PROJECT_REFERENCE.md`: durable product truth and boundaries.
- `docs/LEARNING_INTELLIGENCE_SPEC.md`: Evidence/Intelligence semantics.
- `docs/CHILD_SAFETY_POLICY.md`: child safety and Parent Boundaries.
- `docs/IMPLEMENTATION_PLAN.md`: current technical architecture.
- `docs/LEARNING_PRODUCT_ROADMAP.md`: capability evolution, never execution authority.
- `TASKS.md`: executable queue only.
- `project-state/PROJECT_STATE.md`: short live operational state.

History, review evidence, and research are non-authoritative.

## Protected areas

Product Owner approval is required before changing child safety or Parent Boundary meaning; auth, privacy, ownership, or data isolation; Evidence or Learning Intelligence authority/semantics; destructive schema/data behavior; or irreversible external action. Preserve raw work and source provenance.

Tutor availability is independent of curriculum. Route AI through the Model Gateway. Normal Tutor turns use one primary call; semantic mode, strategy, method, and prior-method relation come from that call, while code validates, enforces policy, and persists canonical values. Canvas is a representation surface; Chat/Tutor remains language and reasoning authority.

## Engineering and verification

Use RED → GREEN → REFACTOR for behavioral work when practical. Keep the user experience simple and the modular monolith explicit; do not add core infrastructure, agents, or services without approval. Use migrations for schema changes. Match verification to risk, inspect the diff, run `git diff --check`, and report any unrun gate exactly.

Before custom-building a substantial UI, chat, retrieval, or learning-artifact subsystem, inspect `research/repository/TECHNOLOGY_REUSE_CATALOG.md`; record an ADOPT, PARTIAL ADOPT, or REJECT decision before equivalent custom infrastructure is complete.
