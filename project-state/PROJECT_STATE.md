# Lina Personal Learning System — Project State

## Current goal

Gate B production acceptance is `PASSED` after independent composed verification
of TASK-026. REC-20 Parent–Student Authorization is `REVIEW`; do not begin
Parent visibility work until it receives independent approval.

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
  automatic close is now governed separately by TASK-020.
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
  Mode/strategy selection is deterministic and compact. It is `DONE`, not a
  Gate B pass.
- TASK-019 adds a project-owned `candidate-event-v1` contract to that same
  primary call. OpenAI structured output separates public text from hidden
  metadata; deterministic validation persists only source-linked candidates.
  Absent/malformed metadata is recorded on the Tutor message without blocking
  the response. No Learning Event, Evidence, state, pattern, or learner label
  is created. `strategy_applied` is distinct from `strategy_outcome`, which
  still requires an observable Student outcome. TASK-019 is `REVIEW`, not a
  Phase 2 Exit Gate or Gate B pass.
- TASK-020 adds a centrally configured, versioned inactivity-plus-grace
  lifecycle. Student return before closure refreshes the same OPEN session;
  after the full window, a row-locked close atomically records one deferred
  `SESSION_CONSOLIDATION` job and the next Student entry receives a new OPEN
  session. The worker tick performs only lifecycle/queue work; Candidate Event
  interpretation and all derived intelligence remain deferred. TASK-020 is
  `DONE`, not a Phase 3 or Gate B pass.
- TASK-021 now consumes only CLOSED sessions with valid source-linked Candidate
  Events. It sends compact relevant Student/Tutor excerpts through one
  structured `SESSION_EVIDENCE` Gateway call, validates contextual Events and
  approved categorical Evidence rubrics before persistence, and preserves
  session/Candidate/raw-message/run/model lineage. Empty sessions create no
  derived rows; retries reuse their processing run. No Current State, Pattern,
  Card, mastery, or confidence view is created. TASK-021 is `DONE`, not a
  Phase 3 or Gate B pass.
- TASK-022 now derives temporary Current Learning State only from completed,
  source-linked TASK-021 Evidence. States retain Student/subject/concept/type/
  policy/run/evidence/timestamps, resolve or expire deterministically, and the
  Tutor selector uses only active same-subject current-policy rows. No Pattern,
  Card, mastery, or confidence view is created. TASK-022 is `DONE`, not a
  Phase 3 or Gate B pass.
- TASK-023 now derives only deterministic, versioned Math Patterns from
  completed TASK-021 Evidence. It uses normalized type/key/scope identity,
  per-Evidence support/challenge provenance, configurable lifecycle thresholds,
  recency weighting, counter-evidence, and recurrence cycles. Scope starts at
  concept and can broaden only through diverse Math evidence; no Card,
  mastery/confidence view, or global/cross-subject pattern is created. It is
  `DONE`, not a Phase 3 or Gate B pass. REC-19 corrects counter-evidence
  handling: a validated specific misconception improvement challenges only
  that exact normalized key, and promoted scopes retain contributing support
  and counter Evidence lineage for the same deterministic lifecycle.
- REC-16 is `DONE`: Context and Subject scopes are recomputed from current
  qualifying concept and task-diverse Evidence, so resolved concepts no longer
  sustain them, one worksheet cannot create generalization, and one-concept
  recurrence cannot reactivate a resolved broader scope.
- TASK-024 now builds a compact, versioned on-demand Learner Intelligence Card
  from active, same-subject Current State plus relevant ACTIVE/STABLE Patterns.
  It ranks the explicit question before stale focus, State before historical
  guidance, and narrow scope before broad scope within each tier; Card source
  IDs and policy/schema metadata remain internal runtime provenance. It creates
  no Evidence, State, Pattern, or Card database row. REC-20 ensures exact
  applicable Pattern scope outranks broader ACTIVE scope while Current State
  remains first. It is `DONE`, not a Phase 3 or Gate B pass.
- TASK-025 now derives versioned categorical Decision Views from validated
  Evidence, with active Current State and ACTIVE/STABLE concept Pattern context.
  It persists scoped learning-status, independence, retention, and
  strategy-effectiveness views with Evidence/State/Pattern IDs, concise
  deterministic explanations, and policy lineage. Current State and recent
  independent Evidence outrank historical support Patterns; no raw Tutor text
  or Candidate Event alone can create a view. REC-18 corrected Evidence
  version semantics: only the latest completed interpretation of each raw
  Candidate observation counts, while older versions remain historical. It is
  `DONE`, not a Phase 3 or Gate B pass.
- TASK-026 now provides bounded, DB-job-backed reprocessing for selected
  CLOSED sessions by student/subject/session IDs or date range. Each durable
  run records its exact Evidence interpretation and downstream policy versions,
  keeps per-session staged Evidence result/error state, and atomically activates
  the complete selected scope only after every item succeeds. State, Pattern,
  and Decision are rebuilt in that same transaction from one authoritative
  Evidence interpretation per raw Candidate. Superseded State rows and
  PatternEvidence links remain auditable but cannot influence runtime; partial
  failure preserves the complete prior authority and retries reuse completed
  session work. Activation audit records prior/new per-session authority,
  timestamp, and version identity. Raw messages/Candidates and historical
  derived rows remain preserved; no Card is materialized. A new deterministic
  composed Math journey verifies raw message → same-call Candidate → close/job
  → one Evidence call → source-linked Evidence/State/Decision → bounded later
  Tutor context, with staged reprocessing preserving old runtime authority
  until atomic replacement. TASK-026 is `DONE`; Gate B is `PASSED`.
- REC-20 adds a durable, explicit Parent/Student relationship boundary. A
  verified Clerk Parent must resolve to the matching local Parent `User` and an
  explicit link before the minimal Student identity summary is returned. It is
  `REVIEW`; no Parent dashboard, learning intelligence, or linking UX exists.
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

- TASK-015 remains blocked. TASK-027 onward remains blocked until REC-20
  receives independent approval, despite Gate B having passed.
- The temporary local PostgreSQL instance is appropriate for the sandbox demo
  but not for destructive integration tests. A disposable PostgreSQL test
  database/workflow remains a deferred local-development improvement.
- Real AWS/S3 staging verification remains deferred and non-blocking; do not
  request credentials or remove the existing S3 implementation.
- The following remain frozen until the applicable later gates pass: Lina
  Validation UI beyond the existing surface; Science; Voice/STT; production
  Vision/handwriting/drawing; Learning Canvas; Interactive Artifact Engine;
  advanced motion/gamification; Grade-transition production work; and Phase 4
  work pending REC-20 independent approval.

## Next recommended action

Independently review REC-20 Parent–Student Authorization before unblocking
TASK-027. Do not start Parent visibility work without that approval.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `TASKS.md`
- Independent implementation audit (REC-01 remediation basis)
