# Lina Personal Learning System — Implementation Plan

## Status

Approved execution architecture for the next implementation slice: `FULL-POWER-CANVAS-01`.

## Current baseline

Implement from the completed Canvas baseline:

`62df59bcc8c43074c223d79b73bcf97a0905ed4c`

Do not silently start from an older `main` if it lacks the required Canvas baseline. Use an isolated short-lived branch/worktree and preserve unrelated work.

## System shape

Lina remains a modular monolith:

```text
Next.js Student / Parent surfaces
          ↓
FastAPI application services
          ↓
Tutor / Studio / Content / Intelligence / Model Gateway
          ↓
PostgreSQL + pgvector / Object Storage / Worker
```

FULL-POWER-CANVAS-01 adds bounded capabilities inside the existing architecture; it is not a microservice conversion.

## Target Canvas architecture

```text
Student
  ↓
Primary Tutor
  ├─ teaching / reasoning / facts / grounding
  └─ CanvasBrief + bounded visual learner context
        ↓
Full-Power Canvas Agent
        ↓
Capability + Reusable Visual Registry search
        ↓
REUSE / ADAPT / CREATE
        ↓
┌─────────────────────────────────────────────────────┐
│ Fast paths                                           │
│ typed Agentic Canvas / visual-toolbelt / JSXGraph / │
│ Konva / MathLive / approved visual capabilities     │
└─────────────────────────────────────────────────────┘
        or
┌─────────────────────────────────────────────────────┐
│ CREATE path                                          │
│ generated package → validate → compile → sandbox    │
│ → browser preview → bounded review/refinement       │
└─────────────────────────────────────────────────────┘
        ↓
Semantic Manifest + stable semantic IDs
        ↓
Studio Runtime / Scene / Event / Snapshot / Interaction
        ↓
same Primary Tutor observation
```

## Implementation principles

### 1. Preserve working foundations

Do not rebuild:

- Primary Tutor runtime;
- safety/Parent Boundaries;
- filtered learner-context logic;
- CanvasBrief admission;
- Studio ownership/persistence/replay;
- stale-result fencing;
- ObjectStorage/generated-asset adoption;
- Model Gateway;
- browser-independent production renderer harness.

### 2. Expand capability, not authority

The Canvas Agent may choose how to represent the Tutor's approved educational semantics. It must not gain:

- teaching authority;
- learner-state authority;
- safety authority;
- direct database or Studio-write authority;
- unrestricted private context;
- unrestricted network/filesystem/application access.

### 3. Reuse / Adapt / Create

Routing is quality-first and cost-aware:

```text
REUSE  = existing artifact strongly fits
ADAPT  = existing structure fits; parameter/presentation changes are enough
CREATE = existing artifacts would compromise the learning representation
```

Do not force CREATE when simple reuse is sufficient. Do not force REUSE when the result would be visibly or educationally inferior.

### 4. Reusable Visual Registry

Use existing PostgreSQL/ObjectStorage unless implementation evidence proves a different core dependency is necessary.

Registry responsibilities:

- immutable artifact/version identity;
- capability/semantic tags;
- parameter schema;
- runtime/dependency declaration;
- interaction/Manifest schema;
- lineage/fork information;
- quality/validation lifecycle;
- bounded search/inspect/instantiate.

Keep build history separate from promoted reusable artifacts.

### 5. Custom Visual Runtime

Custom generated visual packages are allowed only inside an isolated visual runtime.

Required controls:

- allowlisted/versioned dependencies;
- static validation where useful;
- bounded compilation;
- opaque/sandboxed browser execution;
- no cookies/secrets;
- no arbitrary network;
- no database/filesystem authority;
- bounded CPU/time/memory;
- strict semantic event bridge;
- failure isolation so Tutor remains available.

Choose the simplest safe implementation. Do not build a giant custom DSL if an isolated generated React/SVG package plus strict contracts is simpler and more expressive.

### 6. Semantic Manifest

Every final Canvas runtime kind must produce a validated implementation-independent Manifest.

The Manifest is the Tutor understanding contract and should cover educationally meaningful entities, facts, quantities, relations, progression, current state, interactions, focus, calculated results, and provenance.

Visible/interactive educational objects use stable semantic IDs.

### 7. Browser preview / bounded refinement

Routine trusted REUSE should not require model visual review.

Custom CREATE should normally use:

```text
generate → render → preview → accept OR one refinement
```

A second correction is justified only by validation/render failure or another concrete acceptance failure. Avoid open-ended self-critique loops.

### 8. Cost and latency

Keep every capability available but route intelligently:

- reuse/parameter binding is cheapest;
- adaptation is preferred when sufficient;
- typed deterministic rendering should handle common cases;
- custom generation is used when it materially improves learning;
- image generation / code interpreter are on demand;
- avoid extra model calls purely for polish when deterministic rendering can deliver the quality.

Record model/tool usage, latency, and cost where existing observability supports it.

## Execution workstreams

These are continuous workstreams, not Product Owner checkpoints.

### A. Governance + protected contracts

Reconcile project rules with the Full-Power direction and introduce/extend versioned contracts for:

- reusable artifact identity/version;
- custom visual package metadata;
- Semantic Manifest;
- semantic bridge events;
- capability/runtime identity.

Use lightweight RED→GREEN tests for protected boundaries.

### B. Registry + REUSE/ADAPT

Implement bounded search/inspect/instantiate/version/fork behavior using existing infrastructure.

Prove one reusable artifact can serve new values without code regeneration and that learner-specific instance data does not leak into reusable definitions.

### C. CREATE + sandbox

Implement the smallest safe custom visual build/execution path.

Prove:

- allowlisted dependency use;
- compile/render;
- arbitrary network blocked;
- application authority unavailable;
- Tutor remains available on failure.

### D. Full-Power Canvas Agent

Extend the existing single Canvas Agent with skills/tools for:

- registry search/inspect/reuse/adapt;
- typed visual capabilities;
- custom creation;
- generated images;
- deterministic truth tools;
- preview/review decision.

Do not create permanent subject-specific agents.

### E. Tutor continuity

Connect finalized Manifest + Studio semantic state/events back to the same Primary Tutor.

The Tutor must be able to explain the visible educational state without reading implementation code.

### F. Integrated acceptance

Run a compact real-provider/real-browser acceptance set covering:

- REUSE;
- ADAPT;
- novel CREATE;
- generated illustration + semantic overlay where useful;
- language/RTL;
- age/grade presentation calibration;
- meaningful Canvas action → same Tutor;
- sandbox negative case.

Use exact Agent-produced artifacts in browser proof; do not substitute hand-authored replicas.

## TDD and verification economy

For meaningful new behavior:

```text
define behavior
→ smallest relevant test
→ RED for intended reason
→ implement
→ GREEN
```

During implementation:

- use focused tests;
- reuse existing coverage;
- do not repeatedly run the full PostgreSQL/browser/live-provider suite;
- do not create duplicate acceptance harnesses.

Near closure:

1. focused new-boundary tests;
2. representative real-provider + real-browser proof;
3. directly affected PostgreSQL lifecycle/security proof;
4. typecheck/build status;
5. `git diff --check`;
6. one broad regression.

Visual quality is an acceptance dimension; "tests passed" alone is insufficient.

## Deferred

Do not bundle unrelated work into this task:

- Parent dashboard redesign;
- broad UI polish unrelated to Canvas;
- multi-family SaaS;
- public artifact marketplace;
- teacher/classroom administration;
- generic website/app builder;
- arbitrary internet-enabled generated applications;
- new learner psychology/personalization systems;
- infrastructure replacement without proof.

## Definition of Done

Use the full Definition of Done in:

`docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md`

At minimum, closure requires working REUSE, ADAPT, CREATE, safe sandboxing, reusable artifact/version behavior, Semantic Manifest/Tutor understanding, meaningful Studio round-trip, exact truth preservation, real-provider output rendered through the production browser path, visible quality at or above the prior accepted floor for comparable cases, and no regression of safety/ownership/Studio/Tutor boundaries.
