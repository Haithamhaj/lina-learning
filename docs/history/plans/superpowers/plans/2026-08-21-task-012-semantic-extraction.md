# TASK-012 Educational Semantic Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a versioned, source-linked Grade 5 Math semantic model derived from the approved TASK-011 structural tree.

**Architecture:** The Content domain sends bounded, normalized structural batches to the existing `CURRICULUM_SEMANTICS` Model Gateway route. A project-owned schema validates model output, deterministic validators enforce source, parent, identity, and coverage rules, and dedicated semantic-run/item/source tables preserve derivation lineage without changing structural artifacts.

**Tech Stack:** Python, SQLAlchemy, Alembic, PostgreSQL, Pydantic, existing Model Gateway, pytest.

**Spec:** `/Users/haitham/.codex/attachments/c97109bc-08e7-4a04-89ab-c71a48f506c3/pasted-text.txt`

## Global Constraints

- Grade 5 Math only; no universal concept graph.
- Do not implement TASK-013 retrieval/indexing or any Tutor, safety, or intelligence changes.
- Route all semantic AI calls through `ModelGateway` using `ModelTask.CURRICULUM_SEMANTICS`.
- Preserve original documents and all approved TASK-011 structural runs.
- Semantic meaning comes from the structured model contract, never document-text keyword rules.
- New semantic identities preserve completed prior semantic derivations; failed runs preserve prior derivations and structural readiness.

---

### Task 1: Define the semantic contract and failing contract tests

**Files:**
- Create: `services/content/semantic_contract.py`
- Create: `tests/test_semantic_contract.py`

**Interfaces:**
- Produces `SemanticExtractionBatch`, `SemanticExtractionItem`, and `SemanticExtractionOutput`.
- Produces `parse_semantic_output(text: str) -> SemanticExtractionOutput`.

- [ ] Write tests for allowed semantic types, duplicate keys, invalid parent/source references, and complete batch accounting.
- [ ] Run the new tests and confirm they fail because the contract is absent.
- [ ] Implement Pydantic schema parsing and deterministic validation helpers.
- [ ] Re-run the contract tests.

### Task 2: Add versioned semantic persistence with source lineage

**Files:**
- Modify: `services/platform/db/models.py`
- Modify: `services/content/repository.py`
- Create: `migrations/versions/<revision>_semantic_processing_runs.py`
- Create: `tests/test_semantic_extraction_postgres.py`
- Modify: PostgreSQL test cleanup fixtures that truncate content tables.

**Interfaces:**
- Produces `ContentSemanticProcessingRun`, `ContentSemanticItem`, and `ContentSemanticItemSource`.
- Produces repository helpers that persist an explicit semantic-run tree and one-or-more structural source links per item.

- [ ] Write PostgreSQL tests for explicit parent/source lineage, same-identity idempotency, changed identity preservation, and failed-new-run preservation.
- [ ] Run focused PostgreSQL tests and confirm they fail because the tables/helpers are absent.
- [ ] Add models, migration, and minimal repository persistence.
- [ ] Upgrade the disposable PostgreSQL test database and re-run persistence tests.

### Task 3: Replace heuristic semantics with bounded gateway extraction

**Files:**
- Replace: `services/content/semantics.py`
- Modify: `services/model_gateway/factory.py`
- Modify: `scripts/setup_eureka_demo.py` only if needed to keep its fixture provider explicit and reproducible.
- Modify: `tests/test_semantic_extraction_postgres.py`

**Interfaces:**
- Produces `extract_educational_semantics(session, document, gateway, structural_run, semantic_identity) -> ContentSemanticProcessingRun`.
- Uses `create_curriculum_semantics_gateway` without a provider SDK in Content.

- [ ] Write tests for the controlled Unit/Lesson/Concept/Objective/Explanation/Example/Exercise/Vocabulary/Figure/Table/Formula fixture and malformed/catastrophic output rejection.
- [ ] Run the focused tests and confirm the old heuristic implementation fails them.
- [ ] Implement deterministic bounded batches, prompt/context construction, gateway routing, global validation, and safe run state recovery.
- [ ] Re-run focused semantic tests.

### Task 4: Add a real-Eureka semantic golden verifier and document batching

**Files:**
- Create: `scripts/verify_eureka_semantic_representation.py`
- Create: `tests/test_eureka_semantic_verifier.py`
- Modify: `docs/DEVELOPMENT_DEMO.md` or an adjacent content-processing document with the bounded-batch strategy, only if that document is the project’s appropriate demo/runbook.

**Interfaces:**
- Verifier accepts an ignored local Eureka PDF and selected normalized structural regions.
- Verifier reports model-backed validation separately from fixture validation.

- [ ] Write a verifier/unit test that rejects absent semantic source/page lineage and checks the small Eureka golden set.
- [ ] Run it and confirm it fails before the verifier exists.
- [ ] Implement the verifier using persisted model output and explicit expected semantic assertions.
- [ ] Run fixture and configured-real-model Eureka validation where the local route is available.

### Task 5: Verify, record review state, and publish

**Files:**
- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`

- [ ] Run semantic contract/focused/PostgreSQL/migration/Eureka/full-Python/diff verification.
- [ ] Set TASK-011 `DONE`, TASK-012 `REVIEW`, and retain TASK-013+ `BLOCKED` only after evidence is recorded.
- [ ] Commit and push the scoped TASK-012 change set.
