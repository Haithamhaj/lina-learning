# Lina — Active Execution Queue

This file contains the **current** execution queue. Historical implementation task lists belong under docs/history or retained closure and evidence documents.

An explicit current Product Owner instruction authorizes work. A task appearing here is not automatic authorization for protected changes, production deployment, paid provider evaluation, or data migration.

## Current state

The core Tutor, learner-context, Learning Intelligence, Student-source, Studio and Canvas, and live deployment foundations are implemented.

The current phase is **real-use repair and recalibration**. Controlled natural use is temporarily paused after the first real Lina sessions exposed blocking/important repair items; resume only after the agreed repair batch is locally accepted and deployed.

## 1. LIVE-VALIDATION-01 — Controlled natural use

**Status:** PAUSED AFTER E30 REAL-USE FINDINGS

**Purpose:** Use Lina naturally and capture real defects and behavior before additional architecture work. This activity is currently paused while the E30 repair/recalibration batch is defined and implemented.

**Expected output:**

- real conversation evidence;
- real Canvas behavior;
- recovery and session evidence;
- actual latency observations;
- new tracker items only when evidence supports them.

**Likely areas:** production logs and DB, docs/TUTOR_CANVAS_REPAIR_TRACKER.md, project-state/PROJECT_STATE.md.

**Verification required:**

- distinguish product defect from model variation;
- distinguish live or provider behavior from synthetic fixtures;
- no product patch during initial observation unless a blocker prevents testing.

**Depends on:** deployed App and Worker.

## 1A. REAL-USE-REPAIR-01 — E30 repair and recalibration batch

**Status:** APPROVED / IN PROGRESS — R01 AND R02 LOCALLY CLOSED; LATER SLICES PENDING

**Implementation spec:** `docs/REAL_USE_REPAIR_01_IMPLEMENTATION_SPEC.md`

**R01 local result:** SOURCE-STREAM-01 passes focused and affected PostgreSQL tests, including the shared-stream scope review (E31-E33 in the repair tracker). Authenticated browser and deployed real-use acceptance remain pending; this does not advance R02 or the rest of the batch.

**R02 local result:** VOICE-STT-01 has a bounded browser recorder lifecycle, editable transcript/Send recovery, explicit JSON file-transcription request, safe provider failure categories, and a distinct no-speech response. Local Chrome, provider contracts, PostgreSQL, TypeScript, and broad regression passed apart from two documented baseline failures (E34). The actual Lina STT adapter and Model Gateway then transcribed synthetic WAV and WebM through the authorized `MODEL_API_KEY`, twice each, with HTTP 200, JSON `text`, and one successful disposable AI execution per attempt (E35). The cause of E30's five historical 502 responses cannot be reconstructed from this current success. Authenticated/deployed Lina acceptance remains pending.

**R03 local result:** CORE-PROFILE-BOOTSTRAP-01 has a preview-first operator command that updates only an exact existing Student's display name, DOB, and active GradePeriod through existing Core Profile services (E36). Disposable PostgreSQL proves preview rollback, idempotent apply, bounded Tutor context/model input without raw DOB, and no Parent/Personal Facts/Evidence/Pattern/AI execution writes. The known date-dependent Parent Grade test remains a separate baseline failure. At E36, no production data had been changed; the later approved application is recorded below. R04 is not started.

**R03 production data result:** With the Product Owner's explicit approval and supplied values, the operator command applied Lina's Core Profile to the exact existing Clerk Student (E37). Independent read-only production verification found one active GradePeriod, no Parent relationship or Personal Fact, and the existing Tutor context/model payload projected `display_name=لينا`, `age_years=9`, and `grade_level=5` without raw DOB. No model call, new Tutor turn, deployment, commit, or push occurred; live learner-facing use remains to be verified. R04 is not started.

**Current tracker scope:**

- SOURCE-STREAM-01;
- VOICE-STT-01;
- VISUAL-CHOICE-01;
- CORE-PROFILE-BOOTSTRAP-01;
- MEMORY-LIVE-01 acceptance;
- LI-CALIBRATION-01;
- STRATEGY-FIDELITY-01;
- MODEL-GPT6-01;
- COST-RATE-01.

**Purpose:** Correct the first real-use defects before further natural Lina testing, without reopening settled architecture.

**Scope rules:**

- preserve Primary Tutor, Evidence, Personal Facts, Core Profile, Studio, and Safety authority boundaries;
- use the current Canvas capability for proactive visual teaching before treating generated images as a required workaround;
- keep raw Evidence/provenance even when downstream LI calibration is weakened;
- migrate model routing intent rather than flattening every route to one model;
- evaluate each JEV decision slice separately.

**Verification required:**

- focused deterministic regressions for every changed contract;
- affected PostgreSQL tests;
- real provider checks for STT and GPT-6;
- actual browser proof for source/voice/Canvas-visible behavior;
- full affected regression before deployment;
- controlled Lina retest only after deployment.

## 2. TEACH-FLOW-01 — Teaching-flow integrity

**Status:** READY AFTER LIVE EVIDENCE REVIEW

**Tracker scope:**

- CONV-MOMENTUM-01
- STRATEGY-FIDELITY-01
- PED-ADAPT-01

**Purpose:** Make learner-visible teaching behavior match declared teaching semantics.

**Expected output:**

- unfinished guided learning leaves a useful next affordance when appropriate;
- EXPLAIN_THEN_CHECK contains an actual learner check when that strategy is selected;
- genuine DID_NOT_HELP causes a substantively different method or representation;
- legitimate targeted clarification is not misclassified as method failure.

**Likely areas:** services/tutor/runtime.py, teaching-decision contracts and tests, runtime/tutor/visual-guidance-v2.md.

**Verification required:**

- cross-subject fixture scenarios;
- no forced question after every answer;
- no new fixed teaching flow;
- live follow-up after local acceptance.

**Protected:** do not change Learning Intelligence semantics as a shortcut.

## 3. JEV-EVAL-01 — Bounded decision quality evaluation

**Status:** ACTIVE DATA COLLECTION

**Purpose:** Evaluate JEV where Lina already uses bounded decisions.

**Current decision slices:**

1. Visual Personalization fact selection.
2. Exact Canvas reuse selection.
3. Segment rubric comparison.
4. Visual Need decision — new repair-release slice; existing three semantic roles/modes remain unchanged.

**Expected output:**

- agreement and disagreement counts;
- representative disagreement cases;
- probability distributions;
- latency and cost;
- false-positive and false-negative patterns;
- recommendation per slice: retain current role, expand, narrow, or remove.

**Likely areas:** ai_executions, Canvas audit metadata, segment rubric decision records, and evaluation reporting.

**Verification required:**

- do not compare only synthetic examples;
- keep each decision slice separate;
- no authority expansion merely from popularity or a small sample.

**Blocked by:** enough real cases.

## 4. PERF-UX-01 — Tutor latency and buffering

**Status:** OPEN

**Tracker scope:** PERF-01, UX-BUFFER.

**Purpose:** Identify which phase creates learner-visible waiting.

Measure separately:

- context assembly;
- Primary Tutor provider time;
- bounded decision calls;
- terminal validation;
- persistence;
- proxy and SSE delivery;
- Canvas worker composition.

**Expected output:** phase-level latency evidence and one bounded recommendation.

**Do not:** redesign One Call or multi-call architecture before measurement.

## 5. PERSONALIZATION-RELEVANCE-01 — Relevance calibration

**Status:** IN REVIEW

**Purpose:** Prevent optional learner context from feeling forced or repetitive.

**Expected output:**

- identify repeated Personal-Fact use;
- verify source lineage;
- distinguish valid continuity from decorative insertion;
- tune selection only after multiple real cases.

**Protected:** Personal Facts must not become Learning Evidence or ability inference.

## 6. E2E-LIVE-01 — Real Tutor to Canvas acceptance

**Status:** IN REVIEW

**Purpose:** Continue validating the real deployed end-to-end path.

Expected path:

    Student
    → Primary Tutor
    → Canvas brief
    → Worker / Canvas
    → visible Scene
    → truthful Student action
    → Studio
    → same Primary Tutor

**Must observe:**

- graph and visual correctness;
- answer-hiding correctness;
- one foreground lane;
- recovery, reload, and retry behavior;
- no interaction storms;
- no false claim that a visual is visible;
- useful natural teaching continuation.

## 7. IMG-V2-01 — Educational generated images

**Status:** PLANNED / NOT YET IMPLEMENTATION-AUTHORIZED

**Current agreed direction:**

- distinct capability;
- Science first;
- eligible need: shape, structure, process, or scene;
- structured Canvas remains Math-first;
- Canvas delivery;
- educational annotated output by default when useful;
- 10 successful visible generated images per learner per day;
- failed or invisible retries do not count;
- quota resets at learner-local midnight.

**Remaining before implementation:**

- provider and model;
- questionable-output rejection and retry behavior;
- quota persistence and enforcement;
- exact annotation and delivery contract;
- acceptance plan.

## 8. AUTH-01 — Initial Daily auth refresh issue

**Status:** DEFERRED

Resolve only when it materially affects controlled use.

Do not mix it with Tutor or Canvas pedagogy work.

## 9. CALLS-01 — Foreground/background call responsibility study

**Status:** DEFERRED

When resumed, study:

- which background calls add real value;
- trivial-session suppression;
- candidate metadata responsibility;
- cost and latency;
- whether any call can move out of the foreground safely.

Do not start from a target call count.

## Completed foundations

The following are not active queues:

- Learning Intelligence core;
- Personal Facts and Core Profile;
- Student-source pipeline;
- Studio durable state;
- Agentic and Full-Power Canvas foundations;
- custom visual sandbox;
- reusable visual registry;
- REUSE, ADAPT, and CREATE;
- Tutor and Canvas repair slices E24 and E28;
- live App and Worker deployment baseline;
- JEV bounded-decision integration.

See docs/history, closure documents, and docs/TUTOR_CANVAS_REPAIR_TRACKER.md for detailed evidence.

## Verification baseline

For code changes:

- focused tests first;
- affected PostgreSQL tests;
- TypeScript typecheck when web is touched;
- actual browser proof for learner-visible visual behavior;
- python3 scripts/check_repository_truth.py;
- git diff --check;
- broader suite near closure when justified.

Always report unrun gates explicitly.
