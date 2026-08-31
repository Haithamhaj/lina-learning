# Lina Personal Learning System

Lina Personal Learning System is a personal AI learning system designed first around Lina's real learning experience. It aims to keep the natural flexibility of a capable general AI tutor while adding the part a normal chat does not provide reliably over time: **evidence-grounded learning intelligence that improves how the system teaches the individual learner.**

The project is not a book chatbot, a conventional LMS, or a digital copy of school. Lina's current question drives the interaction. Books, school material, captured pages, and trusted references are optional grounding sources that can improve alignment and context; the Tutor remains usable with zero uploaded curriculum.

## Why this project exists

A Custom GPT, Gem, or general AI chat can already answer questions, read a PDF, understand an image, and explain a topic. Lina Learning exists to add a durable learning loop around that capability:

```text
Natural learning interaction
        ↓
Raw, source-linked learning history
        ↓
Completed Segment semantic review
        ↓
Session-authorized Evidence
        ↓
Current State / Patterns
        ↓
Learner Intelligence Card
        ↓
Relevant later personalization
        ↓
Better future teaching
```

The durable product asset is therefore not one model, prompt, book, or provider. It is the traceable, revisable understanding of how Lina is learning and the ability to use that understanding without letting history override what she demonstrates now.

## Current implemented core

The repository currently contains substantially more than its original Phase 0 foundation. The accepted core includes:

- a Next.js Student experience and FastAPI backend,
- Clerk-based Student/Parent role boundaries,
- PostgreSQL + pgvector persistence,
- DB-backed jobs and a separate worker entrypoint,
- a provider-neutral Model Gateway and AI execution ledger,
- a Math-first Student Tutor with SSE streaming,
- Arabic/English conversational continuity,
- child-safety and Parent Learning Boundary enforcement,
- zero-book Tutor availability,
- optional structural/hybrid curriculum grounding,
- session-local Segments / Learning Threads,
- Segment-scoped semantic Learning Review,
- deterministic Session-scoped Intelligence Finalization,
- source-linked Event/Evidence materialization,
- Current Learning State and Learner Patterns,
- an on-demand Learner Intelligence Card,
- relevant later Tutor personalization,
- versioned reprocessing and authority replacement.

The accepted Learning Intelligence architecture is:

> **Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority**

One primary Tutor model call remains the normal Student-turn boundary. Candidate metadata from that call is provisional only; it is not Evidence.

## Product direction versus current implementation

The intended Lina product is not text-only. The following are approved product directions but remain sequenced/gated rather than automatically executable:

| Capability | Current product status |
|---|---|
| Text Tutor / Math proving ground | Implemented |
| Math + Science initial subject family | Approved core direction; Science production deferred |
| Voice → speech-to-text input | Approved core direction; deferred by sequencing |
| Image / photographed homework input | Approved core direction; deferred by sequencing |
| Handwriting / drawing interpretation and evidence | Approved core direction; deferred by sequencing |
| Visual / interactive learning representations | Approved core direction; deferred by sequencing |
| Learning Canvas / broader Artifact Engine | Approved direction; gated |
| Parent Evidence / Intelligence visibility | Approved first-product-loop capability; broader UI deferred |
| Grade progression | Approved direction; production deferred |

A deferred capability is not rejected and should not be silently removed from the product roadmap. Its promotion order should be informed by real Lina usage and explicit Product Owner decisions.

## Curriculum and grounding

The current question is authoritative. Curriculum is optional grounding, not permission to learn.

```text
Student question
   ↓
Safety
   ↓
optional retrieval + relevant learner intelligence
   ↓
ONE primary Tutor call
```

When content exists, the project preserves the original source, builds structural retrieval-ready representations, and may add educational semantic enrichment. Semantic curriculum extraction is optional enrichment rather than a prerequisite for Tutor availability, basic retrieval, or Learning Intelligence.

## Real-use status

**Limited real Lina use has occurred.** Lina herself participated in part of a real Tutor interaction, and that persisted interaction was subsequently continued and used as part of system testing and Tutor calibration.

This does **not** establish stable daily Lina use, a complete recurring Lina `Session → Review → Evidence → Card → later Tutor` loop, or longitudinal real-use personalization across multiple natural Lina sessions. Those remain separate verification horizons.

## Model and deployment stance

Application domains request AI by task through the Model Gateway. The currently implemented real provider route is OpenAI, but provider/model choice is not intended to become permanent product architecture.

Likewise, repository support for a particular development or deployment environment does not define the product architecture. The system remains a modular monolith with Web, API, PostgreSQL, object storage where needed, and a background worker process.

## Document authority

Do not infer current execution state from historical phase text. Use the governing documents according to their roles:

- `AGENTS.md` — rules for Codex/AI agents and protected areas.
- `docs/PROJECT_REFERENCE.md` — stable approved product truth and durable product/architecture decisions.
- `docs/LEARNING_INTELLIGENCE_SPEC.md` — canonical Learning Intelligence semantics and contracts.
- `docs/LEARNING_PRODUCT_ROADMAP.md` — approved capability evolution and sequencing; roadmap presence alone does not authorize implementation.
- `docs/IMPLEMENTATION_PLAN.md` — implementation direction and technical boundaries.
- `project-state/PROJECT_STATE.md` — current operational snapshot and current next action.
- `TASKS.md` — executable task state and durable task history.
- `project-state/SYSTEM_MAP.html` — visual architecture plus current readiness overlay.

When historical records conflict with newer governing truth, preserve them as history but do not resurrect superseded architecture.

## Local commands

### Web

```bash
npm install
npm run dev
```

### API

```bash
python -m pip install -r apps/api/requirements.txt -r apps/api/requirements-dev.txt
npm run dev:api
```

### Database migrations

```bash
alembic upgrade head
```

### Verification

```bash
npm run test:db:up
npm run test:python
npm run test:db:down
```

`npm run test` adds the web typecheck before the Python path. Read `AGENTS.md` and the current task/state documents before making implementation changes.
