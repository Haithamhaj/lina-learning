# Technology reuse decisions

## STUDIO-AGENTIC-01 — OpenMAIC artifact infrastructure

**Decision: REJECT for this task; preserve a future package-level fit check.**

STUDIO-AGENTIC-01 corrects an already implemented Studio Core. Its bounded
Canvas Agent produces the project-owned `agentic-canvas-scene-v1` contract and
settles it through the existing Runtime, Scene, Event, Snapshot, interaction,
ownership, SSE, and Tutor-observation paths. Adopting OpenMAIC packages now
would add a second artifact/runtime abstraction at the exact boundary this task
must preserve, without removing existing project-owned infrastructure.

This is not a rejection of future package-level reuse. If Lina later starts a
generic Artifact Engine task, that task must re-evaluate the current standalone
OpenMAIC DSL/renderer/importer packages, verify their then-current license and
browser/server fit, and prefer `PARTIAL ADOPT` when a package can consume Lina's
typed artifact contracts without importing multi-agent classroom authority,
storage, safety, learner-state, or application architecture.

The current decision therefore keeps the learner experience and runtime single:
Primary Tutor semantics → bounded Canvas Agent composition → project-owned typed
Scene → existing Studio state. It does not authorize a parallel platform.
