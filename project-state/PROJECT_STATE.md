# Lina Personal Learning System — Project State

## Current goal

TASK-003 is complete. The next recommended task is TASK-004:
Parent/Student auth and authorization baseline. TASK-005, TASK-006, and TASK-007
are also eligible because their declared dependencies are complete.

## Current reality

- The repository foundation is bootstrapped from the approved Starter Pack.
- The web shell is Next.js/TypeScript and uses locally owned shadcn/ui-compatible
  primitives as its baseline functional UI layer.
- The API shell is FastAPI with health and foundation-status endpoints.
- TASK-001 is marked `DONE` after local and browser verification.
- TASK-002 is marked `DONE` with typed server configuration and browser-safe
  frontend configuration.
- TASK-003 is marked `DONE` with an Alembic PostgreSQL foundation, pgvector
  enablement, and identity/grade-period tables applied to development.
- No Tutor, retrieval, Learning Intelligence, multimodal, artifact, auth,
  content, or object-storage product feature has been added.

## Active decisions

- Use a modular monolith.
- Keep the foundation dependency-light and defer optional technology candidates
  until the task that needs them.
- Keep server-only settings and secrets inside the API/service configuration
  module; only `NEXT_PUBLIC_*` values may reach the browser bundle.
- Keep Alembic migrations as the development schema source of truth; apply
  production schema changes through Replit Publish rather than startup DDL.
- Preserve the approved documents as source-of-truth references.

## Protected areas

Evidence-first intelligence, current behavior outranking historical
personalization, raw-source preservation, layered child safety, one primary
Tutor call, rebuildability, and the Phase 0/real-Lina decision gates.

## Active risks

- TASK-004, TASK-005, TASK-006, and TASK-007 are now eligible; TASK-008 and later
  tasks remain blocked by their declared dependencies.

## Next recommended action

Begin TASK-004 next, using the auth and authorization requirements in `TASKS.md`.
TASK-005, TASK-006, and TASK-007 may be handled independently afterward. Do not
begin TASK-008 or later tasks until their dependencies are complete.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`