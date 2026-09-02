# STUDIO-ORCH-01 — Current Lina Feasibility Audit

**Status:** Research only. This report maps current capabilities; it does not
authorize a protocol or modify the FE-02 prototype.

## Facts

### Governing architecture

The project is a modular monolith with vertical-slice delivery. Its named
domains already include Tutor, Learning Artifacts, Model Gateway, and the
Learning Canvas. The approved long-term artifact direction is typed artifact
specifications plus reusable renderers: AI chooses the educational
representation and the application renders it. Artifact failure must not block
the Tutor. See [`docs/PROJECT_REFERENCE.md`](../../docs/PROJECT_REFERENCE.md)
sections 12, 18, 21, and 23.

Current governing documents also freeze several capabilities from the original
FE-02 slice: Artifact Engine, interactive Canvas runtime, MathLive, JSXGraph,
Konva, images, video, and 3D. The Product Owner's clarified Studio research
brief intentionally studies those future possibilities; it does not unfreeze
them.

Safety is upstream policy, not a Tutor prompt. The hard baseline runs before
student-facing generation. Parent Boundary applicability is semantically
emitted in the same primary Tutor execution, but the server resolves the final
visible result. The same policy applies to artifacts and future tools. See
[`docs/CHILD_SAFETY_POLICY.md`](../../docs/CHILD_SAFETY_POLICY.md) sections
1–7.

### Current end-to-end turn

```text
Student input
  -> Clerk role/ownership
  -> POST /v1/student/math/session/{id}/turn/stream
  -> append Student message
  -> deterministic safety decision
  -> Tutor context + effective Parent Boundaries
  -> Model Gateway stream(ModelTask.TUTOR)
  -> provisional SSE delta(s)
  -> validated/persisted Tutor turn
  -> committed terminal SSE turn
  -> project-owned Daily controller
  -> Chat and prototype Workspace presentation
```

The concrete route is [`apps/api/routes/student.py`](../../apps/api/routes/student.py).
It validates that suggested actions and guided checks refer to the latest
persisted Tutor message before allowing the next turn. The current public
terminal event contains only `text`, `suggested_actions`, and `guided_check`.
It does not export Teaching Method, safety audit, segment state, candidate
metadata, retrieval context, or Canvas state.

`services/tutor/runtime.py` appends the Student message before generation,
applies safety, builds Tutor context, runs the provider-neutral Model Gateway,
and only persists a final Tutor message after completion/validation. It emits
`TutorTextDelta` provisionally and returns `TutorTurn` only after a complete
model result. The SSE generator commits before terminal `turn` emission.

The Daily client controller at
[`apps/web/components/daily-student/use-daily-tutor-session.ts`](../../apps/web/components/daily-student/use-daily-tutor-session.ts)
correctly represents that authority: `delta` creates a provisional Tutor bubble;
terminal `turn` replaces it; incomplete/error removes only that provisional
Tutor bubble and retains the Student message. Its lifecycle trace is bounded
and content-free.

### Existing reusable Studio inputs

| Current source | Reusable future Studio value | Current boundary |
| --- | --- | --- |
| Learning session and ordered messages | Durable conversation chronology and source IDs | Public API intentionally exposes a small message view only |
| Terminal Tutor turn | Source-linked explanation, suggested actions, guided check | No Canvas intent/specification |
| Suggested action / guided check | Server-validated next interaction linked to latest Tutor message | Click is not automatically mastery/Evidence |
| Structured Segment State | Bounded active goal, unresolved point, references, facts, source IDs | Private orientation metadata; not learner truth or public Canvas data |
| Teaching method/mode/strategy | Pedagogical routing provenance | Private payload, not student-facing visual authority |
| Model Gateway | Task-routed provider-neutral execution, lineage, cost/latency logging | Current task classes do not include Canvas composition |
| Child Safety / Parent Boundaries | Upstream visible-content gate for all Studio capabilities | Canvas/tools must be explicitly brought under the gate |
| FE-02 shell | Separate Desktop chat/workspace composition and local stream state | Current Workspace visual is a prototype adapter, not general Canvas truth |

### Current prototype limitation

The FE-02 Workspace derives its board from latest message state and uses a
regular-expression extraction of an equation in Tutor prose. It is a useful
presentation proof for an exact supplied equation; it cannot determine a
pedagogically correct representation for arbitrary prose, preserve edit history,
or report Student canvas actions. It must not become the long-term Canvas
authority.

## Assumptions

- A future Canvas needs server-visible session state; browser-only state cannot
  satisfy the requirement that Tutor reconstruct meaningful Canvas activity.
- Existing `LearningSession`, `LearningMessage`, and session-local Segment
  identity remain plausible lineage anchors, pending a distinct data-model
  decision.
- The Studio may need a new public read model while keeping sensitive private
  Tutor payloads private.

## Risks

- Exporting existing private payload wholesale would expose safety,
  personalization, Candidate, retrieval, or execution internals to the client.
- Treating every Canvas click as learning evidence violates the existing
  Candidate/Evidence authority pipeline.
- Persisting a Canvas before parent-boundary resolution or terminal Tutor
  completion can leak blocked/incomplete material.
- Running a second model call per ordinary turn can regress Tutor latency and
  cost without a measurable quality benefit.

## Contradictions to resolve in later synthesis

| Current approved fact | Clarified Studio requirement | Architecture tension |
| --- | --- | --- |
| FE-02 originally allowed only a conditional Workspace seam | Canvas is an active Student input surface | Requires a separately promoted Canvas capability, not a visual polish patch |
| One primary Tutor call is protected normal path | Specialist agents/models/tools are under consideration | Need explicit value threshold and routing policy |
| Structured Segment State is private orientation metadata | Tutor needs full meaningful Canvas history | Canvas state cannot be silently overloaded into Segment State |
| Current SSE is single request/response stream | Canvas may generate and accept interaction concurrently | Requires a session event/read-model architecture decision |

## Options

1. **Extend the terminal Tutor envelope with optional typed Studio metadata.**
   Lowest orchestration expansion, but risks response-schema bloat.
2. **Introduce a server-composed Studio snapshot from durable sources.**
   Strong resume and privacy boundary; cannot select rich visual semantics by
   itself.
3. **Add a separately durable Studio state/event domain.**
   Meets bidirectional Canvas requirements; requires explicit lifecycle,
   authorization, and persistence design.
4. **Use browser-only Canvas state.**
   Fast prototype route, but does not meet the Tutor-context requirement.

## Recommendations

**Recommendation:** Preserve the current Tutor/session/SSE path as the
baseline and design Shared Studio State as an application-owned domain rather
than extending client message state or exposing raw Tutor payloads.

**Reason:** Current systems already separate raw interaction, derived
orientation, learner intelligence, safety, and visible Tutor content. A
bidirectional Canvas needs equivalent explicit boundaries.

**Expected impact:** Allows a Tutor to consume meaningful Canvas history while
protecting Safety, Candidate/Evidence, and private context boundaries.

**Mandatory / Optional:** Mandatory before an active Canvas implementation.

**Priority:** P0.

**Direct view:** Reuse current session ownership, Model Gateway, terminal-turn
semantics, action/check validation, and content-free lifecycle principles; do
not reuse the FE-02 regex adapter as architecture.

**Risk of ignoring:** The Canvas becomes either a blind frontend widget or an
unsafe leakage of private Tutor internals.

**Confidence:** High on current-state facts; medium on the exact future state
model, which requires synthesis and proof.
