# Lina

Lina is an AI-native personal learning system for school-age learners. It began with one real learner, Lina, and Grade 5 as its proving ground, but the product is designed to grow across school years without becoming a generic LMS, homework-answer bot, or one-child prototype.

The core idea is simple:

> **Learning is the goal. The answer is only a tool.**

Lina is built to understand what is happening in the learning process, adapt how it teaches, use the right representation when useful, and preserve enough evidence over time to make future support more relevant without turning the learner into a label.

## Why Lina exists

Students already have access to answers from AI, teachers, videos, books, and the web. The harder questions are:

- Did the learner actually understand?
- What foundation is missing?
- Was the learner independent or heavily supported?
- Did one explanation fail while another representation helped?
- Can the learner apply the idea again later?
- What should the Tutor do differently next time?

Lina is designed around those questions.

## Product spirit

Lina should feel like one thoughtful learning companion, not a collection of internal systems.

Behind the simple Student experience, Lina keeps responsibilities separate:

- the **Primary Tutor** teaches and holds the conversation;
- **Canvas / Studio** provides interactive visual representation when it helps;
- **Student Core Profile** gives authoritative age, Grade, and identity context;
- **Personal Facts / Personal Memory** preserve explicit safe learner context for continuity and natural examples;
- **Learning Intelligence** derives revisable conclusions only from meaningful learning evidence;
- **JEV** supports a small set of bounded decisions such as visual-personalization selection, exact Canvas reuse selection, and rubric comparison;
- deterministic application logic retains authority for safety, ownership, persistence, lineage, executable validation, and final admission.

The system can be sophisticated internally without making the learner experience complicated.

## What Lina is not

Lina is not:

- a generic ChatGPT wrapper;
- a book chatbot;
- an LMS;
- a test-prep-only product;
- a system that forces hints before teaching;
- a psychological profiling system;
- a permanent learning-style classifier;
- a surveillance product for parents;
- a Canvas-first product where every answer must become a visual.

## The learner-context model

Lina intentionally keeps four sources of learner context separate.

| Context | What it is | What it must not become |
| --- | --- | --- |
| **Current conversation** | What the Student is showing and asking now | Be overridden by old assumptions |
| **Student Core Profile** | Parent/System-authoritative identity, age and Grade context | Mastery, ability or personality |
| **Personal Facts / Memory** | Explicit safe learner-provided context such as interests, preferences and personal references | Learning Evidence or a fixed learning style |
| **Learning Intelligence** | Evidence-grounded conclusions from meaningful learning behavior over time | Permanent labels or unsupported inference |

Current demonstrated behavior has priority over stale historical personalization.

## How personalization works

Personalization in Lina is not simply inserting a favorite color or hobby into every answer.

    Current Student need
    + Core Profile
    + relevant Personal Facts
    + relevant Learning Intelligence
    + current subject/source/Canvas state
            ↓
    Primary Tutor teaching decision
            ↓
    explanation / question / example / visual / practice / support
            ↓
    observable learner outcome

Personal Facts may make an example or visual feel natural. Learning Intelligence may provide a narrow evidence-backed prior. Neither is allowed to force a teaching method when the current Student behavior says otherwise.

A teaching method is not considered effective merely because it was used. Lina requires observable learner behavior before treating a strategy outcome as evidence.

## Primary Tutor

There is one student-facing Tutor identity.

The Primary Tutor owns:

- the educational objective;
- explanation and reasoning;
- teaching mode, strategy and method;
- source grounding;
- interpretation of learner responses;
- deciding when a visual representation would materially help;
- continuation after meaningful Canvas interaction.

The Tutor can answer directly, explain, ask, guide, challenge, model, or stop. Lina does not impose one fixed teaching flow.

## Canvas / Studio

Canvas is a teaching surface, not a second Tutor.

The current Full-Power Hybrid Canvas supports:

- typed educational visual capabilities;
- interactive scenes and semantic learner actions;
- reusable visual artifacts;
- exact reuse when a validated prior visual fits;
- parameterized reuse;
- structural ADAPT and versioning;
- new CREATE paths when existing capabilities are insufficient;
- custom visual packages in an isolated sandbox;
- browser rendering with durable Scene, Event, and Snapshot state;
- semantic state returned to the same Primary Tutor.

A learner action must be truthful. Lina must not fabricate a selection, hide an admitted Chat turn, reveal an answer before the learner acts, or claim a visual is visible merely because the server finished composing it.

## JEV bounded decisions

Lina uses OpenRouter Decisions / **JEV** for narrow decision tasks where the answer space is intentionally bounded.

Current uses include:

1. selecting relevant Personal Facts for visual personalization from an already filtered catalogue;
2. choosing among already authorized executable exact-reuse Canvas actions or NO_MATCH;
3. comparing Learning Intelligence rubric classifications against the governed review output.

JEV does not become the Primary Tutor, Canvas generator, safety authority, evidence authority, database authority, or free-form orchestration layer. The application still validates allowed actions, provenance, ownership, thresholds, persistence, and fallbacks.

## Learning Intelligence

Learning Intelligence is evidence-first and rebuildable.

    Raw interaction
    → completed learning Segment
    → semantic Segment Review
    → staged findings
    → Session finalization
    → validated learning events
    → Evidence
    → Current State / Patterns
    → Learner Intelligence Card
    → relevant later personalization

It tracks learning meaning, not personality.

Examples of useful evidence include independent reasoning, meaningful hint dependency, self-correction, misconception supported by reasoning, transfer, retention, and observable strategy outcomes.

Raw clicks, greetings, one wrong answer, or Tutor assumptions do not automatically become Evidence.

## Personal Facts / Memory

Personal Facts are separate from Learning Intelligence.

They capture explicit learner context such as interests, hobbies, family references, activities, or preferences when safe and useful for conversational continuity.

They can help Lina use a familiar object in an example. They cannot prove ability, personality, motivation, mastery, or a preferred learning method.

## Student sources and multimodal learning

The Student can learn through text, voice, images, PDFs, DOCX files, textbook pages, homework, handwriting, drawings, and Canvas interaction.

Original Student sources remain protected source authority. Extraction, OCR or normalization, retrieval, and visual representation are processing layers, not replacements for the original.

## Parents

The governing principle is:

> **Parents get insight, not surveillance.**

Parent/System authority includes Core Profile and configurable learning boundaries. Evidence-grounded learner conclusions cannot simply be overwritten because an adult disagrees; disagreement can trigger review or revalidation.

A future Parent experience should expose meaningful evidence and useful explanations rather than default full-transcript monitoring.

## Safety

Child safety is enforced as a system boundary, not as a polite Tutor suggestion.

Lina separates:

- a non-overridable child-safety baseline; and
- configurable Parent Learning Boundaries.

Canvas, JEV, Student sources, generated code, retrieval, and Tutor behavior must remain inside those boundaries.

## Current implementation

The current repository and live pilot include:

- Next.js Student and Parent surfaces;
- Daily Student learning experience;
- Clerk-backed identity and ownership;
- FastAPI application services;
- Primary Tutor runtime;
- child safety and Parent Boundaries;
- Student Core Profile;
- Personal Facts / Personal Memory;
- Learning Intelligence pipeline and reprocessing;
- optional content ingestion and RAG grounding;
- voice and speech-to-text;
- image, PDF, and DOCX Student sources;
- durable Studio Runtime, Scene, Event, Snapshot, and Interaction;
- Full-Power Hybrid Canvas with REUSE, ADAPT, and CREATE;
- isolated custom visual runtime;
- reusable visual registry and immutable build provenance;
- OpenAI Model Gateway routes;
- JEV bounded-decision routes through OpenRouter;
- PostgreSQL and pgvector;
- object storage;
- separate background Worker;
- GCP live pilot deployment.

Current structured Studio subject support includes MATH, SCIENCE, ENGLISH, and ARABIC. General Tutor conversation is not limited to those subjects.

## Current phase

The system is in controlled real-use validation.

Local engineering acceptance exists for the core Tutor, Canvas, Learning Intelligence, and learner-context boundaries. Real use is now used to discover what only natural interaction can reveal: teaching-flow quality, latency, recovery behavior, personalization relevance, Canvas usefulness, and longitudinal learning value.

Implementation evidence is not the same thing as learning-effectiveness evidence.

## Architecture

    Student / Parent Web
            ↓
    FastAPI application
            ↓
    Tutor ─ Studio/Canvas ─ Student Sources ─ Content/RAG
      │          │
      ├─ Personal Facts / Core Profile
      ├─ Learning Intelligence
      └─ bounded JEV decisions
            ↓
    PostgreSQL + pgvector / Object Storage / Worker
            ↓
    Model Gateway → OpenAI / OpenRouter Decisions

## Read the project

Start here:

1. README.md — product orientation.
2. docs/PROJECT_REFERENCE.md — durable product truth and boundaries.
3. docs/IMPLEMENTATION_PLAN.md — current architecture and runtime flows.
4. project-state/PROJECT_STATE.md — short current operational state.
5. TASKS.md — active execution queue.
6. docs/README.md — documentation map.

Historical closure, reviews, research, and acceptance evidence remain useful records, but they do not override the current canonical references.

## Common questions

### Is Lina mainly a chatbot?
No. Chat is the primary interaction surface, but Lina also has durable learner context, evidence processing, multimodal Student sources, and an interactive Canvas/Studio runtime.

### Does Lina decide a child has one learning style?
No. Lina may observe that a particular method helped in a specific context, but it does not create a permanent visual, auditory, or similar learner label.

### Does Personal Memory affect mastery?
No. Personal Facts help with continuity and natural examples. Learning Intelligence is the evidence-grounded learning layer.

### Does Canvas teach independently?
No. Canvas represents and captures meaningful learner interaction. The same Primary Tutor remains the teaching authority.

### What is JEV used for?
Small bounded decisions with finite allowed answers, not open-ended teaching or generation.

### Can Lina change its mind about the learner?
Yes. Learning Intelligence is revisable, evidence-linked, and designed to be rebuilt from source history.

## Local commands

    npm install
    npm run dev
    npm run dev:api
    alembic upgrade head
    npm run typecheck
    npm run test:python
