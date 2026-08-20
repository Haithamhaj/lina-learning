# Phase 0 Reuse Decisions

## shadcn/ui — ADOPT BASELINE

The web shell uses the shadcn/ui configuration shape and locally owned
component primitives (`Button` and `Card`). This keeps the functional layer
modifiable and avoids locking the product to a full visual template.

## Clerk — ADOPT for MVP authentication

Clerk provides managed authentication, reducing unnecessary custom
identity/security code. Lina's backend remains the authority for application
roles and authorization semantics, and Clerk-specific behavior is contained in
the auth adapter/boundary.

## Deferred candidates

`assistant-ui`, OpenMAIC packages, and LlamaIndex were not evaluated for
adoption in TASK-001 because this task intentionally does not build chat,
learning artifacts, or retrieval infrastructure. Their required fit checks
belong to the tasks that introduce those subsystems.

## Phase 1–2 fixture vertical-slice decisions

### Docling — ADOPT

Docling is adopted as the structural document-understanding adapter for the
fixture vertical slice. Its `DocumentConverter` supports the required document
formats while the Lina Content domain owns normalized persistence, educational
semantics, source provenance, and reprocessing. It therefore reduces parsing
work without becoming the curriculum model.

### LlamaIndex + Docling — REJECT for MVP retrieval

Docling's official LlamaIndex extension provides a reader and node parser, but
it adds a second indexing abstraction between the project and PostgreSQL.
Native Docling-derived blocks plus project-owned lexical/pgvector retrieval
keep Grade/subject/focus filters, provenance, context budgeting, golden tests,
and rebuild policy explicit with less coupling for this small vertical slice.

### assistant-ui — REJECT for the MVP custom shell

assistant-ui can connect to a custom backend through local and external-store
runtimes, but its client runtime would not remove the project-owned session,
thread persistence, safety decision, SSE contract, or Candidate Event metadata
needed here. The first Student shell stays intentionally small and uses a local
React component over the project API. Re-evaluate if later chat interaction
complexity makes its adapters materially reduce code.
