# Lina Personal Learning System — Project State

## Current goal

Roadmap Track A architecture simplification is COMPLETE / ACCEPTED. REC-35.1 —
Tutor Child Interaction Calibration Pass — is complete following Product Owner
browser acceptance. REC-35.2 / LR-D04A remains in REVIEW behind the mandatory
Lina Stabilization Gate: CTX-01 is CLOSED following independent review;
ACT-01 is CLOSED following independent review; OBS-01 is in VERIFICATION
pending independent review. LR-D04B remains future/evidence-dependent and
REC-25 remains BLOCKED.

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
- REC-35.2 correction is implemented: `tutor_turn_v5` has Luna make the joint
  nullable Mode, Strategy, Method, and prior-method-relation decision in the
  one primary Tutor call. Runtime validates canonical values/cross-fields,
  safety, persistence, and server-grounded Candidate lineage; no phrase router
  selects the semantic axes. Focused contracts, a fresh PostgreSQL suite, and
  a five-turn real-Luna diagnostic passed. Product Owner browser testing then
  established the Lina Stabilization Issue Register v1: REC-35.2 cannot become
  DONE until its ordered gate is completed, beginning with CTX-01 recent
  conversation context integrity.
- CTX-01 is CLOSED after independent review of
  `60fa36415a52100cfa4f86489bf763c335182708`: oldest-first budget selection
  retained an older long message and dropped the immediately preceding Tutor
  question. The minimal fix now selects the newest contiguous suffix within
  budget and returns it chronologically. Context and model-input regressions,
  the focused Tutor suite, and the canonical disposable PostgreSQL suite pass.
- ACT-01 is CLOSED following independent review: resolving an
  accepted suggested action now retains its exact server-owned Tutor message
  ID. Runtime verifies that source belongs to the active session and Tutor,
  persists it on the raw Student action payload, and adds a bounded explicit
  source block to the one Tutor call beside ordinary recent context. Candidate,
  Evidence, teaching semantics, public API/SSE, and the browser contract are
  unchanged.
- OBS-01 root cause is verified and its fix is in VERIFICATION: the Student
  browser now records a bounded, sessionStorage-backed local trace for each
  accepted send. It distinguishes submit, fetch, response headers, reader,
  first delta, terminal turn, EOF, ready, and error without storing Student or
  Tutor content, identity, auth, learning, or curriculum data. The terminal
  turn remains separate from the existing later ready transition; UI-01 was
  not changed.
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
- The Stabilization Gate preserves 13 Product Owner-approved issues. CTX-01
  and ACT-01 are closed; OBS-01 awaits independent review before UI-01.
  Browser/SSE,
  Candidate/Evidence,
  personalization, decision calibration, language, and Math-session scope work
  remain ordered behind it.

## Protected areas

Evidence → State/Pattern → Learner Intelligence Card; current behavior
outranking history; raw source and student-original preservation; explicit
child-safety and Parent Learning Boundaries; one primary Tutor call; derived
mastery/confidence; Model Gateway routing; provenance/rebuildability; modular
monolith; and frozen Vision, Voice, Science, Learning Canvas, Artifact Engine,
and Parent Dashboard expansion.

## Active risks

- REC-35.2 stabilization is active: CTX-01 and ACT-01 are closed; OBS-01 has
  an implemented, automated verification pending independent review. UI-01
  remains unstarted.
  UI-01 is high-confidence but requires observability during verification;
  EVID-01 has an unknown HTTPError root cause; PERS-01 is blocked validation.
  REC-25, LR-D04B, Track B, and other future capability work remain frozen.
- PostgreSQL/pgvector and real AWS/S3 staging verification remain separate
  operational concerns; this governance correction does not change them.

## Next recommended action

Obtain independent review of OBS-01 verification only. Do not start UI-01,
ACT-02, LR-D04B, or REC-25, and do not unfreeze Vision, Voice, Science
production, Learning Canvas, Interactive Artifacts, or Parent Dashboard
expansion.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
