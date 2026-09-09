# Current implementation architecture

This document describes the current technical direction, not build chronology.

## System shape

Lina is a modular monolith. Next.js provides the Student/Parent surfaces; FastAPI owns APIs and application services; PostgreSQL/pgvector stores durable state; a worker handles background work; object storage preserves originals; the Model Gateway owns provider access, usage, latency, cost, and fallback lineage.

## Domain boundaries

- **Identity and platform:** Clerk identity is resolved to local Student/Parent ownership. Migrations evolve durable schema; browser IDs never authorize access.
- **Tutor:** one primary streaming Tutor call on normal turns. Context is bounded and question-led; safety and Parent policy are enforced around the result.
- **Content:** original sources are preserved; Docling creates structural representations; semantic extraction is optional enrichment; retrieval is structural/hybrid and question-driven.
- **Student sources:** voice transcription and owned image/PDF/DOCX assets are transiently prepared for the same Tutor path after safety.
- **Intelligence:** completed Segments receive semantic review, then session finalization creates source-linked Event/Evidence; deterministic services maintain state, patterns, card, and decision views.
- **Personal Facts:** a bounded, reconcilable personal-memory subsystem distinct from Learning Intelligence.
- **Studio:** durable Runtime/Scene/Event/Snapshot state and bounded Canvas Specialist composition; Studio events retain provenance and rejoin the same Tutor.

## Technical rules

Application services request AI only through the Model Gateway. AI handles semantic interpretation; deterministic code owns allowed-value checks, policy, lifecycle, counts, recency, persistence, and rebuildability. No normal-turn extra classifier call is authorized for Tutor mode/strategy/method decisions.

Use migrations for schema changes. Preserve raw inputs and provenance. Artifact failure must not block Tutor. Custom generated HTML/SVG is fallback-only and sandboxed. Reprocessing must start from original sources and version derived outputs.

## Verification

Use focused unit/contract/PostgreSQL/browser checks for the changed boundary; broaden only for cross-cutting or release-risk work. Verify logs/output where applicable, run `git diff --check`, and distinguish deterministic proof, authenticated browser proof, real-provider proof, and real-use/learning-benefit evidence.

## Deferred by evidence and approval

Trusted-reference expansion, broader visual coverage, Parent/Admin expansion, Grade transition, and any new infrastructure remain usage- and approval-driven. Implemented Voice, current Vision, and Canvas foundation are not deferred architecture.
