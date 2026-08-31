# TASKS.md — Lina Personal Learning System

## How to Use This File

- Codex should execute only tasks marked `READY` or the exact Product Owner-approved current track named by `project-state/PROJECT_STATE.md`.
- Normally complete one task at a time.
- A task becomes `DONE` only after its verification and required acceptance pass.
- Future-phase tasks may remain `BLOCKED` until dependencies and decision gates are satisfied.
- If implementation reality invalidates a task, update this file and `project-state/PROJECT_STATE.md`; do not silently improvise a new roadmap.
- Historical task text preserves provenance. A stale historical “next action” does not override the current governing task record below or `PROJECT_STATE.md`.

### Status Values

`READY` · `IN_PROGRESS` · `REVIEW` · `BLOCKED` · `DONE`

---

# Current Governing Documentation Track

## DOC-SYNC-01 — Product Truth & Governing Documentation Synchronization
**Status:** REVIEW  
**Criticality:** 4  
**Product Owner decision:** Structure approved; synchronized document content is awaiting Product Owner acceptance.  
**Purpose:** Remove current agent-execution risk caused by stale Phase-0, pre-SEG-EVID, obsolete Real-Lina, and historical-next-task wording while preserving approved architecture, product direction, task provenance, and frozen capability gates.  
**Canonical truth:** Lina Learning is a personal AI learning system whose differentiator is evidence-grounded longitudinal Learning Intelligence and relevant personalization. Limited Real-Lina use has occurred; stable daily/longitudinal Lina use remains unverified. The implemented accepted intelligence architecture is Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority.  
**Write scope:** `docs/PROJECT_REFERENCE.md`, `project-state/PROJECT_STATE.md`, `README.md`, `docs/LEARNING_INTELLIGENCE_SPEC.md`, `project-state/SYSTEM_MAP.html`, this task record.  
**Conditional correction scope:** `AGENTS.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/LEARNING_PRODUCT_ROADMAP.md` only where the read-only contradiction audit proves current governing drift.  
**Explicit exclusions:** runtime code, Tutor prompt/behavior, Learning Intelligence logic, API, database schema/migrations, Worker/deployment, `.replit`, Model Gateway implementation, Voice/Vision/Science implementation, Learning Canvas/Artifact Engine, Parent expansion, MATH-01, ID-01, EDU-ERR-01, REC-25, LR-D04B, and protected Eureka local work.  
**Verification:** (1) stable product truth is separated from current operational state; (2) Limited Real-Lina use is not confused with daily/longitudinal validation; (3) no current governing document describes SEG-EVID as unimplemented or makes legacy Session Evidence the current semantic authority; (4) no current governing source revives Current School Focus, mandatory curriculum semantics, Candidate-as-Evidence, second normal-turn classifier, or semantic Session summarizer; (5) Voice/Vision/Science/visual artifacts remain visible as approved-deferred rather than implemented/rejected; (6) current execution action lives in `PROJECT_STATE.md`/this task record rather than README/Roadmap; (7) protected local Eureka work is untouched.  
**Acceptance rule:** Authoring does not close this task. Stop for Product Owner review. Only explicit acceptance may change `DOC-SYNC-01` to `DONE / ACCEPTED` and promote `RL-01 — Real-Use Environment & Integrated Intelligence Loop Verification` as the next executable track.

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
**Purpose:** Support document processing, Segment Review, deterministic Session finalization, legacy Session Evidence compatibility, and rebuild work without Redis/Celery.  
**Expected output:** `jobs` table, worker loop, retry/failure status, idempotency hook.  
**Likely areas:** `/workers`, `/services/platform/jobs`.  
**Verification:** Test job moves pending → running → completed; failure is recorded; duplicate/idempotent execution behavior covered.  
**Completion:** Added a PostgreSQL-backed `jobs` table with database-enforced partial unique idempotency keys, transaction-safe `FOR UPDATE SKIP LOCKED` claiming, lease recovery, deterministic retry/failure recording, and an independent worker with `run_once`/`run_forever` and an explicit handler registry. Each claim has a fresh lease token, preventing a stale worker from settling a recovered job even if the worker identifier is reused. Verified on PostgreSQL with concurrent claiming, database constraints, lifecycle, retry/failure, recovery, stale-lease fencing, worker handling, migration downgrade/upgrade, and Alembic metadata checks.

## TASK-007 — AI execution ledger and Model Gateway skeleton
**Status:** DONE
**Dependencies:** TASK-003  
**Purpose:** Centralize model routing and usage/cost observability before Tutor calls exist.  
**Expected output:** task-based `ModelGateway` contract, route configuration model, `ai_executions` logging, provider adapter interface.  
**Likely areas:** `/services/model_gateway`, `/services/platform/observability`.  
**Verification:** Mock provider executes by task; model route can change without caller code change; usage/latency/success fields persist.  
**Completion:** Added a provider-neutral, task-routed Model Gateway backed by a durable PostgreSQL `ai_executions` ledger. A deterministic local provider supports fixtures and tests; callers use application task names while routes may change provider/model. The ledger records usage, latency, estimated cost, and success/failure without exposing provider SDKs to domain services.

## TASK-008 — Child-safety and Parent Learning Boundary configuration foundation
**Status:** DONE
**Dependencies:** TASK-003, TASK-004  
**Purpose:** Persist protected baseline policy version and per-student configurable topic boundaries.  
**Expected output:** policy service contract; topic catalog; Allow / Age-appropriate only / Redirect to parent persistence; protected categories not overrideable.  
**Likely areas:** `/services/platform/safety`, `/apps/api`, DB migrations.  
**Verification:** Parent can change configurable topic state; cannot disable baseline protection; audit metadata recorded; policy unit tests pass.  
**Completion:** Added a versioned, database-backed SafetyDecision boundary with the approved configurable topic states, protected baseline routing, calm redirect/age-handling directives, and compact policy audit records. Parent boundary changes are persisted per student and take effect at evaluation time; the protected baseline is not a configurable category.

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
**Completion:** Added PostgreSQL records for immutable Grade/subject source documents, versioned processing runs, Grade-local curriculum nodes, and source-linked content blocks. Original storage identity is distinct from all derived processing and each retrieval block traces to its source/run.

## TASK-010 — Parent Grade 5 Math book upload
**Status:** DONE
**Dependencies:** TASK-009, TASK-005  
**Purpose:** Let Parent/Admin upload Lina's real Grade 5 Math book while preserving the original source.  
**Expected output:** upload endpoint/UI, checksum, Grade/subject assignment, processing status.  
**Likely areas:** `/apps/web`, `/apps/api`, `/services/content`.  
**Verification:** Supported book upload persists original and metadata; invalid file is rejected; duplicate detection behavior documented.  
**Completion:** Parent/Admin-only API and shadcn-baseline intake UI accept PDF or Markdown source files with Grade/subject metadata. Immutable originals are checksum-addressed in private storage; invalid/mismatched files are rejected, and a same-student checksum duplicate returns the already preserved document rather than storing a second original. Initial status is visible as `UPLOADED`.

## TASK-011 — Docling adapter and normalized structural representation
**Status:** DONE
**Dependencies:** TASK-010, TASK-006  
**Recovery state:** Independently reviewed and accepted. The Docling adapter now emits a project-owned normalized tree and PostgreSQL stores explicit parent/child links, sibling and reading order, hierarchy depth, page/layout provenance, stable per-run item keys, captions, and differentiated text/table/picture/formula items. Structural processing is versioned by source, processor version, and settings version; prior completed runs remain intact. Controlled-fixture and local Eureka PDF verification passed. This is approval of the structural layer only; it is not Phase 1 or Production Engine Acceptance Gate approval.  
**Purpose:** Parse uploaded books using Docling and preserve hierarchy, pages, reading order, figures/tables/formulas/provenance where available.  
**Expected output:** versioned Docling processing adapter and normalized derived representation.  
**Likely areas:** `/services/content/docling`, `/workers`.  
**Verification:** Known fixture produces stable structure; page/source provenance is preserved; re-run is idempotent/versioned.  
**Implementation note:** The previous flattened `ContentBlock` projection is no longer the TASK-011 structural artifact. `document_structural_items` is the source-linked, versioned structural layer; retrieval blocks remain a blocked TASK-013 concern.

## TASK-012 — Educational semantic extraction
**Status:** DONE
**Dependencies:** TASK-011, TASK-007  
**Recovery state:** Rebuilt for review. The former heuristic Unit/Lesson/Exercise mapping has been replaced by a versioned Grade 5 Math semantic derivation from the TASK-011 structural tree. It uses the `CURRICULUM_SEMANTICS` Model Gateway route, validates a project-owned JSON contract and source/parent/coverage rules, and persists explicit semantic-to-structural source lineage. Controlled PostgreSQL fixture verification and a bounded real-Eureka (pages 1–2) Luna golden passed. This approves the semantic layer only; it does not approve TASK-013, Phase 1, or the Production Engine Acceptance Gate.  
**Purpose:** Convert structural document output into Grade 5 Math educational semantics without treating Docling structure as curriculum understanding.  
**Expected output:** Unit/Lesson/Concept/Objectives/Examples/Exercises mapping with source references and schema contract tests.  
**Likely areas:** `/services/content/semantics`, `/packages/schemas`, `/prompts`.  
**Verification:** Schema-valid output on real/fixture pages; source refs valid; no silent catastrophic duplication/missing-unit acceptance.

## TASK-013 — Structural content blocks and indexing
**Status:** DONE
**Dependencies:** TASK-012  
**Recovery state:** Reopened by the independent audit. The existing local embedding/demo ranking path is not verified as the required structural, lexical, and pgvector indexing contract. Rebuilt for review using versioned semantic/structural blocks, a 1536-dimensional Model-Gateway embedding route, PostgreSQL TSVECTOR lexical index, and pgvector HNSW cosine index. Prior index runs remain preserved across new identities and failed builds.  
**Purpose:** Build retrievable semantic/structural units with metadata, lexical index, and embeddings without blind fixed-token-first chunking.  
**Expected output:** content-block creation, Docling hierarchical/hybrid refinement where needed, lexical + pgvector indexing using the selected retrieval-plumbing path.  
**Likely areas:** `/services/content`, `/services/retrieval`.  
**Reuse decision:** **ADOPT native Docling + PostgreSQL/pgvector; REJECT LlamaIndex for TASK-013.** TASK-011/012 already provide project-owned, source-linked structure and semantics; native PostgreSQL indexes preserve that lineage and metadata filtering without another retrieval framework. Re-evaluate only if TASK-014 golden retrieval shows a concrete gap.  
**Verification:** Reuse decision is recorded; definitions/examples/figures remain source-linked; Grade/Subject/Focus metadata remains controllable; oversized blocks refine without losing hierarchy; index rebuild works.

## TASK-014 — Hierarchical/hybrid retrieval service
**Status:** DONE
**Dependencies:** TASK-013  
**Recovery state:** Rebuilt for review using bounded PostgreSQL lexical and pgvector candidate queries, deterministic reciprocal-rank fusion, optional Grade/Subject/Unit/Lesson/Concept narrowing, semantic-parent expansion, exact source provenance, and a context budget. A local real-Eureka pages 1–2 golden set passed 7/7 cases (terminology, paraphrase, example, exercise, figure, with-focus, and without-focus). This approved retrieval layer does not by itself pass Phase 1 or the Production Engine Acceptance Gate.  
**Purpose:** Retrieve Grade/Subject/Focus/Concept-relevant Math context using metadata + lexical + vector ranking over the retrieval approach selected in TASK-013.  
**Expected output:** retrieval API/service with context budget and source provenance.  
**Verification:** Golden questions return intended lesson/pages/content types with acceptable reliability; project-owned filtering, provenance, context budgets, and rebuildability remain intact.

## TASK-015 — Minimal Content Admin and reprocess action
**Status:** BLOCKED
**Dependencies:** TASK-011, TASK-014  
**Recovery state:** Reopened by the independent audit. API endpoints exist, but the required Parent/Admin status page and reprocess visibility are incomplete. Blocked until the structural and retrieval contracts are verified.  
**Purpose:** Show Parent/Admin content readiness and allow versioned reprocessing from the preserved original.  
**Expected output:** book status page, processing version, failures, reprocess action.  
**Verification:** Reprocess creates a new derived run without replacing original; status/failure is visible.

### Phase 1 Exit Gate
**Historical gate, superseded as a Tutor permission gate by Roadmap Track A.** A real Grade 5 Math book and retrieval golden set remain useful grounding validation. They no longer authorize Student Tutor availability, which works with zero content and optional retrieval.

---

# Phase 2 — Math Tutor Vertical Slice

## TASK-016 — Session/thread and Student Math entry flow
**Status:** DONE
**Dependencies:** Phase 1 Exit Gate  
**Recovery state:** Rebuilt for review as the authenticated production path at `/student`, separate from the development-only sandbox. A verified Clerk Student identity resolves to an application-owned Student profile; the browser never supplies `student_id` as authority. The path creates or resumes one open Math session, persists ordered Student messages, restores history on refresh, and prevents cross-Student reads/writes. It intentionally does not run Tutor or automatic session-close behavior; those remain TASK-017 through TASK-020.  
**Purpose:** Let Lina start a natural Math session and change threads/topics without managing internal structure, using a child-appropriate visual shell rather than a generic developer chat UI.  
**Completion note:** The existing `assistant-ui` reuse decision remains `REJECT` for this small project-owned persistence path; PostgreSQL API tests cover first visit, open/resume, ordered persistence and refresh, ownership isolation, and no close side effect; the Student screen calls `/api/v1/student`, never `/api/v1/demo`.

## TASK-017 — Tutor context builder and retrieval integration
**Status:** DONE
**Dependencies:** TASK-016, TASK-014  
**Recovery state:** Rebuilt for review as a deterministic, model-free context boundary. It keeps the current Student question authoritative; includes bounded relevant session/Segment context; uses TASK-014 as curriculum boundary; and selects only relevant active State/Patterns. Historical intelligence remains advisory and never teaching authority.  
**Purpose:** Build compact Tutor context from current turn, optional grounding, conversation continuity, and later-compatible intelligence slots.

## TASK-017A — Safety & Learning Boundary Policy Engine
**Status:** DONE
**Dependencies:** TASK-017, TASK-008  
**Purpose:** Enforce non-overridable child-safety baseline and Parent Learning Boundaries as explicit runtime policy rather than prompt-only behavior.  
**Completion note:** Deterministic hard baseline and server-owned Parent settings remain final. Later SAFE-02 accepted same-primary-call semantic Parent Boundary applicability while preserving server enforcement.

## TASK-018 — Text Tutor runtime with streaming
**Status:** DONE
**Dependencies:** TASK-017A, TASK-007  
**Purpose:** Deliver Grade 5 Math teaching through one primary Tutor call and SSE streaming, consuming approved safety/boundary decisions.  
**Completion:** Production boundary persists Student message, consumes safety, builds approved context, streams one Tutor task, persists completed response and lineage, and serves provider-produced SSE.

## TASK-019 — Candidate Event metadata contract
**Status:** REVIEW
**Dependencies:** TASK-018  
**Historical status note:** Later CAND-* stabilization and SEG-EVID acceptance supersede Candidate-as-durable-authority assumptions; Candidate metadata remains provisional only.  
**Purpose:** Let the same Tutor call flag source-linked candidate observations without writing stable learner conclusions.

### Phase 2 Exit Gate
**Historical gate, superseded as a content-readiness dependency by Roadmap Track A.** Text Tutor operates with zero content or optional grounding. Limited real-Lina interaction later occurred; stable daily/longitudinal use is a separate current verification horizon.

---

# Phase 3 — Learning Intelligence Core

> **Historical task records below describe the implementation evolution. The current accepted architecture is Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority; legacy Session Evidence is compatibility/history, not current primary semantic authority.**

## TASK-020 — Automatic session-close lifecycle
**Status:** DONE
**Purpose:** Close sessions after configurable inactivity/grace and trigger durable background intelligence work.

## TASK-021 — Session Evidence consolidation
**Status:** DONE — HISTORICAL LEGACY PATH
**Purpose:** Historical Session Evidence implementation retained for compatibility/audit where required. It is superseded as the primary current semantic review boundary by SEG-EVID.

## TASK-022 — Current Learning State engine
**Status:** DONE
**Purpose:** Represent temporary active learning state distinctly from stable Patterns.

## TASK-023 — Deterministic Pattern engine and scope lifecycle
**Status:** DONE
**Purpose:** Govern Pattern identity, frequency/recency/counter-evidence, scope, lifecycle, and recurrence deterministically.

## TASK-024 — Compact Learner Intelligence Card and Tutor selector
**Status:** DONE
**Purpose:** Select bounded relevant authorized State/Patterns for later Tutor context without full-history injection.

## TASK-025 — Derived mastery/confidence views
**Status:** DONE
**Purpose:** Produce categorical, versioned decision views without converting them into source learner truth.

## TASK-026 — Intelligence reprocessing pipeline
**Status:** DONE
**Purpose:** Rebuild/version derived intelligence from preserved raw history with safe authority replacement and auditability.

### Phase 3 Exit Gate
Accepted technical/full-system work demonstrates auditable Segment Review → Session-authorized Evidence → State/Patterns/Card → later personalization paths. Stable recurring natural Lina use remains a separate verification horizon.

## SEG-EVID-00 — Governing Documentation Alignment
**Status:** DONE — HISTORICAL

## Full-System Acceptance — Learning Intelligence
**Status:** DONE / ACCEPTED
**Purpose:** Prove the governed path from raw conversation through Segment Review, Session-authorized learning intelligence, and later Tutor personalization under isolated acceptance conditions.  
**Accepted architecture:** **Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority.**  
**Evidence-label rule:** Codex-reported automated/database/real-model evidence, independent code review, browser evidence, limited Real-Lina use, stable daily Lina use, and longitudinal Lina validation are distinct categories.

## SEG-EVID-01A — Governing Contracts & Persistence
**Status:** DONE / ACCEPTED

## SEG-EVID-01B — Segment Completion & Review Jobs
**Status:** DONE / ACCEPTED

## SEG-EVID-01C — Segment Semantic Reviewer
**Status:** DONE / CODE REVIEW VERIFIED / ACCEPTED

## SEG-EVID-01D — Session Finalization & Intelligence Activation
**Status:** DONE / CODE REVIEW VERIFIED / ACCEPTED

## SEG-EVID-01E — Reprocessing & Authority Compatibility
**Status:** DONE / CODE REVIEW VERIFIED / ACCEPTED

## SEG-EVID-01F — Real Model & Multi-Session Verification
**Status:** DONE / CODE REVIEW VERIFIED / ACCEPTED
**Boundary:** Accepted technical/system verification does not itself equal stable daily or longitudinal Real-Lina verification.

---

# Stabilization / Calibration History

The following task IDs are preserved as durable historical evidence and accepted decisions. They are not current executable work merely because they appear here.

| ID | Status | Current governing meaning |
|---|---|---|
| REC-20 | DONE | Parent–Student authorization foundation |
| REC-21 | DONE | Disposable PostgreSQL test environment |
| REC-22 | DONE | AI execution lineage |
| REC-23 | DONE | Parent Content Status read API |
| REC-24 | DONE | Lina validation experience |
| REC-24.1 | DONE | Lina visual calibration pass |
| REC-26 / LR-A01 | DONE | Option A governing correction |
| REC-27 / LR-A02 | DONE | Zero-book Tutor availability |
| REC-28 / LR-A03 | DONE | Structural-first index identity |
| REC-29 / LR-A04 | DONE | Structural-first index builder |
| REC-30 / LR-A05 | DONE | Semantic retrieval advisory |
| REC-31 / LR-A06 | DONE | Source processing lifecycle |
| REC-32 / LR-A07 | DONE | Parent content-status decoupling |
| REC-33 / LR-A08 | DONE | Current School Focus authority removed |
| REC-34 / LR-A09 | DONE | Simplification acceptance |
| REC-35 / LR-A10 | DONE | Limited Real-Lina/manual calibration resumed |
| REC-35.1 | DONE | Tutor child interaction calibration |
| REC-35.2 / LR-D04A | Historical review/accepted foundation context | Later DEC/REP/LANG/CAND tasks carry accepted semantic calibration state |
| CTX-01 | CLOSED | Recent conversation integrity |
| ACT-01 | CLOSED | Suggested-action source context |
| OBS-01 | CLOSED | Browser/SSE lifecycle observability |
| UI-01 | CLOSED | Terminal Tutor turn UI readiness |
| CTX-02 | CLOSED | Direct conversation continuity |
| SAFE-01 | CLOSED | Hands-on/situational safety guidance |
| SAFE-02 | ACCEPTED / CLOSED | Same-primary-call semantic Parent Boundary applicability + server final authority |
| OUT-01 | CLOSED | Configurable Tutor output ceiling |
| DATA-01 | CLOSED | Failed-stream Tutor-message persistence behavior |
| CTX-03 | TECHNICAL RUNTIME VERIFIED | Real-Lina longitudinal/daily validation separate |
| ACT-02 | ACCEPTED / CLOSED | Generic Suggested Actions non-evidentiary; Guided Check bounded |
| CAND-01 | ACCEPTED / CLOSED | Confusion ≠ misconception; grounded misconception semantics |
| SCOPE-01 | DONE / APPROVED | Cross-subject Session/Segment policy |
| SUBJ-01 | DONE / ACCEPTED | Reviewed Broad Subject durable attribution |
| DEC-01 | DONE / ACCEPTED | PriorMethodRelation calibration |
| DEC-02 | DONE / ACCEPTED | TeachingMethod attribution diagnostic accepted |
| REP-01 | DONE / ACCEPTED | Over-practice/repetition control |
| LANG-01 | DONE / ACCEPTED | Language continuity |
| CAND-03 | DONE / ACCEPTED | Candidate schema/runtime constraints |
| CAND-02 | DONE / ACCEPTED | Guided vs independent Candidate semantics |

### Limited Real-Lina clarification

Historical rows that said `REAL-LINA = NOT VERIFIED` reflected the evidence label at that earlier task closure and remain historical provenance. The current Product Owner has clarified that Lina herself did participate in part of a real Tutor interaction and that the persisted interaction was later continued for testing/calibration. This establishes **LIMITED Real-Lina use**, not stable daily or longitudinal validation.

---

# Independent Open / Deferred Tracks

## MATH-01 — Structured Math Readability
**Status:** OPEN / CONFIRMED  
**Criticality:** 4  
**Reality:** Plain-text long-division alignment is unreliable in proportional chat rendering.  
**Boundary:** Future fix must use the smallest useful reusable structured Math representation. It does **not** unfreeze Learning Canvas or the full Artifact Engine.

## ID-01 — Concurrent First-Identity Creation Race
**Status:** OPEN / INVESTIGATION REQUIRED  
**Criticality:** 3  
**Reality:** One concurrent first-identity flow produced a duplicate-user HTTP 500; lookup→create race is plausible but root cause is unproven.  
**Boundary:** Reproduce/root-cause before fix. Not automatically a blocker for private initial Lina use.

## EDU-ERR-01 — Educational Error Classification Foundation
**Status:** APPROVED / DEFERRED  
**Criticality:** 4  
**Boundary:** No Error Memory subsystem/new counters; do not implement without explicit promotion.

## REC-25 — Early Lina Calibration
**Status:** BLOCKED  
**Boundary:** Historical calibration track remains blocked; current Real-Lina operational/product learning work must be explicitly promoted through current state rather than silently reviving this record.

## LR-D04B — Method Outcome Learning
**Status:** DEFERRED / EVIDENCE-DEPENDENT  
**Boundary:** Requires sufficient trustworthy real TeachingMethod outcome Evidence and explicit Product Owner promotion.

## EVID-01 — Legacy Session Evidence HTTPError
**Status:** OPEN LEGACY DEFECT / REMOVED FROM NEW CRITICAL PATH  
**Boundary:** Investigate only if legacy compatibility/reprocessing requires it.

---

# Approved Future Product Capabilities — Frozen Until Promotion

These are intentional product directions, not executable tasks by default:

- Science production support,
- Voice / STT,
- Vision / photographed homework/page/work,
- handwriting/drawing interpretation and governed Evidence,
- annotated original + clean reconstruction,
- visual/interactive Learning Artifacts,
- Learning Canvas,
- broader Parent Evidence/Intelligence UX,
- Parent-managed Student Core Profile/onboarding,
- Grade-transition production,
- Trusted Educational Reference pilot,
- later retention/proactive learning,
- later additional subjects/languages.

Do not infer that “not required for current proving ground” means “optional/unnecessary to the intended product.”

---

# Historical Future-Phase Task IDs

The following older IDs are retained for provenance but remain `BLOCKED` unless a newer explicitly approved task promotes their capability:

- `TASK-027A` Parent-managed Student Core Profile & Tutor Student Context
- `TASK-027` Parent Overview and Math insight views
- `TASK-028` Learner Profile / Pattern / Evidence audit views
- `TASK-029` Parent Learning Boundaries UI
- `TASK-030` AI usage/cost and content status summary
- `TASK-031` historical Real Lina validation gate
- `TASK-032` Voice input / STT
- `TASK-033` Student image / handwriting / drawing understanding
- `TASK-034` Annotate original image first
- `TASK-035` Interactive Learning Artifact engine
- `TASK-036` Science content and Tutor module
- `TASK-037` Retention and proactive in-app learning
- `TASK-038` Grade transition card and next-Grade activation
- `TASK-039` Light gamification / refinement

Their old dependencies/order are historical planning context and do not override `PROJECT_REFERENCE.md`, `LEARNING_PRODUCT_ROADMAP.md`, `PROJECT_STATE.md`, or a newer Product Owner-approved bounded implementation spec.
