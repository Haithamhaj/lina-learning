# GCP Pilot Reference

## Source Baseline
- **Repository**: `https://github.com/Haithamhaj/lina-learning.git`
- **Base SHA**: `3f116a08c38c91726ae45930ac55e843b7ad631c`
- **Working Branch**: `antigravity/gcp-pilot`
- **Purpose of this Branch**: Dedicated branch for establishing, maintaining, and verifying the cost-optimized GCP deployment for the single-child Lina pilot while preserving exact product behavior.
- **Canonical Product Source**: The `main` branch remains the canonical product source until this pilot branch completes full validation, passes regression testing, and is reviewed. No direct pushes or merges to `main` shall occur during this pilot.

## Pilot Goal
- **Scope**: Single-child pilot ("Lina") evaluation.
- **Cost Target**: Minimal infrastructure spend (~$15 - $22/month active; <$1/month paused) without sacrificing system reliability or core features.
- **Invariance Rule**: Product behavior, domain boundaries, intelligence algorithms, tutor pedagogy, and safety policies must remain completely unchanged.

## Current Architecture

| Component | Technology / Service | Deployment Status | Details |
| :--- | :--- | :--- | :--- |
| **lina-app** | Google Cloud Run (Fully Managed) | **DEPLOYED** | Single container housing Next.js standalone frontend + FastAPI backend + Process Supervisor. |
| **Next.js Frontend** | Next.js 14 Standalone (Node 20) | **DEPLOYED** | Bound to public Cloud Run `$PORT` (5000), serving SSR pages, API routes, and client bundles. |
| **FastAPI Backend** | FastAPI / Uvicorn (Python 3.11) | **DEPLOYED** | Bound to internal loopback (`127.0.0.1:8000`), proxied by Next.js rewrites for `/api/*`. |
| **Worker Topology** | Process Supervisor / Cloud Run | **DEPLOYED / CONFIGURED** | Default: Supervisor runs background worker in `lina-app` container (`LINA_ENABLE_WORKER=true`). Standalone worker pool image (`Dockerfile.worker`) is also built and available in Artifact Registry if decoupled worker execution is required. |
| **Database** | Google Cloud SQL (PostgreSQL 16) | **DEPLOYED** | Single instance `lina-db` (Enterprise tier, `db-f1-micro`). Connected via Cloud SQL Auth Proxy / Unix socket. |
| **Vector Engine** | PostgreSQL `pgvector` extension | **DEPLOYED** | Enabled in database `lina` for embedding storage and similarity indexing. |
| **Object Storage** | Google Cloud Storage (GCS) | **CONFIGURED** | Bucket `lina-storage-project-lina-2016` (europe-west1). S3-interoperability adapter configured in application code. |
| **Authentication** | Clerk Auth | **DEPLOYED** | Production/development instance `fine-kid-9979.clerk.accounts.dev`. JWT session verification on backend. |
| **Secrets Management** | Google Secret Manager | **DEPLOYED** | Secrets stored centrally in GCP and injected into Cloud Run environment variables at runtime. |
| **Model Runtime** | OpenAI API (`gpt-5.6-luna`) | **DEPLOYED** | Direct streaming SSE connection to OpenAI compatible endpoint for tutor and studio reasoning. |
| **Decoupled Worker Pool** | Cloud Run Worker Pool | **CONFIGURED / NOT YET VERIFIED** | Standalone worker deployment built and configured for heavy decoupled workloads; currently dormant while integrated supervisor worker is active. |
| **Private VPC Connector** | Serverless VPC Access | **PROPOSED** | Direct private IP routing between Cloud Run and Cloud SQL (currently using authorized networks + Cloud SQL connection volume). |

## Google Cloud Resources

| Resource Name | Service Type | Region / Zone | Size / Tier | Purpose | Current Status | Continuous Cost Implications |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lina-app` | Cloud Run Service | `europe-west1` | 1 vCPU, 2 GiB RAM, min: 0, max: 5 | Core web app, API, and supervisor | Running (Active) | Scales to $0 when idle; ~$0.00002400 / vCPU-sec, ~$0.00000250 / GiB-sec during traffic. |
| `lina-worker` | Cloud Run Service / Pool | `europe-west1` | 1 vCPU, 2 GiB RAM, min: 0, max: 1 | Standalone background job processing | Built / Dormant | $0 when min-instances=0 or paused. |
| `lina-db` | Cloud SQL (PostgreSQL 16) | `europe-west1-c` | `db-f1-micro` (1 shared vCPU, 0.6 GB RAM, 10 GB SSD) | Relational database & vector storage | RUNNABLE | ~$7.67 / month compute + ~$1.70 / month SSD storage (Always-on unless stopped). |
| `lina-storage-project-lina-2016` | Cloud Storage Bucket | `europe-west1` | Standard storage, uniform access | Visual assets, uploads, and artifacts | Active | ~$0.02 / GB / month (<$0.50 / month for pilot volume). |
| `lina` | Artifact Registry | `europe-west1` | Standard Docker repository | Container images storage (`lina-app`, `lina-worker`) | Active | ~$0.10 / GB / month (~$1.00 / month for active versions). |
| `lina-database-url` | Secret Manager | Global | Automatic replication | Connection string for Cloud SQL | Active | Negligible (<$0.06 / secret / month). |
| `lina-session-secret` | Secret Manager | Global | Automatic replication | Session cookie signing secret | Active | Negligible. |
| `lina-clerk-publishable-key` | Secret Manager | Global | Automatic replication | Clerk public API key | Active | Negligible. |
| `lina-clerk-secret-key` | Secret Manager | Global | Automatic replication | Clerk backend validation key | Active | Negligible. |
| `lina-model-api-key` | Secret Manager | Global | Automatic replication | LLM provider API key | Active | Negligible. |

*Note: Secret values are managed strictly inside GCP Secret Manager and are never stored in code, Git commits, or documentation.*

## Runtime Configuration

### Public / Non-Secret Environment Variables
- `NODE_ENV`: `production`
- `HOSTNAME`: `0.0.0.0`
- `PORT`: `5000` (dynamically assigned by Cloud Run)
- `API_HOST`: `127.0.0.1`
- `API_PORT`: `8000`
- `LINA_PRODUCTION_PYTHON`: `python`
- `LINA_ENABLE_WORKER`: `false` (in supervisor when worker is decoupled, `true` when integrated)
- `PYTHONUNBUFFERED`: `1`
- `WEB_ORIGIN`: `https://lina-app-176199404149.europe-west1.run.app`
- `ALLOWED_ORIGINS`: `["https://lina-app-176199404149.europe-west1.run.app","https://lina-app-7m3xek3xsa-ew.a.run.app"]`
- `MODEL_PROVIDER`: `openai`
- `MODEL_NAME`: `gpt-5.6-luna`

### Secret Environment Variable References (Values in Secret Manager)
- `DATABASE_URL`: Mounted from `lina-database-url:latest`
- `SESSION_SECRET`: Mounted from `lina-session-secret:latest`
- `CLERK_PUBLISHABLE_KEY`: Mounted from `lina-clerk-publishable-key:latest`
- `CLERK_SECRET_KEY`: Mounted from `lina-clerk-secret-key:latest`
- `MODEL_API_KEY`: Mounted from `lina-model-api-key:latest`

## Database
- **Engine**: PostgreSQL 16 Enterprise Edition.
- **Instance Tier**: `db-f1-micro` (shared core, 0.6 GB RAM, 10 GB SSD).
- **Extensions**: `vector` (pgvector) enabled.
- **Migration Engine**: Alembic.
- **Current Head Revision**: `4f3f83db9c50` (`track_learning_session_activity`).
- **Migration Status**: 45 migrations applied; schema matches code contract.
- **Configured Database Flags**:
  - `idle_in_transaction_session_timeout = 30000` (30 seconds):
    - *When Added*: 2026-09-14 06:15 UTC.
    - *Why*: Cloud SQL `db-f1-micro` has strict memory and connection pooling limits. Orphaned sessions remaining idle inside an open transaction can block subsequent transactions and lead to starvation.
    - *Status*: **MITIGATION ONLY**, NOT a proven root-cause fix. The permanent fix requires application-level audit of transaction lifecycles, ensuring database sessions are not held open across asynchronous streaming model calls.

## Storage
- **Provider**: Google Cloud Storage (GCS) accessed via S3-compatible interoperability API.
- **Bucket**: `gs://lina-storage-project-lina-2016` (Region: `europe-west1`).
- **Adapter**: `S3ObjectStorage` via `services/platform/storage/s3.py`.
- **Private Access Behavior**: Uniform bucket-level access is enabled; public read is disabled; soft delete policy retention is 7 days. Objects are signed with presigned URLs for client viewing.
- **Validation Status**: Bucket provisioned and credentials configured; live end-to-end asset upload validation is **NOT YET VERIFIED**.

## Authentication
- **Provider**: Clerk Auth (`https://clerk.com`).
- **Instance**: `fine-kid-9979.clerk.accounts.dev`.
- **Deployed Origins Authorized in Clerk**:
  - `https://lina-app-176199404149.europe-west1.run.app`
  - `https://lina-app-7m3xek3xsa-ew.a.run.app`
- **Flow**: Next.js client renders Clerk sign-in widgets. On request to FastAPI, the client sends `Authorization: Bearer <clerk_session_jwt>`. FastAPI validates the JWT against Clerk JWKS public keys and loads the associated student/parent profile.

## Model Runtime
- **Provider**: OpenAI-compatible runtime interface.
- **Model**: `gpt-5.6-luna`.
- **Streaming**: Server-Sent Events (SSE) protocol streaming tokens, reasoning events, and visual canvas commands to the client.
- **Authentication**: `MODEL_API_KEY` injected securely from Secret Manager at container initialization.

## Cost Model

| State | Estimated Monthly Cost | Components |
| :--- | :--- | :--- |
| **Active Pilot** (1 child, 1-2 sessions/day) | **$15.00 - $22.00 / mo** | Cloud SQL `db-f1-micro` (~$9.50) + Cloud Run (~$2.00-$4.00) + GCS & Artifact Registry (~$1.50) + Model API tokens (~$4.00-$7.00). |
| **Paused Pilot** (Services idle, DB running) | **~$9.50 / mo** | Cloud SQL `db-f1-micro` (~$9.50) + GCS storage (<$0.50). Cloud Run scales to $0.00. |
| **Cold Paused Pilot** (Cloud SQL stopped) | **<$1.00 / mo** | Storage & artifacts only. All compute and database costs cease completely. |

### Scaling Characteristics
- **Scales to Zero**: Cloud Run `lina-app`, Cloud Run `lina-worker`, Cloud Build. When no requests are being processed, compute cost is $0.
- **Always-On Compute**: Cloud SQL `lina-db` runs continuously unless manually paused (`--activation-policy=NEVER`).
- **Manual Pause Mechanism**: Execute `gcloud sql instances patch lina-db --activation-policy=NEVER` to eliminate the ~$9.50/month database compute charge when testing is paused for days/weeks.

## Known Issues

### 1. Daily Session Connection Hang During Visual Explanation
- **Classification**: `ROOT CAUSE UNDER INVESTIGATION`
- **Observed Symptom**: During an active session in `/student/daily`, a student asked the tutor about honey ("اشرح لي عن العسل") and subsequently requested a non-text visual explanation ("اعمل شرح غير نصي"). The session hung, followed by a connection disruption notification ("صار في خلل بالاتصال"). Upon refreshing the page, no generated visual diagram or Canvas scene appeared.
- **Affected Session**: Interactive student daily session on 2026-09-14 ~06:00 UTC.
- **Mitigations Already Applied**:
  1. Configured Cloud SQL flag `idle_in_transaction_session_timeout = 30000` to prevent hanging PostgreSQL transactions from blocking the connection pool.
  2. Enhanced supervisor logging with unbuffered stdout (`PYTHONUNBUFFERED=1`) and process tags (`[api]`, `[next]`, `[worker]`) to identify the failing sub-process.
  3. Corrected student landing destination to `/student/daily`.
- **Evidence Available**:
  - Live client receives network disconnection during long-running generative SSE calls.
  - Server logs previously exhibited transaction timeout warnings under long LLM generation cycles.
- **Unresolved Questions**:
  1. Is the FastAPI request handler holding an open database transaction while awaiting the streaming completion of the visual generator from OpenAI?
  2. Is Cloud Run's HTTP request timeout closing the connection prematurely during multi-step visual reasoning?
  3. Is the Canvas Specialist failing to commit generated asset metadata, causing the client to wait indefinitely for an asset ID that was never saved?

## Verification Record

| Level | Test / Check | Result |
| :--- | :--- | :--- |
| **Local Tests** | Supervisor topology with `LINA_ENABLE_WORKER` toggle | **PASSED** (Verified worker addition and omission) |
| **Local Tests** | Requirements & constraints validation (PyTorch CPU wheels) | **PASSED** (Builds without CUDA 4GB bloat) |
| **Container Tests** | Cloud Build `Dockerfile.app` compilation | **PASSED** (Next.js standalone + Python 3.11 image built) |
| **Container Tests** | Cloud Build `Dockerfile.worker` compilation | **PASSED** (Worker container built successfully) |
| **Live GCP Tests** | Cloud SQL Connectivity from Cloud Run | **PASSED** (Instance `lina-db` connected, queries execute) |
| **Live GCP Tests** | Alembic migration execution | **PASSED** (Migrated to head revision `4f3f83db9c50`) |
| **Live GCP Tests** | Cloud Run service startup & health | **PASSED** (FastAPI ready, Next.js starts on port 5000) |
| **Live GCP Tests** | Public HTTPS Endpoint reachability | **PASSED** (`https://lina-app-176199404149.europe-west1.run.app`) |
| **Manual Browser** | Clerk Authentication & Sign-in | **PASSED** (User authenticates successfully) |
| **Manual Browser** | Student entry redirection to `/student/daily` | **PASSED** (Lands directly on Daily Student space) |
| **Manual Browser** | Text tutoring conversation | **PASSED** (Tutor responds to conversational prompts) |
| **Manual Browser** | Canvas visual diagram generation | **FAILED / INVESTIGATING** (Connection disruption occurred) |

## Protected Product Areas
The GCP deployment and infrastructure configuration must strictly preserve and never alter:
1. **Tutor Pedagogy**: Socratic questioning style, tone, scaffolding rules, and curriculum pacing.
2. **Learning Intelligence**: Mastery evaluation, cognitive tracking, and session summarization.
3. **Evidence**: Student interaction transcripts, observation records, and learning milestones.
4. **Profile**: Student preferences, grade level, and learning goals.
5. **Personal Facts / Memory**: Personal memory retention and fact extraction boundaries.
6. **Child Safety**: Content filtering, emotional distress detection, and policy enforcements.
7. **Parent Boundaries**: Parent portal data segregation, consent verification, and oversight controls.
8. **Canvas Authority**: Canvas scene state mutations and layout computation algorithms.
9. **Studio Authority**: Studio asset compilation, rendering contracts, and artifact specifications.
