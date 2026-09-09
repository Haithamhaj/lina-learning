# Fixture-Based Phase 0–3 Learning Loop Design

## Decision and scope

The Product Owner authorized autonomous implementation through TASK-026 and
the Phase 3 Exit Gate. The requested path must remain a modular monolith and
must not add Redis, Celery, a dedicated vector database, an agent framework,
or future Phase 4 product work.

The requested fixture rule permits a small, clearly labelled learning document
and deterministic local model adapter for implementation verification. It does
not claim that a fixture is Lina's real Grade 5 book, nor that a synthetic
session is an Early Lina Calibration Checkpoint. Those real-use validations
remain recorded as deferred, non-blocking validation work under this explicit
execution authorization.

## Architecture

The FastAPI application remains the single API boundary. Domain services own
the following responsibilities:

```text
platform/model_gateway  -> task-routed model calls and AI execution ledger
platform/safety         -> non-overridable baseline + parent topic policy
content                 -> originals, processing, curriculum, blocks
retrieval               -> project-owned metadata + lexical/vector ranking
tutor                   -> sessions, threads, context, SSE, candidates
intelligence            -> evidence, states, patterns, card, decision views
workers                 -> durable document/consolidation/rebuild jobs
```

PostgreSQL is authoritative for operational and derived state. Original files
remain in the existing storage abstraction. All model/provider behavior stays
behind the Model Gateway. A deterministic local provider makes the fixture demo
and tests reproducible; it is not a production provider commitment.

## Data flow

```text
Parent fixture document upload
  -> immutable storage original + content document/version
  -> Docling structural adapter + educational semantic extraction
  -> source-linked content blocks + lexical/pgvector retrieval
  -> student session/message + SafetyDecision + compact tutor context
  -> one Tutor Gateway execution + streamed response + Candidate Events
  -> inactivity close + idempotent consolidation job
  -> validated learning events/evidence
  -> current state + deterministic patterns + compact card + decision views
  -> relevant slice for a later Tutor turn
  -> versioned reprocessing can rebuild derived outputs
```

## Reuse decisions

1. **Docling — ADOPT.** It is the approved structural document baseline. The
   adapter owns normalized persistence and makes Docling replaceable.
2. **LlamaIndex — REJECT for MVP retrieval.** A focused dependency review will
   record that the native Docling + project-owned PostgreSQL path preserves
   provenance, metadata filtering, deterministic rankings, and rebuildability
   with less framework coupling for this small slice.
3. **assistant-ui — REJECT for the MVP shell.** Its custom runtime would add a
   client adapter without reducing the small project-owned SSE/session contract.
   The local React shell remains intentionally small and is not a general chat
   framework.
4. **shadcn/ui — retain ADOPT BASELINE.** Existing local primitives remain the
   functional layer; no unrelated design library is added.

## Safety and intelligence invariants

- The SafetyDecision is evaluated before the Tutor and is stored with an audit
  record; a Tutor prompt cannot override it.
- Candidate Events are raw, hidden metadata and are never evidence by
  themselves.
- Consolidation is session-level, bounded to relevant excerpts, and lineage is
  versioned.
- Current Learning State, Patterns, the Intelligence Card, and derived decision
  views are separate layers.
- Deterministic code owns counts, recency, weights, scope/lifecycle transitions,
  and card selection. Model output may only classify/describe event semantics.
- Pattern scope begins at a concept; `strategy_effectiveness` requires an
  observable learner outcome and never the strategy selection alone.
- Raw interactions and original files are preserved. Reprocessing creates a new
  processing version and does not rewrite the older derived history.

## Practical demo

The API ships a fixture seed and a documented sequence that uploads a small
equivalent-fractions document, sends a meaningful Math attempt, closes the
session, runs the consolidation worker once, and opens a later turn whose debug
trace contains only the relevant Intelligence Card slice. This is a practical
local demonstration, not a real-book or real-Lina acceptance claim.
