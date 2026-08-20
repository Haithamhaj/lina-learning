# Lina Personal Learning System — Project State

## Current goal

Phase 3 Learning Intelligence Core is complete for the approved development
sandbox: the browser demo exercises real local Grade 5 Eureka content through
retrieval, Tutor, Candidate Events, Evidence, State/Patterns, Card, decision
views, later-session personalization, and reprocessing. Early Lina Calibration
remains explicitly deferred and is not claimed as satisfied.

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
  parent/student role enforcement, trusted-role resolution that excludes
  user-writable metadata, Clerk authorized-party validation, and separate
  protected web surfaces.
- TASK-005 is marked `DONE` with a provider-neutral private object contract,
  local filesystem storage, and a production-ready S3-compatible provider with
  HMAC-authenticated metadata bundles, HTTPS-only endpoint enforcement,
  conditional collision protection, and server-mediated private access.
  Production configuration fails explicitly when `STORAGE_PROVIDER=local`.
  HMAC rotation is available as a resumable server-side migration that validates
  the complete inventory before preserving S3 object properties during
  same-key metadata copies.
  Upload UI remains deferred to a later task.
- TASK-006 is marked `DONE` with PostgreSQL jobs, database-level idempotency,
  transaction-safe `FOR UPDATE SKIP LOCKED` claiming, lease recovery,
  retry/failure recording, and a separate polling worker process. Per-claim
  lease tokens prevent stale workers from settling a re-leased job. Its registry
  intentionally has no content/intelligence handlers yet; those remain owned by
  their future domain tasks.
- TASK-007 is marked `DONE` with a task-routed Model Gateway and PostgreSQL AI
  execution ledger. The local deterministic provider is limited to tests and
  the fixture demo; it is not a production model-provider choice.
- TASK-008 is marked `DONE` with a deterministic, versioned SafetyDecision
  service, protected baseline routing, persistent per-student family boundaries,
  and audit records. It is the enforced upstream contract for later Tutor work.
- TASK-009 is marked `DONE` with immutable source-document records, versioned
  derivation runs, Grade-local curriculum nodes, and source-linked content
  blocks. These records remain rebuildable and provenance-first.
- TASK-010 is marked `DONE` with a Parent/Admin upload endpoint and simple
  shadcn-baseline intake UI. Supported originals are checksum-addressed,
  preserved unchanged in private storage, assigned Grade/subject metadata, and
  start in an inspectable `UPLOADED` state; invalid/mismatched files are
  rejected and same-student duplicates safely reuse the existing source.
- TASK-011 through TASK-026 are marked `DONE`: Docling structural conversion,
  semantic/source-linked retrieval, a small Tutor session path and runtime
  safety consumption, Candidate Events, worker-backed close/consolidation,
  derived evidence/state/pattern/card/decision views, and versioned rebuilds
  are all available in the development-only Sandbox/Test Learner demo.

## Active decisions

- Use a modular monolith.
- Keep the foundation dependency-light and defer optional technology candidates
  until the task that needs them.
- Keep server-only settings and secrets inside the API/service configuration
  module; only `NEXT_PUBLIC_*` values may reach the browser bundle.
- Keep Alembic migrations as the development schema source of truth; apply
  production schema changes through Replit Publish rather than startup DDL.
- Keep Clerk's browser session cookie transport separate from FastAPI's verified
  JWT/API role boundary; only signed role claims or Clerk public metadata may
  establish `PARENT_ADMIN`, while missing or untrusted metadata defaults to
  `STUDENT`. Validate a present Clerk `azp` against `web_origin` and
  `allowed_origins`.
- Clerk is adopted for MVP authentication; the Lina backend owns application
  roles and authorization semantics, and Clerk-specific behavior stays in the
  auth adapter/boundary.
- Use PostgreSQL jobs plus a separate worker process for initial batch work;
  do not add Redis, Celery, cron infrastructure, or a distributed scheduler
  without demonstrated scaling need and approval.
- Keep AI calls behind the Model Gateway; task routes, provider/model identity,
  usage, latency, estimated cost, and success/failure remain ledgered.
- Preserve the approved documents as source-of-truth references.

## Protected areas

Evidence-first intelligence, current behavior outranking historical
personalization, raw-source preservation, layered child safety, one primary
Tutor call, rebuildability, and the Phase 0/real-Lina decision gates.

## Active risks

- The real Grade 5 Eureka Math workbook is approved only as local development
  and test curriculum content; it must remain outside Git. Its sandbox demo
  validation does not validate claims about Lina or replace real-book validation
  on Lina's selected curriculum.
- Early Lina Calibration is explicitly deferred by Product Owner approval for
  this sandbox-only Phase 1–3 run. It remains required before claims about real
  Lina or further product expansion.
- Real AWS/S3 staging verification is deferred and non-blocking. It remains
  recommended before changing the deployment secret because dry-run cannot
  validate conditional-copy permissions for tags, Object Lock, or SSE-KMS.
- Browser role testing can create a student session but cannot provision a
  `PARENT_ADMIN` metadata claim; parent authorization is covered by API tests and
  the metadata-driven web guard.

## Next recommended action

Review the Sandbox/Test Learner loop in the browser and use findings for the
deferred Early Lina Calibration. Do not start Phase 4.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`
