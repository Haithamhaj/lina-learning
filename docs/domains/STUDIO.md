# Studio and Canvas

## Purpose

Studio is Lina's durable visual and interactive learning workspace.

It is not an autonomous Tutor. The Primary Tutor retains teaching, language, reasoning, and interpretation authority.

## Durable state

Studio persists:

- Runtime;
- Scene;
- Event;
- Snapshot;
- Student interaction;
- Tutor observation.

The browser renders and sends bounded actions. It does not own durable semantic state.

## Full-Power Canvas

The current system supports:

- typed educational renderers;
- diagrams and processes;
- number lines and plots;
- text grouping and classification;
- reusable visual artifacts;
- exact REUSE;
- parameterized reuse;
- structural ADAPT;
- new CREATE;
- custom visual packages inside the approved sandbox.

Typed renderers are a fast path, not a capability ceiling.

## Authority flow

    Primary Tutor
    → educational objective and Canvas brief
    → Canvas composition
    → validated Scene
    → browser
    → meaningful Student action
    → Studio state
    → same Primary Tutor

Canvas-originated actions do not automatically become Learning Evidence.

## Truthful interaction

Studio must not:

- fabricate a Student target;
- expose a hidden answer as learner state;
- silently erase an admitted Chat turn;
- create uncontrolled parallel Tutor interactions;
- claim a visual is visible only because server work completed.

## Recovery

Canvas lifecycle truth distinguishes pending, running, failed, ready, and current Scene state.

Depending on the actual condition, the product may wait, reload the existing Scene, retry failed work, or replace a semantically insufficient Scene.

Canvas failure must never make normal Tutor chat unavailable.

## Reuse

The system may use JEV to choose among already authorized exact-reuse actions or NO_MATCH.

Candidate loading, ownership, executable validation, artifact/version/build lineage, parameters, storage access, and final reuse admission remain deterministic application responsibilities.

## Current subject support

Structured Studio support currently includes MATH, SCIENCE, ENGLISH, and ARABIC.

General Tutor conversation is broader and does not require a registered Studio subject.

Future Studio capability work is usage-driven rather than catalogue-driven.
