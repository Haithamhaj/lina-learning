# Lina Personal Learning System — Project Reference

## Status

Approved living product reference.

## Product identity and intended learners

Lina is an AI-native personal learning system that began with Lina and Grade 5 as the first real-world proving ground. It is intended to grow across school-age learners from primary through secondary education without becoming a generic LMS or homework-answer bot.

The product objective is **learning and understanding**. Answers, visualizations, exercises, tools, and models are means to that end.

The durable asset is the evolving, evidence-grounded understanding of the learner together with preserved raw learning history and provenance.

## Core product principles

- Learning before answers.
- Teach the learner without labeling the learner.
- Current demonstrated behavior outranks stale historical assumptions.
- Personalize teaching and representation, not only content.
- Parents receive meaningful insight, not surveillance.
- Books and sources ground what is being learned; they do not dictate one teaching method.
- Raw interactions and originals remain authoritative and rebuildable.
- Child safety and ownership/privacy are explicit protected boundaries.
- The Student experience remains simple even when internals are sophisticated.

## Learner-context authorities

Do not collapse these into one profile:

- **Student Core Profile:** age, Grade, identity/context controlled by Parent/System.
- **Personal Facts:** explicit, safe, reconcilable learner context.
- **Current Conversation Context:** what matters now.
- **Learning Intelligence:** evidence-grounded conclusions over time.

The system must not infer personality, psychology, intelligence, talent, attention, or permanent learning-style labels.

## Tutor authority

The Primary Tutor is the sole teaching and student-facing reasoning authority.

It owns:

- the educational objective;
- facts and source grounding;
- teaching strategy;
- explanation;
- interpretation of meaningful learner actions;
- continuation after Canvas interaction.

Normal Tutor availability is independent of curriculum availability.

## Canvas product direction

Canvas is not a finite diagram renderer catalogue.

The approved architecture is a **Full-Power Hybrid Canvas**:

```text
Primary Tutor
    ↓
CanvasBrief
+ server-filtered Visual Learner Context
    ↓
Full-Power Canvas Agent
    ↓
REUSE / ADAPT / CREATE
    ↓
Visual runtime
    ↓
Safe validation / sandbox when generated code is used
    ↓
Browser render + bounded preview/refinement
    ↓
Semantic Manifest + Studio state/events
    ↓
Same Primary Tutor
```

### Governing Canvas principles

- Typed renderers are a fast path, not a capability ceiling.
- The Canvas Agent receives maximum useful **visual authority** while retaining minimum **system authority**.
- Reuse is preferred only when it preserves learning quality.
- The Agent may adapt or create a new visual when that better serves understanding.
- Custom generated visual code is a first-class approved capability only inside a strict isolated sandbox.
- The Agent may use approved React/SVG/Motion, JSXGraph, Konva, MathLive, chart/simulation capabilities, project-owned generated images, and future approved visual capabilities according to representational need.
- No subject-to-library hardcoding is required.
- Exact mathematical/scientific truth must be supplied by typed inputs or deterministic tools; rendering must not invent missing values.
- Student-specific private context must not become reusable artifact content.

## Reusable Visual Registry

Successful generalized visual artifacts can be stored as immutable/versioned reusable definitions.

The system should distinguish:

```text
Reusable artifact definition
≠
student-specific Canvas instance
```

A reusable artifact may be:

- reused with new parameter values;
- adapted to new presentation requirements;
- forked/versioned when structural change is useful.

Every generation may remain in build history for provenance, but only safe, parameterizable, validated, reusable, sufficiently high-quality artifacts should be promoted into the reusable registry.

This is intended to improve future latency, cost, consistency, and quality without converting one learner's private information into templates.

## Tutor understanding boundary

Every finalized Canvas, regardless of implementation technology, must expose a validated **Semantic Manifest** with stable semantic IDs.

The Manifest should describe educationally meaningful:

- objective;
- entities;
- facts;
- quantities;
- relations;
- presentation/progression;
- current visual state;
- meaningful interactions;
- calculated results;
- active focus;
- provenance.

The Tutor should not need to read generated React/SVG code to understand the Canvas.

Meaningful Canvas actions flow through Studio and return to the same Primary Tutor. Raw clickstream does not automatically become Evidence.

## Student sources and privacy

Student work may include text, voice, images, PDFs/DOCX, handwriting, drawings, homework, and textbook pages.

Raw student sources remain protected originals. The normal safe path is:

```text
Student source
→ safety / authorized processing
→ Primary Tutor understanding
→ distilled educational semantics
→ Canvas composition
```

Do not casually forward raw source bytes, OCR dumps, private storage IDs, Personal Memory, or Learning Intelligence into custom visual code.

## Learning Intelligence

Learning Intelligence remains evidence-first, rebuildable, and separate from Personal Facts.

```text
Raw interaction
→ completed learning segment
→ semantic review
→ validated learning event
→ Evidence
→ Current State / Patterns
→ compact learner intelligence
→ relevant later personalization
```

A selected teaching method or visual representation is not Evidence of effectiveness by itself. Observable learner outcomes are required.

## Parent / Admin

Parent/Admin may control books, Grade context, safe learning boundaries, model routes, processing/reprocessing, and inspect meaningful learner evidence/changes.

Parent disagreement can trigger review/revalidation but does not directly overwrite evidence-grounded learner conclusions.

## Architecture boundaries

- Lina remains a modular monolith.
- Model/provider routing remains observable and replaceable.
- Studio owns durable Runtime/Scene/Event/Snapshot and semantic interaction state.
- Generated assets become project-owned before durable student-facing use.
- Canvas failure must never block Tutor chat.
- Existing Scene/history compatibility is preserved where required.
- New infrastructure is added only when the approved capability demonstrates need.

## Current implementation baseline

The migration baseline for FULL-POWER-CANVAS-01 is the completed Agentic Canvas / Visual Intelligence branch at:

`62df59bcc8c43074c223d79b73bcf97a0905ed4c`

That baseline already includes:

- Tutor-authored `CanvasBriefV1`;
- bounded server-resolved visual learner context;
- one Canvas Agent via OpenAI Agents SDK;
- typed Studio Scene persistence/replay;
- deterministic and hosted tools;
- generated-asset ownership;
- same-Tutor Canvas continuity;
- semantic Canvas interactions;
- visual plan persistence;
- production renderer/browser harness.

FULL-POWER-CANVAS-01 extends that baseline. It does not authorize rebuilding those foundations.

## Governing Full-Power reference

The detailed approved architecture and acceptance definition lives in:

`docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md`
