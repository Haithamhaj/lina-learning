---
name: Workspace dependency isolation
description: Prevent duplicate framework runtimes when installing dependencies in a workspace monorepo.
---

Keep the root workspace manifest focused on scripts and workspace membership.
Install and lock web dependencies through the actual web workspace, then
validate the dependency tree before building.

**Why:** A root-level installer retry can leave a second Next/React runtime
behind, causing server-rendering hook failures even when TypeScript passes.

**How to apply:** If the tree shows multiple framework/runtime versions,
remove generated dependency state, regenerate the workspace lockfile, prune,
and confirm one compatible React/Next tree before accepting build results. With
Clerk's Next peer in this npm workspace, pin the root peer-resolution versions
to the web app's versions as needed; otherwise npm can auto-install an
incompatible newer Next at root even when the web package declares Next 14.