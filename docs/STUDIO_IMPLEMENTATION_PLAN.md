# Lina Learning Studio — Implementation Plan

**Status:** Product Owner approved and accepted — repository verification and governing promotion completed through `STUDIO-GOV-01`
**Approved:** 2026-09-02
**Purpose:** Convert the approved Learning Studio architecture decisions and the Grade 5 Math renderer research into a production-intent, dependency-ordered implementation plan.
**Scope:** Studio Core, bidirectional Tutor/Workspace orchestration, durable Studio state, subject capabilities, initial production activities, FE-02 integration, verification, and the bounded path to an optional Canvas Specialist.
**Current readiness:** `STUDIO-GOV-01`, `FE-02-PRESERVE-01`, and `STUDIO-STATE-01` are `DONE / ACCEPTED`. `STUDIO-SUBJECT-01` is the only ready task; all later Studio tasks remain dependency-ordered and blocked.
**Authorization boundary:** This plan authorizes dependency-ordered task promotion. It does not authorize a single bulk implementation run, uncontrolled schema/runtime changes, dependency installation, FE-02 acceptance, Canvas Specialist production calls, or production deployment. Each named implementation task remains independently reviewable and must preserve its stated gate.

---

## 1. Authority, Evidence, and Baselines

### 1.1 Repository baseline

The latest research baseline reviewed for this plan is:

- Repository: `Haithamhaj/lina-learning`
- Branch: `codex/ctx-03`
- Latest research commit: `eafd1121a240bd7873de46d260b296dcde52a46f`
- Current accepted application database head before Studio work: `a1d2e3f4b5c6`

The FE-02 Desktop Learning Studio shell is preserved as a remote prototype asset. It is not accepted production Studio architecture and must not be mixed into foundation commits.

### 1.2 Governing source order

Implementation must preserve the existing authority order:

1. `AGENTS.md`
2. `docs/PROJECT_REFERENCE.md`
3. `docs/CHILD_SAFETY_POLICY.md`
4. `docs/LEARNING_INTELLIGENCE_SPEC.md`
5. `docs/LEARNING_PRODUCT_ROADMAP.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. `project-state/PROJECT_STATE.md`
8. current promoted task file(s)

Research inputs are non-authoritative until Product Owner approval and promotion:

- `research/studio-orch-01/08_ARCHITECTURE_SYNTHESIS.md`
- `research/studio-orch-01/09_PRODUCT_OWNER_DECISION_PACKET.md`
- `research/curr-render-math-01/*`

### 1.3 Approved Product Owner decisions captured by this plan

The following decisions were explicitly approved during architecture review:

1. **Target architecture:** Application-owned, subject-agnostic Studio Core; one Student-facing Tutor; persistent Canvas/Workspace; deterministic renderers for known activities; optional Canvas Specialist for `CUSTOM_COMPOSE` only.
2. **Production intent:** Build the real database, protocol, state, and runtime contracts from the start. Acceptance scenarios test the production implementation; they are not throwaway demos.
3. **Foundation scenarios:** Math, Science, and Language must prove the same cross-subject Studio Core.
4. **State model:** Durable semantic Event Log plus Materialized Current Snapshot.
5. **Transport:** Existing Tutor SSE remains Chat authority; Canvas/Studio uses a dedicated authenticated resumable Studio event/state feed from the first production implementation. Snapshot reads support initial load and reconnect, not permanent polling architecture.
6. **Canvas role:** Canvas/Workspace is a first-class Student input and output surface and may be active in a large portion of learning.
7. **Tutor observability:** Every meaningful Canvas event and committed state change remains reconstructable and available to Tutor.
8. **Specialist eligibility:** Canvas Specialist is used only for `CUSTOM_COMPOSE` when known capabilities are insufficient. Tutor states the educational need; Studio Core makes the final deterministic routing decision.
9. **External reuse:** Reuse mature technology when it materially reduces work without adding greater coupling, licensing risk, state duplication, or operational complexity. Otherwise use a small Lina-owned primitive or a bounded fit spike.
10. **UI truth:** The browser may render optimistic state, but durable truth remains server-owned.
11. **Subject architecture:** Studio Core is not Math-specific. Subject and interaction language are separate axes. Subject-specific renderers, payloads, validators, and guidance live behind a small capability boundary.
12. **Vision authority:** Original media remains immutable source truth. Vision interpretation, annotation, and reconstruction are derived and source-linked; they do not become Evidence directly.
13. **Safety:** The existing Safety and Parent Boundary authorities remain unchanged and apply to every Studio, renderer, asset, Vision, and specialist boundary.
14. **Performance:** Every Studio path receives measurable latency and cost budgets. Final thresholds are established by benchmarks, not guessed before implementation.
15. **Make-Ten foundation:** `9 + 6` remains a cross-grade production activity for proving bidirectional Studio behavior. It is not included in the Grade 5 concept-coverage denominator.

### 1.4 Task-level implementation details still requiring code-grounded confirmation

The architecture, authority model, production intent, and phase sequence are approved. The following exact implementation details remain subject to repository audit and confirmation inside their named task:

- exact table, event, API, and module names;
- the initial Studio-event retention policy;
- the exact Math renderer correction set and revised coverage figure;
- the exact initial Grade 5 renderer batch after correction;
- the exact specialist timeout and measured latency targets;
- any external package installation.

Approval of this plan promotes these recommendations as implementation direction, subject to task-level review.

---

## 2. Implementation Objective

Build a production-intent Learning Studio in which Lina can learn through both Chat and an active Workspace without creating two competing teaching authorities.

```text
Lina
  ├─ Chat: type / speak / ask
  └─ Workspace: view / move / draw / build / order / annotate / submit
             ↓
Application-owned Studio Core
  ├─ durable semantic event history
  ├─ materialized current snapshot
  ├─ scene and source-turn versions
  ├─ StudentInteraction routing
  ├─ authorization, safety, idempotency, cancellation
  └─ subject capability and renderer dispatch
             ↓
Tutor — sole Student-facing teaching authority
  ├─ sees current scene and all unseen meaningful events
  ├─ continues teaching from Canvas actions
  └─ emits response plus optional Workspace intent
             ↓
Workspace execution
  ├─ source view
  ├─ annotation
  ├─ known visual
  ├─ known interactive activity
  └─ custom compose → optional Canvas Specialist
```

The implementation must support a high rate of Canvas usage without requiring a high rate of additional model calls.

---

## 3. Explicit Non-Goals

The first Studio implementation does not include:

- a second Tutor or a Teaching Manager above Tutor;
- a Canvas Agent call on every turn;
- a generic agent framework owning application sessions or state;
- arbitrary model-generated HTML, CSS, or JavaScript;
- a freeform collaborative whiteboard;
- CRDT collaboration;
- a generic plugin marketplace;
- automatic Learning Evidence from Canvas clicks or validator success;
- pressure-oriented Exam Mode, countdowns, rankings, or public scores;
- a full Science curriculum catalog;
- a full English or Arabic curriculum catalog;
- full Vision implementation;
- generated images, 3D, or simulations unless separately promoted;
- WebSockets, Redis, Celery, microservices, or a separate database without demonstrated need;
- a second RAG system for renderers or Studio state.

---

## 4. Current Repository Reality and FE-02 Boundary

### 4.1 Reusable current assets

The implementation should reuse the current accepted foundations:

- FastAPI authentication and Student ownership resolution;
- `LearningSession` and Segment lineage;
- current Tutor context assembly and one-primary-call runtime;
- Model Gateway task/provider abstraction and AI execution ledger;
- PostgreSQL/Alembic and DB-backed Job/Worker foundation;
- current Tutor SSE provisional-delta and terminal-turn lifecycle;
- Safety and Parent Boundary policy engine;
- raw learning-message persistence;
- Content and Retrieval boundaries;
- Personal Facts and Learner Intelligence authority separation;
- object-storage abstraction for original and derived assets;
- Next.js/Tailwind/shadcn web baseline;
- the useful layout and interaction lessons in the preserved FE-02 prototype.

### 4.2 FE-02 parts to preserve

Preserve after independent review:

- `/student/daily` greenfield product route;
- Desktop Chat + Workspace composition;
- project-owned Chat stream controller;
- provisional/terminal transcript behavior;
- composer direction handling and accessibility basics;
- responsive/narrow layout behavior;
- Workspace visual hierarchy that can become the host for real Studio state.

### 4.3 FE-02 prototype-only parts to replace

Do not preserve as product architecture:

- parsing Tutor prose or equations in the browser to infer Canvas meaning;
- Canvas state derived from transcript text;
- local React state as Studio truth;
- repeated question/guidance/status cards that mirror Chat instead of hosting a learning object;
- SVG generated only from literal equation text inside Tutor output;
- any assumption that Canvas updates only after Chat has completed.

### 4.4 Prototype preservation preflight

Before implementation starts:

1. record hashes and exact file inventory of the current FE-02 prototype;
2. preserve it on a dedicated prototype branch/commit or an immutable patch artifact;
3. do not commit it to the production branch as accepted FE-02 behavior;
4. begin Studio foundation work from a clean, isolated worktree;
5. later port only explicitly retained pieces.

---

## 5. Target Architecture

```text
                                         Lina
                         ┌─────────────────┴─────────────────┐
                         │                                   │
                       Chat                              Workspace
                 type / voice / ask             view / drag / build / submit
                         │                                   │
                         └─────────────────┬─────────────────┘
                                           ▼
                              Application-Owned Studio Core
                   ┌────────────────────────────────────────────────┐
                   │ Auth / Student / Session / Segment scope       │
                   │ StudioEvent Log + StudioSnapshot               │
                   │ Scene/source-turn versions                     │
                   │ StudentInteraction trigger policy              │
                   │ Idempotency / cancel / supersede / recovery    │
                   │ Safety / Parent Boundary                       │
                   │ Subject Capability and validator dispatch      │
                   │ Renderer allowlist and specialist scheduler    │
                   │ Dedicated resumable Studio feed                │
                   └───────────────┬────────────────────────────────┘
                                   │
             ┌─────────────────────┼─────────────────────────┐
             ▼                     ▼                         ▼
      Tutor / Teaching       Renderer Registry       Canvas Specialist
          Authority          deterministic/code     optional CUSTOM_COMPOSE
             │                     │                         │
             │                     └──────────┬──────────────┘
             │                                ▼
             └──────────────────────── Active Scene
                                              │
                                      semantic operations
                                              │
                                              └────────────► Tutor context
```

### 5.1 Authority model

| Component | Owns | Must not own |
|---|---|---|
| Application / Studio Core | auth, state, events, snapshots, versions, persistence, trigger routing, cancellation, Safety, renderer validation | teaching substitution |
| Tutor | educational objective, dialogue, final Student-facing response, sequencing, interpreting Studio history | direct state mutation, renderer technology, Evidence activation |
| Canvas Specialist | bounded visual/interactive composition proposal | independent objective, Student-facing teaching answer, direct writes, Safety/Evidence authority |
| Renderer | deterministic rendering and typed semantic operation emission | model reasoning or state acceptance |
| Subject Capability | subject renderers, activity schemas, validators, subject guidance and fallbacks | generic transport, auth, event sequencing, Studio lifecycle |
| Browser | optimistic display and user-input capture | durable truth, final validation, authorization |

---

## 6. Domain and Module Boundaries

Keep the modular monolith. Add a cohesive Studio/Learning Artifacts domain without creating another deployment unit.

Recommended logical shape:

```text
services/
  studio/
    contracts.py
    events.py
    snapshots.py
    reducer.py
    operations.py
    interactions.py
    orchestration.py
    history.py
    specialist.py           # dormant until specialist task is promoted
    subjects/
      registry.py
      contracts.py
      math.py
      science.py
      english.py
      arabic.py
    renderers/               # server-side contracts/registry metadata
      registry.py
      activities.py
      validators.py

apps/api/routes/
  studio.py

apps/web/
  components/daily-student/
  lib/studio/
    controller.ts
    contracts.ts
    reducer.ts               # safe UI projection, never durable authority

workers/
  studio_handlers.py         # specialist/background work only when promoted
```

Exact paths may adapt to actual repository conventions, but the following boundaries are mandatory:

- API routes remain thin.
- Studio state logic does not live in frontend components.
- Subject validators do not live in generic routes.
- Tutor does not call a renderer library directly.
- Renderer implementations do not write database rows directly.
- Canvas Specialist calls go through Model Gateway and application scheduling.

---

## 7. Production Data Model

### 7.1 Design principle

Use one additive Studio foundation migration that creates the durable entities required by the approved architecture. Avoid a temporary schema that must be replaced after testing.

The migration must preserve all existing rows and advance from `a1d2e3f4b5c6` without resetting the Daily-Use database.

### 7.2 Recommended conceptual records

#### `StudioRuntime`

One active Studio runtime per `LearningSession`.

Suggested fields:

- `id`
- `student_id`
- `learning_session_id` — unique
- `active_segment_id` — nullable, lineage reference
- `status` — `ACTIVE | CLOSED | FAILED`
- `latest_event_sequence`
- `current_snapshot_id`
- `active_scene_id`
- `tutor_observed_sequence_watermark`
- `created_at`, `updated_at`, `closed_at`

Purpose:

- owns event-sequence allocation;
- anchors all Studio records to Student and Learning Session;
- holds the current observation watermark and active scene references.

#### `StudioScene`

Accepted renderer/activity instance.

Suggested fields:

- `id`
- `studio_runtime_id`
- `student_id`
- `subject_key`
- `concept_keys`
- `activity_key`
- `artifact_type`
- `renderer_key`, `renderer_version`
- `activity_contract_version`
- `payload_schema_version`
- `scene_version`
- `source_turn_id` / source Tutor-message reference
- `status` — `PREPARING | ACTIVE | COMPLETED | FAILED | SUPERSEDED | ARCHIVED`
- `accepted_scene_payload` — typed JSONB envelope
- `accessibility_payload`
- `locale`, `direction_policy`
- source asset references when applicable
- timestamps

Purpose:

- stores only accepted scene state and safe metadata;
- records renderer and schema versions needed for reconstruction;
- supports persistent Workspace continuity across multiple turns.

#### `StudioEvent`

Durable source of Studio semantic history.

Suggested fields:

- `id`
- `studio_runtime_id`
- `student_id`
- `learning_session_id`
- `segment_id` — nullable
- `scene_id` — nullable
- monotonic `sequence`
- `actor` — `STUDENT | TUTOR | CANVAS_SPECIALIST | RENDERER | SYSTEM`
- `event_kind`
- `event_schema_version`
- `subject_key`
- `activity_key`
- `source_turn_id`
- `base_scene_version`
- `resulting_scene_version`
- `idempotency_key`
- `causal_event_ids`
- `payload_schema_version`
- typed `payload`
- `result_status`
- `occurred_at`, `created_at`

Required constraints:

- unique `(studio_runtime_id, sequence)`;
- unique `(studio_runtime_id, idempotency_key)` where present;
- Student consistency across Runtime, Scene, Session, and Event;
- source-turn and scene references cannot cross Students or Sessions.

#### `StudioSnapshot`

Materialized current projection.

Suggested fields:

- `id`
- `studio_runtime_id` — unique for the current snapshot
- `student_id`
- `snapshot_schema_version`
- `sequence_watermark`
- `scene_sequence_watermark`
- `active_scene_id`
- `active_scene_version`
- `active_subject_key`
- `active_activity_key`
- `active_teaching_step`
- `last_meaningful_student_event_id`
- bounded `snapshot_payload`
- `updated_at`

Purpose:

- initial page load;
- reconnect/resume;
- low-latency Tutor context;
- current renderer state;
- deterministic rebuild target.

It is a projection and must be fully rebuildable from accepted events plus versioned scene seeds.

#### `StudentInteraction`

A semantic Canvas action that requires or schedules Tutor reasoning.

Suggested fields:

- `id`
- `studio_runtime_id`
- `student_id`
- `source_event_id`
- `interaction_type`
- `trigger_policy_version`
- `status` — `PENDING | RUNNING | COMPLETED | FAILED | CANCELLED | SUPERSEDED`
- `tutor_execution_id`
- `tutor_message_id`
- `created_at`, `started_at`, `completed_at`

Required rule:

- a record-only event does not create `StudentInteraction`;
- one source event may create at most one Tutor-triggering interaction.

#### `TutorStudioObservation`

Audit record for events selected into a Tutor turn.

Suggested fields:

- `id`
- `studio_runtime_id`
- `student_id`
- `tutor_execution_id`
- `student_interaction_id` — nullable for Chat-originated turns
- `from_sequence_exclusive`
- `through_sequence_inclusive`
- `status` — `SELECTED | COMMITTED | FAILED | CANCELLED | SUPERSEDED`
- `created_at`, `committed_at`

Purpose:

- proves exactly which events entered a Tutor reasoning step;
- supports retry and watermark correctness;
- avoids treating context assembly as acknowledgement.

#### `CanvasSpecialistRun`

Operational seam for future `CUSTOM_COMPOSE` work, created in the foundation migration even if initially dormant.

Suggested fields:

- `id`
- `studio_runtime_id`
- `student_id`
- `source_turn_id`
- `base_scene_version`
- `subject_key`
- `capability_profile_version`
- `status` — `PENDING | RUNNING | COMPLETED | FAILED | CANCELLED | SUPERSEDED | REJECTED`
- `job_id`
- `ai_execution_id`
- `output_schema_version`
- `accepted_scene_version`
- `deadline_at`
- bounded failure metadata
- timestamps

Do not persist full prompts or unrestricted model output in this operational row.

### 7.3 Data that must not be duplicated in Studio events

- original image/file bytes;
- full Tutor prompts;
- full Personal Memory or Learner Intelligence cards;
- raw Safety directives;
- unrestricted Canvas screenshots on every event;
- low-level pointer telemetry;
- duplicated transcript content already owned by LearningMessage.

Use stable references to original sources and derived artifacts.

### 7.4 Retention recommendation

Initial production policy:

- retain meaningful Studio events with the associated LearningSession history;
- retain the current snapshot and accepted scene versions required for reconstruction;
- store content-heavy originals/derived media in object storage and reference them;
- archive closed scenes read-only;
- do not load historical Studio data into Tutor context by default;
- provide authorized older-history query when current snapshot plus unseen events is insufficient;
- align deletion/export policy with the Student’s broader learning-history policy.

---

## 8. Event Semantics, Reducer, and State Integrity

### 8.1 Event classes

#### UI-ephemeral

Examples: hover, viewport, pointer movement, unfinished drag, animation frames.

- browser only;
- no durable Studio event;
- no Tutor call.

#### Semantic record-only

Examples: committed object move during exploration, slider change, point placement, intermediate stroke, token reordering before submit.

- validate;
- append event;
- update snapshot;
- broadcast committed state;
- no Tutor call unless Activity Contract says otherwise.

#### Tutor-triggering StudentInteraction

Examples: answer submitted, step submitted, completed configuration, help request, explicit inspect request, drawing submitted for review.

- append event;
- update snapshot;
- create `StudentInteraction`;
- schedule one Tutor turn.

#### System/specialist lifecycle

Examples: scene ready, renderer failed, specialist timed out, run superseded, patch accepted/rejected.

- update state and feed;
- trigger Tutor only through explicit policy.

### 8.2 Generic event envelope and typed subject payload

The common event envelope must be subject-agnostic. Subject-specific payloads are selected and validated by the active Subject Capability and Activity Contract.

Do not use one unrestricted JSON payload for every activity.

### 8.3 Atomic append and snapshot reduction

Recommended transaction:

```text
Lock StudioRuntime sequence row
→ validate Student / Session / Scene / base version / idempotency
→ allocate next monotonic sequence
→ append StudioEvent
→ run pure deterministic reducer
→ write StudioSnapshot and Scene version
→ optionally create StudentInteraction
→ commit
→ broadcast committed event/state
```

If any step fails, no partial event/snapshot state is accepted.

### 8.4 Deterministic reducer

The reducer must be a pure, versioned function:

```text
reduce(snapshot, accepted_event) -> new_snapshot
```

Required verification:

- rebuild from event zero equals stored snapshot;
- repeated rebuild is deterministic;
- unknown event/schema version fails explicitly;
- rejected events do not mutate the projection;
- cross-subject transition closes/archives the prior active scene cleanly.

### 8.5 Optimistic UI

The browser may apply a supported local optimistic projection for responsiveness, but:

- every command includes `idempotency_key` and `base_scene_version`;
- server response/feed confirms the accepted state;
- rejection restores the authoritative snapshot with calm feedback;
- optimistic state is never used as Tutor context or persisted evidence.

### 8.6 Stale-result rejection

Every scene-changing command and specialist result carries:

- source turn;
- base scene version;
- capability/renderer version;
- idempotency key.

A result generated from an obsolete source turn or scene version is `SUPERSEDED` or `REJECTED`, never blindly merged.

---

## 9. Tutor Observation Watermark

### 9.1 Selection

At Tutor-context construction:

1. read the current snapshot;
2. capture `through_sequence = latest committed semantic sequence`;
3. select every semantic event with sequence greater than the last committed Tutor watermark and less than or equal to `through_sequence`;
4. create a `TutorStudioObservation` in `SELECTED` state;
5. include the current snapshot, selected events, and authorized history tool in Tutor context.

Events arriving after `through_sequence` remain unseen for the next turn.

### 9.2 Advancement invariant

Advance `tutor_observed_sequence_watermark` atomically only after:

- provider execution succeeds;
- terminal Tutor output validates;
- final Tutor message persists;
- Tutor turn transaction commits;
- corresponding observation record becomes `COMMITTED`.

### 9.3 Failure behavior

The watermark must not advance after:

- provider failure or timeout;
- incomplete SSE stream;
- terminal-output validation failure;
- cancellation/supersession before commit;
- persistence failure or rollback.

The same unseen events remain eligible for the next successful Tutor turn.

### 9.4 Older-history access

Provide a server-owned, Student/Session-scoped history-query boundary for Tutor. It returns typed semantic events or bounded causal slices, not raw database access.

---

## 10. Transport and API Contracts

### 10.1 Transport split

- **Tutor SSE:** conversational provisional deltas and terminal Tutor turn only.
- **Studio feed:** accepted Studio events, scene/snapshot updates, StudentInteraction status, renderer/specialist lifecycle.

Do not mix independent Canvas lifecycle into provisional Tutor text events.

### 10.2 Required API surface

Conceptual routes:

```text
GET  /api/v1/student/studio/session/{learning_session_id}/snapshot
GET  /api/v1/student/studio/{studio_runtime_id}/events/stream
POST /api/v1/student/studio/{studio_runtime_id}/operations
POST /api/v1/student/studio/{studio_runtime_id}/interactions/help
GET  /api/v1/student/studio/{studio_runtime_id}/history   # server/tool boundary; not unrestricted UI
```

Exact route names may follow repository conventions.

### 10.3 Studio feed contract

Requirements:

- authenticated and Student-scoped;
- monotonic sequence per Studio runtime;
- resumable through `Last-Event-ID` or explicit `after_sequence`;
- sends current snapshot on initial connection or when the requested cursor is no longer sufficient;
- heartbeat without Student content;
- supports reconnect without duplicate state application;
- browser handles event idempotently;
- status events contain safe metadata only.

Conceptual feed events:

- `STUDIO_SNAPSHOT`
- `STUDIO_EVENT_COMMITTED`
- `SCENE_UPDATED`
- `STUDENT_INTERACTION_STATUS`
- `RENDERER_STATUS`
- `CANVAS_SPECIALIST_STATUS`
- `STUDIO_ERROR`

### 10.4 Operation endpoint behavior

Input includes:

- runtime/scene identity;
- base scene version;
- activity/action key;
- payload schema version;
- typed action payload;
- idempotency key;
- optional source-turn reference.

Response distinguishes:

- accepted committed operation;
- duplicate idempotent replay;
- stale scene conflict;
- invalid typed payload;
- forbidden/non-enumerating ownership failure;
- unsupported activity/action;
- safe activity-level validation result.

### 10.5 WebSocket decision

Do not add WebSockets initially. SSE plus authenticated command endpoints satisfy the selected one-way server feed and client command model. Reconsider only if later real-time collaboration or bidirectional transport constraints prove SSE insufficient.

---

## 11. Tutor ↔ Workspace Orchestration

### 11.1 Turn origins

A Tutor turn may originate from:

- new Chat message;
- Canvas `StudentInteraction` such as submit/help/review;
- explicit application continuation declared by an Activity Contract.

Do not create a fake Chat message for a Canvas action.

### 11.2 Tutor input

Tutor context may include:

- raw current Student message or StudentInteraction summary;
- current conversation continuity;
- current Studio snapshot;
- all unseen semantic Studio events through the selected watermark;
- authorized older-history query tool;
- Student Core Context;
- Personal Memory;
- relevant Learner Intelligence;
- optional Retrieval grounding;
- active Subject Capability guidance;
- current Activity Contract and allowed next semantic actions.

### 11.3 Tutor output

Extend the strict Tutor result with an optional versioned `workspace_intent` that expresses educational need, not renderer implementation.

Conceptual contract:

```text
WorkspaceIntent
  version
  action:
    NO_CHANGE | OPEN_ACTIVITY | UPDATE_ACTIVITY | CLOSE_ACTIVITY |
    FOCUS_SOURCE | REQUEST_ANNOTATION | REQUEST_CUSTOM_COMPOSE
  subject_key
  concept_keys
  learning_goal
  activity_hint
  representation_need
  expected_student_response_mode
  presentation_sequence
  source_references
  safe_text_fallback
```

Tutor must not choose React, SVG, JSXGraph, Konva, MathLive, or a provider directly.

### 11.4 Workspace Execution Router

```text
Workspace need
  ├─ SOURCE_VIEW
  ├─ ANNOTATION
  ├─ KNOWN_VISUAL
  ├─ KNOWN_INTERACTIVE
  └─ CUSTOM_COMPOSE
```

Routing order:

1. preserve or focus an existing active scene when suitable;
2. show source asset when the source itself is the learning object;
3. use an annotation capability when work should remain anchored to the source;
4. select an approved known visual/activity from Subject Capability;
5. only then evaluate `CUSTOM_COMPOSE` specialist eligibility;
6. otherwise use honest text/static fallback.

### 11.5 Persistent Workspace across turns

A scene remains active across Tutor turns until:

- the activity completes;
- Tutor explicitly closes/replaces it;
- Student changes subject/topic and the activity contract requires closure;
- source turn is superseded;
- scene becomes invalid or fails safely.

Do not regenerate the Canvas from scratch for each message.

### 11.6 Concurrent interaction rules

- record-only Canvas events during Tutor streaming are committed normally and remain unseen for the next Tutor turn;
- a new Tutor-triggering StudentInteraction creates a newer causal boundary;
- an uncommitted Tutor turn may be cancelled/superseded;
- raw Student input remains persisted;
- late terminal output is rejected if its active-turn token is stale;
- the client removes or marks provisional text when a turn is cancelled.

### 11.7 Immediate deterministic feedback

Use validators and activity rules for immediate bounded feedback when possible. Do not call Tutor after every drag or field edit.

Validator output should be typed, such as:

- `VALID`
- `INVALID`
- `UNDER_SPECIFIED`
- `VALID_ALTERNATIVE`
- `INCOMPLETE`

The Activity Contract decides whether a result remains local, becomes record-only context, or triggers Tutor.

---

## 12. Subject Capability Architecture

### 12.1 Contract

Use a small code-owned registry, not a generic plugin framework.

Conceptual `SubjectCapabilityProfile`:

- `subject_key`
- profile/version
- supported Grade range
- concept namespace
- approved Activity Contracts
- approved Renderer Contracts
- action-payload schemas
- validator dispatch
- Tutor guidance fragment
- Canvas Specialist tool/skill profile
- grounding preferences
- accessibility and locale rules
- deterministic fallbacks
- evaluation fixtures

### 12.2 Subject versus interaction language

Keep separate:

```text
subject_key = MATH
locale = ar
```

and:

```text
subject_key = ARABIC
locale = ar
```

The first is Math taught in Arabic. The second is Arabic as an academic subject.

### 12.3 Initial capabilities

Production foundation includes bounded, real contracts for:

- `MATH`
- `SCIENCE`
- `ENGLISH`
- `ARABIC`

Only Math and Science are initially enabled as product subjects. English/Arabic profiles may remain gated but must prove that Studio Core does not depend on Math fields or LTR-only behavior.

### 12.4 Adding a subject

A new subject should primarily require:

1. profile registration;
2. activity and renderer registration;
3. typed action schemas;
4. validators;
5. Tutor/Canvas guidance;
6. fixtures and evaluation.

It must not require rewriting event sequencing, snapshots, transport, cancellation, authorization, or Tutor-observation semantics.

---

## 13. Renderer, Activity, and Validator Contracts

### 13.1 Renderer Contract

Every renderer declares:

- renderer key and version;
- supported subjects/concepts/activities;
- typed scene-input schema;
- display-only and interactive modes;
- supported semantic actions;
- required validator(s);
- state/reducer adapter;
- accessible text/control equivalent;
- keyboard/touch behavior;
- RTL/LTR behavior;
- mobile behavior;
- reduced-motion behavior;
- failure fallback;
- source-view/annotation/reconstruction compatibility;
- implementation adapter and dependency status.

### 13.2 Activity Contract

Every activity declares:

- activity key and version;
- subject/concept scope;
- renderer key;
- initial scene schema;
- allowed actions;
- record-only actions;
- validation actions;
- Tutor-triggering actions;
- completion condition;
- immediate-feedback policy;
- support/hint actions;
- safe fallback;
- event-payload versions.

### 13.3 Validator Contract

A subject validator:

- accepts typed mathematical/scientific/language state;
- returns bounded typed status and safe feedback codes;
- may validate partial progress;
- accepts legitimate alternative methods;
- never chooses pedagogy;
- never creates Evidence;
- is versioned and fixture-tested.

### 13.4 Renderer independence

Studio Core dispatches by renderer/activity key. The underlying implementation may change from plain SVG to a library adapter without changing Studio event/state contracts.

---

## 14. Math Capability and Renderer Integration

### 14.1 Research input

`CURR-RENDER-MATH-01` provides a strong planning baseline:

- 35 mapped Grade 5 concept nodes;
- 8 proposed Core renderer families;
- concept → representation → interaction → validator mapping;
- transparent coverage denominator;
- source/rights manifest;
- McGraw alignment placeholder.

Before implementation, run a bounded correction task rather than treating the current counts and names as final.

### 14.2 Grade 5 renderer research correction gate

`CURR-RENDER-MATH-01A` is a correction gate immediately before the Grade 5
Math renderer batch. It does not block Studio Core state, subject, protocol,
runtime, bounded cross-subject foundation activities, or FE-02 Studio
integration.

`CURR-RENDER-MATH-01A` must:

1. add the missing Grade 5 decimal addition/subtraction capability under `5.NBT.B.7`;
2. map numerical-expression interpretation/writing across `5.OA.A.1–2`;
3. replace the overly method-specific top-level `long_division_workspace` identity with a broader `division_workspace` or equivalent contract supporting modes such as:
   - equal groups;
   - area model;
   - partial quotients;
   - standard algorithm/long division;
   - decimal division;
4. decide whether `measurement_data_workspace` remains a shell with explicit sub-renderers or splits into at least measurement-conversion and line-plot capabilities;
5. add `ten_frame_group_transfer` as a cross-grade foundation activity outside the Grade 5 coverage denominator;
6. recalculate concept count, coverage denominator, Core coverage, and recommended batch;
7. preserve the source/license boundaries in the published manifest.

### 14.3 Cross-grade production foundation activity

`ten_frame_group_transfer` supports the approved `9 + 6` scenario.

Requirements:

- React/SVG baseline;
- keyboard/button equivalent to drag;
- semantic `TRANSFER_ITEM` operation;
- deterministic group-count validator;
- record-only exploration and Tutor-triggering submit/step completion defined by Activity Contract;
- snapshot restore;
- duplicate and stale-operation rejection;
- Arabic/English/mixed-language presentation;
- no inclusion in Grade 5 coverage statistics.

This bounded foundation activity does not depend on completion of
`CURR-RENDER-MATH-01A` or the full Grade 5 renderer catalog correction.

### 14.4 Recommended Grade 5 Batch 1

After the correction gate, the preferred initial Grade 5 batch is:

- `number_line`
- `place_value_workspace`
- `fraction_model_workspace`
- `division_workspace`

This batch covers materially different state models: continuous magnitude, place-value structure, whole/partition invariants, and multi-step algorithm/strategy state.

Approval of this plan authorizes these as the default implementation recommendation, subject to the corrected coverage report and per-renderer task review.

### 14.5 Later Grade 5 renderer waves

Likely next candidates:

- `area_array_model`
- measurement-conversion workspace
- line-plot workspace
- `volume_composer`
- `coordinate_geometry_plane`
- `shape_property_explorer`
- `expression_pattern`

No heavy library is required merely because a renderer is listed.

### 14.6 McGraw-Hill alignment

When the physical/licensed book arrives:

- verify edition/year/ISBN and volumes;
- capture Table of Contents and minimum necessary lesson metadata;
- map chapters/lessons to stable concept keys and existing renderers;
- add terminology, expected depth, question form, and school relevance;
- preserve source and rights provenance;
- do not fork publisher-specific renderer implementations unless a repeated capability gap is proven.

Khan Academy remains reference-only under the current research rights decision. IM K–5 v1 assets may be evaluated for reuse only with asset-level verification, attribution, and provenance.

---

## 15. Cross-Subject Production Acceptance Activities

These are production-grade bounded activities built on the same Studio Core, not temporary demos.

### 15.1 Math — Make-Ten `9 + 6`

Proves:

- spatial Student input;
- semantic event append;
- snapshot reduction;
- Tutor visibility without repeated Chat text;
- watermark behavior;
- reload/reconnect;
- idempotency/stale rejection;
- accessible alternative.

### 15.2 Science — Process Ordering

Recommended initial activity: ordered stages of a bounded scientific process, using authored/trusted fixture content.

Proves:

- non-Math subject profile;
- token/stage reordering;
- deterministic sequence/relationship validator;
- configuration submission as StudentInteraction;
- Tutor reaction from Canvas state;
- same event/feed/recovery architecture.

The activity may use the water cycle as a fixture, but it must be implemented as a generic `process_sequence_workspace`, not a one-off water-cycle component.

### 15.3 English — Sentence Ordering

Proves:

- text-oriented Workspace rather than graphic Canvas;
- typed token identity and ordering events;
- deterministic authored-answer validator;
- LTR subject content with either Arabic or English Tutor explanation;
- submission-triggered Tutor continuation.

### 15.4 Arabic — Sentence Annotation/Ordering

Proves:

- Arabic as an academic subject, not merely RTL UI;
- stable token/span identity;
- RTL interaction and focus order;
- label assignment or token reordering;
- typed grammar/answer schema;
- same Studio Core and event feed.

---

## 16. Canvas Specialist

### 16.1 Role

Canvas Specialist is a bounded visual/interactive composition specialist, not a second Tutor.

### 16.2 Eligibility

Studio Core permits one specialist run only when:

1. Tutor emits a structured `REQUEST_CUSTOM_COMPOSE` need;
2. an enabled Subject Capability exists;
3. no approved known renderer/activity adequately covers the goal;
4. output can be expressed as a typed, allowlisted ScenePlan;
5. a deterministic subject validator or safe non-graded fallback exists;
6. execution can be asynchronous/deferred without blocking Chat;
7. source turn and scene version are current;
8. Safety, privacy, and provider route requirements are satisfied.

### 16.3 Ineligible cases

Do not use the specialist for:

- ordinary arithmetic;
- casual conversation;
- existing known activities;
- decoration only;
- unsupported or unvalidated subject content;
- arbitrary browser code;
- a request whose delay harms the learning flow.

### 16.4 Execution

```text
Tutor response streams normally
→ application creates CanvasSpecialistRun
→ existing Worker / Model Gateway executes Canvas task
→ specialist receives fixed objective, capability pack, source turn, base scene version
→ specialist returns typed ScenePlan proposal
→ application validates and accepts/rejects
→ accepted scene/event is committed and broadcast
```

Maximum normal specialist behavior: one additional Canvas model call for one eligible request. No blocking agent-as-tool loop in the first implementation.

### 16.5 Provider flexibility

Tutor and Canvas may use different providers/models. Add a task-specific Canvas route only after quality, structured-output, tool behavior, latency, privacy, retention, fallback, and cost are benchmarked.

---

## 17. Vision and Student Work Seam

Vision implementation remains separately promoted, but Studio contracts must be ready for it.

```text
Original asset — immutable source truth
  ↓
VisionRun — derived interpretation
  ↓
Annotation / Reconstruction / Side-by-side Scene
  ↓
Tutor and Workspace
```

Requirements:

- original asset always preserved;
- every derived interpretation has source asset and run/version lineage;
- uncertainty that can change the answer is explicit and may require clarification;
- annotation does not overwrite the original;
- reconstruction is a derived Studio scene;
- Studio events reference asset/artifact IDs instead of copying media content;
- Vision interpretation and Canvas actions do not become Evidence directly.

---

## 18. Safety, Privacy, and Authorization

No new Safety authority is created. Every boundary uses existing enforcement.

Apply server-side ownership and Safety/Parent Boundary checks to:

- Studio runtime creation/read;
- snapshot reads;
- feed subscription/resume;
- operation submission;
- StudentInteraction creation;
- original and derived asset access;
- Vision runs;
- Canvas Specialist requests/results;
- renderer output that contains model/source-derived content;
- older-history query.

Privacy rules:

- minimize content in operational traces;
- do not duplicate child content across event rows;
- record identifiers, versions, statuses, latency, and safe failure codes;
- preserve non-enumerating cross-Student denial;
- never expose internal Tutor/Canvas prompts, Evidence, Personal Facts, or raw Safety data to the Student UI.

---

## 19. Performance and Operational Model

### 19.1 Measurement points

Establish benchmark instrumentation for:

- local optimistic interaction response;
- server operation acknowledgement;
- DB append + snapshot reduction;
- Studio-feed propagation;
- initial snapshot load;
- reconnect and catch-up;
- Tutor first token and terminal turn;
- Tutor-trigger delay after Canvas submit;
- renderer first useful state;
- Canvas Specialist queue, first state, rich-ready, timeout;
- stale/cancel rate;
- payload size and event backlog;
- model cost by task/provider.

### 19.2 Performance invariants

- known local interactions do not wait for an LLM;
- routine Tutor turns retain one primary Tutor call;
- deterministic renderer failure never blocks Chat;
- specialist work is asynchronous/deferred;
- feed/reconnect must be resumable and idempotent;
- historical event volume does not require full replay on every load or Tutor turn;
- exact numeric budgets are set after controlled benchmarks and realistic-device tests.

### 19.3 Observability

Add content-minimized operational metrics for:

- event append/reducer failures;
- version conflicts and stale rejections;
- snapshot divergence/rebuild checks;
- feed disconnect/resume;
- StudentInteraction queue/processing;
- Tutor observation lag and failure non-advancement;
- renderer failures/fallbacks;
- specialist latency/cost/failure/cancel/supersede.

---

## 20. Technology Reuse Policy

### 20.1 Decision rule

```text
Need
→ existing mature technology fits behind Lina contract?
  ├─ yes, low integration/rights/authority cost → adopt or partially adopt
  ├─ yes, but platform coupling exceeds value → use small Lina-owned primitive
  └─ unclear → bounded fit spike
```

### 20.2 Initial posture

- React DOM/SVG: baseline for first production activities.
- Motion: meaningful orientation/feedback only; never correctness-only animation.
- MathLive: evaluate for a named structured-expression input gap.
- JSXGraph: evaluate for a named geometry/coordinate gap.
- React Konva: evaluate for a named spatial-manipulation gap.
- A2UI: evaluate against Lina-owned ScenePlan only after the local contract exists.
- AG-UI: reuse event/state concepts; do not migrate runtime without measured benefit.
- OpenMAIC: evaluate DSL/renderer packages, not the full product.
- tldraw: future freeform-only evaluation; not the initial Studio foundation.
- generated SVG/HTML/image/3D: future gated capabilities.

### 20.3 Governing-document reconciliation

The existing Technology Reuse Catalog contains broad `ADOPT BASELINE` wording for some libraries. Before implementation, reconcile it with the approved rule: technology is reused when a named renderer/activity demonstrates fit; no package is installed solely because it appears in the catalog.

---

## 21. Implementation Phases and Tasks

### Phase 0 — Governance and worktree safety

#### `STUDIO-GOV-01 — Promote Approved Studio Architecture`

**Status:** DONE / ACCEPTED.
**Purpose:** Move approved decisions from research/conversation into governing architecture and current task state.
**Output:** concise updates to Project Reference, Implementation Plan, Technology Reuse Catalog, Project State, System Map, and task overlay.
**Verification:** no historical protected decisions are overwritten; research remains non-authoritative history; diff limited to governance.
**Dependencies:** Product Owner approval of this plan.

#### `FE-02-PRESERVE-01 — Preserve Prototype Shell`

**Status:** DONE / ACCEPTED.
**Purpose:** Preserve the FE-02 shell without promoting its prototype Canvas adapter.
**Accepted output:** remote prototype branch `prototype/fe-02-studio-shell-2026-09-02` at `8648371480b0aac116af2a49e2d3d7493d26360f`, parent `059ff3aa6bfb983507470f484596bf05eae3b9b3`, with `prototype/FE-02_PROTOTYPE_MANIFEST.md`.
**Accepted verification:** seven focused Node tests, TypeScript typecheck, production build, and SHA-256 identity passed. The prototype remains non-production.

### Phase 1 — Production Studio state foundation

#### `STUDIO-STATE-01 — Durable Studio State`

**Status:** ONLY READY TASK.
**Purpose:** Implement additive migration, models, repositories, event append, snapshot reducer, scenes, interactions, observations, specialist-run seam.
**Output:** production tables/contracts and pure reducer.
**Likely areas:** DB models, migration, `services/studio/**`, PostgreSQL tests.
**Verification:** fresh migration; in-place Daily-Use migration; Student isolation; ordering; idempotency; rebuild equality; stale rejection; rollback atomicity.
**Extra model calls:** zero.
**Dependencies:** accepted `STUDIO-GOV-01` and `FE-02-PRESERVE-01` only.

### Phase 2 — Subject and activity capability foundation

#### `STUDIO-SUBJECT-01 — Subject Capability Registry`

**Purpose:** Implement subject, renderer, activity, action-schema, validator, locale, and fallback registry.
**Output:** Math, Science, English, Arabic bounded profiles and fixtures.
**Verification:** register a new fixture subject without changing generic Studio state/transport/orchestration.
**Dependencies:** STUDIO-STATE-01.

### Phase 3 — Dedicated Studio protocol

#### `STUDIO-PROTOCOL-01 — Commands, Snapshot, and Resumable Feed`

**Purpose:** Implement authenticated operation endpoints, snapshot reads, dedicated Studio SSE feed, resume, sequence, reconnect, and broadcast.
**Output:** API contracts and project-owned web Studio controller.
**Verification:** real auth; cross-Student denial; resume without duplicate state; Last-Event-ID; version conflict; idempotent replay; feed failure/reconnect.
**Dependencies:** STUDIO-STATE-01, STUDIO-SUBJECT-01.

### Phase 4 — Tutor/Workspace runtime orchestration

#### `STUDIO-RUNTIME-01 — Tutor Studio Context and Watermark`

**Purpose:** Add snapshot/unseen-event context, observation records, successful-commit watermark advancement, and history tool boundary.
**Verification:** failed/incomplete/cancelled Tutor turns do not advance watermark; events arriving during generation remain unseen; one normal Tutor call.
**Dependencies:** STUDIO-PROTOCOL-01.

#### `STUDIO-RUNTIME-02 — Workspace Intent and Execution Router`

**Purpose:** Add versioned optional WorkspaceIntent and route to source/annotation/known visual/known interactive/custom compose.
**Verification:** Tutor does not select implementation technology; `NO_CHANGE` preserves scene; fallback is honest; Canvas failure does not fail Chat.
**Dependencies:** STUDIO-RUNTIME-01, STUDIO-SUBJECT-01.

#### `STUDIO-RUNTIME-03 — Canvas-Originated Tutor Turns`

**Purpose:** Route declared StudentInteractions to Tutor without fake Chat messages; implement record-only versus triggering behavior and supersession.
**Verification:** submit/help triggers one Tutor turn; exploration does not; raw interaction persists; stale terminal result rejected.
**Dependencies:** STUDIO-RUNTIME-01/02.

### Phase 5 — Cross-subject production activities

#### `STUDIO-ACT-MATH-01 — Make-Ten Group Transfer`

Production implementation of `ten_frame_group_transfer` and approved acceptance flow.
It is a bounded cross-grade foundation activity and does not depend on the
Grade 5 renderer research correction.

#### `STUDIO-ACT-SCI-01 — Process Sequence Workspace`

Production generic process-ordering activity with Science fixture and validator.

#### `STUDIO-ACT-EN-01 — English Sentence Ordering`

Production text Workspace fixture using generic token/action contracts.

#### `STUDIO-ACT-AR-01 — Arabic Sentence Annotation/Ordering`

Production RTL academic-subject fixture with stable span/token identity.

Each task verifies accessibility, touch, keyboard, locale, semantic events, snapshot rebuild, validation, Tutor continuation, and no false Evidence.

### Phase 6 — FE-02 product integration

#### `FE-02-STUDIO-01 — Connect Real Studio to Daily Student App`

**Keep:** greenfield route, Chat/Workspace layout, stream controller patterns, responsive shell.
**Replace:** prose/equation parsing, message-derived Canvas, duplicated placeholder cards, browser-only state.
**Add:** Studio controller, snapshot load, feed resume, active-scene renderer host, optimistic operations, pending/error/reconnect states, cross-subject activity rendering.
**Verification:** authenticated visual flows for empty, active, streaming, reconnect, error, RTL/LTR, narrow layout, keyboard.

### Phase 7 — Grade 5 Math renderer batch

#### `CURR-RENDER-MATH-01A — Correct Math Planning Pack`

**Status:** BLOCKED UNTIL THE GRADE 5 MATH RENDERER IMPLEMENTATION GATE.
**Purpose:** Resolve the Grade 5 Math catalog corrections in Section 14.2.
**Output:** corrected research files, recalculated coverage, renamed/split renderer recommendations, and cross-grade Make-Ten entry.
**Verification:** official Grade 5 standards mapping, defined denominator, rights manifest unchanged except verified corrections.
**Dependency boundary:** this gate does not block Studio state, subject,
protocol, runtime, bounded Math/Science/English/Arabic foundation activities,
or FE-02 Studio integration. It must be accepted before `MATH-RENDER-BATCH-01`.
**Implementation:** none.

#### `MATH-RENDER-BATCH-01`

Implement, after corrected research approval:

- `number_line`
- `place_value_workspace`
- `fraction_model_workspace`
- `division_workspace`

Each renderer receives its own independently reviewable task and validator suite. Do not combine all into one giant change.

### Phase 8 — Full production acceptance

#### `STUDIO-ACCEPT-01 — Full-System Studio Acceptance`

Run the complete acceptance matrix in Section 22 on the Daily-Use runtime and a disposable test database. Do not create real Lina history until Product Owner authorizes a controlled real-use step.

### Phase 9 — Optional specialist and reuse evaluations

#### `STUDIO-SPECIALIST-01 — Canvas Specialist Value Evaluation`

Compare deterministic Science baseline with one Canvas specialist ScenePlan. Add `ModelTask.CANVAS` only in this promoted task.

#### `STUDIO-REUSE-01 — External Technology Fit Decisions`

Bounded evaluations for A2UI, AG-UI semantics, OpenMAIC packages, and named renderer libraries. Adopt only proven high-leverage pieces.

### Phase 10 — Production deployment

Promote the accepted Studio build through the project’s normal private deployment path. Deployment must use the same accepted schema/runtime/contracts; no post-test architecture rewrite is permitted.

---

## 22. Acceptance Matrix

### 22.1 Database and reconstruction

- additive migration from `a1d2e3f4b5c6`;
- existing Student/Session/Message counts preserved;
- zero cross-Student references;
- monotonic sequence under concurrency;
- idempotent replay;
- event/snapshot atomicity;
- full rebuild equals materialized snapshot;
- unsupported schema/version fails explicitly;
- closed scene remains reconstructable.

### 22.2 Tutor observation

- snapshot + every unseen event enters Tutor context;
- events after selected upper bound remain for next turn;
- successful terminal commit advances watermark exactly once;
- provider failure, incomplete stream, cancellation, validation failure, or rollback does not advance it;
- history tool is Student/Session scoped.

### 22.3 Transport

- Tutor SSE unchanged for Chat authority;
- dedicated Studio feed authenticates and resumes;
- initial snapshot and event catch-up are consistent;
- reconnect does not duplicate state;
- stale base version returns explicit conflict;
- feed failure does not block Chat;
- no sensitive content in lifecycle telemetry.

### 22.4 Orchestration

- Chat and Canvas can originate Tutor turns;
- record-only event does not call Tutor;
- submit/help interaction calls Tutor once;
- persistent scene survives multiple turns;
- new StudentInteraction supersedes uncommitted stale Tutor work;
- Canvas failure preserves usable Chat;
- routine path uses one Tutor model call;
- known activities use zero Canvas model calls.

### 22.5 Math scenario

- 9 + 6 ten-frame/group-transfer renders;
- drag and keyboard action are equivalent;
- transfer event results in 10 and 5;
- Tutor reacts without Lina restating the action;
- reload restores exact accepted state;
- duplicate/stale operations are rejected;
- not counted in Grade 5 coverage denominator.

### 22.6 Science scenario

- stages can be reordered and submitted;
- Science validator returns typed result;
- Tutor sees exact submitted configuration;
- generic Studio schema contains no Math-specific assumptions.

### 22.7 Language scenarios

- English tokens reorder and submit correctly;
- Arabic tokens/spans preserve identity and RTL behavior;
- academic subject remains separate from Tutor locale;
- same Studio state/transport/orchestration works unchanged.

### 22.8 Accessibility and device

- all drag actions have keyboard/button alternative;
- focus behavior and error status are accessible;
- meaningful state has text alternative;
- no color-only correctness;
- reduced motion supported;
- Arabic/English/mixed direction verified;
- narrow layout remains usable;
- optimistic rejection restores state clearly.

### 22.9 Safety and authority

- every route/feed/asset/run is server-authorized;
- unrelated Student returns non-enumerating denial;
- renderer or specialist cannot bypass Safety/Parent Boundary;
- Canvas action does not directly create Candidate, Evidence, Current State, or Pattern;
- original media remains immutable source truth.

### 22.10 Performance

Benchmark and record:

- local interaction responsiveness;
- operation commit latency;
- feed propagation;
- snapshot restore;
- Tutor first token/terminal response;
- Canvas-trigger-to-Tutor delay;
- event backlog/context size;
- renderer error/fallback rate;
- specialist metrics when promoted.

Production thresholds are approved after measurement and before deployment.

---

## 23. Key Risks and Controls

| Risk | Control |
|---|---|
| Canvas and Tutor diverge | Application-owned state, one teaching authority, fixed source-turn/scene version |
| Event volume grows | semantic events only, snapshots, older-history query, no pointer telemetry |
| Snapshot diverges from log | pure versioned reducer and continuous rebuild tests |
| Tutor loses Canvas events | post-success watermark only |
| Model output overwrites newer work | base version, source turn, cancellation, stale rejection |
| Subject logic leaks into Core | generic envelope + typed capability payloads/validators |
| Renderer over-constrains valid math | validators accept legitimate alternative methods |
| Canvas model becomes second Tutor | ScenePlan-only contract and no direct writes |
| External framework captures state | adapter boundary and fit spike before adoption |
| FE-02 prototype becomes architecture | preserve shell selectively; replace prose-derived adapter |
| Vision changes source truth | immutable original + derived lineage |
| UI feels slow | optimistic edge, no LLM for known interactions, measured budgets |
| Canvas interactions become false Evidence | existing Segment/Session intelligence authority remains unchanged |
| Scope expands into full curriculum platform | bounded subject activities and phased renderer catalog |

---

## 24. Deferred Capabilities

Deferred until separately promoted and proven:

- full Canvas Specialist production route;
- A2UI runtime adoption;
- AG-UI runtime migration;
- OpenMAIC package adoption;
- tldraw/freeform board;
- MathLive/JSXGraph/Konva except named fit tasks;
- generated SVG as routine output;
- sandboxed generated code;
- image generation;
- general simulations and 3D;
- full Vision workflow;
- full Science renderer catalog;
- full English/Arabic curriculum catalogs;
- collaborative Canvas;
- teacher/classroom administration;
- pressure Exam Mode.

---

## 25. Definition of Studio Foundation Complete

The foundation is complete only when:

1. governing decisions are promoted and current task state is aligned;
2. the Daily-Use database is migrated in place without data loss;
3. Studio events and snapshots are durable, versioned, reconstructable, and isolated;
4. the dedicated feed resumes after disconnect;
5. Tutor sees all unseen meaningful Canvas events and watermark failure rules pass;
6. Canvas-originated submissions trigger Tutor without synthetic Chat input;
7. Math, Science, English, and Arabic bounded activities run through the same Core;
8. FE-02 uses real Studio state and no prose/equation parsing as authority;
9. accessibility, RTL/LTR, mobile, failure, auth, and recovery acceptance pass;
10. performance budgets are measured and approved;
11. known activities need no Canvas-model call;
12. no Canvas interaction bypasses Safety or Learning Intelligence authority;
13. the accepted implementation is the same architecture intended for private production deployment.

---

## 26. Approval Effect

Approval of this document authorizes:

- `STUDIO-GOV-01` repository verification and governing-document promotion;
- creation of the dependency-ordered task sequence above;
- preservation/isolation of the FE-02 prototype before production Studio changes;
- correction of the Math renderer research before renderer code;
- promotion of the first implementation task only after the governance diff is accepted.

It does **not** authorize Codex to implement multiple phases in one run. Runtime, schema, protocol, renderer, and specialist work must proceed through the named task sequence with independent verification and Product Owner review.

Approval does **not** automatically authorize:

- Canvas Specialist production calls;
- installation of external packages;
- Vision implementation;
- production deployment;
- use of real Lina data in uncontrolled tests;
- broad curriculum ingestion or reproduction of protected source content.

Each remains behind its named task and acceptance gate.

---

## 27. Governance and State Foundation Closure Status

`STUDIO-GOV-01`, `FE-02-PRESERVE-01`, and `STUDIO-STATE-01` are complete and
accepted. The durable Studio state foundation is implemented at Alembic head
`b6e4c2a9d7f1`; the dependency sequence remains task-gated.

### 27.1 Only ready task

```text
STUDIO-SUBJECT-01 — Subject Capability Layer
```

### 27.2 Completed governance outcome

`STUDIO-GOV-01` completed:

1. repository verification against the checked-in repository and published research commits;
2. the governing promotion and dependency-ordered task sequence;
3. addition of this document as `docs/STUDIO_IMPLEMENTATION_PLAN.md`;
4. the minimum consistent governing/reference/task-state promotion;
5. recording of the dependency-ordered task sequence without starting runtime, schema, renderer, protocol, or FE-02 implementation.

`FE-02-PRESERVE-01` completed:

1. remote prototype preservation on `prototype/fe-02-studio-shell-2026-09-02` at `8648371480b0aac116af2a49e2d3d7493d26360f`, parent `059ff3aa6bfb983507470f484596bf05eae3b9b3`;
2. manifest at `prototype/FE-02_PROTOTYPE_MANIFEST.md`;
3. seven focused Node tests, TypeScript typecheck, production build, and SHA-256 identity verification;
4. retention of the prototype as non-authoritative, non-production architecture.

### 27.3 Current source baselines

- Studio orchestration synthesis: `9466da4d2eb3916f5c5cc61d047c3e800f276620`
- Grade 5 Math renderer planning pack: `eafd1121a240bd7873de46d260b296dcde52a46f`
- Application database head before Studio work: `a1d2e3f4b5c6`
- Accepted Studio state foundation head: `b6e4c2a9d7f1`

### 27.4 Immediate post-governance sequence

After accepted governance and prototype-preservation closure, the remaining work stays dependency ordered:

```text
STUDIO-STATE-01 — DONE / ACCEPTED
→ STUDIO-SUBJECT-01 — ONLY READY TASK
→ STUDIO-PROTOCOL-01
→ STUDIO-RUNTIME-01 / 02 / 03
→ Cross-subject production activities
→ FE-02-STUDIO-01
→ CURR-RENDER-MATH-01A — Grade 5 renderer correction gate
→ Grade 5 renderer tasks
→ STUDIO-ACCEPT-01
```

No later task is implicitly authorized by the existence of this sequence.
