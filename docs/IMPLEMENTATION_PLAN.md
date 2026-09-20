# Lina Personal Learning System — Implementation Plan

## Status

**Current technical architecture and execution direction.**

This document describes the system that exists now. Historical Canvas closure, hardening, review, and branch-specific implementation documents remain evidence of how the system was built; they are not current execution authority.

## 1. Architectural stance

Lina is a modular monolith.

The current architecture intentionally avoids microservices and standing subject-agent fleets.

    Browser
      ↓
    Next.js
      ↓
    FastAPI application
      ├─ Tutor
      ├─ Student Sources
      ├─ Content / Retrieval
      ├─ Studio / Canvas
      ├─ Personal Facts / Core Profile
      ├─ Learning Intelligence
      └─ bounded Decision Services
            ↓
    PostgreSQL + pgvector / Object Storage / Background Worker
            ↓
    Model Gateway
      ├─ OpenAI
      └─ OpenRouter Decisions / JEV

Keep the learner-facing experience simple even when internal responsibilities are modular.

## 2. Main runtime components

### 2.1 Web

**Technology:** Next.js, React, TypeScript.

Primary surfaces:

- Student Daily experience;
- Student subject and session views;
- Parent surface;
- authentication;
- source upload and source preview;
- voice input;
- Studio renderer host.

The web client does not own durable learning or Canvas semantics.

### 2.2 API

**Technology:** FastAPI, Python.

The API owns authenticated application operations including session opening and recovery, Tutor streaming, Student source admission, Studio protocol, Parent and Core Profile operations, content operations, and controlled status or health endpoints.

### 2.3 PostgreSQL + pgvector

PostgreSQL is durable application authority for users and students, learning sessions and messages, segments, AI execution lineage, Personal Facts, Learning Intelligence, Studio Runtime and Scene state, Canvas specialist runs, artifact lineage, jobs, and bounded decision records.

pgvector supports semantic retrieval and selection where required.

### 2.4 Background Worker

Longer-running work is decoupled from the foreground request where appropriate.

The Worker handles areas such as Canvas specialist composition, content and intelligence jobs, Segment review and finalization flows, reusable visual processing, and bounded JEV decision work associated with background tasks.

Foreground teaching should not wait on unrelated background analysis.

### 2.5 Object storage

Object storage holds project-owned immutable or source assets such as preserved Student originals, generated assets, custom visual build artifacts, and other durable binary objects.

Database records hold bounded references and provenance, not arbitrary raw binary state.

## 3. Primary Tutor runtime

The Primary Tutor is the only learner-facing teaching authority.

### 3.1 Input assembly

The Tutor context builder may include, when relevant:

- current Student turn;
- immediate and recent conversation;
- scoped semantic recall;
- Core Profile;
- Personal Memory;
- relevant Learning Intelligence;
- current Segment state;
- current subject and concept context;
- retrieved curriculum or source context;
- Studio or Canvas state;
- Parent Boundaries;
- safe visual-personalization catalogue.

Context is capacity-bounded and current behavior remains highest priority.

### 3.2 Model output

The Tutor produces structured output including student-facing text, optional suggested actions, optional guided check, teaching metadata, prior-method relation, optional subject or concept hints, optional Canvas brief and change intent, and other bounded runtime fields.

The response schema is versioned.

### 3.3 Safety

Safety and Parent Boundaries are not delegated to the Tutor model as final authority.

The application evaluates non-overridable safety, supplies effective Parent Boundary context, resolves and enforces final visible behavior, and may suppress or replace model output when required.

## 4. Student-source flow

    Student source
    → owner/session validation
    → type and size validation
    → preserved original
    → safety processing
    → extraction or normalization when applicable
    → Tutor context
    → optional retrieval or Canvas semantics

The original remains authoritative.

No extracted representation may silently rewrite source truth.

## 5. Personal Facts / Memory

Personal Facts are a dedicated subsystem separate from Learning Intelligence.

    explicit learner statement
    → bounded extraction
    → reconciliation
    → current Personal Memory document or card
    → optional later Tutor context

Rules:

- Student assertion is the source;
- current conversation can override old memory immediately;
- facts do not become Evidence;
- no psychological or personality inference;
- no automatic teaching-method selection from interests.

## 6. Core Profile

Core Profile is Parent/System-authoritative.

It supplies identity, age, and Grade context used to calibrate language, abstraction, amount of information, interaction complexity, representation concreteness, and age-appropriateness.

It does not claim mastery or intelligence.

## 7. Learning Intelligence architecture

Canonical current pipeline:

    Learning Messages
    → Learning Segment
    → Segment Learning Review
    → staged findings
    → Session Intelligence Finalization
    → Learning Events
    → Evidence
    → Current Learning State / Learner Patterns
    → Learner Intelligence Card
    → relevant Tutor context

### 7.1 Candidate Events

Candidate Events are optional source-linked hints.

They do not directly create Evidence or update stable intelligence.

### 7.2 Review authority

Segment Review interprets meaningful learning behavior from raw source context.

Session Finalization controls activation into validated downstream intelligence.

### 7.3 Deterministic governance

Code governs lifecycle, recency, scope, evidence weighting, counter-evidence, pattern thresholds, card bounds, versioning, reprocessing, and lineage.

Models interpret semantic meaning inside bounded contracts.

## 8. Studio / Canvas architecture

### 8.1 Durable Studio state

Studio owns Runtime, Scene, Event, Snapshot, Student interaction, and Tutor observation.

The browser renders state; it does not become state authority.

### 8.2 Full-Power Hybrid Canvas flow

    Primary Tutor
    → CanvasBrief
    → filtered learner presentation context
    → Canvas composition pipeline
    → REUSE / ADAPT / CREATE
    → typed or custom visual runtime
    → validation / preview / sandbox
    → accepted Scene
    → browser
    → meaningful Student interaction
    → Studio event/state
    → same Primary Tutor

### 8.3 Typed fast paths

Typed educational capabilities remain the safest and fastest option when they fit.

Examples include math boards, number lines, plots, diagrams, process views, grouping and classification, text interaction, and math input.

### 8.4 Reusable visual registry

Reusable visual identity is separate from Student-specific instances.

The registry stores generalized validated artifacts, versions, and builds.

Instance parameters and learner context do not become generic reusable source by accident.

### 8.5 Custom visual runtime

Generated custom code:

- runs only inside the approved sandbox;
- has no cookies, secrets, database, or application authority;
- cannot make unrestricted network calls;
- communicates through a bounded semantic bridge;
- is previewed and validated before durable learner-facing use;
- must expose implementation-independent semantic meaning.

### 8.6 Semantic Manifest

The Primary Tutor should understand educational state without reading generated code.

Every accepted custom runtime therefore exposes bounded semantic identity and state including objective, entities, facts, quantities, relations, meaningful interactions, current state or focus, and provenance.

## 9. REUSE / ADAPT / CREATE

### 9.1 REUSE

Use when an existing validated capability satisfies the educational need without structural change.

Exact reuse is freshly revalidated before execution.

### 9.2 ADAPT

Use when a validated parent artifact remains useful but generalized structure or capability must change.

ADAPT creates new version and build lineage rather than mutating history.

### 9.3 CREATE

Use when reuse or adaptation would compromise learning quality.

CREATE is bounded by capability allowlists, authoring attempt budget, preview, sandbox, semantic validation, and ownership or provenance requirements.

## 10. JEV bounded decision integration

OpenRouter Decisions / JEV is integrated through the existing Model Gateway ledger.

It is used only for finite decision problems.

### 10.1 Visual personalization

Inputs:

- admitted Canvas brief;
- server-filtered Personal Fact candidates.

Outputs:

- bounded fact-selection probabilities and decision.

Application validation remains final.

### 10.2 Exact reuse

Inputs:

- Canvas brief;
- finite authorized executable exact-reuse actions;
- NO_MATCH.

Outputs:

- one bounded choice and probabilities.

Application code revalidates artifact ownership, build identity, manifest digest, parameters, and storage before reuse.

### 10.3 Segment rubric comparison

Inputs:

- already validated Segment findings;
- cited source messages and explicit authority facts;
- finite rubric options.

Outputs:

- bounded rubric decisions for comparison and evaluation.

The Learning Intelligence evidence and finalization authority is not replaced by this component.

## 11. Model Gateway

Model and provider use must go through the Model Gateway or another explicitly approved provider boundary.

The ledger records task, provider, model, latency, usage metrics when available, estimated cost when available, success or failure, and lineage IDs.

Current pilot model and provider choices are operational state, not permanent architecture.

## 12. Foreground reliability

### 12.1 One foreground lane

Daily Chat and Tutor-triggering Canvas interactions share a server-owned foreground admission lane per LearningSession.

This prevents silent supersession, duplicated Tutor execution, Canvas interaction storms, and losing an admitted Student Chat turn.

### 12.2 Session recovery

Ended or non-resumable sessions recover through a deterministic replacement identity.

Old transcript can remain visible while old session-scoped source assets remain historical rather than becoming active runtime source in the replacement session.

### 12.3 Tutor stream bounds

Provider streaming has bounded failure behavior. Transport failure should end predictably rather than hang until infrastructure termination.

## 13. Deployment

Current live pilot runs on GCP.

### Application

Cloud Run service contains Next.js standalone, FastAPI, and the production supervisor. The integrated worker is disabled.

### Worker

A separate Cloud Run Worker Pool handles background jobs, Canvas composition, and browser-preview dependencies where needed.

### Data and platform services

- Cloud SQL / PostgreSQL;
- Secret Manager;
- Artifact Registry;
- Cloud Build;
- object storage.

Deployment and DB migration are explicit operations and require approval.

## 14. Verification strategy

Use the smallest verification that proves the changed boundary.

Typical layers:

1. contract and unit tests;
2. focused PostgreSQL integration;
3. typecheck and build;
4. repository-truth and diff checks;
5. actual browser rendering for visual work;
6. controlled live or provider evidence only when required.

Do not claim learning effectiveness from structural tests.

## 15. Current technical priorities

### Priority A — controlled real-use validation

Observe real use before further architectural expansion.

### Priority B — teaching-flow integrity

Open behaviors:

- unfinished guided sequence can end without a useful next affordance;
- declared EXPLAIN_THEN_CHECK may not visibly include a check;
- repeated confusion does not always trigger a substantive method change.

### Priority C — performance and terminal buffering

Measure where latency comes from before changing call architecture.

### Priority D — personalization relevance

Reduce forced or repetitive personalization and verify source lineage.

### Priority E — JEV evaluation

Compare bounded JEV decisions against current system decisions and only expand authority where evidence justifies it.

### Priority F — Generated educational images V2

Remain a separately designed capability with Science-first eligibility.

## 16. Things not to do

Do not:

- create a new general orchestrator without demonstrated need;
- split the modular monolith into microservices for conceptual cleanliness;
- create one standing agent per subject;
- let Canvas write Learning Intelligence directly;
- let Personal Facts become learner-ability evidence;
- send unrestricted learner context to generated custom code;
- rebuild working Studio, State, or Model Gateway foundations;
- treat a model-selected strategy as evidence of effectiveness;
- force all visuals through custom code;
- force all decisions through JEV;
- optimize latency by silently dropping required safety or authority checks.

## 17. Supporting references

- docs/PROJECT_REFERENCE.md
- docs/LEARNING_INTELLIGENCE_SPEC.md
- docs/CHILD_SAFETY_POLICY.md
- docs/TUTOR_PEDAGOGY_REFERENCE.md
- docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md
- docs/TUTOR_CANVAS_REPAIR_TRACKER.md
- project-state/PROJECT_STATE.md
