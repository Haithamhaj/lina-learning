# Lina Personal Learning System — Project State

## Current goal

TASK-005 and its safe `SESSION_SECRET` rotation follow-up are complete. The
next recommended task is TASK-006:
DB-backed jobs and worker foundation. TASK-007 and TASK-008 are also eligible
because their declared dependencies are complete.

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
- TASK-004 is marked `DONE` with Replit-managed Clerk authentication, explicit
  parent/student role enforcement, and separate protected web surfaces.
- TASK-005 is marked `DONE` with a provider-neutral private object contract,
  local filesystem storage, and a production-ready S3-compatible provider with
  HMAC-authenticated metadata bundles, HTTPS-only endpoint enforcement,
  conditional collision protection, and server-mediated private access.
  Production configuration fails explicitly when `STORAGE_PROVIDER=local`.
  HMAC rotation is available as a resumable server-side migration that validates
  the complete inventory before preserving S3 object properties during
  same-key metadata copies.
  Upload UI remains deferred to a later task.

## Active decisions

- Use a modular monolith.
- Keep the foundation dependency-light and defer optional technology candidates
  until the task that needs them.
- Keep server-only settings and secrets inside the API/service configuration
  module; only `NEXT_PUBLIC_*` values may reach the browser bundle.
- Keep Alembic migrations as the development schema source of truth; apply
  production schema changes through Replit Publish rather than startup DDL.
- Keep Clerk's browser session cookie transport separate from FastAPI's verified
  JWT/API role boundary; missing role metadata must default to `STUDENT`.
- Preserve the approved documents as source-of-truth references.

## Protected areas

Evidence-first intelligence, current behavior outranking historical
personalization, raw-source preservation, layered child safety, one primary
Tutor call, rebuildability, and the Phase 0/real-Lina decision gates.

## Active risks

- TASK-006, TASK-007, and TASK-008 are now eligible; later tasks remain blocked
  by their declared dependencies.
- A real production-like S3 rotation run is still recommended before changing
  the deployment secret; dry-run cannot validate conditional copy permissions
  for tags, Object Lock, or SSE-KMS.
- Browser role testing can create a student session but cannot provision a
  `PARENT_ADMIN` metadata claim; parent authorization is covered by API tests and
  the metadata-driven web guard.

## Next recommended action

Begin TASK-006 next, using the jobs/worker requirements in `TASKS.md`.
TASK-007 and TASK-008 may be handled independently afterward. Do not begin later
tasks until their dependencies are complete.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`
