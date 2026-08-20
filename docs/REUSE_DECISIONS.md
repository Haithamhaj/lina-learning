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
