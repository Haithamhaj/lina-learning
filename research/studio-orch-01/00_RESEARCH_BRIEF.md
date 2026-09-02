# STUDIO-ORCH-01 — Research Brief

**Status:** Published research only. No Studio architecture is approved by this
study.

## Facts

The current `/student/daily` FE-02 surface is an uncommitted prototype shell.
It has a greenfield chat presentation, project-owned SSE controller, and a
message-derived Workspace visual seam. It is not an accepted product UI or a
binding architecture constraint. The protected production baseline remains the
authenticated FastAPI/session/SSE/Tutor/Safety path; normal Tutor turns use one
primary model call.

The clarified product concept is potentially a bidirectional Learning Studio:

```text
Student <-> Tutor / Chat
              <-> application-owned Shared Studio State
              <-> active Canvas / Workspace
              <-> optional Canvas specialist, tools, and renderers
```

Canvas is both an output and a first-class Student input surface. Meaningful
Canvas operations must be represented as structured Studio state/history so the
Tutor can continue teaching without asking the Student to repeat what happened
visually.

## Assumptions

The reports can identify a technically credible direction, but only a later
Synthesis and Product Owner decision can change Lina's approved architecture.
The current uncommitted FE-02 Studio shell is evidence of UI wiring only; it
does not prove a Canvas protocol, a second model call, or an agent framework.

## Questions being researched

1. What Studio state should be ephemeral, session-durable, turn-durable, or
   rebuildable from an event log?
2. Which Chat-to-Canvas orchestration topology best balances educational
   coherence, latency, cost, safety, and operational complexity?
3. How should Tutor, Canvas specialist, renderer, and Student operations share
   state without placing authority in hidden agent context?
4. Which Canvas execution layers are appropriate from deterministic SVG through
   interactive scenes and later simulations?
5. Which external projects can inform or partially serve the architecture
   without replacing Lina's Model Gateway, safety, session, or intelligence
   boundaries?

## Non-negotiable research boundaries

- No implementation, dependency installation, FE-02 modification, or governing
  decision update is authorized.
- `/student` and `StudentMathSession` remain protected legacy/reference assets.
- The existing FastAPI/session/auth/SSE/Safety contracts are current facts, not
  automatically final Studio contracts.
- Raw Student work remains source authority. Derived Canvas content is never
  automatically Evidence, Personal Facts, safety authority, or learner
  intelligence.
- Every meaningful Canvas state change needs a structured representation that
  can be reconstructed for the Tutor; raw pointer noise need not be model
  context.
- Child-safety and Parent Boundary enforcement apply to text, tools, Canvas,
  artifacts, and future generated content.

## Research streams

| Report | Scope |
| --- | --- |
| `01_CURRENT_LINA_FEASIBILITY.md` | Fresh code-grounded audit of the current reusable baseline |
| `02_AGENT_ORCHESTRATION.md` | Teaching/Canvas agent topologies and Model Gateway fit |
| `03_CANVAS_EXECUTION.md` | Renderer, scene, artifact, and capability ladder |
| `04_SHARED_STUDIO_STATE_PROTOCOL.md` | Bidirectional event/state protocol and sequences |
| `05_EXTERNAL_REUSE.md` | Current external technology/reuse assessment |
| `06_OPEN_QUESTIONS.md` | Unresolved questions only, categorized for synthesis |

## Explicit non-decisions

## Contradictions

The product reference deliberately calls for expandable visual learning
artifacts while the protected normal Tutor path is one primary call and the
current stream contains no Canvas state. The research must distinguish a
renderer that organizes Tutor state today from a future specialist that may
propose richer Canvas state without weakening server authority.

## Options

The independent streams compare a single-call renderer-first baseline,
selective specialist planning, and fuller multi-agent coordination. No option
is selected in this brief; the later Synthesis must make the trade-off explicit
against learning quality, latency, cost, safety, privacy, and observability.

This study does not approve a multi-agent topology, a second normal-turn model
call, a provider, a renderer library, AG-UI, A2UI, tldraw, OpenMAIC, MCP Apps,
arbitrary generated HTML/JavaScript, a database schema, or a transport change.
It does not begin STUDIO-ORCH-01 Synthesis.

## Risks

- Treating a polished visual shell as proof of an educationally correct Canvas.
- Letting Canvas interaction become hidden agent context or untraceable learner
  state.
- Adding model calls for visual polish without measurable learning value.
- Allowing a visual tool to bypass Safety or Parent Boundary enforcement.

## Recommendations

**Recommendation:** Treat the remaining reports as an architecture decision
input, then run the separately authorized Synthesis before any implementation.

**Reason:** The clarified bidirectional Canvas requirement changes the scope
from an FE shell to a cross-domain state/orchestration capability.

**Expected impact:** A later implementation can be vertically sliced without
accidentally creating a second Tutor, hidden state machine, or artifact
platform.

**Mandatory / Optional:** Mandatory before Studio architecture implementation.

**Priority:** P0.

**Direct view:** Do not promote any report recommendation by implication.

**Risk of ignoring:** High likelihood of a visually impressive but
non-reconstructable and unsafe Canvas.

**Confidence:** High.
