# Lina Personal Learning System — Project State

## Current goal

Independently review TASK-018 production Tutor runtime evidence. Do not start
TASK-019, real-Lina calibration, or product expansion.

## Current reality

- An independent implementation audit found that the existing development
  sandbox proves useful plumbing, but does **not** prove the Production Learning
  Engine or Phase 3 complete. The affected TASK-011 through TASK-026 work has
  been reopened in `TASKS.md`.
- Verified foundation infrastructure remains usable: typed configuration,
  PostgreSQL/Alembic/pgvector foundation, Clerk role boundaries, private object
  storage, PostgreSQL jobs/worker foundation, Model Gateway/AI ledger,
  SafetyDecision persistence, source-document provenance, and Parent/Admin
  source upload.
- The local Eureka Grade 5 PDF and Sandbox/Test Learner remain development/test
  fixtures only. Existing structural, retrieval, Tutor, Candidate Event, and
  derived-intelligence code remains available as a remediation baseline, not as
  a production-complete engine claim.
- TASK-011 is independently accepted and has a versioned, project-owned Docling structural artifact:
  explicit parent/child and sibling/read order, hierarchy depth, stable item
  identity within a run, page/layout provenance, captions, and distinct
  text/table/picture/formula item types. It was verified with a controlled
  fixture and the ignored local Eureka PDF on a disposable PostgreSQL database.
  It is `DONE`; this verifies the structural layer only.
- TASK-012 is independently accepted and has a separate, versioned Grade 5 Math semantic derivation with
  schema/prompt/model-route/settings/source-structural-run identity, explicit
  semantic parent/child relationships, and per-source structural/page/source
  links. Its bounded Model-Gateway extraction and PostgreSQL fixture/versioning
  tests passed; its local Eureka pages 1–2 semantic golden passed through the
  configured OpenAI Luna route. It is `DONE`; this verifies the semantic layer only.
- TASK-013 is independently verified and has a separate versioned retrieval index derived from a completed
  semantic run: source-linked semantic/structural blocks, Grade/Subject/Unit/
  Lesson/Concept/type metadata, PostgreSQL TSVECTOR lexical index, and a
  1536-dimensional pgvector HNSW cosine index. Fixture PostgreSQL tests passed,
  and a live OpenAI `text-embedding-3-small` smoke call returned 1536 values.
  It is `DONE`; this verifies indexing only.
- TASK-014 has a project-owned hierarchical/hybrid retrieval service over
  that index. It applies Grade/Subject and optional current focus narrowing in
  PostgreSQL, keeps lexical and vector candidates inspectable, fuses bounded
  candidate lists deterministically, expands only matching semantic parents,
  returns exact provenance, and enforces a context budget. Its local real
  Eureka pages 1–2 golden passed 7/7 representative cases, and a bounded
  competing-region golden across pages 2, 18, 30, and 42 passed 6/6 cases,
  including an explicit stale-focus conflict. It is `DONE`; this does not pass
  Phase 1 or any Production Engine gate.
- TASK-016 now has the real authenticated `/student` Math entry path, separate
  from `/demo`: it derives ownership from the verified Clerk Student subject,
  creates/resumes an open Math session, persists ordered raw Student messages,
  restores that history after refresh, and rejects cross-Student access. It is
  `DONE`; Tutor orchestration, safety consumption, Candidate Events, and
  automatic close are deliberately not part of this path yet.
- TASK-017 now has a deterministic, inspectable context boundary. It keeps the
  current question authoritative, limits the recent session window, uses
  optional persisted topic metadata only as retrieval focus, invokes TASK-014
  as the sole retrieval service, and admits only relevant active state/recent
  patterns/stable patterns. Resolved, inactive, irrelevant-subject, and
  irrelevant Math intelligence do not enter context. It is `DONE` and does not
  implement Tutor behavior, safety consumption, Candidate Events, or streaming.
- TASK-017A now explicitly consumes the persisted, versioned SafetyDecision
  before Tutor work: ALLOW and AGE_APPROPRIATE_ONLY continue distinctly; the
  latter carries its age-handling directive; parent redirects and protected
  baseline actions return their policy-defined calm redirect directives. Its
  isolated PostgreSQL policy/contract tests and the full Python suite passed;
  it is `DONE`. REC-09 added eight deterministic English/Arabic golden
  scenarios covering normal learning, each Parent action, baseline precedence,
  safe educational wording, and implicit self-harm meaning. The classifier
  uses only explicit deterministic phrases/context; no model call was used.
  This does not pass any gate.
- TASK-018 now orchestrates the approved production Tutor path: raw Student
  message persistence → persisted/versioned safety decision → explicit safety
  runtime action → bounded `TutorContextBuilder` context → one streamed
  `ModelTask.TUTOR` call for allowed interactions → reliable Tutor response
  persistence → Student SSE. Redirect/block paths make no Tutor model call.
  Mode/strategy selection is deterministic and compact; Candidate Events are
  intentionally absent pending TASK-019. TASK-018 is `REVIEW`, not a Gate B
  pass.
- No real-Lina calibration, Phase 1/2/3 exit claim, or later product expansion
  is currently authorized.

## Active decisions

- Use a modular monolith; retain verified infrastructure unless a concrete
  contract or maintenance reason requires change.
- Existing implementation has **no sunk-cost protection**. If it does not
  satisfy an approved contract, it may be replaced cleanly rather than patched
  superficially. Independently verified infrastructure should not be rewritten
  without cause.
- A task is not production-complete merely because its demo works or its
  implementing agent marked it `DONE`. Its stated verification criteria must
  pass and the implementation must match the governing contract.
- Preserve raw sources, raw interactions, provenance, rebuildability,
  Model-Gateway-only AI routing, explicit runtime safety enforcement, and the
  Evidence → State/Pattern → Intelligence Card architecture.
- Keep the approved reuse decisions and dependency-light platform direction;
  do not add new infrastructure merely to remediate a contract gap.

## Protected areas

Evidence-first intelligence; current behavior outranking historical
personalization; raw-source preservation; layered child safety and Parent
Learning Boundaries; one primary Tutor call; derived mastery/confidence views;
rebuildability; modular-monolith architecture; and the required calibration and
Real Lina decision gates.

## Active risks

- TASK-015 and TASK-019 onward remain blocked; TASK-018 awaits independent
  review. The Production Engine Acceptance Gate has not passed.
- The temporary local PostgreSQL instance is appropriate for the sandbox demo
  but not for destructive integration tests. A disposable PostgreSQL test
  database/workflow remains a deferred local-development improvement.
- Real AWS/S3 staging verification remains deferred and non-blocking; do not
  request credentials or remove the existing S3 implementation.
- The following remain frozen until the Production Engine Acceptance Gate
  passes: Lina Validation UI beyond the existing surface; Science; Voice/STT;
  production Vision/handwriting/drawing; Learning Canvas; Interactive Artifact
  Engine; advanced motion/gamification; Grade-transition production work; and
  Phase 4 and later work.

## Next recommended action

Review TASK-018 runtime, streaming, and safety evidence. Do not start TASK-019
or later work without explicit authorization and the applicable gate.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`
- Independent implementation audit (REC-01 remediation basis)
