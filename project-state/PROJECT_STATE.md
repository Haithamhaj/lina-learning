# Project state

## Current goal

Complete REPO-TRUTH-01 through 03: reconcile documentation and repository hygiene on `repo/truth-reset-01`, then stop for Product Owner approval before promoting `main`.

## Current reality

The accepted source baseline is `7ce6bcba41a6df92ff7862718a5d340925546415`; remote `main` is the older ancestor `b213e66f5e2505879610c0056f4bc5e576a01edc`. The current root `main` worktree contains unrelated local changes and is protected by an isolated cleanup worktree.

## Active decisions

`main` becomes the one canonical branch only after the stop gate. The FE-02 prototype remains preserved. Current truth is separated from history, review evidence, and research.

## Protected areas

Safety/Parent Boundaries, ownership/privacy, Learning Intelligence semantics, raw provenance, Model Gateway routing, Studio/Canvas contracts, and runtime behavior are unchanged by this cleanup.

## Active risks

Remote main protection is not yet inspected. Authenticated Daily acceptance and longitudinal real Lina calibration remain unproven product gates.

## Next recommended action

Finish the bounded repository cleanup and request Product Owner approval for main promotion. After promotion, begin `UI-REFINE-01`.

## Critical references

`README.md`, `AGENTS.md`, `docs/PROJECT_REFERENCE.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/LEARNING_INTELLIGENCE_SPEC.md`, `docs/CHILD_SAFETY_POLICY.md`, `TASKS.md`.
