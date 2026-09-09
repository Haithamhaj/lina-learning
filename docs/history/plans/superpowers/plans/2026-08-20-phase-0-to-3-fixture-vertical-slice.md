# Phase 0–3 Fixture Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete TASK-007 through TASK-026 and demonstrate the evidence-grounded learning loop with a fixture document, without claiming real-book or real-Lina validation.

**Architecture:** PostgreSQL remains the durable source of originals, interactions, and derived intelligence. FastAPI routes delegate to modular content, retrieval, Tutor, safety, Model Gateway, and intelligence services. The existing worker executes idempotent document, consolidation, and rebuild jobs.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy/Alembic, PostgreSQL/pgvector, Docling, Next.js/TypeScript, pytest.

**Spec:** `docs/superpowers/specs/2026-08-20-phase-0-to-3-fixture-vertical-slice-design.md`

## Global Constraints

- Execute only TASK-007 through TASK-026; do not implement Phase 4 routes or dashboards.
- Use real PostgreSQL semantics for migrations, queue behavior, and pgvector paths.
- Preserve original files and raw interactions; all intelligence remains derived and versioned.
- Use one primary Tutor gateway call per turn and no model SDK calls outside the gateway.
- Treat fixture validation as fixture validation, never as a real-book or real-Lina claim.
- Record Docling, LlamaIndex, and assistant-ui decisions before equivalent custom work is complete.

---

### Task 1: TASK-007 and TASK-008 platform boundaries

**Files:** model gateway, safety service, migration, platform tests, API routes.

- [ ] Write failing tests for task-routed execution logging, protected safety,
  parent boundary updates, and policy auditing.
- [ ] Implement a deterministic local Model Gateway provider and durable AI
  execution ledger; use it for future Tutor/semantic/consolidation calls.
- [ ] Implement the versioned SafetyDecision service and parent policy storage.
- [ ] Run focused tests, migration upgrade/check, update TASKS/project state.

### Task 2: TASK-009 through TASK-015 content and retrieval

**Files:** content models/repositories/routes, Docling adapter, semantics,
retrieval service, worker handlers, fixture tests, reuse decisions.

- [ ] Write failing PostgreSQL tests for immutable original/content lineage,
  fixture upload, normalized parsing, semantic source references, retrieval, and
  reprocessing.
- [ ] Add content schema and upload/service route using the existing storage
  contract; accept a labelled text/Markdown fixture and PDF when Docling can
  parse it.
- [ ] Add a Docling adapter, deterministic semantic extractor through the Model
  Gateway, source-linked structural blocks, and native PostgreSQL lexical/vector
  retrieval.
- [ ] Register document processing/reprocessing handlers, record native
  retrieval/Docling and LlamaIndex decisions, and add the minimal parent content
  status/reprocess route/UI.
- [ ] Run focused PostgreSQL/golden retrieval tests, full suite/build, update
  TASKS/project state. Record real-book validation as deferred.

### Task 3: TASK-016 through TASK-019 Tutor vertical slice

**Files:** session/thread/message models/services, context selector, Tutor,
safety integration, SSE route, student page, candidate persistence/tests.

- [ ] Write failing tests for session/thread persistence, compact context,
  SafetyDecision enforcement, one Gateway Tutor call, bilingual local response,
  SSE output, ledger entry, and candidate capture.
- [ ] Implement sessions/threads/messages and project-owned Tutor context,
  including retrieval and later-compatible intelligence slots.
- [ ] Implement safety-gated Tutor runtime and SSE route over the Model Gateway.
- [ ] Add candidate-event contract/persistence and a small student shell;
  record the assistant-ui fit decision before the custom shell is marked done.
- [ ] Run API/UI tests and fixture calibration trace. Record it as synthetic,
  not an Early Lina Calibration Checkpoint.

### Task 4: TASK-020 through TASK-026 intelligence lifecycle

**Files:** session-close worker handler, intelligence schema/services,
consolidation, state/pattern/card/decision/reprocess services, integration tests,
demo script/docs.

- [ ] Write failing PostgreSQL tests for idempotent close/consolidation,
  rubric-safe Evidence, current-state expiry, deterministic lifecycle/scope,
  card selection, policy-recomputable views, and versioned rebuilds.
- [ ] Implement session close and bounded consolidation with source lineage.
- [ ] Implement deterministic state/pattern engines, compact card selector, and
  decision views without writing source evidence.
- [ ] Implement reprocessing through the worker, retaining prior versions.
- [ ] Add a practical fixture demo command and an end-to-end test proving that
  a later Tutor context consumes a relevant card slice without full history.
- [ ] Run all migrations, PostgreSQL tests, full Python suite, TypeScript check,
  production build, task/state updates, and Phase 3 exit checklist.
