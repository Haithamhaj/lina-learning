# SAFE-02 Semantic Parent Boundaries — Implementation Plan

> **For Codex:** Execute this plan inline in the existing isolated `codex/ctx-03` worktree. The Product Owner has explicitly authorized this SAFE-02 implementation; do not begin CTX-03C.

## Goal

Move configurable Parent Boundary applicability into the existing single primary Luna Tutor call while retaining deterministic hard-baseline enforcement and making the server the final authority for every visible response.

## Architecture decisions

- Keep the protected baseline upstream and deterministic; it may stop the Tutor before any model call.
- Replace lexical Parent-topic routing with typed Luna semantic metadata in the one Tutor response contract.
- Add the configurable `SEXUAL_CONTENT` category without reinterpreting existing `HUMAN_REPRODUCTION` Parent settings; legacy rows remain historical-only and the new category uses its server-owned default until explicitly configured.
- Give Luna only compact effective server settings. Validate its typed semantic decision, then have the server resolve the effective action and compose redirects from bounded fragments.
- Add a provider-neutral decision event and a streaming guard. OpenAI may release buffered ordinary deltas after a valid early decision; providers that cannot expose the decision safely remain buffered through completion.
- On an enforced redirect, preserve only segment relation/state and allowed redirect fragments; never reveal or persist the model's ordinary text or Candidate metadata.

## Tasks

1. Write RED contract/policy/runtime/provider tests covering SAFE-02 A–W, including no-leak streaming, persistence, audit, candidate isolation, one-call and hard-baseline behavior.
2. Extend the typed Tutor structured contract and prompt with semantic Parent Boundary metadata and compact effective settings; bump the schema to v7.
3. Refactor safety policy into hard-baseline evaluation plus server-owned Parent Boundary settings/resolution. Remove `_CATEGORY_TERMS` and preserve legacy Parent Boundary rows without migration.
4. Add the streaming decision event/parser and runtime decision-first guard; enforce the final visible text and persistence branch.
5. Run focused tests, PostgreSQL safety/segment tests, full Python suite, and web typecheck. Execute the bounded real-Luna 10-case diagnostic after automated Green.
6. Update `TASKS.md` and `project-state/PROJECT_STATE.md`, review the exact diff, commit only SAFE-02 files as `fix: enforce semantic parent boundaries`, and push `origin/codex/ctx-03` without merging.

## Verification commands

```bash
uv run --with-requirements apps/api/requirements.txt --with pytest python -m pytest \
  tests/test_safety_policy_postgres.py tests/test_tutor_safety_contract.py \
  tests/test_tutor_runtime_contract.py tests/test_tutor_runtime_scenarios.py \
  tests/test_model_gateway_streaming.py tests/test_openai_provider.py
npm run test:python
cd apps/web && npm run typecheck
```
