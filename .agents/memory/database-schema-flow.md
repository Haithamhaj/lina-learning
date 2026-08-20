---
name: Managed PostgreSQL schema flow
description: Replit development and production schema application boundary for this project.
---

Keep the repository migration source of truth for development, but do not run
DDL at application startup or during deployment. Replit's Publish flow applies
the development schema diff to production.

**Why:** Applying schema changes during every process start or deploy can mutate
production unexpectedly and bypass the Publish rename/data-safety review.

**How to apply:** Run and verify migrations against the development database,
document rollback/rebuild SQL, and direct production schema changes through the
Publish flow.