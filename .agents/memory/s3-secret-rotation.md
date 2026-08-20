---
name: S3 secret rotation
description: Operational constraints for rotating HMAC metadata signatures on private S3 objects.
---

Rotate private-object metadata signatures as a coordinated, server-side
operation: freeze writes, inventory and authenticate with the old secret,
copy metadata in place with an ETag precondition, then switch the application
secret only after verification. Preserve system properties and refuse
encryption modes whose keys are unavailable; keep the old secret until a
resumable run and post-rotation reads succeed.

**Why:** An HMAC secret change invalidates every existing metadata bundle, and
a metadata replacement that drops encryption, retention, caching, or privacy
properties can damage access or expose student originals even when the bytes
are untouched.

**How to apply:** Use the dedicated rotation migration and its documented
temporary listing/conditional-permission ceremony before changing
`SESSION_SECRET`; validate against a production-like bucket for provider
specific copy and IAM behavior.