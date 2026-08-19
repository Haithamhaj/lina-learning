# Lina Personal Learning System — Project State

## Current goal

TASK-002 is complete. The next recommended task is TASK-003: PostgreSQL and
migration foundation. TASK-005 is also eligible because its only dependency,
TASK-002, is complete.

## Current reality

- The repository foundation is bootstrapped from the approved Starter Pack.
- The web shell is Next.js/TypeScript and uses locally owned shadcn/ui-compatible
  primitives as its baseline functional UI layer.
- The API shell is FastAPI with health and foundation-status endpoints.
- TASK-001 is marked `DONE` after local and browser verification.
- TASK-002 is marked `DONE` with typed server configuration and browser-safe
  frontend configuration.
- No Tutor, retrieval, Learning Intelligence, multimodal, artifact, database, or
  authentication feature has been added.

## Active decisions

- Use a modular monolith.
- Keep the foundation dependency-light and defer optional technology candidates
  until the task that needs them.
- Keep server-only settings and secrets inside the API/service configuration
  module; only `NEXT_PUBLIC_*` values may reach the browser bundle.
- Preserve the approved documents as source-of-truth references.

## Protected areas

Evidence-first intelligence, current behavior outranking historical
personalization, raw-source preservation, layered child safety, one primary
Tutor call, rebuildability, and the Phase 0/real-Lina decision gates.

## Active risks

- TASK-003 and TASK-005 are now eligible; later Phase 0 tasks remain blocked by
  their declared dependencies.

## Next recommended action

Begin TASK-003 next, using the database/migration requirements in `TASKS.md`.
TASK-005 may be handled independently afterward. Do not begin TASK-004 or later
tasks until their dependencies are complete.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`