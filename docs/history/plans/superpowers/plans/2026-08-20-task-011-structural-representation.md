# TASK-011 Structural Representation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a versioned, project-owned Docling structural tree that later Content tasks can consume without rereading an original document.

**Architecture:** The Docling adapter converts SDK objects to immutable project-owned normalized items. PostgreSQL stores the tree explicitly in `document_structural_items`, linked to an immutable `content_documents` source and a versioned `content_processing_runs` derivation; `ContentBlock` remains reserved for TASK-013 retrieval units.

**Tech Stack:** Python, Docling, SQLAlchemy, Alembic, PostgreSQL, pytest.

**Spec:** `TASKS.md` TASK-011 and REC-02 prompt.

## Global Constraints

- Preserve original source documents; never overwrite a prior structural run.
- Keep Docling SDK types inside `services/content/docling_adapter.py`.
- Do not implement TASK-012 educational semantics, retrieval, embeddings, Tutor, intelligence, or UI work.
- Use a controlled fixture and the local ignored Eureka PDF for verification; do not commit the PDF.
- Leave TASK-011 in `REVIEW`, and TASK-012 onward `BLOCKED`.

---

### Task 1: Define the project-owned structural contract

**Files:**

- Create: `services/content/structural_contract.py`
- Modify: `services/content/docling_adapter.py`
- Test: `tests/test_docling_adapter.py`

- [x] **Step 1: Write failing adapter tests**

Construct a controlled Docling-shaped fixture with title, section, subsection, paragraph, list, table, picture/caption, and formula. Assert literal stable keys, parent keys, sibling order, reading order, page provenance, heading depth, captions, and item types.

- [x] **Step 2: Run the focused test and observe missing contract failure**

Run: `uv run --with-requirements apps/api/requirements.txt python -m pytest tests/test_docling_adapter.py -q`

- [x] **Step 3: Implement the adapter contract**

Normalize Docling items recursively into project-owned values, retaining explicit hierarchy, ordering, type-specific text/caption data, and layout provenance. Do not return Docling SDK types.

- [x] **Step 4: Re-run the focused adapter test**

Run: `uv run --with-requirements apps/api/requirements.txt python -m pytest tests/test_docling_adapter.py -q`

### Task 2: Persist versioned structural runs and items

**Files:**

- Modify: `services/platform/db/models.py`
- Create: `migrations/versions/1c32f331f02b_document_structural_representation.py`
- Modify: `services/content/repository.py`
- Modify: `services/content/processing.py`
- Test: `tests/test_content_ingestion.py`
- Test: `tests/test_content_models_postgres.py`

- [x] **Step 1: Write failing PostgreSQL behavior tests**

Assert that normalized items preserve parent IDs, sibling/read order, document/run linkage, processor metadata, idempotent same-version behavior, new-version preservation of old items, and failure isolation.

- [x] **Step 2: Run the focused tests and observe the old flattened-block behavior fail**

Run against only a disposable PostgreSQL database: `DATABASE_URL=<disposable url> uv run --with-requirements apps/api/requirements.txt python -m pytest tests/test_content_ingestion.py tests/test_content_models_postgres.py -q`

- [x] **Step 3: Implement the schema and processing path**

Add explicit processing metadata and `document_structural_items`; create one run per document/processor/settings identity; persist each normalized item in two passes so parent IDs resolve. A failed retry clears only that run's incomplete items, never a completed prior run or source.

- [x] **Step 4: Run migration and focused PostgreSQL tests**

Run `alembic upgrade head` and the Task 2 tests against the disposable database.

### Task 3: Validate the actual Docling output

**Files:**

- Create: `scripts/verify_eureka_structural_representation.py`
- Test: `tests/test_docling_adapter.py`

- [x] **Step 1: Write a real-document assertion**

Assert that the adapter output for the local Eureka source includes more than one hierarchy depth, page provenance, stable keys, and representative structural types exposed by the installed Docling version.

- [x] **Step 2: Run it before adding the verifier and observe the missing-verifier failure**

Run: `uv run --with-requirements apps/api/requirements.txt python scripts/verify_eureka_structural_representation.py --help`

- [x] **Step 3: Implement the read-only verifier**

Read the ignored local PDF only, summarize structural types/depth/provenance, and return non-zero if hierarchy is not retained. It must not mutate the sandbox database or storage.

- [x] **Step 4: Run the verifier against `.local/eureka/EM_G5_M1_StudentWorkbook.pdf`**

Record the observed document-specific result without claiming curriculum semantics or retrieval validation.

### Task 4: Record verified recovery state

**Files:**

- Modify: `TASKS.md`
- Modify: `project-state/PROJECT_STATE.md`

- [x] **Step 1: Record only verified facts**

Set TASK-011 to `REVIEW`, retain TASK-012 and later as `BLOCKED`, and state that the Production Engine Acceptance Gate has not passed.

- [x] **Step 2: Run final verification and commit**

Run migration checks, focused tests, the full Python suite with a disposable database where PostgreSQL-marked tests are required, `git diff --check`, and commit only the TASK-011 remediation files.
