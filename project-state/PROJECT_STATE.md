# Lina Personal Learning System — Project State

## Current goal

Roadmap Track A architecture simplification is COMPLETE / ACCEPTED. REC-35.1 —
Tutor Child Interaction Calibration Pass — is complete following Product Owner
browser acceptance. REC-35.2 / LR-D04A — Adaptive Teaching Method Foundation —
is in REVIEW with a Product Owner-approved semantic-authority correction pending
before browser validation. LR-D04B remains future, evidence-dependent work.
REC-25 has not started and remains blocked.

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
- Product Owner review found that the current Teaching Method Foundation uses
  deterministic keyword routing as semantic authority. The approved correction
  keeps one Tutor call but moves joint Mode + Strategy + Method +
  prior-method-relation meaning to Luna; runtime remains the deterministic
  validator/persistence/lineage authority. Browser review waits for that code
  correction.
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
- Relevant personalization advises Luna but does not control it; current Lina
  behavior outranks history. Turn decisions are not learner memory, and
  historical method ranking remains unimplemented and unauthorized before
  sufficient Evidence.

## Protected areas

Evidence → State/Pattern → Learner Intelligence Card; current behavior
outranking history; raw source and student-original preservation; explicit
child-safety and Parent Learning Boundaries; one primary Tutor call; derived
mastery/confidence; Model Gateway routing; provenance/rebuildability; modular
monolith; and frozen Vision, Voice, Science, Learning Canvas, Artifact Engine,
and Parent Dashboard expansion.

## Active risks

- REC-35.2 needs the approved semantic-authority code correction before Product
  Owner browser validation. REC-25 remains blocked; LR-D04B, Track B, and other
  future capability work remain frozen.
- PostgreSQL/pgvector and real AWS/S3 staging verification remain separate
  operational concerns; this governance correction does not change them.

## Next recommended action

Implement only the approved REC-35.2 semantic-authority correction next; do not
begin LR-D04B or resume REC-25, and do not unfreeze Vision, Voice, Science,
Learning Canvas, Interactive Artifacts, or Parent Dashboard expansion.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
