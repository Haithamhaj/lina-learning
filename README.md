# Lina Personal Learning System

Lina is a private, child-appropriate personal learning system. It keeps a natural Tutor conversation available for the question in front of Lina, then adds what ordinary chat cannot reliably provide over time: safe, traceable, evidence-grounded support for how she is learning.

Lina is not an LMS, a book chatbot, or a curriculum gate. Books, captured pages, and trusted references can ground an answer; they never become permission to help.

## Current capability

The accepted repository baseline includes:

- a Daily Student experience, FastAPI API, PostgreSQL/pgvector, and a worker;
- Clerk-based Student/Parent ownership boundaries;
- one primary streaming Tutor call via the Model Gateway, with explicit child safety and Parent Learning Boundary enforcement;
- session-local conversation segments, evidence/intelligence foundations, Personal Facts/Core Profile, and bounded later personalization;
- optional source-preserving content processing and hybrid retrieval;
- voice transcription and Student-owned image, PDF, and DOCX sources with multimodal safety;
- durable Studio runtime/state, Canvas Specialist composition, and continuity between Chat, Canvas, and the same Tutor;
- Studio support for MATH, SCIENCE, ENGLISH, and ARABIC, including the current Math Cartesian plane from `-10` to `10` on both axes.

General conversation remains available outside those four Studio subjects. Implemented does not mean fully validated in recurring real use: authenticated Daily end-to-end acceptance and real Lina calibration remain next gates.

## How the learning loop works

```text
Question or Student source → safety and ownership → optional grounding
→ one primary Tutor turn → completed segment review → session-authorized
evidence → current state/patterns → relevant later personalization
```

Candidate metadata is provisional. Raw interaction and original Student work remain the rebuildable authority.

## Read in this order

1. `README.md` for orientation.
2. `AGENTS.md` for operating rules.
3. `docs/PROJECT_REFERENCE.md` for product truth.
4. `project-state/PROJECT_STATE.md` for current operational reality.

Then use [docs/README.md](docs/README.md) to find the needed contract or domain detail. Do not infer current truth from `docs/history/`, `docs/reviews/`, or `research/`.

## Local commands

```bash
npm install
npm run dev
npm run dev:api
alembic upgrade head
npm run test
```

Use the task-specific verification described in `TASKS.md`; do not run a full suite solely because documentation moved.
