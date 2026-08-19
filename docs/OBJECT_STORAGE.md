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
Use the rotation procedure below before changing it.

## Safe `SESSION_SECRET` rotation

The rotation tool updates S3 user metadata while carrying forward the
copyable system properties from `HeadObject` (content disposition, caching,
storage class, object lock, and supported server-side encryption settings). It
verifies the complete inventory with the old secret, computes each new HMAC
from the verified metadata, and uses a same-key `CopyObject` with an ETag
precondition. Object bytes are not downloaded or replaced. SSE-C objects are
refused because their customer key is not available to the migration. The
tool accepts an object that already verifies with the new secret so an
interrupted run can be resumed without discarding the old secret.

Perform the following steps during a maintenance window:

1. **Prepare recovery and permissions.** Keep bucket versioning or another
   provider backup available. Keep S3 Block Public Access enabled and use
   Object Ownership **Bucket owner enforced** (or a private object-ACL
   baseline) so same-key copies cannot create public student objects.
   Temporarily grant the deployment identity `s3:ListBucket` for the private
   prefix. The existing `s3:GetObject` and `s3:PutObject` permissions are used
   for the metadata-only copy; no delete permission is needed by the tool.
   Because the copy explicitly preserves provider properties, also grant
   these only when the bucket uses the corresponding feature:
   `s3:GetObjectTagging` and `s3:PutObjectTagging` for object tags,
   `s3:PutObjectRetention` and `s3:PutObjectLegalHold` for Object Lock, and
   the KMS key policy permissions required to decrypt and re-encrypt
   SSE-KMS objects (at minimum `kms:Decrypt`, `kms:GenerateDataKey`, and
   `kms:Encrypt` for the source/destination key). A provider may require
   `s3:BypassGovernanceRetention` for governance-locked objects. Confirm
   these conditional permissions with the provider and key policy.
2. **Freeze storage writes.** Stop upload and delete workers, or put the
   application in maintenance mode, so the inventory cannot change while it is
   being verified. Keep the current `SESSION_SECRET` active until the complete
   rotation succeeds.
3. **Load both secrets through the secret manager.** Make the current value
   available as `OLD_SESSION_SECRET` and the replacement as
   `NEW_SESSION_SECRET`. Do not pass secrets as command-line arguments or
   print them. Keep the old secret available for recovery until verification
   is complete.
4. **Verify without writing.** With the S3 configuration for the target bucket
   loaded, run:

   ```bash
   python -m services.platform.storage.rotate_s3_hmac --dry-run
   ```

   The command prints only a JSON count. A failure means at least one object
   is missing, tampered, or signed with neither secret; do not change
   `SESSION_SECRET` until the cause is resolved. Dry-run validates the
   inventory and signatures only; it cannot prove that the metadata copy has
   the required tag, Object Lock, or KMS write permissions.
5. **Run the migration.** Run the same command without `--dry-run`:

   ```bash
   python -m services.platform.storage.rotate_s3_hmac
   ```

   Confirm that `scanned` equals the expected number of stored application
   objects and that `resigned` plus `already_rotated` equals `scanned`. A
   precondition failure means an object changed; restore the maintenance
   state and rerun with both secrets still available.
6. **Switch the application secret.** Set `SESSION_SECRET` to the new value,
   restart every API/worker process, and verify a known private object can be
   read through the authenticated application path. Also verify a newly
   issued private capability works.
7. **Finish and clean up.** Only after the read checks succeed should the old
   secret be removed from the deployment secret manager and the temporary
   `s3:ListBucket` permission be revoked. If verification fails, restore the
   old application secret, keep both values, and resume the tool rather than
   deleting or replacing objects.

For a non-default secret-variable naming scheme, pass
`--old-secret-env NAME --new-secret-env NAME`. The command refuses
`STORAGE_PROVIDER=local`; local development objects do not use S3 metadata
HMACs.

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
    object prefix. Bucket listing is not required for normal application
    traffic, but `s3:ListBucket` is required temporarily for the documented
    `SESSION_SECRET` rotation procedure. The rotation procedure additionally
    needs the conditional tag, Object Lock, and KMS permissions listed in its
    first step when those bucket features are in use.

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

## Staging S3 integration checks

The repository includes an opt-in end-to-end suite in
`tests/test_storage_s3_integration.py`. It is skipped unless
`RUN_S3_INTEGRATION_TESTS=1` explicitly acknowledges that the tests will write
and delete objects in the configured bucket. It is also skipped when any of the
following server-side values are absent:

```text
RUN_S3_INTEGRATION_TESTS=1
S3_BUCKET
S3_REGION
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
SESSION_SECRET
```

`S3_ENDPOINT` is optional for AWS. For another S3-compatible service, set it to
the service's HTTPS endpoint. The suite constructs the same real boto3 client
path used by the application, then verifies:

- a binary stream survives `put`, `head`, `get`, and an application private
  capability read with the same bytes, checksum, and authenticated metadata;
- a second upload to the same key is rejected by S3 conditional-write
  protection and cannot replace the original;
- an out-of-band metadata rewrite is rejected by the HMAC integrity check; and
- an object can be deleted and is then reported as missing.

Run it only against a dedicated staging bucket or isolated test prefix. The
tests use unique keys under `tests/s3-integration/` and clean each key up in a
fixture, but the credentials still need `s3:GetObject`, `s3:PutObject`, and
`s3:DeleteObject`. Do not point this suite at a production bucket.

Load the values from Replit Secrets or your CI secret manager without putting
them in a committed `.env` file. Set the acknowledgement flag only for a
dedicated staging run, then run:

```bash
RUN_S3_INTEGRATION_TESTS=1 pytest -m s3_integration tests/test_storage_s3_integration.py
```

The normal test command remains network-free even when S3 settings are present;
without the explicit acknowledgement flag, pytest reports this module as
skipped. A configured `http://` endpoint fails before any client is built, which
prevents credentials or private bytes from being sent over plaintext. Treat
that failure as a configuration error and correct the endpoint before
switching `STORAGE_PROVIDER=s3` in production.

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
