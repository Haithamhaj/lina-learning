# STUDIO-ORCH-01 — Shared Studio State and Protocol Study

**Status:** Research only. Names and shapes below are conceptual, not approved
API, event, schema, or database contracts.

## Facts

The current public Student protocol is turn-oriented: one authenticated request
opens/resumes a session, one authenticated SSE request streams a Tutor turn,
and the client resolves provisional `delta` to terminal `turn`. It has no
bidirectional Canvas operation channel, Canvas event log, Studio snapshot, or
reconnection semantics beyond reloading session messages.

The current system nevertheless supplies useful anchors: authenticated Student
ownership and `LearningSession`; session-local Segment identity; ordered raw
Student/Tutor messages; source IDs; server-validated actions/checks; Model
Gateway lineage; private Structured Segment State; and content-free browser
lifecycle tracing. These are inputs to a Studio protocol, not an existing
Shared Studio State implementation.

## Required properties

1. Chat and Canvas see the same active Studio situation.
2. Every meaningful Canvas operation is structured, source-linked, and
   reconstructable for Tutor context; raw pointer/move noise is filtered.
3. Canvas does not create independent learning conclusions, Safety decisions,
   Personal Facts, or Evidence.
4. Tutor commands, Canvas-agent patches, and Student Canvas operations are
   ordered, cancellable, and resistant to stale writes.
5. A Student can continue in Chat without restating completed Canvas work.
6. Failure of specialist, renderer, or connection never blocks safe Chat.

## Assumptions

- Studio state is application-owned and scoped to one Student and active
  learning session.
- An event log and materialized snapshot can coexist: events explain what
  changed; the snapshot serves low-latency rendering and bounded Tutor context.
- The event log holds structured operations, not raw pointer telemetry or an
  unrestricted model-generated scene serialization.

## Candidate ownership model

```text
LearningSession (existing durable ownership)
  -> active Segment reference (existing lineage anchor)
  -> StudioEventLog (durable meaningful operations, ordered)
  -> StudioStateSnapshot (versioned materialized/read model)
  -> ActiveScene / ArtifactInstance (derived, source-linked, versioned)
```

| State class | Example | Lifecycle | Tutor visibility |
| --- | --- | --- | --- |
| Ephemeral UI | hover, viewport, uncommitted drag | Browser only | No |
| Meaningful Student operation | object moved, answer submitted, stroke committed | Durable event | Bounded structured context |
| Active scene snapshot | objects, values, active step, selection | Materialized/versioned | Bounded snapshot/context |
| Tutor command | request visual, set teaching step | Durable when accepted | Yes |
| Canvas agent patch | scene update, ready/failed | Durable event plus scene version | Yes |
| Derived interpretation | Candidate/Evidence | Existing protected pipeline only | Existing rules |

`selected_object` should normally remain transient. It becomes durable only
when it is meaningful to the activity or Tutor continuation. A drawing needs a
bounded source-safe representation or original asset reference; browser pointer
samples are not Tutor context.

## Candidate conceptual records

```text
StudioEvent
  event_id, schema_version, student_id, learning_session_id, segment_id
  sequence, occurred_at, actor (student | tutor | canvas_agent | system)
  kind, source_turn_id?, scene_id?, base_scene_version?
  typed_operation_payload, result_status, causal_event_ids[]
  renderer_registry_version?

StudioSnapshot
  snapshot_id, schema_version, learning_session_id, segment_id
  sequence_watermark, active_goal_ref, active_teaching_turn_id
  active_scene_id, scene_version, teaching_step, bounded_scene_summary
  pending_jobs[], tutor_stream_status, canvas_generation_status
  last_meaningful_student_operation_ref, updated_at
```

The snapshot must not copy Personal Memory, Candidate metadata, raw Safety
directives, model prompts, or arbitrary historic Canvas data. The full event
sequence remains available to server-side reconstruction when required.

## Event families

| Actor | Event family | Illustrative operations |
| --- | --- | --- |
| System | lifecycle | studio opened, snapshot restored, job cancelled |
| Tutor | pedagogical command | visual requested, teaching step set, interaction requested |
| Canvas specialist | generation | scene planned, patch accepted, ready, failed |
| Student | meaningful operation | object created/moved/deleted, value changed, stroke committed, option selected, configuration submitted |
| Renderer/tool | deterministic result | validation failed, interaction completed, unsupported operation |

The server accepts only allowed actor/kind pairs and validates Student/session
ownership, scene existence, base version, operation bounds, and source-turn
lineage before recording an event.

## Candidate bidirectional protocol

```text
Client -> Studio command endpoint or event stream
  authenticated Canvas operation + scene_id + base_version
  -> server validation -> append StudioEvent -> reduce snapshot
  -> optional Tutor wake-up / next-turn context

Tutor / Canvas agent -> server
  typed command, spec, or patch + causal source IDs + expected scene version
  -> policy/schema/registry validation -> event + snapshot update

Server -> client
  existing Tutor SSE for provisional conversational text
  plus dedicated authenticated Studio state delta or resumable event feed
```

The current Tutor SSE should retain terminal-turn authority. A separate Studio
channel avoids representing concurrent scene streaming as a partial Tutor text
reply; Synthesis must compare it to a small expanded terminal envelope for
simple cases.

## Versioning, concurrency, and stale protection

- Each scene-mutating operation carries `base_scene_version`.
- The server assigns the monotonic event sequence and next scene version;
  arrival order is never truth.
- Canvas patches name their source Tutor turn and expected base scene version;
  stale patches are rejected or re-planned.
- A new Student question establishes a causal boundary. Pending jobs for a
  superseded teaching turn are cancelled or hidden diagnostics only.
- Retryable Student submits and job completions require idempotency keys.
- Reconnect obtains a snapshot and events after a sequence watermark.
- Cross-Student, cross-session, and cross-Segment references fail validation.

## Required event sequences

### 1. Chat-first

```text
Student sends chat question
-> existing Tutor SSE delta(s)
-> terminal Tutor turn persists
-> Tutor command requests a scene for source turn T
-> Canvas job/spec validates against T and snapshot V
-> SCENE_READY event creates V+1
-> client renders committed workspace
```

### 2. Canvas-first

```text
Student opens approved Canvas activity
-> snapshot identifies active scene/task
-> Student performs meaningful operation O at V
-> server records O and snapshot becomes V+1
-> Tutor receives bounded operation/state context on next turn
-> Tutor reacts in chat or issues a Canvas command
```

### 3. Parallel

```text
Student asks for help
-> Tutor begins SSE text
-> accepted teaching intent starts Canvas specialist independently
-> terminal Tutor turn commits
-> Canvas result validates source turn/version
-> committed scene update arrives later
```

The Canvas must be visibly preparing, not claim a completed Tutor explanation,
until its own committed state exists.

### 4. Interleaved

```text
Tutor terminal turn establishes step 1
-> Canvas displays step 1
-> Student manipulates item
-> operation event updates snapshot
-> Tutor consumes operation summary and responds with step 2
-> Canvas agent patches expected version
-> Student continues without repeating the action
```

### 5. Student manipulates Canvas

```text
Client emits typed operation + idempotency key + base scene version
-> server authorizes Student/session/scene
-> renderer/tool validates parameters
-> append event and snapshot/version
-> broadcast committed state
-> bounded operation history enters later Tutor context
```

### 6. Canvas Agent updates visual

```text
Specialist emits typed patch/spec + source_turn_id + base version
-> server validates policy, lineage, renderer type, and version
-> accepted patch becomes event + snapshot
-> client applies committed update
-> Tutor sees resulting scene summary and causal sequence
```

### 7. Specialist fails

```text
Job error -> CANVAS_FAILED event (identifier/status only in browser trace)
-> last valid scene remains available
-> Chat remains ready; no Tutor replay or Student resubmission
-> optional server-owned bounded retry only if source turn is still active
```

### 8. New question while specialist generates

```text
New Student message creates newer active turn/causal boundary
-> pending job cancelled or marked superseded
-> later completion discarded as stale
-> Tutor handles new question from current Studio snapshot
```

## Risks

- Event logs grow rapidly if UI noise is not filtered.
- A reducer bug can diverge snapshot from history.
- Parallel completion can overwrite newer Student work without strict versions.
- Replayed hidden model text can violate context-minimization/privacy rules.
- Treating visual submission as Evidence before the existing review path can
  corrupt learner-intelligence authority.

## Contradictions

| Requirement | Existing baseline | Needed design clarification |
| --- | --- | --- |
| Tutor sees Canvas history | Tutor context has messages/segment state only | Event-to-context projection and bounded history window |
| Canvas updates independently | SSE is one Tutor stream | Additional Studio transport or retrieval pattern |
| Student manipulates/draws | API accepts chat/actions/checks only | Typed operation authorization and original-work handling |
| Canvas Agent patches | Gateway has Tutor task only | Task, lineage, retry, and failure ownership |

## Options

1. **Snapshot only:** low complexity, but not sequence-reconstructable.
2. **Event log only:** reconstructable, but costly to render/contextualize.
3. **Event log plus materialized snapshot:** supports history and fast state;
   requires reducer/version discipline.
4. **CRDT/freeform state foundation:** useful for collaboration/whiteboards,
   likely excessive before a concrete shared-editing need.

## Recommendations

**Recommendation:** Evaluate an application-owned typed Studio event log plus
versioned materialized snapshot. Render from the snapshot and use a bounded
projection of the event log in Tutor context.

**Reason:** This directly meets the required bidirectional history without
hidden agent state or raw browser noise.

**Expected impact:** Supports Chat-first, Canvas-first, parallel, and
interleaved teaching without turning Canvas into a second Tutor.

**Mandatory / Optional:** Mandatory design decision before active Canvas work.

**Priority:** P0.

**Direct view:** Do not overload `StructuredSegmentState` or client React state
to serve as this protocol.

**Risk of ignoring:** Tutor loses causal knowledge of Canvas work; parallel
Canvas output becomes stale or unsafe.

**Confidence:** Medium-high. The pattern is robust; exact event catalog,
retention, and transport need Synthesis and a proof spike.
