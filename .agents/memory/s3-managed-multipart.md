---
name: S3 managed multipart publishing
description: Preserve immutable destination keys when boto3 managed uploads cannot send conditional upload headers.
---

Boto3 managed `upload_fileobj` transfers do not accept `IfNoneMatch` as an upload argument, so immutable originals require a random staging key followed by a conditional publish. For staged objects larger than S3's single-copy limit, publish with destination multipart copy and `CompleteMultipartUpload` using `IfNoneMatch="*"`.

**Why:** Sending a managed multipart transfer directly to the final key would reintroduce a check-then-replace race, while a single `CopyObject` cannot publish a source larger than 5 GiB. Failed destination multipart publishes also need an abort permission on the final object prefix.

**How to apply:** Keep the complete checksum/HMAC bundle computed before transfer, expire completed staging objects with a lifecycle rule, make cleanup failures observable, and grant multipart abort permissions for both staging and final prefixes.