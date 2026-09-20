# Daily Student frontend

## Product direction

The current proving ground is Lina, Grade 5, using the Daily Student experience.

Long term, Lina should remain one coherent learning product that can evolve with age and Grade. This does not imply separate applications per age group.

## Experience

The approved direction is:

**Learning Chat + Adaptive Learning Workspace**

The interface should feel warm, intelligent, personal, calm, and visually useful.

It should not feel preschool-cartoonish, corporate, dashboard-heavy, or technically fragmented.

## Core behavior

Chat remains independently usable.

The workspace appears when visual or interactive representation materially improves learning.

The Student should not need to understand internal concepts such as Runtime, Scene, Canvas Agent, evidence pipeline, or model routing.

## Daily surface responsibilities

The current Daily experience includes:

- Tutor conversation;
- text input;
- Arabic, English, and mixed-direction handling;
- voice input and STT;
- image, PDF, and DOCX source attachment;
- source preview/continuity;
- Canvas rendering;
- meaningful Canvas actions;
- session recovery;
- loading, pending, saving, and failure states.

## UX invariants

- Never hide an admitted Student turn.
- Never fabricate a Student action.
- Never expose an answer as if the Student chose it.
- Preserve draft/source state during recoverable session replacement.
- Keep Canvas failure isolated from Chat.
- Preserve accessibility, reduced motion, and narrow layouts.
- Do not make background processing look like learner progress certainty.
- Do not show percentages or ETA without evidence.

## Design system

Tailwind plus current shadcn-style primitives remains the functional baseline.

Deep ink is the reading foundation; lavender can express Student identity, mint or teal can guide with the Tutor, and restrained apricot or gold can mark learning accents.

Visual style is subordinate to comprehension and interaction truthfulness.

## Current phase

Frontend work is driven by controlled real use.

Do not redesign the entire interface merely because one local component needs repair. Prefer focused corrections backed by observed Student experience.
