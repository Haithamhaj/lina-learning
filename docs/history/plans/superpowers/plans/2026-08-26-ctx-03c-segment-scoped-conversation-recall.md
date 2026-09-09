# CTX-03C Segment-Scoped Conversation Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the one primary Tutor call exact current-segment complete-exchange continuity, with shared, bounded pgvector recall of older exchanges.

**Architecture:** Raw `LearningMessage` rows remain authoritative. A temporary, session-owned `LearningExchangeEmbedding` index holds only completed Student→Tutor exchange vectors; `TutorContextBuilder` selects disjoint immediate, recent, and older semantic-exchange groups and hands the one ephemeral query vector to curriculum retrieval.

**Tech Stack:** Python, SQLAlchemy, Alembic, PostgreSQL/pgvector, existing Model Gateway, pytest.

**Spec:** `/Users/haitham/.codex/attachments/bf0089d4-ecfb-4d17-a134-4d9c76b419e6/pasted-text.txt`

## Global Constraints

- One primary Tutor call per Student turn; no classifier, summarizer, agent chain, archive/session-crossing recall, or external vector dependency.
- Reuse `ModelTask.EMBEDDING`, `text-embedding-3-small`, 1536 dimensions, the existing execution ledger, and one batch containing the current question plus missing eligible exchange vectors.
- Current Turn is unassigned before Luna decides its Segment relation; old Segment State may not reopen context.
- Raw context groups are complete Exchanges, never sliced messages, and have no duplicate message IDs.
- CTX-03D/E and STATE-01 changes are out of scope. Migration creates empty infrastructure only.

---

### Task 1: Temporary exchange-vector persistence

**Files:**
- Modify: `services/platform/db/models.py`
- Create: `migrations/versions/<revision>_add_learning_exchange_embeddings.py`
- Test: `tests/test_ctx03c_exchange_embeddings_postgres.py`

**Interfaces:**
- Produces `LearningExchangeEmbedding(session_id, segment_id, student_message_id, tutor_message_id, embedding, embedding_model, dimensions, ai_execution_id)` with model-identity uniqueness.

- [ ] **Step 1: Write failing database-contract tests** for migration upgrade/downgrade, no backfill, duplicate prevention, cross-session/cross-segment rejection, roles, and no recall HNSW index.
- [ ] **Step 2: Run the focused tests** and confirm they fail because the table/model do not exist.
- [ ] **Step 3: Add the minimal model, migration, and persistence validation** with foreign keys and ordinary filter indexes only.
- [ ] **Step 4: Run the focused tests** and confirm they pass.

### Task 2: Exchange selection and shared embedding seam

**Files:**
- Modify: `services/tutor/context.py`, `services/retrieval/service.py`
- Test: `tests/test_ctx03c_exchange_embeddings_postgres.py`, `tests/test_tutor_context_postgres.py`, `tests/test_retrieval_postgres.py`

**Interfaces:**
- Produces `ConversationExchangeContext` and a typed precomputed-query state accepted by `RetrievalService.retrieve` / `retrieve_with_debug`.

- [ ] **Step 1: Write failing behavior tests** for explicit completed pairing, failed-turn isolation, current-segment scope, disjoint complete groups, zero recall, state pins, ranking, shared batch/order, malformed output, and lexical-only degradation.
- [ ] **Step 2: Run the focused tests** and confirm they fail against the message-window implementation.
- [ ] **Step 3: Implement minimal complete-exchange selection, lazy batch indexing, conservative recall calibration, and supplied-query retrieval behavior.**
- [ ] **Step 4: Run the focused tests** and confirm they pass.

### Task 3: Tutor payload, lifecycle cleanup, and status

**Files:**
- Modify: `services/tutor/runtime.py`, `services/tutor/session_lifecycle.py`, `services/intelligence/core.py`, `TASKS.md`, `project-state/PROJECT_STATE.md`
- Test: `tests/test_tutor_context_postgres.py`, `tests/test_tutor_segment_runtime_postgres.py`, lifecycle coverage

**Interfaces:**
- Consumes the three explicit exchange groups and persists their debug IDs.
- Produces hidden `Recent raw complete Exchanges` and `Relevant older complete Exchanges from current Segment` sections; session closure removes only temporary exchange vectors.

- [ ] **Step 1: Write failing payload and lifecycle tests** for exact raw input, no old label/window, unassigned current Turn, no duplicate IDs, and vector cleanup without source deletion.
- [ ] **Step 2: Run the focused tests** and confirm they fail.
- [ ] **Step 3: Implement the minimal payload/lifecycle integration and status-only documentation update.**
- [ ] **Step 4: Run focused, protected, and full verification; inspect migration upgrade/downgrade and `git diff --check`.**

## Self-Review

The plan covers temporary persistence, explicit lineage-safe complete-exchange selection, shared embeddings and lexical degradation, semantic/state ranking, model-facing separation, close cleanup, and status/verification. It deliberately excludes all CTX-03D/E capacity, observability, and real-Luna replay work.
