# Lina Personal Learning System — Project State

## Current goal

Roadmap Track A architecture simplification is active. LR-A01 governing
decision correction, LR-A02 — Tutor always available, and LR-A03 — decouple
index identity from mandatory semantics — and LR-A04 — structural-first index
builder — and LR-A05 — semantic retrieval behavior advisory — are complete.
LR-A06 — source processing lifecycle — is complete. LR-A07 — Parent content-
status decoupling — is complete. LR-A08 — school-focus authority cleanup — is
complete. LR-A09 — simplification acceptance — is complete. REC-35 — Real Lina
calibration — has begun and produced verified Tutor UX findings. REC-35.1 —
Tutor Child Interaction Calibration Pass — is complete following Product Owner
browser acceptance. REC-35.2 / LR-D04A — Adaptive Teaching Method Foundation —
is the next approved READY task. REC-25 has not started and remains blocked.

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
- A valid Parent upload now queues the existing structural processor; a
  completed structural run queues the structural-first index builder through
  the Model Gateway. The durable path is source → structural → retrieval index,
  with semantic extraction outside the lifecycle.
- Parent content status now reports grounding readiness from the current
  structural run plus a usable completed index. Semantic enrichment remains a
  separate visible stage; its absence or failure cannot make usable grounding
  globally unavailable.
- New Tutor Candidate Events no longer produce school-focus signals; historical
  `current_focus_signal` and `current_school_focus` records remain auditable
  but have no runtime personalization authority. Recent persisted topic
  metadata remains optional context for ambiguous continuation turns.
- Track A acceptance now proves the complete corrected path together: zero-book
  Tutor availability, optional empty retrieval, source → structural → index
  grounding, semantic-failure tolerance, relevance-first intelligence, and no
  school-position authority.
- REC-35 bounded real-Lina/manual Product Owner calibration has begun and
  produced verified Tutor UX findings for the approved REC-35.1 correction.
- REC-35.1 review correction is verified: `tutor_turn_v3` persists typed
  actions, validates clicks against only the latest Tutor message, separates
  navigation from bounded answer-choice Candidate handling, and preserves the
  Student draft. Automated contracts, a fresh PostgreSQL suite, web build, and
  the real-Luna equivalent-fractions diagnostic passed. Product Owner browser
  acceptance completed the review; REC-25 has not resumed.
- TeachingMethod is now an explicit active architectural decision: it is
  distinct from TeachingStrategy, selected from a small project-owned versioned
  registry, and must persist through bounded method → observable-outcome
  lineage before the existing Evidence pipeline can evaluate it. LR-D04B
  historical method learning remains future, evidence-dependent work.
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
- Current School Focus has no product authority or active Current State;
  relevant recent conversational context remains allowed with relevance before
  recency.
- Semantic type is advisory retrieval metadata, not candidate eligibility.
- Structural processing and structural indexing use deterministic, durable job
  identities; a failed replacement index preserves a prior completed index.
- Parent readiness describes grounding usability, not semantic-enrichment
  completion.
- Trusted Educational Reference Pack is approved future Roadmap Track B work,
  not current implementation.
- Teaching Method Foundation is the next approved scope; immediate method
  switching follows current behavior, while historical method ranking is not
  authorized before sufficient Evidence.

## Protected areas

Evidence → State/Pattern → Learner Intelligence Card; current behavior
outranking history; raw source and student-original preservation; explicit
child-safety and Parent Learning Boundaries; one primary Tutor call; derived
mastery/confidence; Model Gateway routing; provenance/rebuildability; modular
monolith; and frozen Vision, Voice, Science, Learning Canvas, Artifact Engine,
and Parent Dashboard expansion.

## Active risks

- REC-35.2 must preserve the one-call Tutor path and source-grounded Evidence
  lineage without introducing a new service, agent, MCP, or infrastructure.
  REC-25 remains blocked; Track B and other future capability work remain
  frozen.
- PostgreSQL/pgvector and real AWS/S3 staging verification remain separate
  operational concerns; this governance correction does not change them.

## Next recommended action

Execute `REC-35.2 — Adaptive Teaching Method Foundation` only. Do not resume
REC-25 or LR-D04B, and do not unfreeze Vision, Voice, Science, Learning Canvas,
Interactive Artifacts, or Parent Dashboard expansion.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
