# Lina Personal Learning System — Project State

## Current goal

Roadmap Track A architecture simplification is active. LR-A01 governing
decision correction, LR-A02 — Tutor always available, and LR-A03 — decouple
index identity from mandatory semantics — and LR-A04 — structural-first index
builder — and LR-A05 — semantic retrieval behavior advisory — are complete.
LR-A06 — source processing lifecycle — is next.
REC-25 has not started and remains blocked until LR-A09 acceptance.

## Current reality

- Product Owner-approved Option A is recorded in
  `docs/LEARNING_PRODUCT_ROADMAP.md`.
- The Student API/UI now permit an authenticated Student to open/resume Math,
  persist messages, and stream one safe Tutor response with zero content;
  retrieval remains optional and returns empty context when no index exists.
- The existing index builder now builds lexical/pgvector structural retrieval
  blocks from a completed structural run without semantic enrichment, retaining
  exact source lineage and a nullable semantic execution lineage. The semantic-
  backed builder path remains available as optional enrichment.
- Retrieval now keeps structural and semantic blocks eligible from the same
  lexical/vector candidate set. Semantic hints and recent focus only resolve
  equal RRF relevance; null metadata cannot exclude structural grounding.
- Hybrid retrieval remains reusable and protected: Docling structural
  representation, PostgreSQL lexical retrieval, pgvector, deterministic fusion,
  context budgets, and exact source provenance.
- Safety, Model Gateway, Candidate Events, Evidence, Current State, Patterns,
  Learner Intelligence Card, raw-source preservation, and rebuildability remain
  protected/reusable.
- The local uncommitted Prompt-v5/Eureka changes are parked optional
  semantic-enrichment work. They are neither approved nor part of Track A.

## Active decisions

- Tutor is always available; grounding is optional and question-driven.
- Educational semantics are optional rebuildable enrichment, not a Tutor,
  basic-RAG, or interaction-concept prerequisite.
- Concept identity primarily comes from the learning interaction.
- Current School Focus has no product authority; relevant recent conversational
  context remains allowed with relevance before recency.
- Semantic type is advisory retrieval metadata, not candidate eligibility.
- Trusted Educational Reference Pack is approved future Roadmap Track B work,
  not current implementation.

## Protected areas

Evidence → State/Pattern → Learner Intelligence Card; current behavior
outranking history; raw source and student-original preservation; explicit
child-safety and Parent Learning Boundaries; one primary Tutor call; derived
mastery/confidence; Model Gateway routing; provenance/rebuildability; modular
monolith; and frozen Vision, Voice, Science, Learning Canvas, Artifact Engine,
and Parent Dashboard expansion.

## Active risks

- Track A remains incomplete; REC-25 and all future capability work remain
  blocked until LR-A09 acceptance.
- PostgreSQL/pgvector and real AWS/S3 staging verification remain separate
  operational concerns; this governance correction does not change them.

## Next recommended action

Execute `REC-31 — Source Processing Lifecycle` (`Roadmap: LR-A06`) only.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
