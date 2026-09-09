# FE-02 — Greenfield Daily Student App Surface Plan

**Status:** Historical FE-02 prototype/surface guidance. Its protected legacy
boundary and visual evidence remain useful, but its chat-only implementation
path is superseded for current execution by `docs/STUDIO_IMPLEMENTATION_PLAN.md`
and `project-state/DAILY_USE_RELEASE_TASKS.md`.
**Date:** 2026-09-02
**Recommended route:** /student/daily
**Product surface:** Learning Chat + Adaptive Learning Workspace

**Current-use note:** Do not treat this document's conditional/display-only
Workspace wording, local UI state, or FE-02 task status as Studio architecture.
The approved production Workspace is durable, event-backed, and separately
transported; its next task remains prototype preservation only.

## 1. Product Owner scope clarification

The existing /student page and StudentMathSession are protected experimental/legacy functional shell and behavioral-regression-harness assets. They remain the evidence for accepted Student behavior: authenticated session, FastAPI/SSE stream, terminal-turn handling, incomplete-stream rollback, safety/error states, and privacy-safe lifecycle trace.

They are not the implementation basis for the Daily Student App. FE-02 must build a separate greenfield surface at /student/daily. It may reuse the backend/session/SSE/Tutor/Safety/PF-03 contracts, but must not import, wrap, extract from, restyle, modify, or route through StudentMathSession or the current /student page.

This supersedes only the previous FE-02 implementation-path wording that implied evolving the current Student UI. It does not change FE-01 visual direction, library decisions, safety boundaries, or deferred-capability limits.

## 2. Contradiction analysis

| Earlier implication | Risk | Resolution |
| --- | --- | --- |
| Evolve or reorganize the local Student shell. | Product UI changes could alter the functional harness or inherit legacy presentation constraints. | Keep /student unchanged; build the new product surface at /student/daily. |
| Current message/composer UI is the reuse base. | New UI could couple itself to StudentMathSession. | Reuse backend-facing contracts only; new components own presentation and local state. |
| assistant-ui was only a cautious future option. | Greenfield work could overbuild chat plumbing before fit evidence exists. | A serious no-commit presentation-primitives fit check is a pre-code gate. |

## 3. Product UX

The Daily Student App serves learners roughly 10–18. Lina is the first private daily-use Student, not the only design target. The product is warm, intelligent, personal, and visually engaging—not preschool, cartoonish, corporate, or visually noisy.

Learning Chat is the conversational guidance layer: Tutor and Student identity, messages, composer, and preserved stream states. The Adaptive Learning Workspace is a separate learning region that appears only when approved content exists.

- **Chat-only:** Chat uses the available width. Idle, thinking/streaming, empty, error, and safety states remain distinct; Arabic, English, and mixed-direction content remain supported.
- **Workspace-ready:** A future approved source may place Chat and Workspace side-by-side on desktop. FE-02 creates the conditional seam only; it must not render a permanent empty panel or fake artifact.
- **Mobile:** Chat remains primary. Future workspace content can use a stacked or explicit Chat/Workspace state without hiding the stream or producing competing focus targets.

## 3.1 First-screen visual brief — Product Owner approval gate

This one-page brief is the required visual decision for the first 30 seconds of
the real /student/daily route. FE-02 implementation must not start until the
Product Owner approves it.

### First 30 seconds

Lina enters a calm daily learning room, not a dashboard. A compact header says
Lina Learning and gives a small, warm Tutor identity cue; it does not show a
sidebar, course catalogue, streaks, files, settings, attachment controls, or
Workspace preview in this slice. The initial screen is a full-width Learning
Chat with one welcoming sentence that invites a question, attempt, or
explanation request. It should sound capable and personal, not childish:
“What would you like to work through today?”

On desktop, the page uses a centered, 640–760px chat column with a comfortable
reading measure, generous vertical rhythm, and quiet outer margins. Keep
16–24px between turns, 6–10px inside grouped message areas, and 12–16px of
bubble padding. The header is visually secondary to the conversation. There is
no navigation/sidebar in FE-02; navigation is deferred until a later approved
need proves it improves daily learning. No Workspace panel appears unless real,
separately approved Workspace content exists.

Tutor messages sit to the reading-start side in a soft mint/ink surface with a
small Tutor label and restrained avatar/mark. Lina messages sit opposite in a
lavender surface, also with a clear label. Identity placement stays consistent
enough to distinguish Tutor and Lina immediately; only dynamic text direction,
not the message-row structure, follows the message language. Bubbles are
rounded but not toy-like; they use high-contrast approximately 16px-equivalent
body text, short line lengths, and enough spacing to make a multi-step
explanation easy to scan. All learner-visible text, actions, checks, and the
composer use dir="auto" or equivalent direction-aware behavior. The follow-up
region appears only on the latest terminal Tutor turn when the server supplies
suggested actions or a guided check; it has no unsupported toolbar, branch
picker, model control, feedback control, or attachment preview.

The fixed/sticky bottom composer stays inside the learning surface. It is a
broad, softly bordered rounded field with a visible label for assistive
technology, a clear send action, and generous padding for comfortable typing.
It is constrained to the desktop chat column and full width within safe margins
on mobile. It has no paperclip, image, microphone, or disabled attachment
affordance in FE-02: showing one would imply unsupported capability. Keyboard
focus is obvious but quiet.

The empty state is the short capable welcome, “What would you like to work
through today?” Example prompts may appear only when separately approved as
product copy; do not invent them. It does not imitate suggested attachments,
generated media, a course dashboard, streaks, or a marketing illustration wall.
While a turn streams, the provisional Tutor bubble starts with a restrained
“Tutor is thinking…” indicator, then grows with delta text. Only terminal turn
content becomes the final message with actions or a guided check. An error or
incomplete stream removes the provisional Tutor bubble, retains Lina’s
submitted message, explains that the response did not finish, and offers a
clear retry without exposing infrastructure details. Lifecycle trace remains
content-free.

On mobile, the header becomes even quieter, the chat fills the viewport, bubbles
remain readable with safe side margins, and the composer remains reachable above
the browser edge. A later approved Workspace may become a deliberate Chat /
Workspace stacked or tabbed mode; it is invisible now. The visual tone is warm,
intelligent, personal, and visually engaging—not preschool, cartoonish,
corporate, dashboard-heavy, or visually noisy.

### Visible now versus deferred

| Visible in FE-02 | Structurally prepared but invisible | Deferred |
| --- | --- | --- |
| Header, chat-only layout, Tutor/Lina bubbles, composer, empty/thinking/error/safety states, suggested actions and guided checks from terminal turns. | Conditional Workspace boundary and responsive placement rule. | Attachments, images/PDFs, generated images, video, 3D, Artifact Engine, MathLive, JSXGraph, Konva, and navigation/sidebar. |

No permanent empty Workspace or fake Workspace capability appears in the real
route. A controlled Workspace fixture is allowed only in tests or a clearly
non-product preview. Motion is purposeful only and never turns the learning
surface into dense dashboard-card stacking or visual noise.

### 3.2 Approved visual-reference translation and screenshot gate

The FE-02 visual reference is approved for implementation guidance, not a
component/runtime adoption. Use official shadcn compositional chat patterns as
the primary component reference: message rows, distinct bubbles, status
markers, transcript/scroller behavior, and restrained thinking status. Use AI
Elements only as a UX-hierarchy reference for conversation spacing, message
container anatomy, the content region, and composer grouping.

Do not copy AI SDK wiring, `useChat`, `UIMessage`, transport, backend routes,
runtime/session/persistence ownership, provider coupling, or state-machine
assumptions. FE-02 remains project-owned React/Tailwind/shadcn presentation with
a project-owned SSE controller and the named contracts in section 6.

The implementation review must include screenshots or equivalent rendered
evidence for this checklist:

- Desktop: centered 640–760px chat column, quiet header, clear Tutor/Lina
  identity, readable high-contrast bubbles, and no dashboard/card wall.
- Empty chat: the approved capable welcome only; no invented examples, empty
  Workspace, fake artifact, streak, attachment affordance, or marketing wall.
- Streaming: one restrained provisional Tutor bubble that receives `delta`
  content and has no premature follow-up controls.
- Terminal/error: suggested actions or guided checks only after terminal `turn`;
  incomplete/error state removes the provisional bubble, keeps Lina's message,
  and exposes a clear retry.
- Mobile: safe margins, readable bubbles, reachable full-width composer, no
  sidebar/navigation, and no Workspace until real approved content exists.
- Direction/accessibility: visible focus, accessible composer label and send
  action, stable Tutor/Lina row placement, and `dir="auto"` (or equivalent) for
  Arabic, English, and mixed dynamic content.
- Tone: warm, intelligent, personal, and visually engaging; no preschool,
  cartoon, corporate, noisy, or unsupported-control treatment.

## 4. Route strategy

| Route | Role | Decision |
| --- | --- | --- |
| /student | Existing experimental/legacy functional shell and regression harness. | Keep unchanged. No redirect, wrapper, visual update, or component extraction. |
| /student/daily | New Daily Student App greenfield surface. | Create only after fit-gate completion and implementation authorization. |
| Future replacement of /student | Routing migration. | Defer until the new route is accepted and separately approved. |

Parallel routing protects the harness and makes the new product independently reviewable and reversible. Its temporary duplication cost is safer than coupling the product rewrite to a protected UI.

## 5. Greenfield component architecture

These are planning boundaries, not authorization to create files.

| Boundary | Responsibility | Must not own |
| --- | --- | --- |
| Daily route page | Route entry, authenticated composition, metadata, responsive shell placement. | Tutor/session authority, protocol changes, legacy UI reuse. |
| DailyStudentApp | Conditional Chat/Workspace product layout. | Backend state or fake workspace content. |
| DailyLearningChat | Messages, Tutor/Student identity, composer, focus, directionality, visual stream states. | Safety decisions, server session rules, terminal semantics. |
| DailyTutorSession client controller | Route-local use of the existing request/SSE contract, provisional display, rollback. | New API/schema, duplicate persistence, changed lifecycle. |
| DailyLearningWorkspace | Conditional Workspace slot and responsive placement seam. | Attachments, images/PDFs, HTML/JS artifacts, video, 3D, or Artifact Engine. |

The flow stays server-authoritative: authenticated Daily Student App request, existing Tutor endpoint and FastAPI/SSE protocol, existing terminal/lifecycle behavior, then new-route presentation. FE-02 must not add a Tutor payload field, session protocol, safety outcome, or persistence path.

## 6. Named FE-02 contracts

| Contract | Requirement | Verification focus |
| --- | --- | --- |
| FE-02-UI-01 | /student/daily must not import, wrap, extract from, restyle, modify, or route through /student or StudentMathSession. | Protected-file diff and daily-route import review. |
| FE-02-STREAM-01 | Preserve authenticated FastAPI/SSE, provisional delta, terminal turn, and incomplete-stream rollback. | Stream request, terminal-turn, and rollback contracts. |
| FE-02-DATA-01 | Lifecycle and frontend observability retain no Personal Facts, Tutor content, or learner content. | Privacy-trace regression tests and storage inspection. |
| FE-02-WORKSPACE-01 | The real route has no permanent empty Workspace or fake capability; fixtures are test/non-product only. | Chat-only route and controlled-fixture review. |
| FE-02-I18N-01 | Learner-visible messages, actions, checks, and composer input use dir="auto" or equivalent. | Arabic, English, and mixed-direction review. |
| FE-02-SSE-01 | Do not invent SSE events, payload fields, client-owned session truth, or competing state machines. | Endpoint/event schema and controller review. |

## 7. Library fit-check record

assistant-ui is REJECTED for FE-02 after the no-commit presentation-primitives
fit check. Its complete Thread is runtime-bound; its alternatives require state
or transport adaptation that would duplicate protected lifecycle responsibility.
This plan adds no dependency.

The check passes only if presentation-only use can preserve, without backend/API/SSE/Tutor/Safety/PF-03/session changes:

1. Direct compatibility with the current FastAPI/SSE request and event protocol.
2. Server-owned session authority and authenticated lifecycle.
3. Terminal-turn commit behavior and incomplete-stream rollback.
4. Safety/error presentation and lifecycle privacy trace.
5. Custom Tutor/Student message states and Arabic/English/mixed-direction rendering.
6. No competing runtime lifecycle, persistence model, backend adapter requirement, or dependency-driven architecture.

| Option | Decision |
| --- | --- |
| assistant-ui presentation primitives | REJECT for FE-02; reconsider only in a separately approved later task. |
| New local React/Tailwind/shadcn surface | Default fallback if proof fails or creates coupling; build presentation locally for /student/daily. |
| assistant-ui runtime/backend/session architecture | REJECT. |

ThreeUI/Spline remain visual references. Three.js/React Three Fiber remain later isolated lazy-loaded Workspace candidates, never the app architecture, default chat layer, or always-on WebGL.

### FE-CHAT-UI-01 completed component-first fit check

The accepted decisions are: existing local React/Tailwind/shadcn primitives,
ADOPT PATTERN; official shadcn Message/Bubble/Marker/MessageScroller patterns,
PARTIAL ADOPT PATTERN; Vercel AI Elements, VLLNT UI, and shadcn.io AI registry,
UX REFERENCE ONLY; and 21st.dev Agent Elements, REJECT.

FE-02 needs no chat UI-library installation. It uses project-owned
React/Tailwind/shadcn components and a project-owned SSE controller. It may
borrow official shadcn presentation patterns, but must not use AI SDK/useChat,
transport/session/persistence ownership, backend/SSE changes, provider
coupling, or runtime-bound chat state. Project-owned code retains message and
composer rendering, action chips, guided checks, direction-aware content,
safety/error states, terminal turn, rollback, and lifecycle privacy trace.

## 8. Expected later file set

### Create after implementation authorization

- apps/web/app/student/daily/page.tsx
- apps/web/components/daily-student/daily-student-app.tsx
- apps/web/components/daily-student/daily-learning-chat.tsx
- apps/web/components/daily-student/daily-learning-workspace.tsx
- apps/web/components/daily-student/use-daily-tutor-session.ts
- apps/web/tests/daily-student-surface-contract.test.tsx
- apps/web/tests/daily-student-stream-contract.test.ts

### May change only if essential to the new route

- Shared neutral shadcn/ui primitives, additively and backward-compatibly.
- Web test configuration only if additive daily-route coverage cannot otherwise run.

### Must remain untouched

- apps/web/app/student/page.tsx
- apps/web/components/student-math-session.tsx
- Existing Student page tests and legacy Student UI styling/components.
- Backend/API/SSE schema and routes.
- Tutor runtime/context/capacity; PF-03 and Personal Facts; Safety; schema/migrations; Voice; Vision; RAG; Learning Intelligence.
- Package manifests and lockfiles until a separately approved library decision.
- .acceptance-artifacts.

## 9. Slice after authorization

Implement:

- New /student/daily route and greenfield shell.
- Learning Chat connected to existing backend/session/SSE contract.
- Chat-only full-width layout when no workspace content exists.
- Conditional desktop Workspace slot only when an approved future caller supplies content.
- Mobile stacked or explicit Chat/Workspace behavior when content exists.
- Preserved thinking/streaming, empty, error, safety states; identity, directionality, keyboard basics, and accessible labels/focus.

Prepare structurally only:

- Explicit workspace-slot boundary with no payload/schema addition.
- Conditional desktop/mobile Workspace placement.
- Safe future seam for visual/file/media/interactive artifacts.

Defer:

- Attachments, image/PDF handling, generated images, arbitrary HTML/JS rendering, video, 3D, Artifact Engine, MathLive, JSXGraph, Konva, assistant-ui dependency adoption, Three.js/React Three Fiber dependency adoption, and backend/API/SSE schema changes.

## 10. Acceptance criteria

1. /student and StudentMathSession are untouched by the FE-02 change set.
2. /student/daily is a separate greenfield route that does not import, wrap, extract from, or route through legacy Student components.
3. Existing backend/session/SSE/Tutor/Safety/PF-03 contracts are preserved without schema or runtime change.
4. Chat is full width without a permanent empty Workspace.
5. The conditional Workspace seam supports desktop and mobile placement without fake artifacts.
6. Streaming/thinking, terminal-turn, rollback, empty, error, and safety states remain correct.
7. Arabic/English/mixed-direction behavior and keyboard/accessibility basics are reviewed.
8. No deferred capability, dependency, or Landing work is included.
9. The assistant-ui gate result is recorded before adoption or equivalent custom chat infrastructure is complete.
10. The Product Owner has approved the first-screen visual brief and the implementation satisfies FE-02-UI-01 through FE-02-SSE-01.

## 11. Required verification after implementation

1. Existing Student page contract tests.
2. Existing terminal-turn stream tests.
3. Existing incomplete-stream rollback tests.
4. Existing lifecycle privacy trace tests.
5. New daily-route chat-only and conditional-Workspace layout tests.
6. New daily-route stream-contract tests proving preserved request, terminal, and rollback behavior.
7. Manual desktop/mobile review with Arabic, English, and mixed-direction messages.
8. Keyboard and accessibility-basics review: composer, visible controls, focus order, labels, error/safety announcement.
9. npm run typecheck from apps/web.
10. npm run build from apps/web.
11. git diff --check.

If a test cannot run, report the exact blocker and keep FE-02 unaccepted. New route tests never replace the legacy /student regression harness.

## 12. Risks and guardrails

| Risk | Guardrail |
| --- | --- |
| Product work alters the legacy harness. | Protect the two legacy UI files and existing Student tests; review staged scope before commit. |
| assistant-ui creates hidden runtime ownership. | Require the fit check and explicit approval before installation. |
| Workspace scope becomes fake or premature artifacts. | No permanent empty panel; all artifact/media runtimes remain deferred. |
| New stream client drifts from accepted behavior. | Keep legacy stream tests and add daily-route contract coverage. |
| Landing visual ideas dictate Daily App architecture. | Keep Landing separate and use the FE-01 visual system only. |

No UI implementation, route creation, dependency addition, or runtime change is authorized by this document alone.
