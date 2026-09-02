# STUDIO-ORCH-01 — Architecture Synthesis

**Status:** Synthesis published for Product Owner decision. It is
non-authoritative until the decisions below are approved and promoted through
the governing task process. No Studio implementation is authorized by this
document.

## Recommendation

**Recommendation:** Adopt an application-owned, subject-agnostic Studio Core
with durable semantic event history plus materialized snapshots; retain the
existing Tutor as the sole Student-facing teaching authority; use deterministic
typed renderers for routine work; and evaluate an optional, application-scheduled
Canvas specialist only for explicitly eligible complex scenes.

**Reason:** This is the smallest architecture that lets Canvas be a first-class
Student input, gives Tutor complete meaningful Canvas observability, preserves
routine one-call Tutor latency, and supports future subjects without placing
subject logic or state authority in a model, renderer, or framework.

**Expected impact:** Release 1 can prove bidirectional learning with a
deterministic Math activity, while a second cross-subject proof can measure
whether a specialist ScenePlan improves a real representation enough to earn
latency and cost.

**Mandatory / Optional:** Mandatory architecture direction before active Studio
implementation; optional Canvas-specialist execution after Proof A; external
package adoption optional after explicit proof.

**Priority:** P0.

**Direct view:** Choose Option B as the target direction, but ship its
single-Tutor/deterministic-renderer subset first. Do not introduce a Teaching
Manager, hosted multi-agent runtime, generic freeform Canvas, or arbitrary
generated browser code.

**Risk of ignoring:** A visually rich Workspace will either become browser-only
and invisible to Tutor, or a second unbounded teaching system with stale state,
unsafe authority, and subject-specific rewrites.

**Confidence:** High on application-owned state and deterministic-first
direction; medium on the exact specialist threshold and package choices, which
Proofs A and B must measure.

## Evidence classification

### Facts — checked repository evidence

- The current authenticated Student path is turn-oriented: the Student stream
  route emits provisional delta events and one terminal turn event. It has no
  Canvas state lifecycle or concurrent event feed. See
  apps/api/routes/student.py:147-232.
- TutorRuntime invokes one streaming ModelTask.TUTOR request and persists the
  terminal result after validation. See services/tutor/runtime.py:314-506.
- ModelGateway is provider-neutral and records identifier-only operational
  lineage. ModelTask already includes Tutor, Session Evidence, Segment Evidence,
  Curriculum Semantics, Embedding, and Personal Facts; Canvas is not yet a
  task. See services/model_gateway/gateway.py:121-234,
  services/platform/db/models.py:47-55, and
  services/model_gateway/factory.py:25-205.
- Project policy already favors typed artifact specifications plus reusable
  renderers, says artifact failure must not block learning, and says Math and
  Science are first while the core must extend to future subjects. See
  docs/PROJECT_REFERENCE.md:1051-1140 and 1972-1985.
- Current FE-02 Workspace is a message-derived prototype adapter, not durable
  Studio authority. The uncommitted FE-02 shell is out of scope for this
  Synthesis.

### Assumptions — explicit and testable

- A make-ten activity can prove the smallest useful semantic Canvas operation.
- A current scene snapshot plus unseen semantic events is sufficient for most
  Tutor turns when an authorized older-history query is available.
- Routine visual requests are usually served adequately by a small typed
  renderer catalog.
- A cross-subject specialist proof can be measured against a deterministic
  baseline without altering the normal Tutor authority.

### Inferences — derived, not yet proven

- Event log plus materialized snapshot is more suitable than snapshot-only for
  reconstruction, cancellation, and Tutor observability.
- A general Canvas planner plus deterministic subject adapters is less complex
  than one specialist per subject while avoiding a permanently overloaded
  universal specialist.
- A custom Lina protocol informed by AG-UI semantics is a safer first boundary
  than a full AG-UI migration.

### Risks

- Adding Canvas state to LearningMessage, StructuredSegmentState, Candidate
  Event, Personal Facts, Learner Intelligence, or browser-only React state
  would violate existing authority boundaries.
- A Canvas specialist can become a second Tutor unless its objective, output,
  tools, and commit rights are constrained.
- A generic JSON blob without subject validators becomes weakly typed and
  untestable as subjects expand.
- Prompt compaction must never silently discard semantic Studio history.

### Open proof questions

- The first renderer/use case and learner-value measure.
- The specialist eligibility and timing/cost thresholds.
- The exact durable retention and older-history query policy.
- Whether a minimal Studio feed is sufficient for Proof A.
- Whether an external package measurably reduces effort without weakening
  authority, accessibility, or privacy.

## Target architecture

~~~text
Student
  | chat message or Canvas interaction
  v
Application-owned Studio Core
  |-- authenticate / authorize Student and LearningSession
  |-- Safety and Parent Boundary enforcement
  |-- semantic StudioEvent log and ordered sequences
  |-- StudioSnapshot and Scene/ArtifactInstance reducer
  |-- StudentInteraction classifier and Tutor-trigger policy
  |-- Model Gateway, specialist scheduler, cancellation, stale rejection
  |-- renderer/tool allowlists and domain-validator dispatch
  |-- privacy-minimized operational lineage
  |
  +--> Tutor / Chat (Student-facing teaching authority)
  |      receives learner/curriculum context + current snapshot +
  |      all semantic events since successful observation watermark +
  |      authorized older-history query tool
  |
  +--> deterministic renderer catalog
  |      executes validated subject payloads and emits semantic operations
  |
  +--> optional Canvas specialist
         receives fixed teaching objective + allowed capability pack +
         source turn + scene revision; proposes typed ScenePlan only
~~~

### Authority model

| Owner | Owns | Does not own |
| --- | --- | --- |
| Application | auth, Student/session scope, StudioEvent history, snapshots, sequences, versions, idempotency, scheduling, cancellation, stale rejection, Safety, Parent Boundaries, persistence, validator/renderer allowlists, operational privacy | pedagogical substitution |
| Tutor | teaching objective, conversation, final Student-facing response, sequencing, deciding Canvas usefulness, interpreting Canvas state/history | direct scene/state writes, safety finalization, Evidence/Personal Facts writes |
| Canvas specialist | visual/interactive composition within a fixed objective, typed ScenePlan/patch proposal, required explanatory/a11y metadata | independent objective, Tutor answer, direct persistence, authorization, safety, Evidence, learner intelligence |
| Renderer | deterministic execution of accepted specifications, accessible presentation, semantic operation emission, locale/direction behavior, safe failure | model reasoning, state acceptance, policy decisions |
| Subject capability layer | artifact catalog, interaction payload schemas, domain validator, subject fallback, fixtures and specialist tool profile | shared sequencing, transport, authorization or generic Studio lifecycle |

## Subject architecture

### Subject-agnostic Studio Core

Studio Core owns only cross-subject mechanics: orchestration, event history,
snapshots, sequences and scene versions, source-turn lineage, interaction
routing, cancellation, stale-result rejection, specialist lifecycle, transport,
reconnect, renderer boundary, Safety, authorization, accessibility foundations,
and locale/direction foundations.

It must not contain Math-specific fields such as equation, fraction, numerator,
number line, arithmetic operation, or geometry point. Those belong in typed
subject/renderer payloads.

### Subject Capability Layer

Use a small registry-style boundary, conceptually a SubjectCapabilityProfile.
The name is not approved. A profile supplies:

- subject key and supported grade range;
- Tutor and Canvas guidance constrained to that subject;
- allowlisted artifact/renderer catalog;
- valid Student interaction/action schemas;
- deterministic domain validators where applicable;
- accessibility text/control equivalents;
- curriculum-grounding requirements and subject fallbacks;
- specialist tool/skill profile, if a specialist is ever eligible;
- evaluation fixtures for each supported activity.

This is a registry/adapter boundary, not a plugin marketplace. Adding a subject
should primarily register a profile, artifacts/renderers, validators, guidance,
and fixtures. It must not rewrite Studio Core, event envelope, transport,
versions, cancellation, recovery, authorization, or specialist lifecycle.

### Generic envelope plus typed payloads

A conceptual StudioEvent envelope contains Student/session/Segment scope,
subject key, activity type, artifact type, actor, generic event meaning, source
turn, scene ID/version, monotonic sequence, idempotency key, causal references,
status, occurred time, payload schema version, and typed payload.

Generic meanings can cover object creation/move/resize/delete, value changes,
committed stroke, text annotation, token reorder, label assignment, option
selection, response/configuration submission, step completion, scene ready or
failed, and accepted/rejected specialist patch. Names are illustrative, not
approved.

The payload is selected by SubjectCapabilityProfile and renderer. Math may
validate a counter transfer or expression; Science a parameter/unit/process
relationship; English/Arabic token identity, span integrity, ordering,
grammar-label and answer schemas. Subject validators are called through the
capability boundary; Core does not inspect subject internals.

### Academic subject is not interaction language

Academic subject is Math, Science, English, Arabic, Geography, History, Coding,
or a future subject. Interaction language/locale is Arabic, English, mixed,
RTL, or LTR. Math may be taught in Arabic, English, or mixed language without
changing its Math capability. English and Arabic as academic subjects require
their own language-learning profiles, activities, grammar/vocabulary/writing
validators, and artifacts; RTL alone is not Arabic-subject support.

### Cross-subject specialist topology

| Topology | Assessment | Decision |
| --- | --- | --- |
| One general specialist with dynamically supplied capability pack | Lowest initial agent count; prompt/tool profile can be bounded per subject | Use only as a Proof B candidate |
| Specialist per subject | Higher subject isolation and potential quality ceiling | Defer; unnecessary until evidence shows a general planner fails a subject |
| General planner plus deterministic subject adapters/renderers/validators | Keeps subject correctness in typed code and reduces model scope | Recommended Release-1/Proof B shape |
| Hybrid general planner plus rare advanced domain specialist | Preserves an upgrade path for later complex domains | Long-term option only |

## Final architecture options

| Dimension | A. Single Teaching Agent | B. Tutor manager plus optional Canvas specialist | C. Teaching Manager above Tutor and Canvas |
| --- | --- | --- | --- |
| Educational/Chat authority | Tutor | Tutor | Separate manager plus Tutor |
| Canvas authority | App renderer | App plus optional constrained specialist proposal | Manager/coordinator plus specialist proposals |
| Application authority | Full state/policy | Full state/policy | Full state/policy, with more joins |
| Simple calls | 1 Tutor | 1 Tutor | 2 sequential |
| Complex calls | 1 Tutor | 1 Tutor plus optional Canvas call | 3 or more |
| Parallelism | None needed | Tutor and specialist only when eligible | possible, but high join complexity |
| First chat token | Best | Best for deferred/parallel specialist | often delayed |
| First useful Canvas | post-turn typed | post-turn typed | post-turn |
| Rich-ready Canvas | typed catalog ceiling | async when specialist eligible | async |
| Context duplication | none | limited objective/scene slice | high across manager/Tutor/specialist |
| Conflict/cancel/stale | app renderer guard | app version/source-turn guard | app must coordinate many actors |
| Specialist failure | not applicable | preserve chat and last valid scene | more failure pathways |
| Cost/ops | low | medium | high |
| Current Lina fit | strongest | strong after state/protocol proof | weak |
| Cross-subject extension | strong through profiles | strong through profiles/tool packs | potentially strong but overbuilt |

**Decision:** Option B is the target architecture, with Option A as its Release-1
routine path. Option C is rejected for current scope: no evidence justifies
another teaching authority, duplicated context, latency, and operational
complexity.

### Tutor complete Canvas observability and watermark correctness

Initial tutor_observed_sequence_watermark is the highest committed semantic
Studio sequence already acknowledged by a previous successfully committed Tutor
turn, or zero/no-observation for a new Studio context.

For a Tutor call, Studio Core selects the current snapshot plus all semantic
events with sequence greater than that watermark. Events that arrive while the
Tutor is generating receive later sequences and remain unseen for that call;
they are included in the next Tutor selection or available through the history
query. The selected events are never marked observed merely because context was
built.

The watermark advances atomically only after all four conditions hold: the call
received the selected events, provider work completed, terminal output passed
validation, and the terminal Tutor turn committed durably. Provider failure,
incomplete stream, timeout, cancellation, terminal validation failure,
transaction rollback, or persistence failure leaves the watermark unchanged.
The same unseen events must be selected for the next successful Tutor reasoning
step. A retry uses the same event selection; it does not duplicate semantic
events. Cross-Student, cross-session, and cross-Segment references are rejected
before snapshot/history projection.

Tutor can query older full semantic history through an application-owned,
authorized tool/service. This supports complete observability without replaying
the whole log in every prompt. Browser hover, pointermove, viewport, uncommitted
drag, transient focus, and animation frames are not semantic events. A committed
stroke, move/transformation, answer, annotation, reordering, configuration,
step completion, scene transition, patch, cancellation, or supersession is.

## Canvas event to Tutor reaction policy

| Class | Examples | Durable state | Tutor behavior |
| --- | --- | --- | --- |
| UI-ephemeral | hover, viewport, pointermove, unfinished drag, transient selection | browser only | never call Tutor |
| Semantic record-only | committed exploration move, simulation value change, scene navigation, unfinished stroke | append event and reduce snapshot | no call unless activity contract requests it |
| Tutor-triggering StudentInteraction | answer/configuration submission, help request, drawing for review, explicit inspect request, response opportunity complete | append event plus StudentInteraction | schedule one Tutor turn with snapshot and unseen events |
| System/specialist lifecycle | scene ready/failed, timeout, superseded result, patch accepted/rejected | append relevant event/status | visible status; call Tutor only through explicit policy |

Minimum Release-1 trigger policy: a typed activity declares which semantic
operations become StudentInteraction. Group rapid record-only events into an
activity-defined transaction or a short server-side debounce window; never group
across explicit submissions or source-turn boundaries. Canvas is an equal input
channel because a declared StudentInteraction routes to Tutor without an
equivalent chat message, not because every pointer movement calls a model.

## Shared Studio State model

### State strategy comparison

| Strategy | Strength | Failure | Decision |
| --- | --- | --- | --- |
| Snapshot only | fast rendering | no complete reconstruction or reliable unseen-event selection | reject |
| Event log only | complete audit/rebuild | expensive reads/render and hard reconnect | reject as sole model |
| Event log plus materialized snapshot | ordered history plus efficient read/Tutor projection | requires reducer/version tests | adopt |
| CRDT/freeform shared state | useful for future collaborative/freeform editing | complex merge/authorization/semantic extraction | defer |

### Conceptual records

| Record | Purpose/lifecycle | Durability and ownership | Subject/Tutor/Canvas/frontend visibility |
| --- | --- | --- | --- |
| StudioRuntime | session-scoped lifecycle and active status | durable application record or derived runtime projection; scoped to LearningSession/Segment | generic; Tutor sees projection; frontend sees safe status |
| StudioEvent | ordered meaningful operation/state change | durable source of Studio truth; app validates and assigns sequence | generic envelope plus typed subject payload; Tutor sees selected/history; specialist sees relevant projection |
| StudioSnapshot | materialized current scene/activity state | durable/rebuildable projection owned by reducer | generic envelope plus typed scene; safe subset to frontend/Tutor/specialist |
| ArtifactInstance or Scene | active accepted artifact identity, renderer and version | durable/rebuildable under snapshot/event lineage | subject scoped; frontend renders accepted view |
| StudentInteraction | declares a semantic operation requires Tutor policy | durable event-linked request status | Tutor receives it; frontend sees safe pending/complete status |
| CanvasSpecialistRun | source turn, capability, base version, job status, deadline, cancellation/supersession | durable operational record; no content-rich trace | specialist/app details; frontend safe status only |
| Tutor observation watermark | last fully committed observation sequence | durable with successful terminal Tutor commit | app/Tutor context only |
| Pending operation | idempotency/expected version request | short-lived durable or transactional state | app only; safe client status |

No record overloads StructuredSegmentState, LearningMessage payload, Candidate
Event, Personal Facts, Learner Intelligence, or browser React state. Retention,
rebuild/reducer checkpoints, and history-query scope need Product Owner policy;
all records are authorized by Student, LearningSession, and Segment.

## Transport and protocol decision

| Option | Concurrent/Canvas-first fit | Main issue | Decision |
| --- | --- | --- | --- |
| A. Extend Tutor SSE only | poor for independent progress, operations and reconnect | mixes scene lifecycle into Tutor terminal authority | reject |
| B. Current Tutor SSE plus dedicated Studio event feed | strong | requires new protected event transport | Release-1 target after Proof A |
| C. Substantial AG-UI adoption | capable snapshots/deltas/tool/lifecycle | transport/runtime migration and ownership overlap | proof spike only |
| D. Custom Lina protocol informed by AG-UI | exact authority, source/version and privacy design | local protocol/reducer work | long-term target |
| E. terminal envelope plus snapshot polling | adequate for narrow Proof A only | poor parallel/interleaved UX | first-proof fallback |

**First proof transport:** keep existing Tutor SSE exactly authoritative for
delta/terminal Tutor text; use authenticated command endpoints for Canvas
operations and a safe snapshot read/reconnect path. A small resumable Studio
event feed is preferable if needed to prove ordering; polling is acceptable only
where Proof A has no concurrent specialist work.

**Release-1 transport:** current Tutor SSE plus dedicated authenticated,
resumable Studio event/state feed with monotonic sequence, snapshots after a
watermark, idempotency keys, expected scene versions, server broadcasts,
cancel/supersede status, and typed cross-subject payloads.

**Long-term transport:** a Lina-owned protocol retaining these semantics. Reuse
AG-UI concepts of run/lifecycle events, StateSnapshot, StateDelta/JSON Patch,
CUSTOM events, tool-event vocabulary, capabilities and bidirectional state
synchronization. Do not adopt AG-UI merely to avoid designing authority
boundaries.

## Canvas specification and generative UI decision

| Candidate | Contribution | Decision |
| --- | --- | --- |
| Small Lina ArtifactIntent/ScenePlan | source-turn, subject, activity, renderer, version, typed data/action/a11y contract | adopt as first-proof contract |
| Actual A2UI | mature declarative message/catalog/data/action/progressive model | proof spike only |
| A2UI-inspired Lina schema | vocabulary for catalog/data/action/recovery without runtime dependency | partial adopt |
| OpenMAIC DSL subset | typed scene/widget contract reference | bounded evaluation after Proof A |
| Specialist typed ScenePlan | optional proposal for eligible complex visual composition | Proof B |
| Specialist generated SVG | narrow fallback only | defer |
| tldraw scene/action model | action/history design reference for future freeform work | reference/defer |
| Sandboxed HTML/CSS/JavaScript | isolated rare capability | reject for first proof; future gated |

The first-proof contract must include subject key, artifact/activity type,
source-turn lineage, scene version, payload-schema version, an allowlisted
renderer/component catalog, semantic Student actions, validator identity,
accessibility text/control equivalents, locale and direction policy, mobile
behavior, and deterministic text fallback. It may not execute model-authored
code.

External adoption boundaries:

| Candidate | Current maturity/license | Integration and ownership boundary | Security/proof required |
| --- | --- | --- | --- |
| A2UI | v0.9.1 Current Production; v1.0 Candidate; official React/web core path | messages terminate at Lina catalog/validators; Lina owns Studio state and actions | prove catalog allowlist, action validation, a11y/RTL/mobile, bundle and recovery |
| AG-UI | active 2026 MIT protocol; Python/TypeScript paths; demo is not production proof | reuse event/state semantics; Lina owns transport/persistence/auth | prove FastAPI/SSE compatibility, resume/order/privacy and migration cost |
| OpenMAIC | THU-MAIC/OpenMAIC v1.0.0 2026-08-27; MIT after v0.3.0 | evaluate DSL/renderer only; reject full classroom, imports/storage/generation ownership | package fit, sandbox/a11y/bundle, contract mapping |
| tldraw | source available tldraw license; production key required | future freeform only; Lina would own semantic event extraction | license, bundle, a11y/mobile, state lock-in proof |
| Agents SDK | current code path after Agent Builder sunset; hosted multi-agent experimental | optional bounded Canvas wrapper; Lina owns Gateway/state/policy | redaction, provider differences, cancel/recovery, specialist quality proof |

Sources were accessed 2026-09-02:
- https://openai.com/index/introducing-agentkit/
- https://openai.github.io/openai-agents-python/models/
- https://github.com/a2ui-project/a2ui/blob/main/docs/public/guides/renderer-development.md
- https://docs.ag-ui.com/
- https://docs.ag-ui.com/concepts/events
- https://docs.ag-ui.com/integrations
- https://github.com/ag-ui-protocol/open-ag-ui-canvas
- https://github.com/THU-MAIC/OpenMAIC/releases
- https://github.com/THU-MAIC/OpenMAIC/blob/main/CHANGELOG.md
- https://tldraw.dev/community/license
- https://tldraw.dev/releases/v4.0.0
- https://ai-sdk.dev/docs/introduction
- https://apps.modelcontextprotocol.io/

## Canvas execution ladder

| Tier | Trigger/use cases | Owner, contract and renderer | Interaction/events/validation/a11y | Latency/fallback/adoption gate |
| --- | --- | --- | --- | --- |
| 1. Typed React/SVG | routine number/fraction/process/annotation views | app plus subject profile; ArtifactIntent; native React/SVG | typed operations, domain validator, DOM/SVG alternatives, RTL/mobile | post-turn; text fallback; Proof A baseline |
| 2. MathLive | structured math entry | Math profile; expression contract | expression submission, parser/equivalence validation, keyboard/Arabic/mobile proof | local entry/post-turn feedback; text input fallback; separate approval |
| 3. JSXGraph | geometry/graph construction | Math profile; typed geometry scene | named construction actions, geometric validator, keyboard/a11y proof | post-turn; static SVG fallback; separate approval |
| 4. React Konva | spatial manipulative/labeled diagram | profile typed scene graph | committed transforms only, DOM equivalent, action validator | post-turn/async; SVG fallback; separate approval |
| 5. Lina declarative ScenePlan | catalog gap with known safe primitives | application/spec plus deterministic renderer | declared action schemas, subject validator and a11y metadata | post-turn/async; typed fallback; Proof A/B contract |
| 6. A2UI-style declarative UI | structured panels/forms/steps need progressive composition | Lina catalog consuming optional A2UI-like messages | registered actions and validation/recovery, a11y/RTL/mobile catalog | progressive; typed fallback; package proof |
| 7. Canvas specialist | eligible custom visual composition | Model Gateway Canvas task/job returns ScenePlan | app validates source/version/catalog; no direct writes | async rich-ready; last-valid/text fallback; Proof B |
| 8. Freeform/tldraw | proven freeform spatial work | future selected SDK/profile | shape actions filtered into semantic events; a11y/mobile proof | local plus async agent actions; typed fallback; future proof |
| 9. Generated SVG | rare safe illustrative gap | specialist returns sanitized AST/string | mostly static; separate typed controls; text alternative | async; description fallback; future gate |
| 10. Sandboxed HTML | rare isolated validated widget | isolated renderer plus narrow message bridge | allowlisted semantic messages only; strict sandbox/CSP/origin | async; typed fallback; future gate |
| 11. Generated image | supporting real-world/science visual | media capability plus description | no sole semantic interaction; provenance/safety review | async; text/diagram fallback; future gate |
| 12. Simulation | validated parameterized process/model | subject simulation package | typed controls/events, deterministic domain model, full a11y/mobile | local/post-load; static fallback; future gate |
| 13. Optional 3D | genuinely spatial concept | subject-specific 3D model | typed meaningful operations; mandatory 2D/text equivalent | slowest rich-ready; 2D fallback; future gate |

No subject must use all tiers.

## FE-02 prototype judgment

**KEEP PARTS / MATERIAL ORCHESTRATION REDESIGN.**

Keep the greenfield route separation, Desktop Chat/Workspace placement,
project-owned client controller, existing provisional-delta/terminal-turn
handling, content-free lifecycle trace, and responsive presentation lessons.
Treat as prototype-only the Tutor-prose parsing, equation regex extraction,
message-derived Canvas assumptions, duplicated question/guidance cards, and any
browser-local visual state. Replace the Workspace adapter with the Studio
snapshot/event/scene boundary, typed renderer contract, validated semantic
operations, and a dedicated Studio transport/read model. Do not alter it in
this Synthesis.

## Two-stage proof strategy

### Proof A — Bidirectional Studio Foundation

**Exact case:** Math, make-ten 9 + 6.

Tutor establishes make-ten; a deterministic ten-frame/counter renderer displays
the activity; Lina transfers one item from six to nine; the application commits
one semantic operation; snapshot/version update; Tutor receives snapshot plus
unseen event and continues without Lina restating it. Reload restores accepted
scene; duplicate operation is idempotent; stale operation is rejected; Canvas
failure never blocks chat; the operation is not automatically Evidence.

Measures: event/snapshot reconstruction; causal ordering; watermark success and
failure behavior; end-to-end latency; action completion; keyboard/focus/text
alternative; Arabic/English/mixed direction; narrow-screen behavior; recovery;
and no false Evidence.

### Proof B — Cross-subject plus Canvas-specialist value

**Exact case:** Science, water-cycle process relationship activity.

Compare a deterministic Science profile renderer (typed stages/relationships and
validator) with an eligible Canvas specialist typed ScenePlan for a custom
representation. The same generic event envelope must carry subject key, scene
version, source turn, typed process/label action, and validator result. Tutor
observability is identical. The specialist cannot become a second Tutor.

Measures: representation correctness, pedagogical usefulness, first Canvas and
rich-ready time, failure rate, cost, accessibility, RTL/LTR/mobile, manual
renderer effort avoided, and quality improvement over deterministic baseline.

## Specialist eligibility, latency, cost, and failure envelope

### Initial eligibility policy hypothesis

Use application rule plus Tutor structured request. Tutor may request Canvas but
the application permits specialist execution only when all are true:

1. a subject capability/profile and safe renderer catalog are present;
2. no approved deterministic renderer adequately expresses the activity, or the
   required composition materially affects understanding;
3. the requested output is a typed ScenePlan within an allowlist;
4. a deterministic subject validator or safe non-validation fallback exists;
5. the Student is in an active session/source-turn and no newer causal boundary
   supersedes it;
6. the expected delay does not block an immediate Tutor explanation.

Do not use a specialist for ordinary arithmetic, casual conversation, already
covered typed views, decorative requests, unsafe/unvalidated activities,
insufficient domain capability, or any flow where delay would harm the learning
exchange.

### Proof thresholds — hypotheses, not SLAs

| Dimension | Routine path | Eligible specialist path |
| --- | --- | --- |
| Tutor calls | one primary call | one Tutor plus at most one Canvas call |
| first chat token | unchanged from current baseline | unchanged; specialist must be parallel/deferred |
| terminal chat | current baseline | current baseline; no specialist join required |
| first useful Canvas | post-terminal typed view | same typed view or status, never wait for specialist |
| rich-ready Canvas | supported renderer immediately after state commit | asynchronous; target within a learner-tolerable short wait, evaluate as a coarse 5–15 second hypothesis |
| specialist timeout | not applicable | 15 seconds proof hypothesis; preserve chat/last valid scene |
| retry | normal opening/session retry only | server-owned only if source turn/revision remains active; never replay Student content |
| new Student turn | n/a | cancel/supersede job; reject late result |
| fallback | Tutor text/typed safe view | immediate deterministic/last-valid view |
| cost class | one normal model call | two calls only for eligible turns; record separately |

Canvas specialist runs should be application-owned jobs/direct Model Gateway
execution for the proof, not blocking agent-as-tool loops. A later proof may
compare a bounded Agents SDK wrapper, but it must not own sessions, Studio state,
or transport.

## Turn examples

| Scenario | Visible Chat/Canvas and capability | Events, watermark, trigger and fallback |
| --- | --- | --- |
| 1. What is 14 + 7? | Tutor answers; optional typed number representation if catalog fits. One Tutor call. | no Canvas interaction required; no new specialist; text fallback |
| 2. Make-ten 9 + 6 | Tutor opens typed ten-frame; student transfers counter. Math profile/React-SVG. | committed transfer → snapshot V+1 → StudentInteraction if activity expects feedback → Tutor sees event; watermark advances only on committed turn |
| 3. Fraction comparison | Tutor opens typed fraction bars; student selects/submits comparison. | typed answer event validates fraction constraint; Tutor triggered only at submission; fallback text/diagram |
| 4. Canvas-first geometry | app loads approved geometry scene before Chat response. Math profile/typed geometry or later JSXGraph. | construction operation recorded; Tutor later sees unseen events/history query; invalid/stale construction rejected |
| 5. Student drags object | visible local drag then commit. | pointer noise ephemeral; commit is record-only or trigger per activity contract; no automatic model call |
| 6. Student submits Canvas answer | canvas shows pending then response. | response submission creates StudentInteraction; one Tutor reasoning turn receives snapshot/events; failure retains unseen event |
| 7. Student draws for review | Canvas preserves committed drawing representation; Tutor receives safe reference/summary. | committed stroke or drawing submission semantic; trigger only on explicit review; unsupported renderer falls back to explanation |
| 8. Custom Science visual | Tutor streams explanation and Canvas shows preparing/typed base. Specialist may run with Science capability. | typed ScenePlan validates objective/version/catalog; scene-ready commit; no direct specialist teaching output |
| 9. Specialist fails | chat remains usable; last valid or typed Canvas persists with honest status. | failure event records status; no automatic Tutor replay; optional Tutor reaction only policy-driven |
| 10. New question while specialist runs | new chat begins immediately; stale visual never appears. | new causal boundary cancels/supersedes run; source turn/version rejects late plan |
| 11. Science variable/process | typed simulation controls or ordered stages. | value change record-only; configuration/submission triggers Tutor as activity declares; unit/process validator |
| 12. English sentence construction | word tokens reorder, then submit. English academic profile, locale may be Arabic/English. | token reorder events; submission triggers Tutor; syntax/answer validator; DOM textual equivalent |
| 13. Arabic grammar annotation | Student assigns roles/annotates spans. Arabic academic profile. | span/label event preserves token identity; submit triggers Tutor; grammar/schema validator; RTL controls |
| 14. Cross-subject transition | Math scene closes/archives; Science scene starts under new subject profile. | generic lifecycle events; no Math renderer/validator leaks into Science; new capability/profile scope |
| 15. Math Arabic vs English | same Math artifact and validator, local copy/direction differs. | subject remains Math; locale/direction changes renderer text/layout only; event payload unchanged where semantics same |
| 16. Arabic academic subject | Arabic grammar/spelling activity, not merely RTL layout. | Arabic profile supplies grammar artifacts/validators/guidance; language content action is subject-specific |

## Comparative decision matrix

Scores: 1 = weak, 5 = strong. Cost, effort, and operational complexity score
higher when lower burden.

| Criterion | A Single Tutor | B Tutor plus optional specialist | C Teaching Manager plus specialists | Why |
| --- | ---:| ---:| ---:| --- |
| pedagogical coherence | 4 | 5 | 3 | B retains one Tutor while adding bounded composition |
| full Canvas observability | 4 | 5 | 5 | app-owned protocol, not topology, provides this |
| Canvas quality ceiling | 3 | 5 | 5 | B/C can use specialist; C has no proven incremental gain |
| active Student interaction | 4 | 5 | 5 | renderer/state contract is decisive |
| routine first-token latency | 5 | 5 | 2 | C adds manager call |
| complex Canvas latency | 5 | 4 | 2 | B supports parallel/deferred specialist |
| cost | 5 | 4 | 1 | C has 3+ calls |
| failure isolation | 5 | 5 | 2 | B specialist can fail independently |
| implementation effort | 5 | 3 | 1 | B needs state/jobs; C also needs manager join |
| operational complexity | 5 | 3 | 1 | C increases tracing/cancel/recovery paths |
| observability/debuggability | 4 | 5 | 3 | B has causal app coordinator |
| provider flexibility | 4 | 5 | 4 | B supports per-task Canvas route |
| accessibility/RTL/mobile | 4 | 4 | 4 | determined by renderer/profile, not agent count |
| current Lina compatibility | 5 | 4 | 2 | B extends Gateway/state cleanly |
| FE-02 migration path | 4 | 5 | 2 | B replaces adapter without new Tutor manager |
| cross-subject extensibility | 4 | 5 | 4 | B capability packs are explicit |
| subject versus locale separation | 5 | 5 | 5 | profile design provides it |
| effort to add subject | 4 | 4 | 2 | C multiplies prompts/agents |
| subject logic leakage risk | 4 | 5 | 3 | profiles keep B Core clean |

## Implementation sequence — no code

### A. Must change before FE-02 acceptance

| Task | Purpose/output | Dependencies and likely domains | Verification | PO approval | Schema/runtime/dependency/model call |
| --- | --- | --- | --- | --- | --- |
| STUDIO-STATE-01 | Define and implement minimum StudioEvent, snapshot, scene version, watermark, StudentInteraction, idempotency and cancellation contract | Product Owner architecture decision; services Studio/Tutor, platform DB, API read model | contract tests for ordering, rebuild, isolation, idempotency, watermark non-advance on failure | yes | schema yes; runtime yes; no dependency; no extra model |
| STUDIO-SUBJECT-01 | Define minimal SubjectCapabilityProfile, renderer registry seam, validators, action payload boundary; Math/Science/one language fixture | STUDIO-STATE-01; Tutor/subject/artifact domains | register fixture subject without Core/transport/orchestration change | yes | schema no initially; runtime yes; no dependency; no model |
| STUDIO-PROTOCOL-01 | Prove Tutor SSE plus Studio state/operation transport, reconnect, cancel and stale rules | STUDIO-STATE-01 | protocol tests for chat-first/canvas-first/parallel/interleaved/reconnect | yes | schema possibly; runtime/API yes; no dependency; no model |
| STUDIO-RENDER-01 | Build typed deterministic make-ten renderer and accessible operation contract | STATE/SUBJECT/PROTOCOL | Proof A automated and authenticated visual tests; no false Evidence | yes | schema uses prior; frontend/runtime yes; no dependency; no model |
| FE-02-STUDIO-01 | Replace prototype Canvas adapter only after above proofs pass; preserve valid controller streaming behavior | all prior tasks, approved visual review | contract, accessibility, RTL, visual and failure review | yes | possible schema/runtime; no dependency by default; no new model |

### B. Next bounded proofs

| Task | Purpose/output | Dependencies and likely domains | Verification | PO approval | Schema/runtime/dependency/model call |
| --- | --- | --- | --- | --- | --- |
| STUDIO-PROOF-A | End-to-end make-ten 9+6 foundation measurement | STATE/SUBJECT/PROTOCOL/RENDER | all Proof A measures and real learner review | yes | uses approved prior changes; no dependency; no extra model |
| STUDIO-SPECIALIST-01 | Compare deterministic Science water-cycle baseline with optional specialist ScenePlan | Proof A; Science profile; Canvas route design | quality/latency/cost/failure/a11y comparison and no second Tutor authority | yes | likely schema/job/runtime; no dependency initially; one optional model call |
| STUDIO-REUSE-01 | Bounded A2UI/AG-UI/OpenMAIC DSL/renderer evaluation record | Proof A contract | concrete adopt/partial/reject evidence: bundle, a11y, security, mapping | yes | no production change unless separately approved; no model |

### C. Can be deferred

| Task | Purpose/output | Dependencies and likely domains | Verification | PO approval | Schema/runtime/dependency/model call |
| --- | --- | --- | --- | --- | --- |
| STUDIO-MATH-INPUT-01 | Evaluate MathLive structured input for a named activity | Proof A and Math profile | keyboard/mobile/equivalence/safety tests | yes | no schema required initially; frontend; dependency proposal; no model |
| STUDIO-GEOMETRY-01 | Evaluate JSXGraph geometry renderer | profile/validator contract | construction/a11y/RTL/mobile tests | yes | frontend; dependency proposal; no model |
| STUDIO-SPATIAL-01 | Evaluate Konva for a named manipulative | profile/event contract | semantic transform/a11y/mobile tests | yes | frontend; dependency proposal; no model |
| STUDIO-A2UI-01 | Actual A2UI implementation proof if local Scene spec loses materially | successful local baseline | catalog/action/security/recovery/bundle proof | yes | frontend/runtime; dependency proposal; optional model |
| STUDIO-AGUI-01 | Protocol compatibility proof only if custom feed becomes costly | Release-1 transport evidence | SSE/FastAPI resume/order/privacy mapping | yes | API/runtime; dependency proposal; no model |

### D. Future only

| Task | Purpose/output | Dependencies and likely domains | Verification | PO approval | Schema/runtime/dependency/model call |
| --- | --- | --- | --- | --- | --- |
| STUDIO-FREEFORM-01 | tldraw/freeform Canvas proof | real learner need and licensing decision | license/bundle/a11y/mobile/state isolation | yes | frontend/runtime; dependency; optional model |
| STUDIO-GENSVG-01 | sanitized generated SVG fallback | renderer catalog failure evidence | sanitizer/a11y/provenance/fallback tests | yes | runtime; possible dependency; model call |
| STUDIO-SANDBOX-01 | isolated custom interactive code | no typed renderer/simulation fits | CSP/sandbox/message/auth/a11y test suite | yes | runtime/frontend; dependency possible; model call |
| STUDIO-SIM-01 | validated subject simulation | subject model/validator and real-use need | deterministic model/replay/a11y/mobile learning proof | yes | runtime/frontend; dependency possible; no model required |
| STUDIO-3D-01 | domain-specific 3D proof | proven spatial learning benefit | 2D fallback/performance/a11y/device evidence | yes | frontend; dependency likely; optional model |

## Rejected alternatives

- **Teaching Manager above Tutor and Canvas:** rejects a second teaching authority
  and routine latency/cost without evidence of learning gain.
- **Hosted multi-agent beta:** experimental, provider-side orchestration and
  in-flight recovery limits conflict with reconstructable child-data state.
- **AG-UI as immediate runtime migration:** its semantics are useful, but a
  full migration does not solve Lina authority design.
- **A2UI as immediate dependency:** mature enough to evaluate, not proven as
  smaller/better than a local typed ScenePlan.
- **OpenMAIC full platform:** broad classroom, media, material, storage and
  agent assumptions exceed Studio scope.
- **tldraw as main foundation:** freeform board and license/bundle/state burden
  precede a demonstrated learner need.
- **Generated HTML/JS or generic SVG as routine Canvas:** unacceptable security,
  correctness and accessibility boundary.
