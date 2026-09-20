# Lina Personal Learning System — Project Reference

## Status

**Canonical living product reference.**

Updated to reflect the current implemented and deployed system. Historical plans, implementation records, reviews, and closure documents are supporting evidence and do not override this file.

## 1. Product identity

Lina is an AI-native personal learning system for school-age learners.

It began with Lina and Grade 5 as the first real proving ground. The product is intended to grow across school years and subjects, but that future breadth must not turn the current system into an abstract platform before real learner value is proven.

The central product objective is:

> **Help the learner understand deeply, build foundations, apply knowledge, retain it, and become appropriately more independent over time.**

Answers, models, visuals, exercises, retrieval, memory, and analytics are means to that objective.

## 2. Product spirit

The learner should experience **one coherent learning companion**.

Internally Lina may use multiple models, background jobs, deterministic validators, memory layers, Studio state, retrieval, and decision services. Those internals must not fragment the learner experience.

The system should be sophisticated where sophistication creates real value and simple where complexity would only make the product harder to use or maintain.

## 3. Core principles

1. Learning before answers.
2. Teach the learner without labeling the learner.
3. Current demonstrated behavior outranks stale historical assumptions.
4. Personalize teaching and representation, not just content.
5. One Primary Tutor owns the learner-facing teaching relationship.
6. Canvas is a representation and interaction surface, not a second Tutor.
7. Personal Facts and Learning Intelligence are different authorities.
8. Raw learner and source history remains authoritative and rebuildable.
9. Parents receive insight, not surveillance.
10. Safety, ownership, provenance, and persistence are application authorities, not model discretion.
11. Use models for semantic judgment; use code for hard boundaries.
12. Do not force reuse, personalization, visuals, quizzes, or questions merely because the system can produce them.

## 4. What Lina is not

Lina is not:

- a generic AI chat wrapper;
- a homework-answer generator;
- a curriculum viewer with chat added;
- a fixed tutoring script;
- a psychological profiler;
- a permanent learning-style classifier;
- a grade-only analytics system;
- an LMS;
- a Parent surveillance product;
- a multi-agent UI where the Student chooses among internal agents.

## 5. Learner-context authorities

These must remain distinct.

### 5.1 Current conversation

The strongest signal for what support is needed now.

The current Student turn can override stale historical expectations immediately.

### 5.2 Student Core Profile

Parent/System-authoritative context such as identity, date of birth or derived age, active Grade, and other explicitly governed profile context.

Core Profile calibrates age-appropriateness, language, abstraction, information amount, and interaction complexity.

It is not mastery, ability, personality, or Evidence.

### 5.3 Personal Facts / Personal Memory

Explicit, safe learner context preserved for continuity.

Examples include interests, hobbies, favorite activities, family or pet references, and ordinary preferences explicitly stated by the Student.

Personal Facts may make examples, analogies, conversation, or visuals feel natural.

They must not become Evidence, ability claims, personality inference, motivation diagnosis, learning-style labels, or automatic teaching-method selection.

### 5.4 Learning Intelligence

Evidence-grounded, revisable interpretation of meaningful learning behavior over time.

It can represent current learning state, scoped patterns, support dependence, reasoning evidence, misconception evidence, transfer, retention, self-correction, strategy outcomes, and evidence confidence.

It is not a permanent description of the learner.

## 6. Primary Tutor

There is one student-facing Tutor identity.

The Primary Tutor owns the educational objective, explanation, reasoning, source grounding, teaching mode, teaching strategy, teaching method, pacing, amount of support, meaningful application or checks when useful, interpretation of Student responses, whether a representation surface would materially help, and continuation after meaningful Canvas interaction.

The Tutor does not have to follow a fixed explanation, question, quiz, reward sequence.

A direct answer, concise explanation, worked example, guided attempt, visual, challenge, clarification, or stopping point may each be correct depending on the current need.

### 6.1 Teaching concepts

Keep these distinct:

- **Teaching Mode** — broad interaction posture.
- **Teaching Strategy** — how the current learning move is organized.
- **Teaching Method** — concrete instructional method or representation approach.
- **Surface** — Chat, Canvas, source, voice, and related interaction surfaces.

A selected strategy or method is not Evidence that it worked.

## 7. Personalization

Personalization should be felt, not announced.

Canonical decision inputs:

    Current Student behavior
    + Core Profile
    + relevant conversation history
    + relevant Personal Facts
    + relevant Learning Intelligence
    + current subject/concept/source
    + current Canvas/Studio state
            ↓
    Primary Tutor decision

Rules:

- current behavior wins over history;
- Personal Facts can personalize context but not ability;
- Learning Intelligence is a scoped prior, not a command;
- no method is forced from one old success;
- no visual is forced because the Student likes drawing;
- no repeated personalization phrase should be inserted merely because a fact is available;
- the system should prefer relevance over demonstrating that it remembers.

## 8. JEV bounded decision layer

Lina uses OpenRouter Decisions / **JEV** for selected bounded decision tasks.

### 8.1 Visual personalization selection

Given an already filtered safe Personal Fact catalogue and an admitted Canvas brief, JEV can judge which facts, if any, naturally improve the visual presentation.

The answer space is bounded to the supplied candidate facts. It cannot invent Personal Facts.

### 8.2 Exact Canvas reuse selection

Given only already authorized, executable, same-learner reusable visual actions, JEV can select one exact replay or NO_MATCH.

It cannot alter frozen parameters, invent a new visual, bypass artifact and build validation, override ownership, or turn an inexact match into reuse.

Application code revalidates executability and provenance.

### 8.3 Segment rubric comparison

JEV can classify already validated Segment findings against finite rubric options so the system can compare bounded rubric judgments.

Learning Intelligence authority remains governed by the approved review, finalization, and Evidence pipeline.

### 8.4 Governing JEV principle

JEV is a bounded decision component, not a general Lina agent.

It does not own teaching, Canvas generation, Safety, learner identity, persistence, Evidence lifecycle, free-form orchestration, or database mutation authority.

## 9. Canvas / Studio

Canvas exists because some ideas are easier to understand by seeing, manipulating, comparing, grouping, sequencing, plotting, or interacting.

### 9.1 Authority split

    Primary Tutor
      → educational meaning and Canvas brief

    Canvas system
      → visual composition

    Deterministic tools and code
      → exact values, validation, executable boundaries

    Studio
      → durable Runtime, Scene, Event, Snapshot, Interaction state

    Same Primary Tutor
      → understands the semantic state and continues teaching

### 9.2 Full-Power Hybrid Canvas

The implemented architecture supports typed visual renderers, diagrams and processes, math surfaces, interactive text and grouping activities, reusable visual artifacts, exact REUSE, parameterized reuse, structural ADAPT and versioning, CREATE when needed, custom React/SVG/Motion and approved visual capabilities, JSXGraph, Konva, MathLive, project-owned generated assets, and isolated custom visual packages.

Typed renderers are a fast path, not a capability ceiling.

### 9.3 Reuse rules

    REUSE
      when the existing validated capability fits the educational need exactly

    ADAPT
      when generalized capability or structure should change

    CREATE
      when reuse or adaptation would compromise the educational representation

Reuse must never be forced simply to reduce cost.

### 9.4 Truthful interaction

A Student action must represent what the Student actually did.

The system must not select a hidden element on the learner's behalf, reveal the solution before the Student acts, lose an admitted Chat turn because a Canvas event arrived, create uncontrolled Tutor-interaction storms, or say a visual is visible merely because server composition succeeded.

### 9.5 Failure behavior

Canvas failure must not break Tutor availability.

The system distinguishes pending, running, failed, ready, and learner-reported display failure. Recovery may include waiting, reload, retry, or replacement according to the actual server state and educational need.

## 10. Student sources and grounding

Student learning input may include text, voice or STT, images, PDFs, DOCX, homework, handwriting, drawings, and textbook pages.

The preserved original is source authority.

Safe processing may derive normalized text, extracted structure, retrieval context, educational semantics, and Canvas briefs.

Derived processing must never silently replace the original as truth.

## 11. Content and RAG

Curriculum and content retrieval is optional grounding.

Tutor availability never depends on curriculum availability.

Content helps determine what source material says, which concept or reference is relevant, and what terminology or facts should ground an explanation.

It does not dictate one tutoring style.

## 12. Learning Intelligence

Canonical path:

    Raw Interaction
    → Completed Learning Segment
    → Segment Learning Review
    → Staged Findings
    → Session Intelligence Finalization
    → Validated Learning Event
    → Evidence
    → Current Learning State / Learner Patterns
    → Learner Intelligence Card
    → relevant future personalization

### 12.1 Candidate hints

Turn-level Candidate Events may help later review, but they are optional hints.

They are not Evidence and cannot directly update stable learner intelligence.

### 12.2 Evidence principles

Evidence should represent meaningful observable learning behavior.

Usually meaningful:

- independent reasoning;
- substantial support need;
- self-correction;
- misconception supported by reasoning;
- meaningful transfer;
- retention after elapsed time;
- strategy outcome;
- resolving a learning loop.

Not meaningful by itself:

- greeting;
- clicking;
- viewing;
- one wrong answer;
- Tutor choosing a method;
- vague impressions.

### 12.3 Current State vs Patterns

Current Learning State describes relevant current conditions.

Learner Patterns require repeated, evidence-supported observations across time or context.

One ordinary interaction must not become a stable pattern.

## 13. Parents

Parents are meaningful partners, not default observers of every message.

Parent/System authority includes Core Profile, learning boundaries, and relevant account or ownership controls.

Future Parent insight should expose evidence summaries and useful examples, not default transcript surveillance.

A Parent disagreement can request review or revalidation; it does not manually rewrite Evidence-derived conclusions.

## 14. Safety and boundaries

Lina separates:

1. non-overridable child-safety rules;
2. Parent-configurable learning boundaries;
3. age-appropriate Tutor behavior.

Safety is enforced by the application boundary. Models cannot weaken it.

## 15. Architecture

Lina remains a modular monolith.

    Next.js Student / Parent
            ↓
    FastAPI
            ↓
    Tutor Runtime
    Studio / Canvas
    Student Sources
    Content / Retrieval
    Personal Facts / Core Profile
    Learning Intelligence
    JEV bounded decisions
            ↓
    PostgreSQL + pgvector
    Object Storage
    Background Worker
            ↓
    Model Gateway
    OpenAI / OpenRouter Decisions

This is intentionally not a microservice architecture.

## 16. Current implementation and deployment

Implemented today:

- Daily Student surface;
- Parent surface and ownership;
- Primary Tutor;
- bilingual Arabic and English behavior;
- Core Profile;
- Personal Facts and Personal Memory;
- Learning Intelligence;
- Student source upload and safety paths;
- voice and STT;
- Content and RAG;
- Studio durable state;
- Full-Power Canvas;
- reusable visual registry;
- custom visual sandbox;
- background Worker;
- Model Gateway;
- JEV bounded decisions;
- GCP live pilot.

Current structured Studio product subjects include MATH, SCIENCE, ENGLISH, and ARABIC. General Tutor conversation is broader.

## 17. Current product phase

The system is in **controlled real-use validation**.

Engineering acceptance establishes that architecture and contracts work under tested conditions. It does not yet prove long-term learning benefit, broad unrestricted CREATE reliability, optimal teaching flow, optimal personalization frequency, acceptable latency in every real case, or longitudinal accuracy of Learning Intelligence.

Those require real use.

## 18. Current priorities

1. Natural live-use observation and defect discovery.
2. Teaching-flow integrity:
   - unfinished guided learning should leave a useful next affordance;
   - declared strategy should match visible behavior;
   - a failed method should cause a substantive adaptation.
3. Performance and buffering investigation.
4. Personalization relevance calibration.
5. JEV decision-quality evaluation against existing decisions.
6. Generated educational images V2 after remaining design and acceptance questions are resolved.

## 19. Protected areas

Changes require explicit Product Owner approval when they materially alter child safety, Parent Boundaries, ownership and privacy, Learning Intelligence or Evidence semantics, Core Profile authority, Personal Facts authority, Primary Tutor authority, production model/provider policy, production data migration, or irreversible deployment and data operations.

## 20. Product FAQ

### Does Lina remember everything?
Raw history is retained according to system rules, but runtime context is selective. Personal Memory is not the same as transcript replay, and Learning Intelligence is not a transcript summary.

### Can Lina conclude a learner is visual?
No. It may learn that a visual method helped in a particular evidenced context, but not create a permanent learning-style label.

### Can Canvas create Evidence?
Not directly. Canvas actions become durable Studio events. Learning meaning still passes through the governed intelligence path.

### Can JEV change learner truth?
Not by itself. It provides bounded decisions inside allowed contracts; deterministic code and governed subsystem authority remain final.

### Can the Parent change Learning Intelligence manually?
No. The Parent may trigger review or revalidation, but Evidence authority remains source-linked.

### Is Grade 5 the product limit?
No. It is the current proving ground.

## 21. Canonical references

- README.md — orientation.
- docs/PROJECT_REFERENCE.md — this product reference.
- docs/IMPLEMENTATION_PLAN.md — technical architecture.
- docs/LEARNING_INTELLIGENCE_SPEC.md — Learning Intelligence authority.
- docs/CHILD_SAFETY_POLICY.md — safety and Parent Boundaries.
- docs/LEARNING_PRODUCT_ROADMAP.md — capability direction.
- project-state/PROJECT_STATE.md — current operational snapshot.
- TASKS.md — active execution queue.
- docs/TUTOR_PEDAGOGY_REFERENCE.md — pedagogy reference.
- docs/TUTOR_CANVAS_REPAIR_TRACKER.md — repair and acceptance evidence register.
