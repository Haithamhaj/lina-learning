# Private object storage operations

The API storage contract is private by default. The S3-compatible provider uses
the server-side client for all reads and writes, and returns an application-
signed capability instead of a public or presigned URL. Original keys are
immutable: a second upload for the same key fails rather than replacing the
first upload.

## Integrity model

Every object written by the S3 provider stores an HMAC-SHA256 signature over a
canonical bundle that covers the object key, content type, byte size, SHA-256
checksum, stored-at timestamp, and all caller-supplied metadata. The signature
is computed with `SESSION_SECRET` as the key and stored as private S3 user
metadata (`lina-hmac`).

Reading an object (`head`, `get`, `create_private_access`) verifies the bundle
signature before returning any metadata. An absent or invalid signature causes
`StorageIntegrityError` regardless of whether the raw bytes match their stored
SHA-256 checksum. This means a bucket-level writer who replaces user-metadata
fields without knowing `SESSION_SECRET` cannot forge a response that passes
verification.

**Consequence:** `SESSION_SECRET` must be stable across application restarts.
Rotating it without re-signing every stored object's metadata will break reads.
Plan a coordinated rotation if you ever change the secret.

## Bucket requirements

For a production bucket:

1. Keep **Block Public Access** enabled and do not grant `s3:GetObject` to
   `Principal: "*"`.
2. Use the bucket's default server-side encryption (SSE-S3 or SSE-KMS).
   Bucket versioning is optional for disaster-recovery purposes; the application
   already refuses logical replacement at the key level.
3. Add a lifecycle rule that aborts incomplete multipart uploads after a short
   period, such as one day. This bounds the cost of interrupted large uploads.
4. Do not configure a public website endpoint or public CDN origin for student
   originals. Downloads must go through an authenticated API path that checks
   the application's private capability.
5. Grant the deployment identity only the required bucket actions:
   `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` for the private
   object prefix. Bucket listing is not required by the provider.

## Endpoint transport security

`S3_ENDPOINT` must use HTTPS. The application rejects any endpoint whose URL
scheme is not `https://` so that credentials (SigV4 authorization headers) and
private object bytes are never sent over plaintext transport. Endpoints must not
embed credentials in the URL.

For development or integration tests that use a local fake/moto client, inject
the client directly via the `client` constructor parameter instead of setting an
`http://` endpoint; the transport check is skipped when an explicit client is
provided. AWS endpoint URLs do not require setting `S3_ENDPOINT` — leave it
empty and set `S3_REGION` only.

## Deployment configuration

Set these server-only values in the deployment environment:

```text
APP_ENV=production
STORAGE_PROVIDER=s3
S3_BUCKET=<private bucket name>
S3_REGION=<bucket region>
S3_ENDPOINT=<HTTPS-only S3-compatible endpoint; leave empty for AWS>
S3_ACCESS_KEY_ID=<deployment access key>
S3_SECRET_ACCESS_KEY=<deployment secret>
SESSION_SECRET=<stable application signing secret — must not change without re-signing>
```

Put credentials and `SESSION_SECRET` in Replit Secrets or the deployment
environment's secret manager. Never commit them, place them in `.env.example`,
or expose them through `NEXT_PUBLIC_*` settings. The production configuration
also requires `DATABASE_URL`.

**Production storage provider is mandatory.** Starting the application with
`APP_ENV=production` and `STORAGE_PROVIDER=local` is a configuration error that
fails at startup. Production must use an explicitly configured, durable provider
(`s3`).

Before switching a deployment to S3, create the bucket and lifecycle rule,
apply the least-privilege policy, verify the endpoint and region, and run the
storage integration checks against a non-production bucket.
