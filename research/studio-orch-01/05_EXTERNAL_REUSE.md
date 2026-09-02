# STUDIO-ORCH-01 — External Reuse Landscape

**Status:** Research only. Package versions, maturity, and licenses are
time-sensitive; sources below were consulted on 2026-09-02. No dependency is
approved or installed by this report.

## Facts

Lina has a FastAPI, server-owned session and SSE contract, a project-owned web
controller, privacy/safety boundaries, and a protected one-primary-Tutor-call
baseline. Reuse must fit those boundaries rather than replace them.

The technology catalog already requires an OpenMAIC evaluation before a generic
custom Artifact DSL/renderer layer. It also says to evaluate `assistant-ui`
before hand-building broad chat plumbing; that question was previously decided
for the protected FE-02 surface, whose project-owned SSE controller remains the
baseline here.

## Assumptions

“Compatible” means a package can be constrained behind Lina-owned contracts; it
does not mean its default persistence, auth, telemetry, transport, or agent
state is acceptable. An external protocol may be useful as a reference without
being adopted as a runtime dependency.

## Risks

- Frameworks with their own session, messages, tool loop, or telemetry can
  silently displace server authority and privacy boundaries.
- A vendor-specific GenUI stream can force the frontend to rely on fields that
  FastAPI/SSE does not own.
- Latest release claims become stale quickly; final evaluation needs a
  lockfile-level version, license, security, and bundle review.

## Contradictions

Several candidates assume a TypeScript/Node agent server or their own runtime,
while Lina's authoritative runtime is Python/FastAPI. Some can model rich UI
messages but Lina deliberately does not use their message/transport ownership.
The right near-term posture is reference or constrained adapter, not wholesale
platform adoption.

## Options

| Candidate | Maturity / provider / framework / transport | Security and contract fit | Decision label |
| --- | --- | --- | --- |
| OpenAI Agents SDK | OpenAI-maintained Python SDK; agent-as-tool, handoff, tracing/testing; provider abstraction | Can be wrapped, but tracing/session semantics need redaction and it overlaps coordination | **LATER EVALUATION** |
| AG-UI / CopilotKit | AG-UI lifecycle/state-sync protocol over HTTP/SSE, WebSocket, webhooks; CopilotKit is client/runtime on top | Protocol concepts fit bidirectional state; CopilotKit owns too much frontend/runtime | **AG-UI: LATER EVALUATION; CopilotKit: REJECT CURRENT** |
| Google A2UI | Google declarative agent-to-UI JSON, public-preview direction, host renderer model | Useful schema/reference; preview maturity and React fit need proof | **LATER EVALUATION** |
| tldraw Agent Starter Kit | React/Vite whiteboard starter and agent canvas example; SDK licensing/production key considerations | Interaction reference only; mutable board state and weight do not fit first Canvas | **REFERENCE ONLY** |
| OpenMAIC packages | Open-source artifact/renderer/DSL family; broader platform exceeds package need | Catalog-mandated evaluation; assess specific packages, not platform architecture | **PARTIAL ADOPT EVALUATION** |
| Vercel AI SDK / GenUI | TypeScript/Node SDK, AI UI/message and stream patterns, Vercel ecosystem | Conflicts with no-AI-SDK and FastAPI/SSE ownership; source of ideas only | **REJECT CURRENT / REFERENCE** |
| MCP Apps | Tool-provided iframe Apps with host bridge/MCP auth model | Better for third-party tool surfaces than core Student Canvas | **LATER EVALUATION** |
+
### Source, maturity, and compatibility notes

| Candidate | Public release/update signal observed | License / provider / framework | Transport and security relevance | Lina compatibility conclusion |
| --- | --- | --- | --- | --- |
| OpenAI Agents SDK | Official docs accessed 2026-09-02; repository release chronology requires re-check at adoption | OpenAI; Python; MIT repository license | SDK tracing and sessions need explicit content-minimizing configuration; tool/provider differences affect structured output and streaming | Adapter/reference only until a bounded specialist need proves it |
| AG-UI | Official docs accessed 2026-09-02; public protocol is active, exact version must be pinned later | Open protocol; TypeScript ecosystem; MIT repository license | HTTP POST/SSE, WebSocket, and webhook lifecycle/state events map conceptually to Studio; auth and event ownership remain application concerns | Protocol reference / later evaluation |
| CopilotKit | Repository/release metadata accessed 2026-09-02; active client-runtime product | CopilotKit; React/Angular integrations; MIT repository license | Brings client-side co-pilot, state, and tool conventions that overlap Lina's controller and session authority | Reject current |
| Google A2UI | Public-preview material accessed 2026-09-02; React renderer direction remains evolving | Google/open project; declarative JSON host renderers; Apache-2.0 repository license | Host validates/renderers own UI; schema could inform a bounded future spec, but maturity and server fit are unproved | Later evaluation |
| tldraw Agent Starter Kit | Starter-kit documentation accessed 2026-09-02; product-quality whiteboard reference | tldraw; React/Vite; starter source MIT, SDK production licensing/key terms must be reviewed | Mutable canvas and agent integration require custom state, permission, and accessibility controls | Reference only |
| OpenMAIC | Repository/release notes accessed 2026-09-02; 0.x-to-1.0 evolution is recent | OpenMAIC family; package-specific JavaScript/TypeScript; repository license/release terms must be pinned per package | Renderer/DSL pieces may fit typed artifacts; broad platform risks uploads/agent/runtime overlap | Partial-adopt evaluation mandated by catalog |
| Vercel AI SDK / GenUI | Official docs accessed 2026-09-02; actively evolving SDK | Vercel; TypeScript/Node; Apache-2.0 repository license | UIMessage/transport/runtime conventions conflict with the project-owned FastAPI/SSE contract | Reject current; design reference only |
| MCP Apps | Official Apps/spec documentation accessed 2026-09-02; ecosystem protocol, not a first-party Canvas framework | MCP community; host/tool iframe Apps; licensing varies by component | iframe/AppBridge/MCP auth are useful for isolated third-party tools, but introduce cross-context permissions and message validation | Later evaluation, not core Studio |

These are research snapshots, not security clearance. Exact versions, licenses,
release dates, transitive dependencies, vulnerabilities, data retention, and
provider terms must be re-verified immediately before any adoption proposal.


## Recommendations

### 1. Preserve the Lina-owned protocol

- **Recommendation:** Treat all external options as reference material or
  adapters behind a Lina-owned shared Studio protocol.
- **Reason:** Safety, parent policy, session truth, durable source lineage, and
  privacy trace cannot be delegated to a UI/agent framework.
- **Expected impact:** Reuse remains reversible and testable.
- **Mandatory / Optional:** Mandatory.
- **Priority:** P0.
- **Direct view:** No external runtime should become the source of truth.
- **Risk of ignoring:** Framework capture and unsafe split-brain state.
- **Confidence:** High.

### 2. Evaluate OpenMAIC at package level

- **Recommendation:** Fulfil the catalog's OpenMAIC evaluation before any
  generic Artifact DSL/renderer infrastructure decision.
- **Reason:** It is the project-approved reuse gate for this exact problem.
- **Expected impact:** Evidence-based adopt/partial-adopt/reject decision.
- **Mandatory / Optional:** Mandatory evaluation; adoption optional.
- **Priority:** P0.
- **Direct view:** Evaluate renderer/DSL packages only; do not adopt its broad
  platform by default.
- **Risk of ignoring:** Violates explicit reuse-first architecture rule.
- **Confidence:** High.

### 3. Keep external agent and GenUI runtimes out of the first proof

- **Recommendation:** Do not add Agents SDK, CopilotKit, AI SDK, tldraw, or MCP
  Apps to the first Studio proof spike.
- **Reason:** The essential unanswered questions are state authority and
  educational usefulness, not framework availability.
- **Expected impact:** Cleaner evidence on whether specialist planning earns its
  cost.
- **Mandatory / Optional:** Recommended guardrail.
- **Priority:** P1.
- **Direct view:** Use their patterns as design references, not dependencies.
- **Risk of ignoring:** The experiment may prove a library integration instead
  of a learning architecture.
- **Confidence:** High.

## Official sources consulted

- OpenAI Agents SDK: [multi-agent patterns](https://openai.github.io/openai-agents-python/multi_agent/), [models](https://openai.github.io/openai-agents-python/models/), [tracing](https://openai.github.io/openai-agents-python/tracing/), and [testing](https://openai.github.io/openai-agents-python/testing/).
- AG-UI: [official overview](https://docs.ag-ui.com/). CopilotKit:
  [official repository](https://github.com/CopilotKit/CopilotKit).
- Google A2UI: [official repository](https://github.com/google/A2UI) and
  [announcement](https://developers.googleblog.com/en/introducing-a2ui-an-open-project-for-agent-driven-interfaces/).
- tldraw: [Agent Starter Kit](https://www.tldraw.dev/examples/ai/agent-starter-kit)
  and [SDK licensing](https://www.tldraw.dev/docs/real-world-licenses).
- OpenMAIC: [official repository](https://github.com/anthropics/openmaic).
- Vercel: [AI SDK](https://ai-sdk.dev/docs/introduction) and
  [Generative UI](https://ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces).
- MCP Apps: [official Apps documentation](https://apps.modelcontextprotocol.io/)
  and [MCP specification](https://modelcontextprotocol.io/specification/2025-06-18).

The sources establish current public direction, not an approval, exact
version-pin, or complete security assessment. Each later adoption needs a
specific provider/framework/transport, license, vulnerability, bundle,
accessibility, and privacy review.
