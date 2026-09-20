# Lina reuse decisions

## Status

Current living summary of how Lina reuses technology and visual capability.

## 1. Governing principle

Reuse is valuable only when it preserves or improves learning quality, correctness, safety, latency, cost, or maintainability.

Do not force reuse merely because an artifact already exists.

## 2. Canvas reuse hierarchy

The current visual system distinguishes:

1. typed existing capability;
2. exact reusable visual instance or version;
3. parameterized reuse;
4. structural ADAPT;
5. new CREATE.

The intended decision is:

    exact fit → REUSE
    same generalized capability but structural change needed → ADAPT
    existing capability would compromise the representation → CREATE

## 3. Exact reuse

Exact reuse is intentionally strict.

Candidate actions must already be:

- owned by the same learner where learner-scoped;
- backed by validated or trusted artifact/version state;
- backed by a validated immutable Build;
- consistent with stored source and manifest digests;
- executable with frozen valid parameters.

JEV may choose among the finite authorized exact-reuse actions or NO_MATCH.

JEV does not create the candidate set and cannot change parameters.

Before execution, Lina revalidates ownership, artifact/version/build identity, manifest digest, parameter equality, storage access, and executable integrity.

## 4. Reusable registry vs build history

Keep these separate.

### Build history

Preserves generation and version provenance.

### Reusable registry

Contains only visuals that are sufficiently safe, generalized, parameterizable, validated, and reusable.

Student-specific private context must not become reusable artifact definition content.

## 5. ADAPT

ADAPT creates explicit parent-child lineage.

Use it when the existing artifact remains conceptually useful but generalized structure or capability must change.

Do not mutate the parent artifact in place.

## 6. CREATE

CREATE is justified when:

- no existing representation fits;
- reuse would distort educational meaning;
- required interaction is unavailable;
- adaptation would be more complex or lower quality than a bounded new build.

CREATE still runs inside approved validation, preview, sandbox, and provenance boundaries.

## 7. External technology reuse

External libraries and packages may be reused when they fit Lina's boundaries without importing unwanted application authority.

Current examples already used in the product include React, Motion, JSXGraph, Konva, MathLive, Playwright, PostgreSQL/pgvector, and provider SDK or API boundaries.

Technology adoption must not grant an external package authority over:

- learner identity;
- Safety;
- Learning Intelligence;
- Personal Facts;
- Studio persistence;
- application ownership;
- unrestricted network or storage access.

## 8. OpenMAIC historical decision

The earlier STUDIO-AGENTIC-01 decision rejected adopting OpenMAIC as a parallel artifact/runtime platform because Lina already had project-owned Runtime, Scene, Event, Snapshot, interaction, ownership, and Tutor-observation boundaries.

That remains a useful principle: reuse a package when it fits a specific capability boundary, but do not import a second application architecture merely to gain one feature.

## 9. Future reuse evaluation

Any new external technology should be judged on:

- exact problem solved;
- overlap with existing capability;
- learner-facing benefit;
- security and privacy boundary;
- source/provenance fit;
- maintenance burden;
- reversibility;
- real latency/cost effect.

Prefer a small high-leverage stack over overlapping frameworks.
