---
name: GitHub repository bootstrap
description: Constraint of GitHub REST Git Database operations when starting from a completely empty repository.
---

When creating a new GitHub repository through the connected API, an entirely
empty repository cannot accept a Git tree/ref operation. Seed it with a
temporary Contents API commit first, then create the intended tree and commit
and move `main` to that commit; keep the seed file out of the real baseline
tree.

**Why:** GitHub does not initialize the repository's Git database until the
first content commit exists.

**How to apply:** Verify the final repository, `main` ref, and baseline commit
after the seed replacement. Treat the temporary seed commit as bootstrap
plumbing, not as the project baseline.