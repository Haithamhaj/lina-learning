# STUDIO-ORCH-01 — Agent Orchestration Study

**Status:** Research only. No agent topology, framework, provider, or extra
model call is approved by this report.

## Facts

Lina's ModelGateway is provider-neutral at the application-task boundary: a
route selects provider/model and normalized providers execute or stream while
recording usage, latency, success/failure, and identifier-only lineage. It is
not an agent coordinator, shared-state store, workflow engine, or event bus.

The Gateway is not Tutor-only. ModelTask currently names Tutor, Session
Evidence, Segment Evidence, Curriculum Semantics, Embedding, and Personal Facts
(services/platform/db/models.py:47-55); task-specific factories configure those
routes (services/model_gateway/factory.py:25-205). There is no ModelTask.CANVAS
or Studio-specialist route. A Canvas task could extend the existing
provider-neutral pattern, but separate provider settings, capability validation,
privacy/retention review, and fallback behavior would still be required.

The current normal Tutor path is exactly one streaming model invocation. Its
strict output envelope already includes visible text, suggested actions, guided
check, teaching decisions, `structured_segment_state`, Parent Boundary decision,
and Candidate metadata. It includes no Canvas intent, object state, operation
log, artifact request, or specialist-job state.

The current public SSE has only provisional `delta` and terminal `turn`. It
does not support Canvas generation/status, concurrent scene state, operation
history, cancellation, or reconnection semantics.

Official OpenAI Agents SDK terminology is useful but not itself an architecture
decision: **agents as tools** lets a manager retain the final user-facing turn;
a **handoff** transfers the user-facing conversation to another agent. The SDK
supports code-directed orchestration, structured outputs, parallel independent
work, custom model providers, tracing, and deterministic workflow tests. Its
default tracing may retain generation/tool inputs and outputs, which conflicts
with Lina's content-minimizing trace policy unless intentionally configured.

Sources accessed 2026-09-02:

- https://openai.github.io/openai-agents-python/multi_agent/
- https://openai.github.io/openai-agents-python/models/
- https://openai.github.io/openai-agents-python/tracing/
- https://openai.github.io/openai-agents-python/testing/
- https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-architecture
- https://langchain-ai.github.io/langgraph/tutorials/multi_agent/multi-agent-collaboration/

OpenAI announced on 2026-06-03 that it is winding down Agent Builder and that
Agent Builder will no longer be available on the OpenAI Platform after
2026-11-30. Its stated code-based continuation path for software
implementations is the OpenAI Agents SDK. Source:
https://openai.com/index/introducing-agentkit/ (accessed 2026-09-02). Agent
Builder is therefore not a Lina architecture dependency.

## Assumptions

- A Canvas specialist proposes declarative visual/interaction operations. It is
  not an independent teacher and does not emit executable browser code.
- Complete Canvas history is durable and reconstructable, while Tutor context
  receives a bounded snapshot and relevant ordered operations—not raw pointer
  noise or an unlimited transcript.
- A second model call requires measurable visual/learning quality benefit.

## Options

| Option | Educational / Chat authority | Canvas / state authority | Calls: simple / complex | Fit |
| --- | --- | --- | --- | --- |
| A. Single Teaching Agent | Tutor owns teaching and conversation | Deterministic renderer; application owns Studio state | 1 / 1 | Strong current baseline |
| B. Tutor Manager + Canvas Specialist tool | Tutor manager retains final student-facing response | Specialist proposes typed scene work; application validates/writes | 1 / 2+ | Plausible bounded multi-agent route |
| C. Teaching Manager + Tutor + Canvas specialists | Manager conducts, Tutor speaks | Manager mediates specialists; app must still own state | 2 / 3+ | High latency and authority risk |
| D. Peer Tutor/Canvas + coordinator | Tutor remains conversational; peers act concurrently | Application coordinator resolves versions/events | 1–2 / 2+ | Future-scale only |
| E. Hybrid Fast/Deep | Tutor handles routine teaching immediately | Routine deterministic Canvas; complex specialist job | 1 / 2 when eligible | Strong hypothesis for proof |

### A. Single Teaching Agent

The existing Tutor emits a nullable, typed visual intent and the application
selects a renderer. It preserves one context, best first-token latency, and
straightforward rollback. Its limitation is specialist visual composition
quality for genuinely complex activities.

### B. Tutor Manager + Canvas Specialist as tool

The manager retains Tutor continuity and asks the specialist for a bounded
scene/patch proposal. This aligns better with an agent-as-tool than a handoff:
Canvas should not replace the Tutor as the Student-facing authority. The
application—not the manager—must authorize scene writes, versions, safety,
idempotency, and cancellation. Nested specialist use is normally sequential;
parallelism needs deterministic application scheduling.

### C. Teaching Manager + Tutor Specialist + Canvas Specialist

This adds a teaching conductor above the current Tutor. It can coordinate rich
lessons but introduces a second semantic teaching authority, more context
copies, join/conflict policy, and first-response latency. No current evidence
shows it improves Lina's learning quality enough to justify that cost.

### D. Peer Tutor/Canvas agents + coordinator

An application-owned coordinator dispatches peers against Shared Studio State.
It supports Canvas-first, parallel, and interleaved work, but requires an
append-only operation log, optimistic concurrency, cancel tokens, source-turn
lineage, and deterministic conflict handling. It is an architecture option for
later scale, not a first implementation shortcut.

### E. Hybrid Fast/Deep

Routine turns use the existing Tutor plus deterministic renderer. For an
explicit, eligible complex visual task, Tutor streams immediately while a
Canvas specialist produces an allowlisted typed plan/patch asynchronously. The
application accepts it only if its source turn and scene revision are current.


### Detailed simple and complex turn sequences

**Timing classes:** Immediate = existing stream can release a first chat token;
post-turn = terminal Tutor state is committed before Canvas appears; asynchronous
= independently tracked Canvas work may finish later. “Rich-ready” means a
validated interactive/visual Canvas state, not a provisional model draft.

#### A. Single Teaching Agent

**Simple:** Student request → application authorization and Safety/Parent policy
→ Tutor T (existing Tutor provider/model, learner/curriculum context + current
Studio snapshot + events since Tutor watermark) streams one response → terminal
turn commits → application renders a deterministic typed view. Calls: one,
sequential. First chat token: immediate. First Canvas: post-turn. Rich-ready:
only where an existing typed renderer can render immediately after commit.

**Complex:** Identical one-call flow. Tutor may request an allowlisted renderer
through a constrained Canvas-request tool, but no Canvas model runs. T receives
the same bounded context; there is no duplicated model context. The app is final
state authority, rejects invalid/stale render requests, and cancels transient
render work on a new Student turn. No specialist timeout exists; unsupported
content falls back to text plus an honest Canvas state. Safety is server-owned;
tracing contains operation identifiers, not content. Cost/implementation: low.

#### B. Tutor Manager plus Canvas Specialist as Tool

**Simple:** Same as A; manager T retains the final student-facing response.
Calls: one, sequential; immediate chat and post-turn deterministic Canvas.

**Complex:** Student request → policy → T receives teaching context, snapshot,
and Canvas inspection/update tools → T asks Canvas C as a tool or emits a
deferred Canvas request → C (candidate Canvas route/provider/model) receives
only fixed learning objective, source turn, allowed catalog, scene snapshot,
base version, and relevant events → typed ScenePlan returns → application
validates and commits. Blocking agent-as-tool execution is sequential and may
delay chat; deferred application scheduling allows immediate chat and
asynchronous rich-ready Canvas. T and C duplicate only selected objective/scene,
not a full transcript. T owns the answer; application resolves conflicts,
cancels C on a new Student turn, rejects stale source/version output, and uses a
specialist deadline after which chat and last valid scene remain. Safety gates
requests and commits; tracing is redacted. Cost/implementation: medium.

#### C. Teaching Manager plus Tutor and Canvas Specialists

**Simple:** Student request → policy → teaching manager M plans → Tutor T
receives M plan plus learner/curriculum/Studio projection and streams. Calls:
two, sequential. First chat token: delayed. First Canvas: post-turn. M and T
duplicate teaching context and introduce a second semantic teaching layer.

**Complex:** M fixes objective and may dispatch T and C in parallel. T streams
the chat answer; C receives an immutable scene snapshot/catalog and produces a
plan. Calls: three or more. Rich-ready: asynchronous after manager/application
join. The application, rather than M, commits only version-valid outcomes,
cancels all children on a new Student turn, rejects late results, and allows T's
safe terminal answer to stand on specialist timeout. Safety and persistence stay
server-owned; each model trace must be separately redacted. Cost/implementation:
high. No current evidence justifies this option.

#### D. Peer Tutor and Canvas plus Coordinator

**Simple:** Same one-call T path as A, controlled by an application coordinator.
Calls: one. First chat: immediate; deterministic Canvas: post-turn.

**Complex:** Coordinator captures active source turn and scene revision V, then
runs T and C in parallel. T receives learner/curriculum context, snapshot and
events since watermark; C receives source objective, V, allowed catalog, scene
slice and semantic action history. Calls: two, parallel. First chat: immediate;
first Canvas can be post-turn; rich-ready: asynchronous. There is purposeful
duplication of the objective and scene slice only. The application orders
semantic events, accepts a plan only for V and the active source turn, cancels C
on a new Student turn, and discards late output. Specialist timeout retains the
last valid scene. Safety/Parent policy and content-minimized tracing remain
application-owned. Cost/implementation: medium-high/high.

#### E. Hybrid Fast/Deep

**Simple:** Same as A. T has teaching/conversation tools and constrained
Canvas-inspect/request tools; a deterministic renderer responds to the terminal
turn. Calls: one, sequential. First chat immediate; first Canvas post-turn;
rich-ready within the typed repertoire.

**Complex:** An application-owned eligibility rule permits C. T starts the
existing stream while C is scheduled in parallel or after a stable terminal
objective. C has scene/renderer/declarative-artifact planning tools but cannot
change the objective. Calls: two when eligible, parallel or deferred. Chat token
is immediate; deterministic Canvas is post-turn; specialist rich-ready is
asynchronous. T and C receive deliberately narrow projections. Tutor remains
the final visible teaching authority. The app resolves conflicts, records
cancellation, rejects stale plans by source turn and scene revision, applies a
specialist timeout, and cancels/supersedes C if a new Student turn arrives.
Safety and trace redaction are server-owned. Cost/implementation: medium to
medium-high.

### OpenAI Agents SDK patterns and their Lina boundary

- **Agents as tools:** appropriate pattern to evaluate if Tutor must retain the
  student-facing conversation while a Canvas specialist returns a bounded plan.
  It does not grant the specialist state-write authority.
- **Handoffs:** transfer active-agent ownership; weak fit for normal Canvas
  because Canvas should not become the student-facing Tutor.
- **Code orchestration:** an application may schedule independent calls in
  parallel, choose models/providers per agent, and own joins/cancellation. This
  best matches Lina's need for causal state control.
- **Per-agent/provider models:** technically supported by the SDK, but Lina
  still needs its own ModelTask route, capability profile, cost/latency,
  Arabic/English quality, and retention evaluation.
- **Tracing/redaction:** SDK tracing is useful only behind a content-minimizing
  configuration and project-owned operational policy.
- **Hosted multi-agent beta:** service-created subagents are separate from
  local handoffs/agents-as-tools. Official docs identify beta schemas,
  unavailable approval interruptions, nested orchestration cost, and inability
  to restore an in-flight response in another process/event loop. It is
  reference-only for Lina, not recommended merely because Agent Builder sunsets.


## Multi-provider / multi-model analysis

Separate Tutor provider/model A and Canvas provider/model B are technically
possible only if Lina extends its own Gateway route policy. A route capability
profile should require strict structured output, streaming semantics when
needed, tool behavior, usage/cost accounting, privacy/retention terms,
Arabic/English quality, deterministic test adapter, and fallback behavior.

No evidence in this study favors OpenAI, Anthropic, Gemini, GLM, or another
provider for Canvas work. “OpenAI-compatible” is not sufficient proof: official
Agents SDK guidance warns cross-provider differences in structured output,
tools, streaming, usage, and API semantics. Provider choice needs Studio golden
fixtures and a quality/latency/cost/privacy evaluation.

## Risks

- A manager or Canvas agent can silently become a second Tutor.
- SDK-managed sessions, browser state, and database state can split-brain.
- Specialists can overwrite newer Student work without source/version checks.
- Default agent traces can expose child content.
- Extra sequential calls regress first-token latency and cost.
- Framework runtime adoption can displace Model Gateway, Safety, session, or
SSE ownership before requirements are proven.

## Contradictions

| Clarified requirement | Current baseline | Decision needed |
| --- | --- | --- |
| Active Canvas input/history | FE-02 has presentation-only Workspace | State/event protocol before topology |
| Optional specialist agents | One primary Tutor call protected | Define normal vs complex eligibility |
| Tutor sees complete meaningful Canvas sequence | Context budget is bounded | Define event projection/window and reconstruction path |
| Canvas can be parallel/interleaved | Terminal Tutor turn is current visible boundary | Define independent Studio lifecycle/transport |

## Recommendations

### Recommendation 1

**Recommendation:** Treat Hybrid Fast/Deep as the leading architecture
hypothesis for proof, not an approved decision.

**Reason:** It preserves fast one-call routine tutoring while allowing an
explicit specialist route only when deterministic rendering is insufficient.

**Expected impact:** Strong Canvas potential without forcing ordinary turns
through costly agent chains.

**Mandatory / Optional:** Mandatory comparison in Synthesis; optional future
implementation.

**Priority:** P0.

**Direct view:** Use an application-owned code coordinator; models propose
typed intent, while the application schedules and validates state changes.

**Risk of ignoring:** Either a passive Canvas or an expensive agent chain for
every turn.

**Confidence:** Medium-high.

### Recommendation 2

**Recommendation:** Define Shared Studio State/event protocol before selecting
an orchestration SDK or provider.

**Reason:** The non-negotiable requirement is complete meaningful Canvas
history available to Tutor; no agent framework substitutes for a canonical
application state source.

**Expected impact:** Enables safe Canvas-first, parallel, and interleaved flows.

**Mandatory / Optional:** Mandatory.

**Priority:** P0.

**Direct view:** Persist ordered semantic operations and scene snapshots; pass
bounded projections to Tutor while retaining full reconstruction server-side.

**Risk of ignoring:** Lost Student work, stale scenes, and untraceable learning
interactions.

**Confidence:** High.
### Recommendation 3

**Recommendation:** Do not adopt OpenAI Agents SDK, Semantic Kernel, LangGraph,
or another general agent framework as the first Studio runtime.

**Reason:** Lina already owns Gateway, Safety, durable sessions, jobs, and SSE;
framework sessions/traces conflict unless adapter-bound.

**Expected impact:** Avoids duplicated authority and an irreversible runtime
migration.

**Mandatory / Optional:** Mandatory first-proof boundary; optional later
adapter evaluation.

**Priority:** P1.

**Direct view:** Agents SDK is a useful reference and possible private bounded
specialist helper, not product session/transport/state authority.

**Risk of ignoring:** Hidden state, privacy leakage, and provider/framework
coupling.

**Confidence:** High.
