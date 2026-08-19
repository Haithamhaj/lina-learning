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

### Verification

```bash
npm run typecheck
npm run build
python -m pytest
```

The foundation intentionally does not include Tutor, retrieval, Learning
Intelligence, multimodal, artifact, content, or object-storage features. The
database layer currently contains only the Phase 0 schema foundation.