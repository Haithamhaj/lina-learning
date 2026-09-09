# Lina

Lina is an AI-native personal learning system for school students. It began with one learner—Lina, the founder's daughter—and Grade 5 as its first real proving ground. The product is designed to grow into age- and grade-aware learning support across primary through secondary education; that broader scope is vision, not a claim of current implementation.

## Why Lina exists

Students can reach answers easily through AI, teachers, videos, books, and online resources. The harder question is what happened after the answer: did the Student understand, build a foundation, apply the idea independently, retain it, or need a different intervention?

Parents often see a grade, completed homework, or a test result—not the learning process behind it. Lina exists to make that process more understandable and to improve teaching over time without turning the learner into a label.

## Vision

Lina is designed to grow with a Student across school years:

```text
Primary school → Middle school → Secondary school
```

The daily user is the Student. The initial go-to-market is B2C, with the Parent as the initial buyer/payer and a meaningful partner in understanding learning. This does not define a future Parent Dashboard or institutional product.

## Mission

Build an AI-native learning environment that helps every Student understand deeply, build strong foundations, and grow in appropriate independence through natural tutoring, multimodal learning, interactive representation, and evidence-grounded personalization over time.

## Learning philosophy

**Learning is the goal. The answer is only a tool.**

Lina helps a Student understand, build strong foundations, apply learning, retain it, and become appropriately more independent over time. It is not a homework-answer generator, generic school chatbot, book chatbot, test-prep-only system, or LMS.

When a learner is stuck, explaining or teaching a solution can be appropriate. The goal is understanding, not artificial struggle or indefinite answer withholding.

## How Lina understands a learner

Lina keeps four authorities separate:

- **Student Core Profile:** Parent/System-authoritative identity and age/Grade context.
- **Personal Facts:** explicit, safe, durable context stated by the Student, such as interests or hobbies.
- **Current Conversation Context:** what matters in the interaction now.
- **Learning Intelligence:** what actual learning Evidence suggests over time.

This is how Lina can know the learner without labeling the learner. It does not create psychological profiles, intelligence labels, attention labels, permanent learning styles, or inferred talent labels.

## How personalization works

Lina personalizes how the Student is taught, not merely what content is shown.

```text
Student interaction → meaningful Evidence → relevant learner context
→ teaching decision → adapted teaching → observable new outcome
```

Teaching Mode, Teaching Strategy, Teaching Method, and representation/surface are distinct. Historical intelligence is guidance, not a command; current Student behavior outranks stale assumptions. A method being used is not proof it worked—an observable Student outcome is required before it contributes to teaching-effectiveness intelligence.

## Parents

**Parents get insight, not surveillance.** Important learner conclusions should be explainable through an Evidence summary and, when appropriate, specific relevant learning examples—not default full-transcript monitoring. Parent disagreement can trigger review but cannot manually rewrite Learning Intelligence; Evidence remains authoritative. Safe ordinary Personal Facts may inform Parent understanding where appropriate, without making the Parent their source.

## Current proving ground

Lina and Grade 5 are the current real-world proving ground. That focus keeps evaluation concrete; it does not make Lina permanently a one-child or Grade-5-only product.

## Current implemented capability

The accepted repository baseline includes:

- Student/Parent ownership and authentication;
- a primary Tutor with child safety and Parent Learning Boundaries;
- Learning Intelligence foundations, Personal Facts, and Core Profile;
- optional source-preserving content/RAG grounding;
- Voice/STT and Student-owned image, PDF, and DOCX sources;
- durable Studio/Canvas runtime with Chat–Canvas–Tutor continuity;
- current MATH, SCIENCE, ENGLISH, and ARABIC Studio support; and
- the Daily Student surface.

MATH, SCIENCE, ENGLISH, and ARABIC are the current structured Studio product subjects. Tutor and general conversation are not restricted to those four subjects; broader structured Studio support is not implied.

Implementation is distinct from proof of long-term value. Authenticated Daily end-to-end acceptance, recurring real Lina use, and longitudinal personalization calibration remain separate gates.

## Architecture and reading order

Lina is a modular monolith: web client, FastAPI API, PostgreSQL/pgvector, worker, object storage where needed, and Model Gateway. Read `AGENTS.md`, `docs/PROJECT_REFERENCE.md`, and `project-state/PROJECT_STATE.md` first; [docs/README.md](docs/README.md) routes to detailed current contracts. History, reviews, and research are non-authoritative.

## Local commands

```bash
npm install
npm run dev
npm run dev:api
alembic upgrade head
npm run test
```
