# TASKS.md — Lina Personal Learning System

## How to Use This File

- Codex should execute only tasks marked `READY`.
- Normally complete one task at a time.
- A task becomes `DONE` only after its verification passes.
- Future-phase tasks may remain `BLOCKED` until dependencies and decision gates are satisfied.
- If implementation reality invalidates a task, update this file and `project-state/PROJECT_STATE.md`; do not silently improvise a new roadmap.

### Status Values

`READY` · `IN_PROGRESS` · `REVIEW` · `BLOCKED` · `DONE`

---

# Phase 0 — Repository & Runtime Foundation

## TASK-001 — Repository foundation
**Status:** DONE
**Dependencies:** None  
**Purpose:** Establish the repository-native Codex harness and runnable app skeleton without learning features.  
**Expected output:** Next.js app shell, FastAPI app shell, repository structure, governing docs in place, documented local run/test commands; shadcn/ui established as the baseline functional web component layer unless a concrete incompatibility is documented.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services`, `/packages`, `/docs`, `/project-state`, root config files.  
**Reuse check:** Read `docs/TECHNOLOGY_REUSE_CATALOG.md`; do not add optional UI/motion/RAG/artifact dependencies during foundation scaffolding merely because they may be useful later.  
**Verification:** Web and API start locally; baseline test commands execute; governing docs including the technology reuse catalog resolve from `AGENTS.md`; base UI setup is modifiable and not template-locked; no Tutor/Science/artifact feature code added.  
**Completion:** Verified with live web/API workflows, Next.js production build, TypeScript check, FastAPI tests, API smoke requests, and browser smoke test. The shadcn/ui baseline is locally owned and documented in `docs/REUSE_DECISIONS.md`.  

## TASK-002 — Environment and configuration foundation
**Status:** DONE
**Dependencies:** TASK-001  
**Purpose:** Create typed environment/config handling for web, API, DB, object storage, and model-provider settings.  
**Expected output:** Example env file, server-side secret handling, configuration validation, no API keys exposed to frontend.  
**Likely areas:** `/apps/api`, `/apps/web`, `/services/platform/config`.  
**Verification:** Missing required config fails clearly; frontend bundle contains no server secrets; tests cover config parsing.  
**Completion:** Verified with 9 configuration tests, TypeScript check, production build, secret-name scan of the Next output, API smoke checks on port 8000, and browser smoke testing.

## TASK-003 — PostgreSQL and migration foundation
**Status:** DONE
**Dependencies:** TASK-002  
**Purpose:** Establish PostgreSQL, pgvector capability, migrations, and foundational identity/grade tables.  
**Expected output:** Migration runner and initial tables for users, students, parent relationships, grade periods.  
**Likely areas:** `/apps/api`, `/services/platform/db`, `/migrations`.  
**Verification:** Fresh DB migrates up successfully; migration rollback/rebuild path documented; DB integration test passes.  
**Completion:** Verified with Alembic upgrade/check, PostgreSQL 16 development schema inspection, pgvector enablement, generated downgrade SQL, and 12 passing Python tests.

## TASK-004 — Parent/Student auth and authorization baseline
**Status:** DONE
**Dependencies:** TASK-003  
**Purpose:** Represent and authorize `PARENT_ADMIN` and `STUDENT` roles with separate protected surfaces.  
**Expected output:** Baseline login/session mechanism and role checks; separate web shells/routes.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/platform/auth`.  
**Verification:** Student cannot access Parent/Admin endpoints/pages; Parent can access admin shell; auth tests pass.  
**Completion:** Clerk-managed login/session wiring, role migration, JWT/JWKS verification, role-specific API dependencies, separate `/student` and `/parent` shells, and 15 passing tests. API tests verify both role directions; browser verification confirms the student flow and the parent surface is metadata-driven with a safe student default.

## TASK-005 — Object-storage abstraction
**Status:** DONE
**Dependencies:** TASK-002  
**Purpose:** Preserve original books and student images behind a provider-neutral storage interface.  
**Expected output:** Upload/store/read metadata interface with signed/private access pattern; local/dev backend supported.  
**Likely areas:** `/services/platform/storage`.  
**Verification:** Upload/read/delete test fixture works; originals preserve checksum; no public-by-default student asset URLs.  
**Completion:** Added a provider-neutral storage contract, local filesystem provider, SHA-256 and metadata preservation, expiring HMAC private capabilities, traversal protection, and atomic collision protection for originals. Extended with a production-ready S3-compatible provider (boto3) using conditional `IfNoneMatch` collision protection, HMAC-authenticated metadata bundles, HTTPS-only endpoint enforcement, and server-mediated private access. Production configuration now fails explicitly when `STORAGE_PROVIDER=local`. Added a resumable `SESSION_SECRET` rotation migration that verifies all metadata before same-key, ETag-guarded S3 copies while preserving object properties and refusing unsupported SSE-C objects. Tests cover both providers, configuration validation, metadata integrity tampering, endpoint security, conditional deletes, and HMAC rotation. Cloud bucket requirements, rotation permissions, and the integrity model are documented in `docs/OBJECT_STORAGE.md`.

## TASK-006 — DB-backed jobs and worker foundation
**Status:** DONE
**Dependencies:** TASK-003  
**Purpose:** Support document processing, Segment Review, deterministic Session
finalization, legacy Session Evidence compatibility, and rebuild work without
Redis/Celery.
**Expected output:** `jobs` table, worker loop, retry/failure status, idempotency hook.  
**Likely areas:** `/workers`, `/services/platform/jobs`.  
**Verification:** Test job moves pending → running → completed; failure is recorded; duplicate/idempotent execution behavior covered.  
**Completion:** Added a PostgreSQL-backed `jobs` table with database-enforced
partial unique idempotency keys, transaction-safe `FOR UPDATE SKIP LOCKED`
claiming, lease recovery, deterministic retry/failure recording, and an
independent worker with `run_once`/`run_forever` and an explicit handler
registry. Each claim has a fresh lease token, preventing a stale worker from
settling a recovered job even if the worker identifier is reused. Verified on
PostgreSQL with concurrent claiming, database constraints, lifecycle,
retry/failure, recovery, stale-lease fencing, worker handling, migration
downgrade/upgrade, and Alembic metadata checks.

## TASK-007 — AI execution ledger and Model Gateway skeleton
**Status:** DONE
**Dependencies:** TASK-003  
**Purpose:** Centralize model routing and usage/cost observability before Tutor calls exist.  
**Expected output:** task-based `ModelGateway` contract, route configuration model, `ai_executions` logging, provider adapter interface.  
**Likely areas:** `/services/model_gateway`, `/services/platform/observability`.  
**Verification:** Mock provider executes by task; model route can change without caller code change; usage/latency/success fields persist.  
**Completion:** Added a provider-neutral, task-routed Model Gateway backed by a
durable PostgreSQL `ai_executions` ledger. A deterministic local provider
supports fixtures and tests; callers use application task names while routes may
change provider/model. The ledger records usage, latency, estimated cost, and
success/failure without exposing provider SDKs to domain services.

## TASK-008 — Child-safety and Parent Learning Boundary configuration foundation
**Status:** DONE
**Dependencies:** TASK-003, TASK-004  
**Purpose:** Persist protected baseline policy version and per-student configurable topic boundaries.  
**Expected output:** policy service contract; topic catalog; Allow / Age-appropriate only / Redirect to parent persistence; protected categories not overrideable.  
**Likely areas:** `/services/platform/safety`, `/apps/api`, DB migrations.  
**Verification:** Parent can change configurable topic state; cannot disable baseline protection; audit metadata recorded; policy unit tests pass.  
**Completion:** Added a versioned, database-backed SafetyDecision boundary with
the approved configurable topic states, protected baseline routing, calm
redirect/age-handling directives, and compact policy audit records. Parent
boundary changes are persisted per student and take effect at evaluation time;
the protected baseline is not a configurable category.

### Phase 0 Exit Gate
Phase 1 tasks may become `READY` only when TASK-001 through TASK-008 are `DONE` and local verification is documented.

---

# Phase 1 — Grade 5 Math Content Foundation

## TASK-009 — Grade/book content data model
**Status:** DONE
**Dependencies:** Phase 0 Exit Gate  
**Purpose:** Model Grade-associated source documents, versioned processing runs, curriculum nodes, content blocks, and provenance.  
**Expected output:** migrations and repositories for documents, document versions/runs, curriculum nodes, content blocks.  
**Likely areas:** `/services/content`, `/migrations`.  
**Verification:** Original and derived artifacts are distinguishable; processing version/provenance is queryable.  
**Completion:** Added PostgreSQL records for immutable Grade/subject source
documents, versioned processing runs, Grade-local curriculum nodes, and
source-linked content blocks. Original storage identity is distinct from all
derived processing and each retrieval block traces to its source/run.

## TASK-010 — Parent Grade 5 Math book upload
**Status:** DONE
**Dependencies:** TASK-009, TASK-005  
**Purpose:** Let Parent/Admin upload Lina's real Grade 5 Math book while preserving the original source.  
**Expected output:** upload endpoint/UI, checksum, Grade/subject assignment, processing status.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/content`.  
**Verification:** Supported book upload persists original and metadata; invalid file is rejected; duplicate detection behavior documented.  
**Completion:** Parent/Admin-only API and shadcn-baseline intake UI accept PDF or
Markdown source files with Grade/subject metadata. Immutable originals are
checksum-addressed in private storage; invalid/mismatched files are rejected,
and a same-student checksum duplicate returns the already preserved document
rather than storing a second original. Initial status is visible as `UPLOADED`.

## TASK-011 — Docling adapter and normalized structural representation
**Status:** DONE
**Dependencies:** TASK-010, TASK-006  
**Recovery state:** Independently reviewed and accepted. The
Docling adapter now emits a project-owned normalized tree and PostgreSQL stores
explicit parent/child links, sibling and reading order, hierarchy depth,
page/layout provenance, stable per-run item keys, captions, and differentiated
text/table/picture/formula items. Structural processing is versioned by source,
processor version, and settings version; prior completed runs remain intact.
Controlled-fixture and local Eureka PDF verification passed. This is approval
of the structural layer only; it is not Phase 1 or Production Engine Acceptance
Gate approval.
**Purpose:** Parse uploaded books using Docling and preserve hierarchy, pages, reading order, figures/tables/formulas/provenance where available.  
**Expected output:** versioned Docling processing adapter and normalized derived representation.  
**Likely areas:** `/services/content/docling`, `/workers`.  
**Verification:** Known fixture produces stable structure; page/source provenance is preserved; re-run is idempotent/versioned.  
**Implementation note:** The previous flattened `ContentBlock` projection is no longer
the TASK-011 structural artifact. `document_structural_items` is the source-
linked, versioned structural layer; retrieval blocks remain a blocked TASK-013
concern.

## TASK-012 — Educational semantic extraction
**Status:** DONE
**Dependencies:** TASK-011, TASK-007  
**Recovery state:** Rebuilt for review. The former heuristic Unit/Lesson/Exercise
mapping has been replaced by a versioned Grade 5 Math semantic derivation from
the TASK-011 structural tree. It uses the `CURRICULUM_SEMANTICS` Model Gateway
route, validates a project-owned JSON contract and source/parent/coverage rules,
and persists explicit semantic-to-structural source lineage. Controlled
PostgreSQL fixture verification and a bounded real-Eureka (pages 1–2) Luna
golden passed. This approves the semantic layer only; it does not approve
TASK-013, Phase 1, or the Production Engine Acceptance Gate.
**Purpose:** Convert structural document output into Grade 5 Math educational semantics without treating Docling structure as curriculum understanding.  
**Expected output:** Unit/Lesson/Concept/Objectives/Examples/Exercises mapping with source references and schema contract tests.  
**Likely areas:** `/services/content/semantics`, `/packages/schemas`, `/prompts`.  
**Verification:** Schema-valid output on real/fixture pages; source refs valid; no silent catastrophic duplication/missing-unit acceptance.  

## TASK-013 — Structural content blocks and indexing
**Status:** DONE
**Dependencies:** TASK-012  
**Recovery state:** Reopened by the independent audit. The existing local
embedding/demo ranking path is not verified as the required structural,
lexical, and pgvector indexing contract. Rebuilt for review using versioned
semantic/structural blocks, a 1536-dimensional Model-Gateway embedding route,
PostgreSQL TSVECTOR lexical index, and pgvector HNSW cosine index. Prior index
runs remain preserved across new identities and failed builds.
**Purpose:** Build retrievable semantic/structural units with metadata, lexical index, and embeddings without blind fixed-token-first chunking.  
**Expected output:** content-block creation, Docling hierarchical/hybrid refinement where needed, lexical + pgvector indexing using the selected retrieval-plumbing path.  
**Likely areas:** `/services/content`, `/services/retrieval`.  
**Reuse check:** Before writing substantial custom indexing/RAG plumbing, run a focused comparison of (A) native Docling structural blocks + project lexical/pgvector indexing and (B) the official Docling + LlamaIndex Reader/Node Parser integration. Record `ADOPT / PARTIAL ADOPT / REJECT` with rationale; default to the simpler native path unless LlamaIndex measurably reduces total complexity while preserving provenance and project filtering/control.  
**Reuse decision:** **ADOPT native Docling + PostgreSQL/pgvector; REJECT
LlamaIndex for TASK-013.** TASK-011/012 already provide project-owned,
source-linked structure and semantics; native PostgreSQL indexes preserve that
lineage and metadata filtering without another retrieval framework. Re-evaluate
only if TASK-014 golden retrieval shows a concrete gap.
**Verification:** Reuse decision is recorded; definitions/examples/figures remain source-linked; Grade/Subject/Focus metadata remains controllable; oversized blocks refine without losing hierarchy; index rebuild works.  

## TASK-014 — Hierarchical/hybrid retrieval service
**Status:** DONE
**Dependencies:** TASK-013  
**Recovery state:** Rebuilt for review using bounded PostgreSQL lexical and
pgvector candidate queries, deterministic reciprocal-rank fusion, optional
Grade/Subject/Unit/Lesson/Concept narrowing, semantic-parent expansion, exact
source provenance, and a context budget. A local real-Eureka pages 1–2 golden
set passed 7/7 cases (terminology, paraphrase, example, exercise, figure,
with-focus, and without-focus). This approved retrieval layer does not by
itself pass Phase 1 or the Production Engine Acceptance Gate.
**Purpose:** Retrieve Grade/Subject/Focus/Concept-relevant Math context using metadata + lexical + vector ranking over the retrieval approach selected in TASK-013.  
**Expected output:** retrieval API/service with context budget and source provenance, with any adopted framework hidden behind the project Retrieval domain contract.  
**Likely areas:** `/services/retrieval`.  
**Verification:** Golden questions return intended lesson/pages/content types with acceptable reliability; framework choice, if any, does not bypass project-owned filtering, provenance, context budgets, or rebuildability.  

## TASK-015 — Minimal Content Admin and reprocess action
**Status:** BLOCKED
**Dependencies:** TASK-011, TASK-014  
**Recovery state:** Reopened by the independent audit. API endpoints exist, but
the required Parent/Admin status page and reprocess visibility are incomplete.
Blocked until the structural and retrieval contracts are verified.
**Purpose:** Show Parent/Admin content readiness and allow versioned reprocessing from the preserved original.  
**Expected output:** book status page, processing version, failures, reprocess action.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/content`.  
**Verification:** Reprocess creates a new derived run without replacing original; status/failure is visible.  

### Phase 1 Exit Gate
**Historical gate, superseded as a Tutor permission gate by Roadmap Track A.**
A real Grade 5 Math book and retrieval golden set remain useful grounding
validation. They no longer authorize Student Tutor availability, which must work
with zero content and optional retrieval.

---

# Phase 2 — Math Tutor Vertical Slice

## TASK-016 — Session/thread and Student Math entry flow
**Status:** DONE
**Dependencies:** Phase 1 Exit Gate  
**Recovery state:** Rebuilt for review as the authenticated production path at
`/student`, separate from the development-only sandbox. A verified Clerk
Student identity resolves to an application-owned Student profile; the browser
never supplies `student_id` as authority. The path creates or resumes one open
Math session, persists ordered Student messages, restores history on refresh,
and prevents cross-Student reads/writes. It intentionally does not run Tutor
or automatic session-close behavior; those remain TASK-017 through TASK-020.
**Purpose:** Let Lina start a natural Math session and change threads/topics without managing internal structure, using a child-appropriate visual shell rather than a generic developer chat UI.  
**Expected output:** session/thread persistence, Math entry screen, message pipeline skeleton, and a coherent Lina-facing visual direction suitable for approximately age 10 with photo/avatar-ready personalization.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/tutor`.  
**Reuse check:** (1) Evaluate `assistant-ui` custom-runtime fit before hand-building full thread/composer/chat plumbing; test FastAPI/SSE compatibility, project-owned persistence, custom attachments/message parts, safety integration, and styling freedom. (2) Inspect approved Framer/Webflow education visual references plus 21st.dev/Motion Primitives/Magic UI/React Bits sources for reusable patterns. Record the assistant-ui decision and selected visual/component sources. Do not adopt a preschool template or full marketing-template architecture.  
**Verification:** Reuse decisions are recorded; Session persists messages; topic switch can create internal thread without Student workflow burden; visual shell feels playful/intelligent rather than preschool/corporate; any reused chat layer remains subordinate to project-owned Tutor/session/safety contracts.  
**Completion note:** The existing `assistant-ui` reuse decision remains
`REJECT` for this small project-owned persistence path; it would not remove the
need for the FastAPI/auth/session boundary and is unnecessary before the Tutor
streaming contract. PostgreSQL API tests cover first visit, open/resume,
ordered persistence and refresh, ownership isolation, and no close side effect;
the Student screen calls `/api/v1/student`, never `/api/v1/demo`. TypeScript
check and production build passed.

## TASK-017 — Tutor context builder and retrieval integration
**Status:** DONE
**Dependencies:** TASK-016, TASK-014  
**Recovery state:** Rebuilt for review as a deterministic, model-free context
boundary. It keeps the current Student question authoritative; includes only a
small ordered session window; derives optional lightweight topic metadata from
persisted message metadata; calls TASK-014 as its sole curriculum boundary; and
selects only question/focus-relevant active state, recent patterns, and stable
patterns. Resolved/inactive and irrelevant-subject intelligence is excluded.
Historical intelligence remains advisory and is never a teaching decision.
**Purpose:** Build a compact Tutor context from current turn, Grade/subject/focus, retrieved book context, and later-compatible intelligence slots.  
**Expected output:** deterministic context-builder contract with token/context limits.  
**Likely areas:** `/services/tutor/context`, `/services/retrieval`.  
**Verification:** Full history is not injected; irrelevant subject history excluded; source context visible in debug trace.  
**Completion note:** Context budgets independently bound current-question,
session, retrieval, and intelligence slices. Debug output records the selected
session message IDs, retrieval source references, selected intelligence IDs,
and source kinds. PostgreSQL tests cover question priority, history bounds,
TASK-014 integration, subject/relevance/status filtering, state-over-history
priority, topic continuity, and budgets. This is not Tutor behavior, safety
consumption, Candidate Event, or streaming work.

## TASK-017A — Safety & Learning Boundary Policy Engine
**Status:** DONE
**Dependencies:** TASK-017, TASK-008  
**Recovery state:** Reopened by the independent audit. The policy foundation is
preserved, but Tutor runtime does not consume `AGE_APPROPRIATE_ONLY` according
to the approved action semantics. Blocked pending TASK-017.
**Purpose:** Enforce the non-overridable child-safety baseline and Parent Learning Boundaries as an explicit runtime policy decision before student-facing Tutor behavior, without relying on Tutor prompt instructions alone.  
**Expected output:** A versioned `SafetyDecision` service/contract that evaluates the interaction context and returns an effective action, category/reason code, policy source/version, and age-handling directive; implementation may use deterministic routing and/or a classifier where needed.  
**Likely areas:** `/services/platform/safety`, `/services/tutor/context`, `/apps/api`, `/packages/schemas`.  
**Verification:** Protected baseline cannot be weakened; Parent boundary states route correctly; Religion default redirect works; a Tutor prompt cannot bypass the policy decision; normal Math requests pass without unnecessary blocking; decisions are auditable.  
**Completion note:** REC-09 added an isolated PostgreSQL deterministic golden
scenario suite: normal Math/Science, every Parent boundary action, baseline
precedence, a safe educational sensitive-word reference, and implicit Arabic
self-harm meaning. The classifier remains deterministic; no model call was
used. TASK-018 is DONE; TASK-019 is under independent review.

## TASK-018 — Text Tutor runtime with streaming
**Status:** DONE
**Dependencies:** TASK-017A, TASK-007  
**Recovery state:** The production boundary now persists the Student message,
consumes `SafetyDecision` through `TutorSafetyRuntime`, builds the approved
bounded Tutor context, makes one streamed `ModelTask.TUTOR` call for allowed
turns, persists the final response, and serves provider-produced SSE events to
`/student`. Compact deterministic scenarios cover modes, bilingual context,
grounding/provenance, safety branches, one-call behavior, and interrupted-stream
persistence. TASK-019 now adds hidden Candidate Event metadata to that same
primary call; no new Tutor runtime authority or second model call is introduced.
**Purpose:** Deliver age-appropriate Grade 5 Math teaching through one primary Tutor call and SSE streaming, consuming the approved safety/boundary decision contract rather than implementing policy inside the Tutor prompt.  
**Expected output:** fixed Tutor identity, adaptive teaching strategy, Learn/Homework/Explore baseline behavior, bilingual response, integration of the upstream `SafetyDecision`.  
**Likely areas:** `/services/tutor`, `/apps/api`, `/apps/web`, `/prompts/tutor`.  
**Verification:** Representative scenarios show grounding, strategy changes, no endless answer withholding, correct consumption of `SafetyDecision`, no prompt-only safety bypass, and complete usage logs.  

## TASK-019 — Candidate Event metadata contract
**Status:** REVIEW
**Dependencies:** TASK-018  
**Recovery state:** The primary Tutor call now returns a versioned, structured
student-facing text plus hidden Candidate Event metadata envelope. Valid
source-linked candidates persist without creating Events, Evidence, state, or
patterns; absent/malformed metadata never blocks the Tutor response. The v1
contract now distinguishes `strategy_applied` from `strategy_outcome`; it
awaits independent review.
**Purpose:** Let the same Tutor call flag meaningful candidate events without writing stable learner conclusions.  
**Expected output:** small hidden structured metadata schema and persistence/buffer hook.  
**Likely areas:** `/services/tutor`, `/packages/schemas`, `/prompts/tutor`.  
**Verification:** Normal chat does not produce unnecessary candidates; meaningful attempts do; schema contract tests pass.  

### Phase 2 Exit Gate
**Historical gate, superseded as a content-readiness dependency by Roadmap Track
A.** Lina can use a text-based Grade 5 Math Tutor with zero content or optional
grounding; Tutor runtime and Candidate Event metadata remain inspectable and
cost-logged.

Before Phase 3 becomes eligible, complete an **Early Lina Calibration Checkpoint**: run one or more natural Grade 5 Math sessions with Lina and inspect the transcript, retrieval trace, Tutor behavior, safety routing, and Candidate Events. Record brief findings in project state. This is an early calibration checkpoint, **not** the Mandatory Real Lina Decision Gate after Phase 4 and does not authorize later feature expansion.

---

# Phase 3 — Learning Intelligence Core

> **Historical implementation boundary:** TASK-020–TASK-026 describe the
> completed legacy/current Session Evidence implementation. SEG-EVID-01
> supersedes Session-wide semantic review as the approved target architecture
> for future Evidence generations while preserving these historical completion
> records and existing data.

## TASK-020 — Automatic session-close lifecycle
**Status:** DONE
**Dependencies:** Phase 2 Exit Gate, TASK-006  
**Recovery state (historical/current legacy implementation):** A versioned central inactivity-plus-grace policy now keeps
quick returns in the same OPEN session, closes only after the full window, and
atomically writes one deferred `SESSION_CONSOLIDATION` job. Lifecycle scans use
row locks and the durable job idempotency key; no Candidate validation or
derived intelligence work runs here. Independent review is complete; TASK-021
is now under review.
**Purpose:** Close sessions after configurable inactivity/grace logic and enqueue consolidation.  
**Expected output:** session lifecycle states and worker trigger.  
**Likely areas:** `/services/tutor/session`, `/workers`.  
**Verification:** quick return can continue same session; inactivity closes once; consolidation job is idempotent.  

## TASK-021 — Session Evidence consolidation
**Status:** DONE
**Dependencies:** TASK-020, `docs/LEARNING_INTELLIGENCE_SPEC.md`  
**Recovery state (historical/current legacy implementation):** Closed sessions now enqueue one `SESSION_EVIDENCE` Gateway
call only when source-linked Candidate Events exist. Strict versioned output
validation creates contextual Learning Events and categorical Evidence with
raw-message/Candidate/session/run traceability; empty sessions create none.
Processing retries reuse the same run safely. Independent review is complete;
TASK-022 is now under review. No Pattern, Card, or decision-view work runs
here.
**Purpose:** Convert Candidate Events + relevant excerpts/thread context into validated Learning Events and Evidence using the approved rubric.  
**Expected output:** versioned consolidation processing run, Events, Evidence, traceability.  
**Likely areas:** `/services/intelligence`, `/prompts/intelligence`, `/packages/schemas`.  
**Verification:** Golden evidence scenarios match expected allowed states; “what must not be inferred” tests pass; every Evidence item traces to source.  

## TASK-022 — Current Learning State engine
**Status:** DONE
**Dependencies:** TASK-021  
**Recovery state:** Versioned, subject-scoped Current State now derives only
from completed TASK-021 Evidence. Deterministic lifecycle rules create, update,
resolve, and expire temporary states; active Tutor selection excludes resolved,
expired, legacy, and other-subject rows. Independent review is complete;
TASK-024 is now under review.
**Purpose:** Represent temporary active difficulties, misconceptions, open loops, recent strategy outcomes, and resolution/expiry.  
**Expected output:** current-state store/service distinct from stable Patterns.  
**Likely areas:** `/services/intelligence/state`.  
**Verification:** one strong event may update current state; resolved/expired state leaves current runtime; historical source remains.  

## TASK-023 — Deterministic Pattern engine and scope lifecycle
**Status:** DONE
**Dependencies:** TASK-021  
**Recovery state:** Completed TASK-021 Evidence now drives a versioned,
deterministic Math Pattern engine with normalized taxonomy/identity, evidence
links, lifecycle, scope promotion, counter-evidence, and recurrence handling.
Specific misconception improvement Evidence now challenges only its matching
normalized Pattern key. Context/subject recomputation includes support and
counter Evidence relationships with queryable lineage, while promotion requires
current qualifying concept and task diversity. REC-16 review is complete; no
decision-view work runs here.
**Purpose:** Implement frequency/recency/context-diversity/counter-evidence governed Pattern lifecycle and scope without free LLM strength judgment.  
**Expected output:** candidate/active/stable/weakening/resolved/superseded transitions, pattern-evidence links, a normalized `pattern_type` + `pattern_key` registry/taxonomy, and a historical recurrence lookup hook.  
**Likely areas:** `/services/intelligence/patterns`.  
**Verification:** unit tests cover promotion, weakening, resolution, scope generalization, semantic normalization to stable pattern keys, and recent counter-evidence outweighing stale history under configured policy. For `strategy_effectiveness`, the Tutor choosing/using a strategy is **not** confirming Evidence by itself; only an observable Lina outcome may support or challenge strategy effectiveness.  

## TASK-024 — Compact Learner Intelligence Card and Tutor selector
**Status:** DONE
**Dependencies:** TASK-022, TASK-023  
**Recovery state:** An on-demand, versioned compact Card now ranks relevant
active Current State and ACTIVE/STABLE current-policy Patterns before applying
centralized bounds. Tutor context receives only that selected slice with
source-ID/policy provenance. REC-20 corrected scope ranking so an exact
concept Pattern outranks a broader Pattern even when the latter is ACTIVE.
Independent audit is complete; no decision-view work runs here.
**Purpose:** Produce compact temporal runtime intelligence and select only relevant intelligence for the current Tutor context.  
**Expected output:** Card materialized state, budget/ranking rules, relevant-intelligence selector.  
**Likely areas:** `/services/intelligence/card`, `/services/tutor/context`.  
**Verification:** Card stays within configured budget; resolved patterns excluded; current behavior can override historical recommendation; relevant patterns remain advisory rather than mandatory; no full profile dump. Historical strategy selection must not itself create confirming Evidence.  

## TASK-025 — Derived mastery/confidence views
**Status:** DONE
**Dependencies:** TASK-021, TASK-024  
**Recovery state:** A versioned deterministic policy now persists categorical
learning-status, independence, retention, and strategy-effectiveness views
from validated Evidence plus current State/Pattern context. Views retain source
IDs/explanations and policy lineage; REC-18 ensures one latest completed
Evidence interpretation per raw Candidate observation is counted. Independent
audit is complete; no TASK-026 reprocessing orchestration is included.
**Purpose:** Provide categorical parent/tutor decision views over Evidence without turning scores into source truth.  
**Expected output:** configurable derived views such as Strong/Developing/Needs revisit + evidence confidence.  
**Likely areas:** `/services/intelligence/decisions`.  
**Verification:** changing decision policy can recompute views without rewriting raw Events/Evidence.  

## TASK-026 — Intelligence reprocessing pipeline
**Status:** DONE
**Dependencies:** TASK-021, TASK-023, TASK-024, TASK-025
**Recovery state:** A bounded, job-backed reprocess run records explicit
session/date scope, Evidence interpretation identity, downstream policy
versions, and durable per-session results. Rebuilt Evidence stays staged until
every selected session succeeds; one final DB transaction then updates the
entire scope's authority and rebuilds State, Pattern, and Decision outputs from
one authoritative Evidence interpretation per raw Candidate. Superseded State
rows and PatternEvidence links remain auditable but cannot influence current
runtime. Partial failure leaves every selected session on the prior coherent
authority; retry reuses completed session Evidence. The activation audit retains
prior and new per-session authority, timestamp, and version identity. Raw
history and prior derived rows remain preserved; the Card remains on-demand.
Independent composed acceptance verification is complete: a bounded Math
journey reached later Tutor context with source lineage, current behavior
overriding historical support, safe failure handling, and authority replacement.
Gate B is `PASSED`; TASK-027+ remains blocked pending independent REC-23
approval.
**Purpose:** Rebuild derived Events/Evidence/Patterns/Card from preserved raw history after rubric/prompt/policy improvements.  
**Expected output:** versioned rebuild job with date/session scope and audit trail.  
**Likely areas:** `/services/intelligence/reprocess`, `/workers`.  
**Verification:** fixture history reprocesses into a new processing version; previous derived version remains auditable or safely superseded.  

### Phase 3 Exit Gate
A meaningful Math session must create auditable Evidence and relevant intelligence that can influence a later Tutor session without loading full history.

## SEG-EVID-00 — Governing Documentation Alignment
**Status:** DONE
**Purpose:** Align every governing document with the approved
Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority.
**Verification:** The eight governing documents agree; AGENTS and Roadmap
contradictions are removed; historical Session Evidence is preserved; and no
implementation code changed.

## Full-System Acceptance — Learning Intelligence
**Status:** DONE / ACCEPTED
**Dependencies:** SEG-EVID-01A–D accepted; SEG-EVID-01E–F completed in order.
**Purpose:** Prove the governed path from raw conversation through real Segment
Review, Session-authorized learning memory, and a later real Tutor
personalization on an isolated acceptance database, then prove the same path
from a clean fresh start.
**Scope:** The durable execution spec is
`docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md`. This objective preserves raw
source authority, requires real `openai / gpt-5.6-luna` Model Gateway evidence
for AI-powered acceptance work, and protects the source database from writes.
**Stages / acceptance:** SEG-EVID-01D, SEG-EVID-01E, and SEG-EVID-01F are
independently **CODE REVIEW VERIFIED / ACCEPTED** as the ordered stages serving
this one objective; they are not separate product goals. The independently
accepted result covers the real Math multi-Session path: real Tutor and Segment
Review executions; Session-authorized Event/Evidence activation; Current State
lifecycle; Pattern support/counter/weakening/resolution; Candidate-free
provenance and TeachingMethod outcome; bounded authoritative retention anchors
including persisted provenance across authority replacement; current behavior
outranking history; relevant later personalization; negative-memory exclusion;
Session-scoped reprocessing with atomic authority activation; and auditable old
Evidence generations. PostgreSQL/Python results and real-Luna execution counts
remain Codex-reported, not independently re-executed. `REAL-LINA VERIFIED =
NO`; browser remains NOT VERIFIED. Accepted SEG-EVID-01A/B/C records and all
deferred/frozen work remain unchanged.
**Completion gate:** Historical isolated-database and separate fresh-start
journeys demonstrate `Conversation → Segments → Reviews → Evidence → Memory →
Tutor personalization` with evidence labels that distinguish automated, real
Luna, database end-to-end, Tutor personalization, browser (if run), and
`REAL-LINA VERIFIED = NO`.

## SEG-EVID-01A — Governing Contracts & Persistence
**Status:** DONE
**Dependencies:** CAND-01 strict schema compatibility correction committed and independently reviewed.
**Purpose:** Implement explicit Segment completion persistence, versioned
`SegmentLearningReview`, Segment Review contract/version identity,
LearningEvent Segment lineage, multi-message provenance, and backward-compatible
legacy handling. No runtime intelligence activation yet.
**Acceptance:** Independently CODE REVIEW VERIFIED. Segment Review creation
requires a durably closed Segment; Event-linked Segment and Segment Review
provenance use `RESTRICT`; and provisional Candidate lineage remains nullable
with `SET NULL` behavior. The migration, legacy backfill, and Candidate-free
downgrade-refusal design were independently reviewed. Codex-reported focused
persistence/migration contracts, relevant database and unchanged-Tutor
regression coverage, and canonical Python verification passed (544 passed,
5 skipped). No Segment Review runtime, job, ModelTask, model call, Session
Finalization, or Evidence activation was included.

## SEG-EVID-01B — Segment Completion & Review Jobs
**Status:** DONE
**Dependencies:** SEG-EVID-01A
**Purpose:** Implement durable Segment completion behavior, deterministic
structural reviewability, `SEGMENT_LEARNING_REVIEW` job scheduling, idempotent
orchestration, session-close handling, and CTX-03 `NEW_SEGMENT` / `UNCERTAIN`
consistency. No semantic determination of learning meaning in B.
**Acceptance:** Independently CODE REVIEW VERIFIED. `CONTINUE` keeps the
current Segment open with no Review; `NEW_SEGMENT`, `UNCERTAIN`, and the
accepted fallback close the prior Segment as `NEXT_SEGMENT_CREATED` before the
next is created. Session close reconciles only its own lineage: superseded open
Segments close as `NEXT_SEGMENT_CREATED` and the final open Segment as
`SESSION_CLOSED`. Structural reviewability requires only durable closure, valid
Session/Segment/Student lineage, and one persisted raw Student
`LearningMessage` assigned to the Segment—never Candidate, Guided Check,
TeachingMethod, Tutor-response, Exchange-count, concept, keyword, or other
semantic prerequisites. Each eligible closure idempotently queues exactly one
`SEGMENT_LEARNING_REVIEW` request at `segment-review-request-v1`, identified by
Segment/request-version only (not prompt/model/rubric versions). The current
strict-grounding/dimensional correction introduces request
`segment-review-request-v3` and prompt `segment-learning-review-prompt-v3`;
v1/v2 rows remain preserved for provenance, while v3 is the current immutable
execution contract. B creates no
`SegmentLearningReview` row or Review handler; `SESSION_CONSOLIDATION` remains
operational; and no Session Finalization, Evidence, Pattern, Card, or
personalization activation was introduced.
**Verification:** Independently verified review status is CODE REVIEW only.
Codex-reported, not independently re-executed: focused PostgreSQL
B/runtime/lifecycle coverage (45 passed) and canonical Python (552 passed,
5 skipped). No GitHub CI status is available.

## SEG-EVID-01C — Segment Semantic Reviewer
**Status:** DONE
**Dependencies:** SEG-EVID-01B
**Purpose:** Implement the `segment_evidence` ModelTask with complete raw
Segment input, optional Candidate hints, Guided Check / TeachingMethod lineage
where present, strict structured semantic output, source/provenance validation,
versioned `SegmentLearningReview`, and staged findings only. No Card/Pattern
activation.
**Implementation note:** `SEGMENT_EVIDENCE` now reviews a durably closed
Segment through the Model Gateway using the strict
`segment-learning-review-v1` contract. Complete ordered raw Segment messages
are retained with a 64,000-character capacity refusal rather than truncation;
Candidate hints are optional and non-authoritative; Guided Check and
TeachingMethod lineage are supplied only when server-validated; and every
accepted Finding is source-grounded in at least one raw Student message in the
same Segment. `findings=[]` is valid. Reviews are versioned, persist safe
failure state before Job retry, and are idempotent after completion. C creates
no LearningEvent, LearningEvidence, Current State, Pattern, Decision View,
Card, Session Finalization, or automatic historical retrieval. Retention is
always `not_tested` in C v1; cross-subject findings remain staged/fail-closed.
The integrity correction validates Candidate hints before AI input: only
current `candidate-event-v1`, exact Student-source, supported-event,
grounded-misconception, and server-owned strategy-lineage Candidates may be
shown as optional hints. Invalid or historical hints are excluded while raw
Segment review continues. `relationship=retention_failure` is also rejected
for C v1.
**Verification:** Codex-reported: focused C and structured-provider coverage
(24 passed); Candidate/CAND-01/TeachingMethod/worker/structured-output/legacy
Session Evidence coverage (87 passed); canonical Python (577 passed, 6 skipped).
Controlled synthetic
real `openai / gpt-5.6-luna` verification completed six representative
Segment scenarios through the strict Gateway path (1 passed); this is real
model transport/representative-scenario verification, not Real-Lina testing
or independent re-execution.
**Acceptance:** Independently **CODE REVIEW VERIFIED / ACCEPTED**. C provides
`ModelTask.SEGMENT_EVIDENCE`, a provider-neutral Gateway, strict
`segment-learning-review-v1`, prompt `segment-learning-review-prompt-v1`,
`evidence-rubric-v1`, and `segment-review-policy-v1`. The complete ordered raw
Segment remains semantic source authority; Findings require exact same-Segment
Student grounding, with validated Guided Check/TeachingMethod context where
available. Candidate hints remain optional/non-authoritative and invalid,
stale, or historical hints are excluded without suppressing raw Review.
Retention is fully closed in C v1 (`not_tested` dimension/context and no
`retention_failure`); there is no automatic historical retrieval. Cross-subject
Findings remain staged as `SAME_AS_SESSION`, `POSSIBLE_CROSS_SUBJECT`, or
`UNCERTAIN`; `findings=[]` is valid. Versioned Reviews are idempotent, persist
safe FAILED state before retry, and C has the actual
`SEGMENT_LEARNING_REVIEW` handler. No Session Finalization enqueue or durable
intelligence activation was introduced. Codex-reported, not independently
re-executed: correction RED (6 failed, 17 passed), focused (24 passed),
relevant regression group (87 passed), canonical Python (577 passed, 6
skipped), and clean `git diff --check`. Controlled synthetic real-model
verification was Codex-reported: `openai / gpt-5.6-luna` produced casual 0
findings, Candidate-free learning explanation, bare-answer incorrect attempt
without misconception, misconception plus self-correction, grounded
`CONCRETE_EXAMPLE` strategy outcome, and `POSSIBLE_CROSS_SUBJECT`. `REAL LUNA
SEGMENT REVIEW TRANSPORT VERIFIED` and `REAL LUNA SEGMENT REVIEW
REPRESENTATIVE SCENARIOS VERIFIED` are CODEX-REPORTED; `REAL-LINA VERIFIED =
NO`. No GitHub CI status is available.

## SEG-EVID-01D — Session Finalization & Intelligence Activation
**Status:** DONE
**Dependencies:** SEG-EVID-01C
**Purpose:** Implement completeness/version gates, deterministic finalization,
Event/Evidence materialization, and Current State / Pattern / Decision
activation with no semantic Session call by default, as Stage D of Full-System
Acceptance.
**Implementation / verification:** Candidate-free, strict Review-grounded
`strategy_outcome` Findings now resolve their exact current-contract Finding by
Review ID and Finding index before downstream use. Valid Candidate-free method
outcomes use the grounded TeachingMethod identity for
strategy-effectiveness Patterns and Decision Views; malformed/mismatched Review
provenance fails closed. Legacy Candidate-backed behavior is preserved and no
Candidate-free misconception recurrence key is invented. Codex-reported focused
PostgreSQL finalization/pattern/decision coverage passed (`74 passed`) and the
canonical Python suite passed (`682 passed, 6 skipped`). A deterministic replay
on a copied isolated database from persisted real-Luna Reviews produced 34
Event/Evidence rows, 11 Patterns, 20 Decision Views, 6
strategy-effectiveness Patterns, and 5 non-insufficient strategy-effectiveness
Decision Views. This is Codex-reported acceptance evidence, not independent
acceptance; no new model call, browser, or Real-Lina verification was performed.
**Acceptance:** Independently **CODE REVIEW VERIFIED / ACCEPTED**:
deterministic Session Finalization, one unified Session Authority, Candidate-free
Event/Evidence downstream authority, exact Segment Review Finding provenance,
cross-subject withholding, atomic rollback with no partial activation, and
legacy/new pipeline separation are accepted. Candidate-free grounded
TeachingMethod strategy outcomes are accepted downstream without weakening
Review validation or manufacturing Candidate identity. The test, real-model,
and copied-database results above remain Codex-reported, not independently
re-executed.

## SEG-EVID-01E — Reprocessing & Authority Compatibility
**Status:** DONE
**Dependencies:** SEG-EVID-01D
**Purpose:** Implement legacy/new coexistence, Session-scoped external
reprocessing, Segment-internal semantic rebuild, atomic activation, and legacy
Session Evidence handling, as Stage E of Full-System Acceptance.
**Implementation:** Reprocessing now dispatches each CLOSED selected Session by
its persisted intelligence pipeline. Legacy `legacy-session-evidence-v1`
Sessions retain the existing versioned `SESSION_EVIDENCE` path. New
`segment-finalization-v1` Sessions enumerate structural Reviewable Segments,
reuse only current-contract, provenance-valid Reviews, rerun unavailable
Reviews through the Segment Model Gateway, and stage deterministic
Event/Evidence without live authority. A completed selected scope alone can
atomically replace all Session authorities and rebuild Current State, Pattern,
and Decision Views. Staged-run ownership, Session/pipeline, and requested
contract identities are validated before any authority mutation. The reprocess
version set now records Segment Review schema/prompt/rubric/review-policy plus
the finalization pipeline; provider/model remain execution provenance, not
semantic compatibility.
**Verification:** Codex-reported focused PostgreSQL E coverage: `14 passed`;
relevant finalization/review/pattern/decision PostgreSQL coverage: `109 passed`;
canonical Python: `686 passed, 6 skipped`; `git diff --check`: clean
(Codex-reported). A copied isolated historical real-Luna database reused
eight current-contract Reviews with no new model execution, staged and
activated 34 Event/Evidence rows, and retained eight Candidate-free grounded
strategy outcomes with six strategy-effectiveness Patterns and five
non-insufficient strategy-effectiveness Decision Views. This is
Codex-reported database evidence, not independent re-execution. Real-Lina and
browser verification remain NOT VERIFIED.
**Acceptance:** Independently **CODE REVIEW VERIFIED / ACCEPTED**:
Session-scoped external reprocessing, per-pipeline legacy/new dispatch,
Segment-internal semantic rebuild for new Sessions, reuse/rerun of
current-contract Segment Reviews, deterministic staging without premature
authority, complete-scope atomic Authority activation and rollback protection,
Candidate-free provenance preservation, and legacy audit compatibility are
accepted. Automated, database, and model results remain Codex-reported unless
independently re-executed.

## SEG-EVID-01F — Real Model & Multi-Session Verification
**Status:** DONE / CODE REVIEW VERIFIED / ACCEPTED
**Dependencies:** SEG-EVID-01E
**Purpose:** Verify confusion, bare wrong answer, explicit misconception,
correction/counter-evidence, TeachingMethod outcome, transfer, retention with
bounded historical anchors, multi-Session Pattern support/counter and
weakening/resolution, Card updates only after Session activation, relevant
future Tutor use, and current Student behavior above historical intelligence,
as Stage F of Full-System Acceptance.
**Current execution / acceptance:** Independently **CODE REVIEW VERIFIED /
ACCEPTED**. Codex-reported isolated Math acceptance
completed `12` normal Sessions, `19` successful real `openai / gpt-5.6-luna`
Tutor executions, `15` successful real Luna Segment Review executions, and
Session-authorized finalization. The bounded authoritative retention anchor
path is `segment-learning-review-v2` / prompt v5 / policy v2: a real Luna
anchor-concept separator mismatch failed strict validation safely, then the
prompt-only exact-copy correction completed a grounded `retained` Review.
Real authorized Evidence exercised support, counter, `WEAKENING`, and
`RESOLVED` Pattern lifecycle states; a later Tutor context selected relevant
State/Pattern Card sources without raw historical transcript injection, while
an unrelated long-division turn selected none. Changed-context transfer was
conservatively `not_tested`, not fabricated. Complete-scope E reprocessing and
rollback/no-partial-activation were exercised. Focused PostgreSQL coverage:
`93 passed`; canonical Python: `688 passed, 6 skipped`; all are Codex-reported,
not independently re-executed. Real-Lina/browser remain NOT VERIFIED.
**Follow-on provenance correction:** A persisted delayed-retention Review now
validates only its exact stored anchor IDs against durable authority history:
the same Student, subject, prior closed Session, exact completed Evidence run,
demonstrated/strong Evidence, concept, and meaningful delay must still match.
Current authority remains the only historical input for a new Segment Review;
a later completed E-path activation audit may prove a formerly-authoritative
anchor for an already persisted Review. Arbitrary old Evidence, malformed
audit lineage, foreign/wrong-run rows, and invalid delay remain fail-closed.
Codex-reported focused PostgreSQL correction coverage: `117 passed`; it reused
no model output and did not rerun the real-Luna journey. Canonical Python:
`689 passed, 6 skipped` (Codex-reported). The retained isolated
acceptance database is not configured in this checkout, so no copied-database
replay was performed for this correction. PostgreSQL/Python execution results
and real-Luna counts remain Codex-reported, not independently re-executed.
Real-Lina/browser remain NOT VERIFIED.

---

## REC-20 — Parent–Student Authorization
**Status:** DONE
**Gate B:** PASSED
**Purpose:** Require a verified Parent to reach a Student only through a local
Parent `User` and an explicit durable Parent/Student relationship.
**Completion note:** The existing `parent_student_relationships` table is now
enforced through one reusable application authorization boundary and a minimal
identity-summary proof route. Bootstrap linking is server-side only; no
browser-supplied Student ID can create or bypass access. Independent approval
is still required before Parent visibility work begins.
**Verification:** Isolated PostgreSQL contracts prove linked access, cross-parent
isolation, duplicate-link prevention, non-enumerating denial, and Student-path
isolation. No Parent dashboard or learning intelligence is exposed here.

---

## REC-21 — Disposable PostgreSQL Test Environment
**Status:** DONE
**Purpose:** Run the full Python suite against one migration-first, disposable
pgvector PostgreSQL database without development-data dependence.
**Completion note:** Canonical npm commands create a named local pgvector
container, require the exact `lina_learning_test` database plus an explicit
test flag, apply Alembic from zero, execute all Python tests, and remove the
container/volume. Existing per-test schema isolation remains intact. CI can use
the same runner against an externally managed pgvector service.
**Verification:** A clean migration and full Python run passed twice on the
disposable database; the test guard rejects any non-canonical database URL.

---

## REC-22 — AI Execution Lineage
**Status:** DONE
**Purpose:** Extend the existing Model Gateway ledger with compact,
identifier-only lineage for Tutor, Session Evidence, semantic extraction, and
embedding operations.
**Completion note:** Each gateway attempt now records its logical operation,
provider/model/usage outcome, and only safe domain identifiers. Tutor results
and same-call Candidate Events point to their execution; processing and index
runs are linked from their executions. Read-only helpers remain scoped by
Student or known application-owned run type. No prompt, response, raw vector,
trace backend, or dashboard was added.
**Verification:** Disposable PostgreSQL contracts cover operation attempts,
Tutor/Candidate, Session Evidence, semantic, index, and runtime-retrieval
lineage; cross-Student helper isolation is included. Independent approval is
required before Parent visibility work begins.

---

## REC-23 — Parent Content Status Read API
**Status:** DONE
**Purpose:** Give an explicitly linked Parent a compact, read-only view of
which Student content documents exist and whether their current retrieval
pipeline is uploaded, processing, ready, or failed.
**Completion note:** The Parent-only route first uses the REC-20 authorization
boundary, then reads a deterministic current lineage: newest structural run,
newest semantic run for that structural run, and newest index for that semantic
run. Historical runs remain internal and cannot make a newer pipeline appear
ready or failed. Responses expose only document identity, Grade/Subject,
compact stage states, and sanitized failure codes/messages.
**Verification:** Isolated PostgreSQL tests cover authorization isolation, no
content, every pipeline stage, current-lineage replacement, stale-index
protection, sanitization, deterministic ordering, and GET non-mutation.
**Independent approval:** Approved by Product Owner on 2026-08-22.

---

## REC-24 — Lina Validation Experience
**Status:** DONE
**Dependencies:** REC-23 independent approval
**Purpose:** Provide the smallest child-safe Grade 5 Math surface for validating
the existing authenticated Student session, real Tutor/SSE runtime, retrieval
grounding, session lifecycle, and invisible personalization behavior.
**Scope:** Student-only `/student` Math entry; child-safe readiness gate; existing
session/resume and streamed Tutor path; correct Tutor labeling; basic
loading/error/retry behavior. The Student response surface must not expose
Evidence, Patterns, model/provider data, source IDs, debug context, or safety
internals. No Science, Voice, Vision, Parent dashboard, Canvas, gamification,
or learning-engine behavior is included.
**Verification:** Focused Student/session/Tutor/readiness contracts; disposable
PostgreSQL full suite; web typecheck and configured production build; no
internal-data exposure in Student responses; `git diff --check`.
**Independent approval:** Approved by Product Owner on 2026-08-22.

---

## REC-24.1 — Lina Visual Calibration Pass
**Status:** DONE
**Dependencies:** REC-24
**Purpose:** Polish the Student Math validation surface for Lina before early
real-use calibration without changing any product/runtime capability.
**Implementation checkpoint:** `813afd27850c86780d1ada070565b4972d1f7d57`
**Independent approval:** Approved by Product Owner on 2026-08-22.

---

# Roadmap Track A — Core Simplification (2026-08-23)

Track A implements the Product Owner-approved Option A correction in
`docs/LEARNING_PRODUCT_ROADMAP.md`. It preserves the hybrid retrieval and
Learning Intelligence architecture while removing content/semantic readiness as
permission to learn. Track B remains a future Roadmap reference after Track A
and Real Lina calibration; it is not READY work here.

## REC-26 — Governing Decision Correction
**Roadmap:** LR-A01
**Status:** DONE
**Dependencies:** None
**Purpose:** Reconcile active governing documents with Roadmap Option A without
changing runtime code, schema, prompts, tests, or historical implementation
evidence.
**Verification:** Governing contradiction searches show no active book/semantic
Tutor gate or Current School Focus authority; Roadmap is discoverable; this
Track has LR-A02 as its only next READY item; REC-25 is blocked.

## REC-27 — Tutor Always Available
**Roadmap:** LR-A02
**Status:** DONE
**Dependencies:** REC-26
**Purpose:** Remove Student-facing content readiness as permission to open a
Math session or call the Tutor while preserving auth, ownership, SafetyDecision,
SSE, persistence, and empty-retrieval behavior.
**Verification:** A zero-book Student can enter Tutor and receive a safe model
answer with empty retrieval; existing protected runtime boundaries remain intact.
**Completion note:** The Student API and Student Math surface no longer treat
content readiness as a Tutor permission. Authenticated zero-content Students
open/resume their owned Math session, can persist messages, and can complete a
safe streamed Tutor turn with empty retrieval. Existing ownership and safety
redirect behavior remain enforced.

## REC-28 — Decouple Index Identity from Mandatory Semantics
**Roadmap:** LR-A03
**Status:** DONE
**Dependencies:** REC-27
**Purpose:** Make index identity support a completed structural run without a
mandatory semantic run, preserving provenance and migration safety.
**Completion note:** `ContentIndexRun` now permits an absent semantic run while
retaining document and structural-run provenance. A partial PostgreSQL unique
index prevents duplicate structural-only identities; the existing semantic-run
unique constraint remains unchanged. Downgrade removes only structural-only
derived index rows before restoring the historical NOT NULL contract; preserved
structural sources support a later rebuild. No index-building behavior changed.

## REC-29 — Structural-First Index Builder
**Roadmap:** LR-A04
**Status:** DONE
**Dependencies:** REC-28
**Purpose:** Build retrieval-ready structural blocks from completed structural
content without blind fixed-token-first chunking.
**Completion note:** The existing index builder now accepts a completed
structural run without semantic enrichment and creates source-linked,
lexical/pgvector structural blocks with nullable semantic lineage. Structural
item boundaries are retained unless one source exceeds the existing 2,000
character block limit; semantic-backed index behavior remains compatible.

## REC-30 — Semantic Retrieval Behavior Advisory
**Roadmap:** LR-A05
**Status:** DONE
**Dependencies:** REC-29
**Purpose:** Retain semantic metadata as optional ranking/navigation enrichment
without making it a core retrieval-candidate eligibility requirement.
**Completion note:** Semantic-type hints and CurrentFocus now only prefer
already-relevant lexical/vector candidates as deterministic RRF tie-breakers.
Structural blocks with null semantic/focus metadata remain eligible, while
semantic-backed expansion, context budgets, and exact provenance are unchanged.

## REC-31 — Source Processing Lifecycle
**Roadmap:** LR-A06
**Status:** DONE
**Dependencies:** REC-29
**Purpose:** Connect preserved source → structural processing → retrieval-ready
index through existing job boundaries; semantic enrichment remains independent.
**Completion note:** Parent upload now durably queues one idempotent structural
processing job. A completed structural run queues one idempotent structural-
index job, which builds the existing structural-first lexical/pgvector index
through the Model Gateway. Semantic extraction is not invoked; failures retain
structural/index provenance and use the existing job retry path.

## REC-32 — Parent Content-Status Decoupling
**Roadmap:** LR-A07
**Status:** DONE
**Dependencies:** REC-28, REC-31
**Purpose:** Present structural/index readiness separately from optional
semantic-enrichment outcome without expanding Parent scope.
**Completion note:** Parent content status now projects the grounding path from
the current structural run and any usable completed index for that run. Both
structural-only and semantic-backed indexes are READY; semantic status remains
visible as independent enrichment detail and cannot override usable grounding.

## REC-33 — Deprecate School-Focus Authority Residue
**Roadmap:** LR-A08
**Status:** DONE
**Dependencies:** REC-27, REC-30
**Purpose:** Remove school-position authority while retaining relevant recent
conversational/topic continuity.
**Completion note:** New Tutor Candidate Event metadata cannot emit
`current_focus_signal`; historical rows remain readable for audit and bounded
reprocessing. Current State no longer derives `current_school_focus`, and old
rows are excluded from runtime Card selection. Recent persisted topic metadata
remains optional conversational continuity, with relevance before recency.

## REC-34 — Simplification Acceptance Suite
**Roadmap:** LR-A09
**Status:** DONE
**Dependencies:** REC-27, REC-28, REC-29, REC-30, REC-31, REC-32, REC-33
**Purpose:** Verify zero-book availability, structural grounding, semantic
failure tolerance, empty-match Tutor behavior, and relevance-first intelligence.
**Completion note:** PostgreSQL acceptance coverage proves all eight Track A
scenarios together: zero-content Tutor use, empty retrieval, structural-only
grounding/provenance, optional semantic failure, relevant intelligence,
stale-school-focus exclusion, recent-topic continuation, and no school-position
authority. Protected Safety and one-primary-call boundaries remain covered by
the focused and full suites; the Candidate → Evidence wording is a completed
legacy/current implementation record superseded for future generations by
SEG-EVID-01.

## REC-35 — Real Lina Calibration Resumes
**Roadmap:** LR-A10
**Status:** DONE
**Dependencies:** REC-34
**Purpose:** Resume bounded Real Lina calibration after Track A acceptance; this
does not authorize Track B or frozen future capability work.
**Completion note:** Bounded real-Lina/manual Product Owner calibration resumed
successfully after Track A and surfaced actionable Tutor-experience findings.
REC-25 calibration remains blocked and is not complete.

## REC-35.1 — Tutor Child Interaction Calibration Pass
**Status:** DONE
**Dependencies:** REC-35
**Purpose:** Implement only the Product Owner-approved findings from the first
real Tutor calibration: age-appropriate concise Tutor interaction; an adaptive
explain → interact/check teaching rhythm; changed representation when the
Student remains confused; light, natural emojis; plain-text Grade-5 Math with
no raw Markdown or LaTeX; 0–4 dynamic suggested actions; free-text input that
remains available; action clicks through the existing Tutor turn path; and the
rule that self-reported understanding or button selection is not mastery
Evidence.
**Protected behavior:** Preserve one primary Tutor model call; Safety before
Tutor; optional grounding; provisional Candidate boundaries; failed-turn
durability; the 800-token budget; and `response.incomplete` handling.
**Explicit exclusions:** REC-25 execution; Track B; Science, Voice, Vision;
Learning Canvas / Artifact Engine; Parent Dashboard expansion; RAG/index
changes; DB migrations; and parked Prompt-v5/Eureka work.
**Completion note:** Product Owner browser acceptance at the current baseline
closed this calibration pass. Accepted scope: age-appropriate conversational
Tutor; explain → interact/check rhythm; changed representation when confused;
plain-text Grade-5 Math without raw Markdown/LaTeX; typed suggested actions
with free text retained; NAVIGATION vs ANSWER_CHOICE behavior; self-report or
button choice is not mastery Evidence; and one primary Tutor call.
**Verification note:** The review correction upgrades the response to
`tutor_turn_v3` structured `{label, kind}` actions, validates action clicks
against the latest persisted Tutor message, keeps NAVIGATION/self-reports
non-evidentiary, and bounds ANSWER_CHOICE Candidates. Focused Tutor/provider/
API/SSE/page-contract tests, Track A acceptance, the relevant PostgreSQL suite,
web typecheck/build, and a real `gpt-5.6-luna` equivalent-fractions diagnostic
passed. Product Owner browser acceptance completed the remaining review gate.
REC-25 remains blocked; the next approved task is REC-35.2.

## REC-35.2 — Adaptive Teaching Method Foundation
**Roadmap:** LR-D04A
**Status:** REVIEW
**Dependencies:** REC-35.1
**Purpose:** Implement TeachingMethod identity, an internal versioned registry,
same-call semantic Mode / Strategy / Method / prior-method-relation decision,
and source-grounded method observability while preserving one primary Tutor call
and the approved provisional Candidate → Segment Review → Session-authorized
Evidence architecture.
**Required boundaries:** TeachingStrategy and TeachingMethod remain distinct;
current behavior outranks history; semantic turn decisions belong to Luna in
the one primary call while runtime validates canonical values/lineage; a
selected method is not Evidence; the selected method must persist as
project-owned Tutor-turn metadata; and Segment Review must receive bounded
method, observable-outcome, concept/context, and audit-source lineage before
Session-authorized Evidence activation. Immediate representation switching is contextual adaptation, not
historical method ranking.
**Explicit exclusions:** LR-D04B longitudinal method learning; REC-25; Track B;
Science; Voice/STT; Vision; Learning Canvas; Interactive Artifact Engine;
Parent Dashboard expansion; RAG/index changes; semantic Prompt-v5/Eureka work;
new infrastructure; and any DB migration unless a blocker is discovered and
separately approved.
**Correction note:** Product Owner review identified a semantic-authority
mismatch in the current implementation: keyword/deterministic natural-language
routing currently chooses Mode, Strategy, Method eligibility, and confusion /
representation meaning. The approved correction requires Luna to make the joint
semantic Mode + Strategy + Method + prior-method-relation decision in the same
primary Tutor call, followed by deterministic validation, persistence, and
server-grounded Evidence lineage. The correction is implemented and verified by
focused contracts, the fresh PostgreSQL suite, and a bounded real-Luna
five-turn diagnostic: a changed method after `DID_NOT_HELP`, `NOT_RELEVANT`
for a topic switch, an immediate-method `EXPLICIT_REPEAT_REQUEST`, and all-null
casual-turn metadata. Product Owner browser acceptance remains the outstanding
review gate; this task remains REVIEW, not DONE. The Product Owner-approved
Lina Stabilization Gate below is now mandatory before this task can become
DONE.

### Lina Stabilization Gate — mandatory before REC-35.2 DONE

**Status:** ACTIVE
**Baseline:** `bda9ff4fe79c91a6ecde7b2aeb54e5103edd9ce5`
**Purpose:** Preserve the Product Owner-approved stabilization backlog from
real browser testing. These issues must not be reordered, merged, silently
closed, or used to start REC-25 or LR-D04B.

#### Stabilization TODO v2.1

| ID | Criticality | Status | Meaning / boundary | Dependency |
|---|---:|---|---|---|
| **CTX-01** — Recent Conversation Context Integrity | 5 | CLOSED | Original oldest-first displacement is closed. | Do not merge with CTX-02. |
| **ACT-01** — Quick Action Source-Context Robustness | 5 | CLOSED | Server-owned suggested-action source context is closed. | S1 original issues complete. |
| **OBS-01** — Browser / SSE Lifecycle Observability | 4 | CLOSED | Browser/SSE lifecycle trace is closed. | S2 complete. |
| **UI-01** — Terminal Tutor Turn Leaves UI Sending | 5 | CLOSED | Real S3 browser use completed with no hang and no refresh. | S2 complete. |
| **CTX-02** — Direct Conversation Continuity | 5 | CLOSED | The failed 1,200-character head+tail mechanism was replaced with Full Immediate Exchange while preserving exact Current Turn lineage. Focused/canonical automated verification and real-Luna beginning, middle, end, and faithful S3-style direct-continuity cases passed; browser verification was unavailable in the isolated worktree but was not required for this faithful backend/context regression. | Closed after independent review. |
| **SAFE-01** — Hands-on Activity Safety Follow-up | 5 | CLOSED | The rejected deterministic physical-hazard-policy hypothesis remains rejected: hard Product Safety restrictions remain upstream, while open-ended situational safety remains Luna/Tutor semantic behavior. One compact Tutor instruction prioritizes immediate real-world Student safety over continuing ordinary teaching/activity when warranted; SafetyPolicyService semantics, one primary Tutor call, and zero additional classifier/model calls are unchanged. Focused/relevant/canonical automated verification, four real `gpt-5.6-luna` safety situations, four isolated benign controls without material overreaction, and the low-information Immediate-Exchange case passed; independent closure review accepted it. Parent Boundary architecture is governed by the later SAFE-02 decision. | Closed. CTX-03 is next. |
| **SAFE-02** — Semantic Parent Boundaries in One Luna Tutor Call | 5 | ACCEPTED / CLOSED | Hard baseline safety remains deterministic and upstream. Same-primary-call Luna metadata determines semantic applicability while the server-owned Parent setting remains final authority; ambiguity is open/ALLOW, Biology/reproduction education remains age-appropriate ALLOW, and sexual content/behavior is separately restricted as `SEXUAL_CONTENT`. Redirects use constrained fragments/fallback, leak no ordinary Luna text, and persist audit metadata only—never Evidence or Learner Intelligence. Historical `HUMAN_REPRODUCTION` rows remain historical and are not reinterpreted. | Closed. No second classifier/model call. |
| **OUT-01** — Configurable Tutor Output Ceiling | 5 | CLOSED | Root cause verified: the normal Tutor payload hard-coded `max_output_tokens=800`. It now reads the positive server-only `TUTOR_MAX_OUTPUT_TOKENS` Setting, defaulting to 2000. This is an API completion ceiling, not a Student-facing verbosity target. The configured ceiling completed the approved 73-turn replay without output-incomplete results. | Closed. |
| **DATA-01** — Historical Tutor Message Persistence Gap | 5 | CLOSED / CURRENT DEFECT FIX ACCEPTED | Historical gap is high-confidence failed-stream behavior; the exact provider trigger remains unknown. Tutor deltas are provisional until terminal `event: turn`; reader error or non-terminal EOF removes only the current provisional Tutor bubble while retaining the durable Student message. Failed/partial Tutor output is never persisted as authoritative conversation. | Closed. Browser verification was unavailable without Clerk configuration; automated terminal-protocol verification passed. |
| **CTX-03** — Hybrid Segment Context Runtime | 5 | TECHNICAL CONTEXT RUNTIME VERIFIED / REAL-LINA VALIDATION DEFERRED | Current-Segment-only runtime: session-local Segment lineage and compact Structured Segment State are accepted; CTX-03C supplies complete immediate/recent/raw-semantic Exchange context from the latest Segment only, with temporary PostgreSQL/pgvector indexing and a shared query embedding. CTX-03D adds only a final deterministic capacity guardrail and private operational lineage; it does not re-rank relevance. Excludes prior-Segment reopening, prior-session/archive retrieval, memory service, retro-linking, extra classifier/summarizer calls, and external vector databases. | CTX-03E-A verified the technical runtime with real `gpt-5.6-luna` and `text-embedding-3-small`; Real-Lina validation remains deferred. |
| **ACT-02** — NAVIGATION vs ANSWER_CHOICE Semantic Misuse | 4 | ACCEPTED / CLOSED | Generic Suggested Action clicks and legacy `ANSWER_CHOICE` clicks are non-evidentiary. Only a validated latest persisted Guided Learning Check answer with exact choice membership can enter bounded Candidate processing; forged, stale, cross-session, and non-member responses are rejected. Runtime owns final authority validation. Configured production build/browser verification was not run because this isolated worktree has no valid Clerk publishable key; it is non-blocking for this backend Evidence-authority closure. | CTX-03E-A technical gate is complete; Real-Lina validation is deferred and does not block Stabilization Track B. |
| **CAND-01** — Confusion / Ambiguity Is Not Misconception | 4 | ACCEPTED / CLOSED | The strict Structured Output correction and source-grounded misconception protection are independently CODE REVIEW VERIFIED at `8efa6d5388c4d2e8599ea2a21cac0766a677e9b1`. Codex-reported focused/relevant and canonical Python execution: 544 passed, 5 skipped. Controlled real `gpt-5.6-luna` representative scenarios were run successfully by Codex through the Tutor/Model-Gateway path, not independently re-executed: confusion, a bare wrong answer, and an arithmetic slip did not become misconception signals; explicit wrong reasoning produced grounded `misconception-evidence-v1`. Turn-level Candidate remains provisional and Segment Review is the future durable semantic authority; this does not claim perfect turn-level Luna classification. | Accepted and closed. Real-Lina validation remains deferred and is not part of CAND-01 closure. |
| **EDU-ERR-01** — Educational Error Classification Foundation | 4 | APPROVED / DEFERRED | Future versioned domain-general plus domain-specific Educational Error Registry: Raw Segment → Segment Review → confirmed educational-error classification → Session-authorized Evidence → existing support/counter Pattern lifecycle → Learner Intelligence. No Error Memory subsystem and no new counters. Its prior SEG-EVID-01F blocker is cleared, but it is not the next action. | Deferred while the approved SCOPE-01 → SUBJ-01 product-boundary sequence proceeds. Do not implement in this commit. |
| **SCOPE-01** — Cross-Subject Conversation & Subject Policy | 3 | DONE / APPROVED | Approved governing cross-subject policy: one technical Session may contain multiple session-local Learning Segments with their own primary Broad Subjects; current Student intent outranks stale context; school context is optional/source-grounded. Governed by `docs/SUBJECT_SCOPE_POLICY.md`; this is policy clarification only, not Science production. | Closed by the approved policy. |
| **SUBJ-01** — Subject Attribution at Segment/Finding/Event Boundaries | 4 | DONE / CODE REVIEW VERIFIED / ACCEPTED | Segment Review v3 owns one primary Broad Subject; deterministic finalization propagates it through Event/Evidence and fail-closes conflicting Finding claims. Fresh retention history is prefiltered before Review input from only one coherent, non-authoritative v8 primary-Tutor-call provisional Broad Subject; missing, conflicting, unsupported, or ambiguous hints expose no history. Repeated v3 finalization is idempotent, and `extended_learning_event` requires source-grounded `EXTENDED` school context. Historical v2 remains audit-readable; no migration or extra normal-turn model call was introduced. | Independent GitHub review / Product Owner acceptance. Automated test execution remains CODEX-REPORTED; real Luna execution remains CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED and are not closure blockers. |
| **DEC-01** — Mode / Strategy / Prior-Relation Calibration | 3 | DONE / CODE REVIEW VERIFIED / ACCEPTED | The one-primary-call PriorMethodRelation contract contrastively distinguishes ordinary direct continuation/direct answers (`CONTINUATION`), explicit dissatisfaction (`DID_NOT_HELP`), explicit helped signals (`HELPED`), same-method repeat requests, true topic switches (`NOT_RELEVANT`), and null. `tutor_turn_v8` is unchanged; no keyword/regex router, extra classifier, or extra Tutor call was introduced. | Independent GitHub review / Product Owner acceptance. Automated tests remain CODEX-REPORTED; real Luna remains CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED and are not closure blockers. |
| **DEC-02** — TeachingMethod Attribution Fidelity | 4 | DONE / DEFECT NOT REPRODUCED / ACCEPTED | Bounded production-path diagnostic found no material false attribution between persisted `teaching_method_id` and the dominant visible Tutor representation. Legitimate registry overlap remains allowed; the bounded sample did not exercise SOCRATIC_FOCUS or SYMBOLIC_EXPLANATION. | Independent architecture/code review accepted. Automated tests remain CODEX-REPORTED; real Luna diagnostic remains CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED and are not closure blockers. |
| **REP-01** — Over-Practice / Repetition Control | 3 | REVIEW / IMPLEMENTED + AUTOMATED VERIFIED + REAL-LUNA VERIFIED | The primary Tutor guidance now asks Luna to avoid low-information near-identical practice after repeated, independently reasoned success on the same current idea, while preserving useful reinforcement for fragile, supported, uncertain, contradictory, recently repaired, or genuinely different work. No fixed threshold or new runtime authority was added. | Awaiting independent GitHub / Product Owner review. Automated verification is CODEX-REPORTED; bounded real Luna verification is CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED. Do not begin LANG-01. |
| **LANG-01** — Language Continuity | 3 | OPEN / STILL PRESENT | Numeric-only Student answers caused an English long-division thread to drift back to Arabic without an explicit language switch. | After REP-01. |
| **CAND-02** — Guided vs Independent Candidate Consistency | 3 | OPEN / STILL PRESENT | Equivalent learning behaviors alternate between guided_success and independent_success without a justified support difference. | Final C calibration after Tutor semantic/prompt changes. |
| **EVID-01** — Session Evidence Consolidation HTTPError | 5 | OPEN LEGACY DEFECT / REMOVED FROM NEW CRITICAL PATH | Three historical `session_evidence` HTTPErrors produced no completed LearningEvent, LearningEvidence, or session authority output; root cause remains unknown. | Investigate/fix under SEG-EVID-01E only if the legacy route remains required for compatibility/reprocessing. |
| **PERS-01** — End-to-End Personalization Validation | 5 | SUPERSEDED / ABSORBED INTO SEG-EVID-01F | SEG-EVID-01F proves Interaction → Segment Review → Session-authorized Evidence → State / Patterns → Card → later Tutor personalization. | Do not retain a duplicate validation gate. |
| **MATH-01** — Structured Math Readability | 4 | OPEN / CONFIRMED | Plain-text long-division alignment is not reliably readable in proportional chat rendering; a future minimal structured Math representation is needed. | Independent; do not unfreeze the Artifact Engine. |
| **ID-01** — Concurrent First-Identity Creation Race | 3 | OPEN / INVESTIGATION REQUIRED | One concurrent demo/session creation attempt returned duplicate-user HTTP 500. Lookup-then-create under DB uniqueness makes a race plausible, not proven. | Independent; exact reproduction/root cause before any fix. |

#### Approved dependency order

1. **A — Conversation & Safety Integrity:** CTX-02 CLOSED → SAFE-01 CLOSED →
   CTX-03 technical gate complete; Real-Lina final validation deferred.
2. **B — Interaction / Evidence Hygiene:** ACT-02 CLOSED → CAND-01 strict
   schema compatibility correction → SEG-EVID-01A → SEG-EVID-01B →
   SEG-EVID-01C → SEG-EVID-01D → SEG-EVID-01E → SEG-EVID-01F accepted
   → SCOPE-01 policy clarification approved → SUBJ-01 subject-attribution accepted
   → DEC-01 calibration accepted → DEC-02 TeachingMethod Attribution Fidelity
   accepted → REP-01 Over-Practice / Repetition Control (implementation awaiting independent review).
   EDU-ERR-01 remains approved but deferred; its prior F blocker is cleared.
3. **C — Tutor Semantic Calibration:** DEC-01 → DEC-02 accepted → REP-01 review → LANG-01
   → CAND-02 final.
4. **D — Evidence / Personalization:** legacy EVID-01 compatibility is
   considered under SEG-EVID-01E; PERS-01 is absorbed into SEG-EVID-01F.
5. **E — Independent Product / Platform:** MATH-01 and ID-01 are independent
   from the Evidence critical path and must not reorder A → B → C → D.

#### CTX-03 implementation slices

| Slice | Status | Scope |
|---|---|---|
| **CTX-03A** | ACCEPTED | Segment persistence + LearningMessage lineage foundation. |
| **CTX-03B** | ACCEPTED / LONG-CONVERSATION REAL-LUNA VERIFIED | Same-primary-Luna Segment relation + compact Structured Segment State. The 73/73 historical replay achieved the expected eight-Segment shape, exact major Human Gold boundaries, no fallback/output-availability failure, and safe invalid-State degradation. `UNCERTAIN` creates a new independent Ephemeral Segment without topic, reassignment, merge, or backfill. |
| **CTX-03C** | ACCEPTED | Recent raw complete Exchange context plus current-Segment-only semantic recall of older relevant complete Exchanges through existing PostgreSQL/pgvector embedding infrastructure. Full Immediate Exchange remains protected; relevance is structural and capacity is only the final guardrail. |
| **CTX-03D** | ACCEPTED | Final deterministic capacity guardrail plus private context lineage/observability. It measures the final serialized Tutor request and drops only whole optional units; protected overflow fails before the one primary Tutor call. |
| **CTX-03E-A** | TECHNICAL CONTEXT RUNTIME VERIFIED / REAL-LINA VALIDATION DEFERRED | Real-Luna / real-embedding technical Context v2 verification passed. Real-Lina validation remains deferred. |

#### Lifecycle and protected successful behavior

Every item follows `OPEN → ROOT CAUSE VERIFIED → FIX IMPLEMENTED →
VERIFICATION → CLOSED`. Automated tests alone never close an item: closing
evidence must include the original behavior or a faithful reproduction. CTX-01
must show that a short answer such as `B) 3` reaches Luna with its immediately
preceding Tutor question; UI-01 must leave the browser interactive after a
terminal Tutor turn without refresh; EVID-01 must produce the intended real
eligible-session Evidence path.

Protect one primary Tutor call; current Student behavior above history;
multilingual capability; dynamic suggested actions; bounded ANSWER_CHOICE
semantics with no mastery from a click alone; provisional-Candidate / durable
Evidence authority separation; server-grounded TeachingMethod lineage; actual method switching
after difficulty; WORKED_EXAMPLE → CONCRETE_EXAMPLE → VISUAL_REPRESENTATION
adaptation; zero-book Tutor availability; Safety before Tutor; and optional
grounding.

**Governance scope:** record the approved Stabilization TODO v2.1 only.
CTX-01, ACT-01, OBS-01, and UI-01 are CLOSED. Do not investigate or start
CTX-02 in this commit. Do not begin REC-25 or LR-D04B. REC-25 remains BLOCKED,
LR-D04B remains future/evidence-dependent, and Track B, Science production,
Voice, Vision, Learning Canvas, Interactive Artifacts, and Parent Dashboard
expansion remain frozen.

#### CTX-01 verification record

- **RED:** `test_recent_context_keeps_immediate_tutor_question_ahead_of_older_long_message`
  failed before production changes because the selected context retained the
  older long Tutor message and omitted the immediate 6 ÷ 2 Tutor question.
  `test_model_input_keeps_immediate_tutor_question_for_opaque_answer` also
  failed because that question was absent from the one-call model input.
- **Implemented invariant:** within the configured recent-message and
  character budget, selection prioritizes the newest contiguous conversation
  suffix. On the first non-fitting older message it stops, then returns the
  selected suffix in chronological order.
- **GREEN:** both regressions pass; `tests/test_tutor_context_postgres.py`
  passes (6); the relevant Tutor suite passes (61); the canonical disposable
  PostgreSQL Python suite passes (417 passed, 5 skipped).
- **Lifecycle:** CTX-01 is **CLOSED** following independent review of
  `60fa36415a52100cfa4f86489bf763c335182708`.

#### ACT-01 verification record

- **RED:** the resolution contract returned only `SuggestedAction`, and the
  Runtime did not accept a source Tutor message ID; the source-context and
  cross-session regression tests failed before production changes.
- **Implemented invariant:** a server-only `ResolvedSuggestedAction` carries
  the typed action plus the exact latest Tutor message ID. Runtime revalidates
  that exact ID as a Tutor `LearningMessage` in the active session, records it
  in the raw Student payload, and adds a bounded source block to the one Tutor
  call without changing Candidate or teaching semantics.
- **Lifecycle:** ACT-01 is **CLOSED** following independent review.

#### OBS-01 verification record

- **RED:** the Student surface had no lifecycle trace, and no browser-local
  trace module existed for the required bounded, private event contract.
- **Implemented invariant:** browser-local session storage retains only the
  last 75 operational events. Each accepted send uses a new opaque local trace
  ID; terminal Tutor event, EOF, and the existing later ready transition are
  recorded separately. Storage failures are ignored so Tutor interaction
  continues normally.
- **Lifecycle:** OBS-01 is **CLOSED** following independent review.

#### UI-01 verification record

- **RED:** a faithful server regression could read the terminal `turn` and,
  before that stream closed, find no persisted Tutor action from an independent
  database session. The page contract also showed `stream_eof` preceding the
  existing `ready` transition.
- **Implemented invariant:** the route buffers its final `TutorTurn`, commits
  the transaction, then emits one terminal event. A commit failure therefore
  emits no terminal event. The browser treats that durable event as the ready
  boundary but continues to drain the response reader; a later EOF or reader
  error cannot reverse a delivered durable turn to an error state.
- **GREEN:** Student/session and interrupted-stream tests pass (15); page
  contracts pass (5); the bounded lifecycle trace proves
  `terminal_turn_received → ui_ready → stream_eof` with delayed EOF (3);
  web typecheck and production build pass. The canonical full Python suite and
  committed-candidate browser trace remain required verification.
- **Lifecycle:** UI-01 is **CLOSED** following real S3 browser use with no hang
  and no refresh. The remaining stabilization work is recorded in TODO v2.1.

**Next action:** independent GitHub / Product Owner review of REP-01 —
Over-Practice / Repetition Control. Browser and Real-Lina validation remain
separate. Do not begin LANG-01, EDU-ERR-01, REC-25, LR-D04B, archive retrieval,
or frozen future capabilities before that review.

---

## REC-25 — Early Lina Calibration
**Status:** BLOCKED
**Dependencies:** REC-24.1, REC-34
**Purpose:** Run early real-Lina Grade 5 Math sessions against the approved
REC-24 validation surface and optional available grounding, inspect Tutor behavior,
retrieval, Evidence, Current State, Patterns, Decision Views, and cross-session
personalization, then calibrate only what observed usage justifies.
**Boundary:** This is calibration only. It does not authorize Science, Voice,
Vision, Canvas, Parent Dashboard expansion, Track B, or other frozen work.

---

# Phase 4 — Parent Basic Visibility & Control

## TASK-027A — Parent-managed Student Core Profile & Tutor Student Context
**Status:** BLOCKED
**Dependencies:** Phase 3 Exit Gate, explicit authorization after REC-24 review
**Purpose:** Let an authorized Parent/Admin create and manage durable factual child information, then make a compact authoritative Student Core Context available to the Tutor.
**Expected output:** Parent-managed child profile UI/API; authorization-safe Parent → Student ownership; date-of-birth-based age derivation; active Grade / GradePeriod linkage; compact Student Core Context for Tutor runtime; and removal of the hardcoded approximately-10-year-old Tutor assumption.
**Boundaries:** no Learner Intelligence or Evidence editing; no learning-style/personality labels; no transcript summary or memory service; no automatic inference of core-profile facts when Parent authority exists.
**Verification:** Parent can edit only owned child profiles; Tutor receives correct identity, derived age, and active Grade; age changes naturally from date of birth; another child's profile cannot leak; Core Profile changes do not mutate Evidence or Learner Intelligence; Tutor no longer relies on hardcoded approximately-10-year-old behavior.

## TASK-027 — Parent Overview and Math insight views
**Status:** BLOCKED  
**Dependencies:** TASK-027A, Phase 3 Exit Gate, explicit authorization after REC-24 review
**Purpose:** Let Parent understand current focus, important changes, learning state, and useful insights without surveillance-style activity counts.  
**Expected output:** Overview + Math views using categorical decision views and evidence-linked insights.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/intelligence`.  
**Verification:** no pseudo-precision percentages; evidence drill-down works; Lina-facing UI contains no analytics.  

## TASK-028 — Learner Profile / Pattern / Evidence audit views
**Status:** BLOCKED  
**Dependencies:** TASK-027  
**Purpose:** Make Patterns, recent changes, successful strategies, current state, and source Evidence inspectable by Parent.  
**Expected output:** Profile + Evidence views with provenance and lifecycle state.  
**Likely areas:** `/apps/web`, `/apps/api`.  
**Verification:** Parent can answer “why does the system think this?” from source-linked evidence.  

## TASK-029 — Parent Learning Boundaries UI
**Status:** BLOCKED  
**Dependencies:** TASK-008, TASK-027  
**Purpose:** Expose configurable family-topic boundaries while keeping protected safety non-overridable.  
**Expected output:** Settings UI for Allow / Age-appropriate only / Redirect to parent; initial Religion and human reproduction/sex education defaults set to Redirect to parent; a compact Parent-visible **Recent Redirects / Policy Audit** view for `REDIRECT_TO_PARENT` events, separate from Lina's Learner Profile.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/platform/safety`.  
**Verification:** setting change affects next relevant Tutor interaction without deployment; baseline safety cannot be disabled; recent redirects are visible with category/time and source/audit access on demand, and are not treated as Learner Intelligence.  

## TASK-030 — AI usage/cost and content status summary
**Status:** BLOCKED  
**Dependencies:** TASK-007, TASK-015, TASK-027  
**Purpose:** Give Parent/Admin enough visibility to inspect cost and processing health without a large admin analytics product.  
**Expected output:** monthly task-level cost summary, content readiness/reprocessing status, model-route visibility.  
**Likely areas:** `/apps/web`, `/apps/api`.  
**Verification:** totals reconcile with AI execution ledger; failed processing is visible; model route changes are auditable.  

---

# Mandatory Real Lina Decision Gate

## TASK-031 — Real Lina validation cycle
**Status:** BLOCKED  
**Dependencies:** TASK-027, TASK-028, TASK-029, TASK-030  
**Purpose:** Validate the actual product loop before expanding into new feature families.  
**Expected output:** Real-use review using Lina's actual Grade 5 Math book and repeated sessions; documented findings/corrections; explicit gate decision.  
**Likely areas:** no major code target; logs, transcripts, retrieval traces, Evidence/Patterns, Parent views.  
**Verification:** Product Owner records one of: `CONTINUE`, `CONTINUE_WITH_CORRECTIONS`, `DO_NOT_EXPAND_YET`.  
**Gate rule:** Phase 5+ tasks remain `BLOCKED` until `CONTINUE` or approved correction path is recorded.

---

# Future Phases — Blocked Until Real Lina Gate

## TASK-032 — Voice input / STT
**Status:** BLOCKED  
**Dependencies:** TASK-031 gate approval  
**Purpose:** Add microphone input, store transcript only, and route transcript through normal Tutor pipeline.  
**Verification:** raw audio is not retained after successful STT under current policy; transcript/source metadata preserved.  

## TASK-033 — Student image / handwriting / drawing understanding
**Status:** BLOCKED  
**Dependencies:** TASK-031 gate approval  
**Purpose:** Understand homework, handwriting, drawings, and diagrams while preserving student originals.  
**Verification:** uncertain visual interpretation triggers clarification; AI interpretation is derived and never replaces original work.  

## TASK-034 — Annotate original image first
**Status:** BLOCKED  
**Dependencies:** TASK-033  
**Purpose:** Return educational annotations on Lina's original image before reconstructing a clean visual when possible.  
**Verification:** annotations remain linked to original; source work is unchanged; annotation is not misclassified as student Evidence.  

## TASK-035 — Interactive Learning Artifact engine
**Status:** BLOCKED  
**Dependencies:** TASK-031 gate approval  
**Purpose:** Implement typed Artifact Specs, Registry, inline card, expandable Learning Canvas, and MVP renderers.  
**Likely areas:** `/services/learning_artifacts`, `/apps/web/components/learning-artifacts`.  
**Reuse check:** Before building a generic custom Artifact DSL/renderer layer, evaluate the current `@openmaic/*` DSL/renderer package family for package-level reuse. Record `ADOPT / PARTIAL ADOPT / REJECT` with rationale. Do not adopt OpenMAIC's multi-agent classroom/platform architecture. Preserve the approved React/SVG + Motion + JSXGraph + React Konva + MathLive renderer stack whether OpenMAIC is used or not.  
**Verification:** Reuse decision is recorded; Artifact failure falls back to Tutor; interactions can emit meaningful learning events; typed specs remain project-owned/replaceable; no unsandboxed arbitrary JS.  

## TASK-036 — Science content and Tutor module
**Status:** BLOCKED  
**Dependencies:** TASK-031 gate approval, stable content/tutor/intelligence contracts  
**Purpose:** Add Grade 5 Science without changing core Tutor architecture.  
**Verification:** Science is added via subject extension points; diagrams/figures work; factual verification policy respected.  

## TASK-037 — Retention and proactive in-app learning
**Status:** BLOCKED  
**Dependencies:** stable Intelligence after real usage  
**Purpose:** Add retention state/review scheduling and child-friendly proactive suggestions when Lina opens the system.  
**Verification:** no pressure/countdowns; old evidence is not erased; retention is distinguished from prior mastery.  

## TASK-038 — Grade transition card and next-Grade activation
**Status:** BLOCKED  
**Dependencies:** Grade transition need, stable Grade-local data  
**Purpose:** Parent activates Grade 6 books; system archives Grade 5 runtime state and carries only compact transition intelligence.  
**Verification:** no automatic Grade inference; full Grade 5 runtime is not injected into Grade 6; archive remains queryable/reprocessable.  

## TASK-039 — Light gamification / refinement
**Status:** BLOCKED  
**Dependencies:** validated Lina UX  
**Purpose:** Add only proven child-friendly celebrations/badges and polish.  
**Verification:** no leaderboard, pressure streaks, points economy, or analytics shown to Lina.  
