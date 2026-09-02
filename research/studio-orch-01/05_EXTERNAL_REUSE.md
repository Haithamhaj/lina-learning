# STUDIO-ORCH-01 — External Reuse Landscape (Corrected)

**Status:** Research only. Releases, licenses, and maturity are time-sensitive.
All sources were reviewed 2026-09-02. No package is approved or installed.

## Facts

Lina owns its FastAPI session/auth/SSE path, Safety/Parent Boundary policy,
Model Gateway routes, persistence, and content-minimizing lifecycle trace.
External tools may inform a constrained adapter but cannot become the source of
truth for Tutor, Student, or Studio state.

The prior study had three material factual weaknesses: it pointed OpenMAIC to
the wrong repository, understated current A2UI maturity, and treated AG-UI too
generically. This correction uses THU-MAIC/OpenMAIC; current A2UI material
describing v0.9.1 Current Production plus a v1.0 Candidate; and AG-UI's official
event/state protocol and Canvas demo separately from CopilotKit.

## Assumptions

Compatibility means that Lina can put a candidate behind app-owned contracts.
It does not grant the package ownership of persistence, authorization,
telemetry, tool execution, learner history, or visible Tutor response. Exact
versions, transitive dependencies, vulnerabilities, terms, and data retention
must be rechecked at any later adoption gate.

## Risks

- A framework's default message/session/trace model can create split authority.
- A Canvas demo can prove a pattern but not child safety, learning quality, or
  operational production readiness.
- External declarative UI can still generate inappropriate catalog/action use
  unless Lina validates it.
- Broad platforms bring uploads, media, agent runtime, and product assumptions
  outside the first Studio need.

## Contradictions

A2UI and AG-UI offer reusable protocols while Lina deliberately owns its
current FastAPI/SSE transport and model lifecycle. OpenMAIC supplies useful
packages but a full classroom product architecture. tldraw offers a rich board
but product licensing and freeform state needs. These are reasons to separate
reference, proof spike, and package adoption decisions.

## Options

## Corrected external assessment matrix

| Candidate / current official evidence | Capabilities relevant to Studio | Integration/security compatibility | Decision |
| --- | --- | --- | --- |
| **A2UI**: official renderer guide calls v0.9.1 Current Production and v1.0 Candidate; stable React/web-core path, JSONL/progressive rendering, component catalogs, data model updates, client actions, validation/recovery | Declarative Canvas cards/forms/widgets from specialist or deterministic plan; messages → Lina-owned catalog → React → action → Studio event | Transport-agnostic; require strict catalog/message/action validation, no arbitrary components/functions; React/runtime dependency decision needed | **PROOF SPIKE** for actual adoption; **PARTIAL ADOPT** of schema ideas |
| **AG-UI**: MIT protocol/repo with active 2026 maintenance; official docs list Python and TypeScript SDKs plus broad integrations | Agent run/lifecycle/tool events, STATE_SNAPSHOT, STATE_DELTA using JSON Patch, CUSTOM events, bidirectional state sync; compatible conceptually with SSE | FastAPI can speak its event semantics, but adopting full protocol would change current stream/state contracts; application remains authorization/persistence owner | **PARTIAL ADOPT** semantics; full adoption is **PROOF SPIKE** |
| **open-ag-ui-canvas** official demo | Python FastAPI backend, Next.js/React frontend, interactive Research/Planner/Haiku canvas | Demonstrates pattern only; includes CopilotKit, LangGraph, CrewAI/Mastra stack and must not be treated as production evidence | **REFERENCE** |
| **AG-UI + A2UI integration** official docs | AG-UI = agent/user run-event-state transport; A2UI = declarative generated surface | Pairing can be: Canvas specialist → A2UI → Lina catalog/React Canvas → Student action → Studio event; each layer still needs source/version/safety validation | **PROOF SPIKE** only |
| **OpenAI Agents SDK**: code orchestration, agents-as-tools, handoffs, providers/models, tracing; hosted multi-agent beta | Bounded Canvas specialist runner or workflow testing patterns | Python fit, but tracing/session/provider defaults must be adapted; hosted beta has state/privacy limitations | **REFERENCE**; specialist wrapper **PROOF SPIKE** |
| **THU-MAIC/OpenMAIC v1.0.0** released 2026-08-27; MIT relicensing began v0.3.0 | Package family for DSL, renderer, importer, generation, storage; interactive/PBL contracts; runtime/session/outbox patterns; sandbox hardening | Full product has uploads/media/classroom/agent features out of scope. Package contracts could be adapted only after catalog-required evaluation | Per-package below |
| **tldraw** Agent Starter Kit/action architecture | Shape/action history, structured context, streamed agent actions, custom action schemas, provider/model flexibility | Strong freeform reference; SDK is source-available under tldraw license, production requires key; board state/a11y/mobile/product lock-in are material | **REFERENCE**; future freeform **PROOF SPIKE** |
| **Vercel AI SDK** | Typed tool UI parts; serializable AI state versus UI state; progressive tool-result rendering | AI SDK UI is Vercel's current path; RSC is experimental. It conflicts with Lina's FastAPI/SSE and no-AI-SDK product constraints | **REJECT** as owner; **REFERENCE** patterns |
| **MCP Apps** | Isolated third-party tool UI in sandboxed app surface | Useful future third-party tool boundary; poor fit for first-party core Canvas where Studio state/interaction is intrinsic | **REFERENCE** / later evaluation |

## A2UI correction and choices

A2UI should not be described as merely public-preview v0.8. Current official
renderer material states v0.9.1 Current Production and v1.0 Candidate. It
supports message processing, custom catalogs, data-model updates, progressive
rendering, client actions, and structured validation failure/recovery. Its
transport is not tied to a single agent provider.

| Choice | Architecture | Benefits | Risks / decision |
| --- | --- | --- | --- |
| A. Actual A2UI adoption | Canvas specialist emits A2UI messages; Lina registers catalog; React Canvas renders; Student action becomes a validated Studio event | Mature message/state/action vocabulary and progressive UI machinery | New dependency/version surface and catalog governance; **PROOF SPIKE** |
| B. Small Lina Artifact/Scene spec inspired by A2UI | Application owns a minimal typed scene/action schema and renderer catalog | Keeps session/SSE/state authority local and small | Lina builds processor/validation; **PARTIAL ADOPT** ideas |
| C. A2UI reference only | Reuse catalog, progressive update, action and recovery concepts | Zero runtime dependency | More custom code; **REFERENCE** |

## AG-UI correction and choices

AG-UI is MIT-licensed, active in 2026, and explicitly describes an event-based,
transport-agnostic agent-to-user protocol. Its state primitives include
STATE_SNAPSHOT and STATE_DELTA (RFC 6902 JSON Patch); it also includes lifecycle,
text, tool-call, CUSTOM, and bidirectional interaction concepts. It has Python
and TypeScript SDK paths, and its documentation explicitly lists A2UI as a
generative-UI integration.

The official open-ag-ui-canvas repository is a **demo**, not production proof:
it has a Python FastAPI agent backend and a Next.js/React frontend for
interactive canvases, but also includes framework/runtime choices Lina has not
approved. Its useful evidence is the separation of an interactive Canvas from
an agent run, not its entire stack.

| Choice | Benefits | Risks / decision |
| --- | --- | --- |
| A. Full AG-UI adoption | Standardizes event/state/tool lifecycle across agent frontends | Replaces/expands current SSE semantics; migration and state ownership risk; **PROOF SPIKE** |
| B. Partial event/state semantics | Reuse snapshot, delta, custom-event and causal-run vocabulary | Lina must maintain transport/reducer; **PARTIAL ADOPT** |
| C. Custom Lina protocol informed by AG-UI | Exact safety, privacy, session and Canvas requirements | More design/implementation work; **leading research baseline** |
| D. Reject | No protocol influence | Avoids scope | Loses useful mature vocabulary; not recommended |

## OpenMAIC correction and package boundaries

The official project is [THU-MAIC/OpenMAIC](https://github.com/THU-MAIC/OpenMAIC),
not the prior cited repository. Its v1.0.0 release is dated 2026-08-27. The
v0.3.0 release records the relicense from AGPL-3.0 to MIT and removed
allow-same-origin from interactive iframe sandboxing. Its release/changelog
material describes package-level DSL, renderer, importer, generation, and
storage boundaries; interactive/PBL content contracts; scene/action generation;
provider-neutral injected model calls; runtime/session event and outbox patterns.

| Package/pattern | Boundary and Lina integration assumption | Decision |
| --- | --- | --- |
| @openmaic/dsl | Typed stage/scene/interactive/PBL contracts; evaluate whether a small subset maps to Lina ArtifactIntent/ScenePlan without importing classroom semantics | **PROOF SPIKE** |
| @openmaic/renderer | Renderer contract/playback canvas; inspect accessibility, bundle and custom-catalog fit before any reuse | **PROOF SPIKE** |
| @openmaic/importer | Course/material import concerns, not a first Studio Canvas requirement | **REJECT CURRENT** |
| @openmaic/generation | Provider-injected outline/scene pipeline; useful separation pattern, but its prompts/course generation are not Lina Tutor semantics | **REFERENCE** |
| @openmaic/storage | Pluggable document/runtime/asset persistence; Lina already has PostgreSQL/session authority | **REJECT CURRENT** |
| interactive/PBL contracts | Useful typed-widget/action concepts; translate every action to Lina Studio event and keep learning authority local | **PARTIAL ADOPT** |
| runtime/outbox/state patterns | Useful ideas for cancel/resume/replay and source lineage | **REFERENCE** |
| iframe hardening | Security pattern: avoid allow-same-origin and validate boundaries | **ADOPT** as an evaluation requirement, not a package |
| full OpenMAIC classroom/product | Course workbench, materials/media/uploads, agents and classroom lifecycle | **REJECT** |

## tldraw correction and choices

Official tldraw material documents Agent Starter Kit concepts such as eyes,
actions, modes and managers; screenshot plus structured-shape context; streamed
actions; custom action schemas; provider/model flexibility; and action/session
history patterns. These are valuable architectural references for a future
freeform Canvas.

The tldraw SDK is **source-available under the tldraw license**, not MIT or
Apache. Production requires a valid trial, commercial, or hobby license key.
Some starter/example code is MIT, but that does not make the SDK MIT. It offers
accessibility improvements, but Lina would still need learning-task keyboard,
RTL, mobile, session-authority, and event-filtering proof.

| Choice | Assessment | Decision |
| --- | --- | --- |
| A. Main Lina Canvas foundation | Rich, mature freeform board but high bundle/licensing/lock-in and broad state/a11y/mobile needs | **REJECT CURRENT** |
| B. Future freeform Canvas | Potential fit when real learner use requires freeform spatial work | **PROOF SPIKE** |
| C. Reuse action/event architecture | Shape snapshots, custom actions, structured context and streamed action patterns | **PARTIAL ADOPT** concepts |
| D. Reject all influence | Avoids dependency | Loses useful architectural lessons | **REJECT** |

## Vercel and MCP Apps

Vercel AI SDK remains rejected as Lina's chat/session/runtime owner. Useful
patterns are typed tool UI parts, serializable AI state versus UI state, and
progressive tool-result rendering. AI SDK RSC remains experimental; Vercel
presents AI SDK UI as its recommended current path. Neither overrides the
project-owned FastAPI/SSE boundary.

MCP Apps remain a possible later boundary for a third-party isolated tool UI,
not core first-party Studio Canvas. Core Canvas requires direct app ownership of
state, authorization, and learning interaction; an iframe/AppBridge/MCP layer
would add permissions and message-validation complexity without solving that
need.

## External sources reviewed

- [A2UI renderer development](https://github.com/a2ui-project/a2ui/blob/main/docs/public/guides/renderer-development.md)
- [AG-UI overview](https://docs.ag-ui.com/) and [events](https://docs.ag-ui.com/concepts/events)
- [AG-UI integrations](https://docs.ag-ui.com/integrations)
- [open-ag-ui-canvas demo](https://github.com/ag-ui-protocol/open-ag-ui-canvas)
- [OpenAI Agents SDK models](https://openai.github.io/openai-agents-python/models/)
- [THU-MAIC/OpenMAIC releases](https://github.com/THU-MAIC/OpenMAIC/releases) and [changelog](https://github.com/THU-MAIC/OpenMAIC/blob/main/CHANGELOG.md)
- [tldraw license](https://tldraw.dev/community/license) and [v4 release](https://tldraw.dev/releases/v4.0.0)
- [Vercel AI SDK introduction](https://ai-sdk.dev/docs/introduction)
- [MCP Apps documentation](https://apps.modelcontextprotocol.io/)

## Recommendations

### 1. Use A2UI and AG-UI as bounded evidence, not platform defaults

- **Recommendation:** Evaluate a minimal Lina Scene spec informed by A2UI and
  AG-UI event semantics before adopting either runtime/protocol wholesale.
- **Reason:** Their current maturity warrants proof, while Lina's ownership
  boundaries remain non-negotiable.
- **Expected impact:** Concrete comparison against a source-bound local baseline.
- **Mandatory / Optional:** Mandatory evaluation before adoption.
- **Priority:** P0.
- **Direct view:** Do not conflate AG-UI, A2UI, and CopilotKit decisions.
- **Risk of ignoring:** A demo stack or protocol becomes accidental authority.
- **Confidence:** High.
### 2. Complete the OpenMAIC package-level evaluation

- **Recommendation:** Evaluate DSL and renderer packages against Lina's exact
  ArtifactIntent/ScenePlan/Studio-event needs; reject the full platform.
- **Reason:** This is the catalog-required reuse gate and the corrected source
  exposes meaningful package boundaries.
- **Expected impact:** Evidence-based adopt/partial/reject record.
- **Mandatory / Optional:** Mandatory evaluation; adoption optional.
- **Priority:** P0.
- **Direct view:** Keep imports, storage, generation and classroom product out
  of the first Studio scope.
- **Risk of ignoring:** Violates reuse-first policy or imports excess platform.
- **Confidence:** High.

### 3. Keep tldraw freeform work future-scoped

- **Recommendation:** Reuse tldraw action/history ideas now; defer SDK adoption
  until freeform learner value, licensing, a11y/mobile and product-lock-in proof.
- **Reason:** The first Canvas needs structured learning actions, not a general
  whiteboard.
- **Expected impact:** Avoids an expensive premature foundation choice.
- **Mandatory / Optional:** Mandatory current boundary.
- **Priority:** P1.
- **Direct view:** Starter-kit MIT code does not license the SDK.
- **Risk of ignoring:** Licensing and opaque freeform state become product debt.
- **Confidence:** High.
