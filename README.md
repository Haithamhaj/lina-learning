# Lina Personal Learning System

This repository contains the Phase 0 foundation for Lina's Personal Learning
System: a minimal Next.js web shell and FastAPI API shell organized around the
approved modular-monolith direction.

The product and architecture are governed by the documents in `docs/`.
Implementation work is tracked in `TASKS.md`; only tasks marked `READY` should
be executed.

## Local commands

### Web

```bash
npm install
npm run dev
```

The web shell listens on `0.0.0.0:5000`.

### API

```bash
python -m pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt
npm run dev:api
```

The API shell listens on `0.0.0.0:8000`.

### Authentication

Authentication is provided by the Replit-managed Clerk tenant. The web app uses
Clerk's cookie-backed session, branded `/sign-in` and `/sign-up` routes, and
separate `/student` and `/parent` surfaces. Users default safely to `STUDENT`;
the explicit `PARENT_ADMIN` role must be present in Clerk metadata/claims.

FastAPI protected routes verify Clerk JWTs against the configured Clerk JWKS and
enforce the role boundary. The current web shells do not call those endpoints
yet; when web API calls are added, preserve Clerk's same-origin cookie transport
instead of copying tokens into custom browser headers.

### Database

The development database is the Replit-managed PostgreSQL instance. Apply the
checked-in Alembic migrations explicitly:

```bash
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

The migrations enable the PostgreSQL `vector` extension, create the identity,
student relationship, and grade-period foundation tables, and add the explicit
user role constraint. Production schema changes are applied through the Replit
Publish flow, not application startup.

### Object storage

`services/platform/storage` owns a provider-neutral private object contract.
Development uses a filesystem provider rooted at `STORAGE_DIR` (default:
`.local/storage/`). Objects retain content type, size, metadata, and SHA-256
checksum. Keys cannot traverse outside the storage root, and an existing key
cannot be silently overwritten so original books and student work remain safe.

Private reads use short-lived signed capabilities through the service contract;
neither provider creates public URLs or exposes storage through the web app. Set
`STORAGE_PROVIDER=s3` for production and provide the bucket, region, and
server-only credentials through Replit Secrets. `S3_ENDPOINT` is optional for
AWS and should be set for another S3-compatible service. See
`docs/OBJECT_STORAGE.md` for bucket lifecycle, integrity model, and deployment
requirements.

### Verification

```bash
npm run test:db:up
npm run test:python
npm run test:db:down
```

`npm run test:python` resets the named `lina_learning_test` database, applies
the complete Alembic history, runs the full Python suite, and removes the
container and volume afterward. It refuses to run against any other database
name and requires the runner's explicit `LINA_TEST_DATABASE=1` boundary, so
test fixtures cannot truncate the development database. `npm run test` adds
the web typecheck before that same Python path.

For CI, provide a PostgreSQL service with pgvector and the exact
`lina_learning_test` database, then set
`LINA_TEST_DATABASE_MANAGED_EXTERNALLY=1` and run `npm run test:python`.
The runner still applies migrations and enables every PostgreSQL suite.

The foundation intentionally does not include Tutor, retrieval, Learning
Intelligence, multimodal, artifact, content-processing, or upload UI features.
The database layer currently contains only the Phase 0 schema foundation.
