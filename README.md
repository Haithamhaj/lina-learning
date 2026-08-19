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

### Verification

```bash
npm run typecheck
npm run build
python -m pytest
```

The foundation intentionally does not include Tutor, retrieval, Learning
Intelligence, multimodal, artifact, authentication, or database features.