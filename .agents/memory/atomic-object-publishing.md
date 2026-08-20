---
name: Atomic original upload publishing
description: Preserve private originals when concurrent writers target the same object key.
---

Never rely on an existence check followed by replacement for original uploads.
Reserve the key exclusively, build bytes and metadata in a transaction directory,
and atomically publish the completed container so readers see a complete object
or no object.

**Why:** Concurrent uploads can both pass a check-then-replace guard, allowing a
later writer to overwrite an original or mix bytes and metadata. A reviewer
rejected that pattern as unsafe for source preservation.

**How to apply:** Keep collision handling at the storage-provider boundary and
test two concurrent writers for one key, asserting exactly one succeeds and the
stored checksum, bytes, and metadata belong to the same winner.