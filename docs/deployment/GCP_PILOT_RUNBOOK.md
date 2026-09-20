# GCP Pilot Operations Runbook

## Purpose

Operational runbook for the current Lina controlled live pilot.

This file describes routine build, deploy, migration, verification, log inspection, and rollback procedures.

> **Security:** Never paste, commit, echo, or log raw secret values. Runtime secrets belong in GCP Secret Manager.

## 1. Environment

    export PROJECT_ID="project-lina-2016"
    export REGION="europe-west1"
    export DB_INSTANCE_NAME="lina-db"
    export APP_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/lina/lina-app"
    export WORKER_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/lina/lina-worker"

    gcloud config set project "$PROJECT_ID"

Before deployment:

- use the reviewed source/worktree;
- confirm git status;
- confirm the intended commit is on origin/main when publication is required;
- run repository truth and diff checks;
- confirm whether a migration is included.

## 2. Important topology

### App

lina-app is a Cloud Run Service containing:

- Next.js standalone;
- FastAPI;
- production supervisor.

The integrated worker is disabled in the current topology.

### Worker

lina-worker is a Cloud Run Worker Pool, not a normal HTTP service.

The pilot currently uses one Worker Pool instance.

Do not use Cloud Run service scaling commands against lina-worker.

## 3. Build App

    gcloud builds submit .       --config cloudbuild-app.yaml       --substitutions=_REGION="$REGION"       --project="$PROJECT_ID"

Record:

- Cloud Build ID;
- produced image digest;
- source commit.

Prefer deploying the immutable digest reported by Cloud Build instead of relying only on latest.

## 4. Deploy App

Use the built digest:

    gcloud run deploy lina-app       --image "$APP_IMAGE@sha256:<APP_DIGEST>"       --region "$REGION"       --allow-unauthenticated       --min-instances 0       --max-instances 5       --cpu 1       --memory 2Gi       --add-cloudsql-instances="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"       --update-env-vars APP_ENV=production       --update-env-vars STORAGE_PROVIDER=s3       --update-env-vars S3_BUCKET=lina-storage-project-lina-2016       --update-env-vars S3_REGION=auto       --update-env-vars S3_ENDPOINT=https://storage.googleapis.com       --update-env-vars AWS_REQUEST_CHECKSUM_CALCULATION=when_required       --update-env-vars AWS_RESPONSE_CHECKSUM_VALIDATION=when_required       --update-env-vars MODEL_PROVIDER=openai       --update-env-vars MODEL_NAME=gpt-5.6-luna       --update-env-vars JEV_MODEL_NAME=typesafe/jev-1.13       --update-env-vars JEV_TIMEOUT_SECONDS=5       --update-secrets DATABASE_URL=lina-database-url:latest       --update-secrets SESSION_SECRET=lina-session-secret:latest       --update-secrets CLERK_PUBLISHABLE_KEY=lina-clerk-publishable-key:latest       --update-secrets CLERK_SECRET_KEY=lina-clerk-secret-key:latest       --update-secrets MODEL_API_KEY=lina-model-api-key:latest       --update-secrets OPENROUTER_API_KEY=lina-openrouter-api-key:latest       --update-secrets S3_ACCESS_KEY_ID=lina-s3-access-key-id:latest       --update-secrets S3_SECRET_ACCESS_KEY=lina-s3-secret-access-key:latest       --project="$PROJECT_ID"

### JEV mode preservation

JEV mode values are environment-specific operational settings.

Routine deploys must preserve the currently approved JEV mode values. Do not reset or change JEV mode flags as part of an unrelated deployment.

Using update-env-vars rather than replacing the full environment helps preserve unrelated approved settings.

## 5. Build Worker

    gcloud builds submit .       --config cloudbuild-worker.yaml       --substitutions=_REGION="$REGION"       --project="$PROJECT_ID"

The Worker image includes the browser-preview runtime required by Canvas validation.

Record the build ID and produced immutable digest.

## 6. Deploy Worker Pool

    gcloud beta run worker-pools update lina-worker       --image "$WORKER_IMAGE@sha256:<WORKER_DIGEST>"       --region "$REGION"       --instances 1       --cpu 1       --memory 2Gi       --add-cloudsql-instances="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"       --update-env-vars APP_ENV=production       --update-env-vars STORAGE_PROVIDER=s3       --update-env-vars S3_BUCKET=lina-storage-project-lina-2016       --update-env-vars S3_REGION=auto       --update-env-vars S3_ENDPOINT=https://storage.googleapis.com       --update-env-vars AWS_REQUEST_CHECKSUM_CALCULATION=when_required       --update-env-vars AWS_RESPONSE_CHECKSUM_VALIDATION=when_required       --update-env-vars MODEL_PROVIDER=openai       --update-env-vars MODEL_NAME=gpt-5.6-luna       --update-env-vars CANVAS_MODEL_NAME=gpt-5.6-luna       --update-env-vars JEV_MODEL_NAME=typesafe/jev-1.13       --update-env-vars JEV_TIMEOUT_SECONDS=5       --update-secrets DATABASE_URL=lina-database-url:latest       --update-secrets SESSION_SECRET=lina-session-secret:latest       --update-secrets MODEL_API_KEY=lina-model-api-key:latest       --update-secrets OPENROUTER_API_KEY=lina-openrouter-api-key:latest       --update-secrets S3_ACCESS_KEY_ID=lina-s3-access-key-id:latest       --update-secrets S3_SECRET_ACCESS_KEY=lina-s3-secret-access-key:latest       --project="$PROJECT_ID"

Again, preserve the currently approved JEV mode values.

## 7. Database migrations

### Check code head

    uv run --with-requirements apps/api/requirements.txt alembic heads

### Check production revision

Use the database URL from Secret Manager without printing it:

    export DATABASE_URL="$(gcloud secrets versions access latest       --secret=lina-database-url       --project="$PROJECT_ID")"

    uv run --with-requirements apps/api/requirements.txt alembic current

### Apply migration

Only with explicit production migration approval:

    uv run --with-requirements apps/api/requirements.txt alembic upgrade head

After migration, rerun alembic current and verify the expected head.

## 8. App health verification

### Service state

    gcloud run services describe lina-app       --project="$PROJECT_ID"       --region="$REGION"       --format='yaml(status.latestReadyRevisionName,status.latestCreatedRevisionName,status.conditions,status.traffic,spec.template.spec.containers[0].image)'

Verify:

- Ready=True;
- latest created equals latest ready;
- intended immutable image digest;
- 100% traffic on intended revision unless a deliberate split is being tested.

### HTTP status

    curl -sS       "https://lina-app-176199404149.europe-west1.run.app/api/v1/status"

Expected:

    {"phase":"phase-0","status":"foundation-ready"}

## 9. Worker verification

    gcloud beta run worker-pools describe lina-worker       --project="$PROJECT_ID"       --region="$REGION"       --format='yaml(status.latestReadyRevisionName,status.latestCreatedRevisionName,status.conditions,status.instanceSplits,spec.template.spec.containers[0].image)'

Verify:

- Ready=True;
- intended image digest;
- 100% instance split on the intended revision;
- manual instance count remains the approved pilot value.

A shutdown log during rollout may belong to the replaced revision. Verify that the new revision subsequently starts the jobs worker.

## 10. Verify model/provider configuration without printing secrets

App:

    gcloud run services describe lina-app       --project="$PROJECT_ID"       --region="$REGION"       --format=json

Worker:

    gcloud beta run worker-pools describe lina-worker       --project="$PROJECT_ID"       --region="$REGION"       --format=json

Check only variable names and non-secret values.

Expected architecture:

- MODEL_PROVIDER=openai
- MODEL_NAME=gpt-5.6-luna
- Worker CANVAS_MODEL_NAME=gpt-5.6-luna
- JEV model configured
- OPENROUTER_API_KEY comes from Secret Manager
- current approved JEV mode values preserved

## 11. App logs

Recent errors:

    gcloud logging read       'resource.type="cloud_run_revision" AND resource.labels.service_name="lina-app" AND severity>=ERROR'       --project="$PROJECT_ID"       --freshness=30m       --limit=50       --order=desc

Recent app logs:

    gcloud logging read       'resource.type="cloud_run_revision" AND resource.labels.service_name="lina-app"'       --project="$PROJECT_ID"       --freshness=30m       --limit=100       --order=desc       --format='value(timestamp,severity,textPayload,jsonPayload.message)'

## 12. Worker logs

Recent Worker errors:

    gcloud logging read       'resource.labels.worker_pool_name="lina-worker" AND severity>=ERROR'       --project="$PROJECT_ID"       --freshness=30m       --limit=50       --order=desc

Recent Worker logs:

    gcloud logging read       'resource.labels.worker_pool_name="lina-worker"'       --project="$PROJECT_ID"       --freshness=30m       --limit=100       --order=desc       --format='value(timestamp,severity,textPayload,jsonPayload.message)'

## 13. Cloud SQL health

    gcloud sql instances describe "$DB_INSTANCE_NAME"       --project="$PROJECT_ID"       --format='yaml(name,state,databaseVersion,settings.tier,ipAddresses,settings.databaseFlags)'

Expected state is RUNNABLE.

## 14. Inspect database sessions safely

With DATABASE_URL loaded from Secret Manager:

    psql "$DATABASE_URL" -c "
    SELECT
        pid,
        now() - xact_start AS xact_age,
        now() - query_start AS query_age,
        state,
        wait_event_type,
        wait_event,
        left(query, 100) AS query_sample
    FROM pg_stat_activity
    WHERE state != 'idle' AND pid <> pg_backend_pid()
    ORDER BY xact_age DESC NULLS LAST;
    "

Do not terminate production sessions without understanding what owns them.

## 15. Rollback App

List revisions:

    gcloud run revisions list       --service lina-app       --region "$REGION"       --project="$PROJECT_ID"

Route traffic back to a known-good revision:

    gcloud run services update-traffic lina-app       --to-revisions=<KNOWN_GOOD_REVISION>=100       --region "$REGION"       --project="$PROJECT_ID"

After rollback, verify health and logs.

## 16. Rollback Worker

Prefer updating the Worker Pool back to a known-good immutable image digest.

Before any revision-split rollback, inspect current Worker Pool CLI support and current instance split. Do not guess Worker Pool commands from normal Cloud Run service syntax.

## 17. Post-deploy controlled smoke check

After both App and Worker are ready:

1. open Student Daily;
2. authenticate normally;
3. send a normal Tutor message;
4. confirm no immediate server or client errors;
5. when appropriate, exercise a Canvas path;
6. confirm Worker receives and processes jobs;
7. inspect recent ERROR logs;
8. verify DB migration/head if the deployment included schema changes.

Do not turn the smoke check into a scripted learning-quality acceptance.

## 18. Real-use rule

Once infrastructure is healthy, natural use becomes the primary source of product evidence.

When an issue appears:

1. capture what the learner experienced;
2. inspect runtime/log/DB evidence;
3. distinguish model variation from contract failure;
4. record the issue before patching;
5. patch immediately only if the defect blocks further useful testing or creates a safety/data-integrity risk.

## 19. Protected boundaries

Routine operations must not silently change:

- Primary Tutor authority;
- child Safety;
- Parent Boundaries;
- ownership and privacy;
- Core Profile authority;
- Personal Facts authority;
- Learning Intelligence / Evidence semantics;
- Studio durable state;
- Canvas sandbox/provenance;
- JEV bounded-decision scope;
- production provider/model policy.
