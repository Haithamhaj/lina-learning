# GCP Pilot Reference

## Status

Current infrastructure reference for the Lina controlled live pilot.

Operational revision names change over time. Use project-state/PROJECT_STATE.md for the latest observed revision IDs and use this document for stable resource topology and deployment expectations.

## Project

- GCP project: project-lina-2016
- Region: europe-west1
- Repository: https://github.com/Haithamhaj/lina-learning.git
- Canonical source: origin/main

## Pilot goal

Run the complete Lina system for controlled real learner use with minimal infrastructure complexity and cost while preserving product, Safety, ownership, learner-context, Evidence, and Canvas boundaries.

## Current topology

| Component | Service | Current role |
| --- | --- | --- |
| lina-app | Cloud Run Service | Next.js frontend + FastAPI backend + production supervisor |
| lina-worker | Cloud Run Worker Pool | Dedicated background jobs and Canvas/intelligence work |
| lina-db | Cloud SQL PostgreSQL 16 | Relational state + pgvector |
| lina-storage-project-lina-2016 | Google Cloud Storage | Student sources, generated assets, visual builds |
| lina | Artifact Registry | App and Worker images |
| Clerk | External auth | Student/Parent identity and session verification |
| OpenAI | Model provider | Primary Tutor, Canvas and approved model tasks |
| OpenRouter Decisions / JEV | Bounded decision provider | Visual personalization, exact Canvas reuse, Segment rubric comparison |
| Secret Manager | GCP | Runtime credentials and provider keys |

## Application topology

### lina-app

Cloud Run service packages:

- Next.js standalone;
- FastAPI / Uvicorn;
- production supervisor.

The integrated background worker is disabled in the current decoupled topology.

Public traffic reaches Next.js. FastAPI listens on internal loopback and is reached through the application proxy/rewrite path.

### lina-worker

The current background topology uses a separate Cloud Run Worker Pool with one pilot instance.

It handles durable job processing including Canvas composition and Learning Intelligence background flows.

The Worker image includes the Node/Playwright/Chrome runtime required for Canvas preview and validation.

## Database

- Engine: PostgreSQL 16.
- Extension: pgvector.
- Migration engine: Alembic.
- Current code/production migration head observed during documentation reconciliation: c8e2f4a6b913.
- Cloud SQL instance: lina-db.

Schema changes require an explicit migration and explicit production migration approval.

## Object storage

- Provider implementation: S3-compatible adapter over Google Cloud Storage interoperability.
- Bucket: lina-storage-project-lina-2016.
- Region: europe-west1.
- Endpoint: https://storage.googleapis.com.
- Signing region: auto.
- Uniform bucket-level access is enabled.
- Runtime HMAC credentials are stored in Secret Manager.

The application preserves source and build provenance in PostgreSQL and uses object storage for binary assets.

## Model runtime

### Primary / Canvas

- Provider: OpenAI through the Model Gateway.
- Current pilot Tutor model: gpt-5.6-luna.
- Current pilot Canvas model: gpt-5.6-luna.

Provider/model choices are operational configuration, not permanent architecture.

### JEV

OpenRouter Decisions / JEV is integrated as a bounded decision provider.

Current decision slices:

- visual-personalization fact selection;
- exact Canvas reuse selection;
- Segment rubric comparison.

JEV mode settings are environment-specific operational controls. Routine deploys must preserve the currently approved JEV mode values rather than resetting them implicitly.

## Secret Manager

Core secret references include:

- lina-database-url
- lina-session-secret
- lina-clerk-publishable-key
- lina-clerk-secret-key
- lina-model-api-key
- lina-openrouter-api-key
- lina-s3-access-key-id
- lina-s3-secret-access-key

Never store secret values in Git, documentation, logs, or screenshots.

## Important runtime environment

Application and Worker use configuration such as:

- APP_ENV=production
- STORAGE_PROVIDER=s3
- S3_BUCKET=lina-storage-project-lina-2016
- S3_REGION=auto
- S3_ENDPOINT=https://storage.googleapis.com
- AWS_REQUEST_CHECKSUM_CALCULATION=when_required
- AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
- MODEL_PROVIDER=openai
- MODEL_NAME=gpt-5.6-luna
- CANVAS_MODEL_NAME=gpt-5.6-luna on Worker
- JEV_MODEL_NAME=typesafe/jev-1.13
- JEV_TIMEOUT_SECONDS=5
- versioned JEV policy/threshold settings
- environment-specific JEV mode settings

The App and Worker must not accidentally diverge on shared provider or storage configuration.

## Authentication

Clerk provides external identity.

FastAPI resolves authenticated ownership and never trusts a browser-supplied Student ID as authority.

The deployed application origins must remain authorized in Clerk.

## Deployment principle

1. Build App and Worker from the same reviewed source state.
2. Prefer immutable image digests for actual deployment.
3. Preserve current environment-specific JEV mode values.
4. Deploy App and Worker separately.
5. Apply DB migrations only when required and explicitly approved.
6. Verify health, startup logs, model configuration and Worker readiness.
7. Treat deployment success as infrastructure evidence, not product acceptance.

## Current validation focus

The pilot is used for controlled natural learning rather than only infrastructure smoke tests.

Current validation includes:

- natural Tutor conversation;
- Canvas correctness and recovery;
- Student-source continuity;
- Learning Intelligence behavior;
- Personalization relevance;
- latency and buffering;
- JEV decision-quality collection.

## Protected product areas

Infrastructure work must preserve:

1. Primary Tutor teaching authority.
2. Child Safety.
3. Parent Boundaries.
4. Student ownership and privacy.
5. Core Profile authority.
6. Personal Facts / Personal Memory boundaries.
7. Learning Intelligence / Evidence authority.
8. Studio durable state.
9. Canvas sandbox and provenance.
10. Model Gateway execution lineage.
11. JEV bounded-decision scope.

## Cost posture

The pilot should remain intentionally small.

Major continuing cost categories are:

- Cloud SQL;
- Cloud Run / Worker runtime;
- object and artifact storage;
- OpenAI model usage;
- OpenRouter/JEV decision usage.

Do not optimize cost by silently weakening required product boundaries.
