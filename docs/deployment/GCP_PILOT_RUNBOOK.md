# GCP Pilot Operations Runbook

This runbook provides step-by-step operational procedures for managing, deploying, monitoring, troubleshooting, and pausing the Lina GCP pilot environment.

> **CRITICAL SECURITY NOTE**: Never paste, commit, or log raw credentials or secret values. Secrets are managed through GCP Secret Manager.

---

## 1. Project & Environment Baseline

Ensure your active shell is targeted to the pilot project and region:

```bash
export PROJECT_ID="project-lina-2016"
export REGION="europe-west1"
export DB_INSTANCE_NAME="lina-db"

gcloud config set project "$PROJECT_ID"
```

---

## 2. Deploying `lina-app`

The `lina-app` service packages the Next.js frontend, FastAPI backend, and supervisor.

### Step A: Build the container image via Cloud Build
```bash
gcloud builds submit . \
  --config cloudbuild-app.yaml \
  --substitutions=_REGION="$REGION" \
  --project="$PROJECT_ID"
```

### Step B: Deploy to Cloud Run
```bash
gcloud run deploy lina-app \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/lina/lina-app:latest" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 5 \
  --cpu 1 \
  --memory 2Gi \
  --add-cloudsql-instances="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME" \
  --set-env-vars APP_ENV=production \
  --set-env-vars STORAGE_PROVIDER=s3 \
  --set-env-vars S3_BUCKET=lina-storage-project-lina-2016 \
  --set-env-vars S3_REGION=auto \
  --set-env-vars S3_ENDPOINT=https://storage.googleapis.com \
  --set-env-vars AWS_REQUEST_CHECKSUM_CALCULATION=when_required \
  --set-env-vars AWS_RESPONSE_CHECKSUM_VALIDATION=when_required \
  --set-env-vars MODEL_PROVIDER=openai \
  --set-env-vars MODEL_NAME=gpt-5.6-luna \
  --set-secrets DATABASE_URL=lina-database-url:latest \
  --set-secrets SESSION_SECRET=lina-session-secret:latest \
  --set-secrets CLERK_PUBLISHABLE_KEY=lina-clerk-publishable-key:latest \
  --set-secrets CLERK_SECRET_KEY=lina-clerk-secret-key:latest \
  --set-secrets MODEL_API_KEY=lina-model-api-key:latest \
  --set-secrets S3_ACCESS_KEY_ID=lina-s3-access-key-id:latest \
  --set-secrets S3_SECRET_ACCESS_KEY=lina-s3-secret-access-key:latest \
  --project="$PROJECT_ID"
```

---

## 3. Deploying `lina-worker`

If decoupled background processing is activated, deploy the standalone Worker Pool.

> **NOTE**: `lina-worker` is a Cloud Run **Worker Pool** (`gcloud beta run worker-pools`), not a standard HTTP Service.

### Step A: Build worker container image
The composing Worker image requires Node 20, the lockfile-pinned Canvas preview
runtime (`playwright`, `sucrase`, and `typescript`), and the Chrome channel
installed by that Playwright version.

```bash
gcloud builds submit . \
  --config cloudbuild-worker.yaml \
  --substitutions=_REGION="$REGION" \
  --project="$PROJECT_ID"
```

### Step B: Deploy worker pool
```bash
gcloud beta run worker-pools update lina-worker \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/lina/lina-worker:latest" \
  --region "$REGION" \
  --min-instances 0 \
  --max-instances 1 \
  --cpu 1 \
  --memory 2Gi \
  --add-cloudsql-instances="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME" \
  --update-env-vars APP_ENV=production \
  --update-env-vars STORAGE_PROVIDER=s3 \
  --update-env-vars S3_BUCKET=lina-storage-project-lina-2016 \
  --update-env-vars S3_REGION=auto \
  --update-env-vars S3_ENDPOINT=https://storage.googleapis.com \
  --update-env-vars AWS_REQUEST_CHECKSUM_CALCULATION=when_required \
  --update-env-vars AWS_RESPONSE_CHECKSUM_VALIDATION=when_required \
  --update-env-vars MODEL_PROVIDER=openai \
  --update-env-vars MODEL_NAME=gpt-5.6-luna \
  --update-env-vars CANVAS_MODEL_NAME=gpt-5.6-luna \
  --update-secrets DATABASE_URL=lina-database-url:latest \
  --update-secrets SESSION_SECRET=lina-session-secret:latest \
  --update-secrets MODEL_API_KEY=lina-model-api-key:latest \
  --update-secrets S3_ACCESS_KEY_ID=lina-s3-access-key-id:latest \
  --update-secrets S3_SECRET_ACCESS_KEY=lina-s3-secret-access-key:latest \
  --project="$PROJECT_ID"
```

---

## 4. Pausing and Resuming the Worker

### Integrated Worker (Inside `lina-app`)
The supervisor toggles the integrated background worker via `LINA_ENABLE_WORKER`:

- **Pause Integrated Worker**:
  ```bash
  gcloud run services update lina-app \
    --region "$REGION" \
    --set-env-vars LINA_ENABLE_WORKER="false" \
    --project="$PROJECT_ID"
  ```

- **Resume Integrated Worker**:
  ```bash
  gcloud run services update lina-app \
    --region "$REGION" \
    --set-env-vars LINA_ENABLE_WORKER="true" \
    --project="$PROJECT_ID"
  ```

### Decoupled Worker (`lina-worker`)
- **Pause Decoupled Worker**:
  ```bash
  gcloud run services update lina-worker \
    --region "$REGION" \
    --min-instances 0 \
    --max-instances 0 \
    --project="$PROJECT_ID"
  ```

- **Resume Decoupled Worker**:
  ```bash
  gcloud run services update lina-worker \
    --region "$REGION" \
    --min-instances 1 \
    --max-instances 1 \
    --project="$PROJECT_ID"
  ```

---

## 5. Checking Cloud Run Logs

View real-time, unbuffered logs streaming from `lina-app`:

```bash
# View last 50 log lines
gcloud beta run services logs tail lina-app --region "$REGION" --project "$PROJECT_ID"
```

Or query recent logs using the logging CLI:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="lina-app"' \
  --limit 50 \
  --order desc \
  --format="value(textPayload,jsonPayload.message)" \
  --project="$PROJECT_ID"
```

To filter by process component (supervisor tags):
```bash
# API logs only
gcloud logging read 'resource.labels.service_name="lina-app" AND textPayload=~"\[api\]"' --limit 30 --project="$PROJECT_ID"

# Next.js logs only
gcloud logging read 'resource.labels.service_name="lina-app" AND textPayload=~"\[next\]"' --limit 30 --project="$PROJECT_ID"
```

---

## 6. Checking Worker Logs

For decoupled `lina-worker`:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="lina-worker"' \
  --limit 50 \
  --order desc \
  --format="value(textPayload,jsonPayload.message)" \
  --project="$PROJECT_ID"
```

---

## 7. Checking Cloud SQL Status

Inspect Cloud SQL health, connectivity, and resource configuration:

```bash
gcloud sql instances describe "$DB_INSTANCE_NAME" --project="$PROJECT_ID" --format="yaml(name,state,databaseVersion,settings.tier,ipAddresses,settings.databaseFlags)"
```

Confirm that the status is `RUNNABLE` and `idle_in_transaction_session_timeout` is active:

```bash
gcloud sql instances describe "$DB_INSTANCE_NAME" --project="$PROJECT_ID" --format="value(settings.databaseFlags)"
```

---

## 8. Database Migrations (Alembic)

### Check Current Migration Revision on Cloud SQL
Using Cloud SQL proxy or temporary local migration runner:

```bash
# Verify current revision in alembic_version table
DB_IP=$(gcloud sql instances describe "$DB_INSTANCE_NAME" --project="$PROJECT_ID" --format='value(ipAddresses[0].ipAddress)')

# Check current revision in the repository code
alembic heads
```

### Run Migrations to Latest Head
To apply pending migrations to Cloud SQL:

```bash
# Ensure DATABASE_URL is sourced from Secret Manager or environment
export DATABASE_URL=$(gcloud secrets versions access latest --secret="lina-database-url" --project="$PROJECT_ID")

# Run Alembic upgrade
alembic upgrade head
```

---

## 9. Inspecting Active Database Sessions and Locks Safely

If requests appear to hang or fail with transaction lock contention:

```bash
# Safe read-only inspection query for active locks and long-running queries
psql "$DATABASE_URL" -c "
SELECT
    pid,
    now() - xact_start AS xact_age,
    now() - query_start AS query_age,
    state,
    wait_event_type,
    wait_event,
    left(query, 80) AS query_sample
FROM pg_stat_activity
WHERE state != 'idle' AND pid <> pg_backend_pid()
ORDER BY xact_age DESC NULLS LAST;
"
```

To view transactions that are currently `idle in transaction`:

```bash
psql "$DATABASE_URL" -c "
SELECT
    pid,
    now() - state_change AS idle_age,
    left(query, 80) AS last_query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY idle_age DESC;
"
```

To terminate a specific stuck transaction safely without restarting the instance:

```bash
# Replace <PID> with the target connection pid
psql "$DATABASE_URL" -c "SELECT pg_terminate_backend(<PID>);"
```

---

## 10. Restarting Services

To force a fresh container instance startup:

```bash
# Update service with no configuration changes to trigger revision recreation
gcloud run services update lina-app --region "$REGION" --project="$PROJECT_ID"
```

---

## 11. Rolling Back to a Prior Container Revision

If an updated revision causes regressions:

### List available revisions:
```bash
gcloud run revisions list --service lina-app --region "$REGION" --project="$PROJECT_ID"
```

### Route 100% traffic immediately to a known-good revision:
```bash
# Example: gcloud run services update-traffic lina-app --to-revisions=lina-app-00011-xxx=100 --region europe-west1
gcloud run services update-traffic lina-app \
  --to-revisions=<REVISION_NAME>=100 \
  --region "$REGION" \
  --project="$PROJECT_ID"
```

---

## 12. Verifying Clerk Authentication Setup

1. Check that Clerk secrets are present in Secret Manager:
   ```bash
   gcloud secrets versions access latest --secret="lina-clerk-publishable-key" --project="$PROJECT_ID" | cut -c 1-10
   gcloud secrets versions access latest --secret="lina-clerk-secret-key" --project="$PROJECT_ID" | cut -c 1-10
   ```
2. Verify deployed origins in Clerk Dashboard (`https://dashboard.clerk.com`):
   Ensure both URLs are registered under "Allowed Origins" and "Redirect URLs":
   - `https://lina-app-176199404149.europe-west1.run.app`
   - `https://lina-app-7m3xek3xsa-ew.a.run.app`
3. Verify public login flow:
   Navigate to `https://lina-app-176199404149.europe-west1.run.app/sign-in` and confirm login UI loads.

---

## 13. Verifying Object Storage (Cloud Storage)

1. Verify bucket existence and uniform bucket access:
   ```bash
   gcloud storage buckets describe gs://lina-storage-project-lina-2016 --project="$PROJECT_ID" --format="yaml(name,location,uniformBucketLevelAccess)"
   ```
2. Verify HMAC keys for S3-interoperability:
   ```bash
   gcloud storage hmac list --project="$PROJECT_ID" --service-account="lina-storage-runtime@$PROJECT_ID.iam.gserviceaccount.com"
   ```
3. Test S3-compatible interoperability access:
   - Ensure `S3_REGION=auto` and `S3_ENDPOINT=https://storage.googleapis.com`.
   - Ensure `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` and `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required` are set to suppress botocore default `x-amz-sdk-checksum-algorithm: CRC32` headers (which cause `SignatureDoesNotMatch` with GCS XML API).
4. Direct GCS upload/download permissions check:
   ```bash
   echo "storage verification $(date)" > /tmp/pilot-test.txt
   gcloud storage cp /tmp/pilot-test.txt gs://lina-storage-project-lina-2016/diagnostics/test.txt --project="$PROJECT_ID"
   gcloud storage cat gs://lina-storage-project-lina-2016/diagnostics/test.txt --project="$PROJECT_ID"
   gcloud storage rm gs://lina-storage-project-lina-2016/diagnostics/test.txt --project="$PROJECT_ID"
   rm -f /tmp/pilot-test.txt
   ```

---

## 14. Estimating Current Cost

1. Query billing account summary via gcloud:
   ```bash
   gcloud beta billing accounts list
   ```
2. Estimate Cloud Run resource consumption:
   Check request counts and active instance seconds in Cloud Monitoring:
   ```bash
   gcloud monitoring metric-descriptors describe run.googleapis.com/container/instance_count
   ```
3. Cloud SQL standard baseline calculation:
   `db-f1-micro` runs at ~$0.0105/hour (~$7.67/month) + 10 GB SSD at ~$0.17/GB/month (~$1.70/month) = **~$9.37/month** base.

---

## 15. Stopping the Pilot Without Deleting Data

When pausing the pilot for extended periods (e.g., between testing rounds), cease all recurring costs while preserving all databases, user accounts, tables, and asset files:

### Step 1: Scale Cloud Run to absolute zero
Ensure min-instances is 0 (it will automatically stop charging compute when no HTTP requests arrive):
```bash
gcloud run services update lina-app --min-instances 0 --region "$REGION" --project="$PROJECT_ID"
gcloud beta run worker-pools update lina-worker --min-instances 0 --max-instances 0 --region "$REGION" --project="$PROJECT_ID" 2>/dev/null || true
```

### Step 2: Pause Cloud SQL Instance (Stops DB Compute Charges)
Cloud SQL provides an activation policy flag that halts the VM while preserving the SSD storage:
```bash
gcloud sql instances patch "$DB_INSTANCE_NAME" --activation-policy=NEVER --project="$PROJECT_ID" --quiet
```
*Result: Database compute billing ($7.67/month) drops to $0.00 immediately. Only the 10GB disk storage ($1.70/month) is retained.*

### Step 3: Resume Pilot When Ready
To resume the pilot:
```bash
# 1. Restart Cloud SQL instance
gcloud sql instances patch "$DB_INSTANCE_NAME" --activation-policy=ALWAYS --project="$PROJECT_ID" --quiet

# 2. Verify Cloud Run responds
curl -s -o /dev/null -w "%{http_code}\n" https://lina-app-176199404149.europe-west1.run.app
```
