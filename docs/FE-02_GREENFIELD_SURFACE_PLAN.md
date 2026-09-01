# FE-02 — Greenfield Daily Student App Surface Plan

**Status:** Product Owner-approved scope clarification; implementation blocked pending an assistant-ui presentation-primitives fit check and explicit implementation authorization.
**Date:** 2026-09-02
**Recommended route:** /student/daily
**Product surface:** Learning Chat + Adaptive Learning Workspace

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

## 6. assistant-ui fit-check gate

Before code is authorized, run a serious no-commit assistant-ui presentation-primitives fit check. This plan adds no dependency; passing the check does not automatically authorize installation.

The check passes only if presentation-only use can preserve, without backend/API/SSE/Tutor/Safety/PF-03/session changes:

1. Direct compatibility with the current FastAPI/SSE request and event protocol.
2. Server-owned session authority and authenticated lifecycle.
3. Terminal-turn commit behavior and incomplete-stream rollback.
4. Safety/error presentation and lifecycle privacy trace.
5. Custom Tutor/Student message states and Arabic/English/mixed-direction rendering.
6. No competing runtime lifecycle, persistence model, backend adapter requirement, or dependency-driven architecture.

| Option | Decision |
| --- | --- |
| assistant-ui presentation primitives | PARTIAL ADOPT only after proof passes and Product Owner approves a dependency. |
| New local React/Tailwind/shadcn surface | Default fallback if proof fails or creates coupling; build presentation locally for /student/daily. |
| assistant-ui runtime/backend/session architecture | REJECT. |

ThreeUI/Spline remain visual references. Three.js/React Three Fiber remain later isolated lazy-loaded Workspace candidates, never the app architecture, default chat layer, or always-on WebGL.

## 7. Expected later file set

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

## 8. Slice after authorization

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

## 9. Acceptance criteria

1. /student and StudentMathSession are untouched by the FE-02 change set.
2. /student/daily is a separate greenfield route that does not import, wrap, extract from, or route through legacy Student components.
3. Existing backend/session/SSE/Tutor/Safety/PF-03 contracts are preserved without schema or runtime change.
4. Chat is full width without a permanent empty Workspace.
5. The conditional Workspace seam supports desktop and mobile placement without fake artifacts.
6. Streaming/thinking, terminal-turn, rollback, empty, error, and safety states remain correct.
7. Arabic/English/mixed-direction behavior and keyboard/accessibility basics are reviewed.
8. No deferred capability, dependency, or Landing work is included.
9. The assistant-ui gate result is recorded before adoption or equivalent custom chat infrastructure is complete.

## 10. Required verification after implementation

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

## 11. Risks and guardrails

| Risk | Guardrail |
| --- | --- |
| Product work alters the legacy harness. | Protect the two legacy UI files and existing Student tests; review staged scope before commit. |
| assistant-ui creates hidden runtime ownership. | Require the fit check and explicit approval before installation. |
| Workspace scope becomes fake or premature artifacts. | No permanent empty panel; all artifact/media runtimes remain deferred. |
| New stream client drifts from accepted behavior. | Keep legacy stream tests and add daily-route contract coverage. |
| Landing visual ideas dictate Daily App architecture. | Keep Landing separate and use the FE-01 visual system only. |

No UI implementation, route creation, dependency addition, or runtime change is authorized by this document alone.
