# FE-01 — Visual System, Library Capability, and Reuse Decision Record

**Status:** ACCEPTED / COMPLETED — documentation-only decision record.
**Scope:** FE-01 only. No UI implementation, dependency, API, Tutor, Personal Facts, schema, or migration change is authorized by this record.
**Depends on:** PF-03 accepted.
**Accepted documentation commit:** `8601ed5f485ff29fdb467db7abfb8f7ad44711b0`.
**Acceptance/state commit:** `ecfc715c19069294e46f746a433acb8f715725be`.
**Leads to:** FE-02 — Daily Student Experience, only after separate explicit authorization.

---

## 1. Decision summary

Lina's Daily-Use Student experience is **Learning Chat + Adaptive Learning Workspace**. Learning Chat is the conversational guidance layer. The Workspace is the visual, media, file, and interactive learning layer that opens when a learning exchange has something better shown than said. The functional component baseline remains the checked-in shadcn/ui/Tailwind setup. The product direction is suitable for learners roughly 10–18: warm, intelligent, personal, and visually engaging, but never preschool, cartoonish, corporate, or visually noisy. Lina is the first private daily-use Student, not the only design target.

FE-02 must evolve the existing local shell into this Chat + Workspace composition; merely improving the existing chat page is insufficient. The local shell remains the baseline for auth, session, SSE, safety-compatible states, and accessibility. `assistant-ui` is **rejected as a full runtime/backend/session replacement**, but is **eligible for a bounded evaluation of chat UI primitives/patterns only** if it can sit behind the current client contract. ThreeUI/Spline remain visual references. Three.js is **rejected as application architecture, an always-on chat layer, and default WebGL**, but is eligible for a later bounded evaluation in isolated, lazy-loaded Workspace modules with a specific learning need.

No decision below authorizes a package installation. A later task may reconsider a rejected or deferred library only with a concrete capability gap, a bounded fit check, and Product Owner approval.

## 1.1 Product Owner FE-02 Scope Clarification — 2026-09-02

This is the current FE-02 implementation-path authority. It supersedes only the earlier implication that FE-02 would evolve, reuse, or reorganize the existing Student UI implementation. It does not change FE-01 visual-system, library, safety, session, or deferred-capability decisions.

The existing Student UI at /student and StudentMathSession are protected experimental/legacy functional shell and behavioral-regression-harness assets. FE-02 must not import, wrap, extract from, restyle, modify, or route through StudentMathSession. The real Daily Student App will instead be a separate greenfield surface at /student/daily.

The new surface reuses accepted backend, authenticated session, FastAPI/SSE, Tutor, Safety, and PF-03 contracts, rather than the existing UI implementation. It remains Learning Chat + Adaptive Learning Workspace for learners roughly 10–18, with Lina as the first private daily-use Student. The visual direction remains warm, intelligent, personal, and visually engaging—never preschool, cartoonish, corporate, or visually noisy.

React, Tailwind, and shadcn/ui remain available baseline primitives. Before FE-02 code begins, assistant-ui needs a serious presentation-primitives fit check for the greenfield surface; it remains rejected as a runtime, backend, session, safety, or streaming-lifecycle replacement. ThreeUI and Spline remain visual references only. Three.js/React Three Fiber, attachments, image/PDF handling, generated images, video, Artifact Engine, MathLive, JSXGraph, and Konva remain deferred unless separately approved.

Where this record uses terms such as evolve the local shell, reuse the local shell, or local-shell layout composition in connection with FE-02, read those phrases as superseded by this section. The legacy UI remains valid evidence for protected behavior and regression coverage, not a component source for the new product surface.

---

## 2. Evidence inspected

This record is grounded in the accepted `codex/ctx-03` worktree:

- `apps/web/app/student/page.tsx` — authenticated Student page and responsive page shell.
- `apps/web/components/student-math-session.tsx` — local Student/Tutor chat, UI states, suggested actions, guided checks, visual shell, and responsive composition.
- `apps/web/lib/tutor-stream-turn-protocol.ts` and `apps/web/lib/tutor-stream-lifecycle-trace.ts` — terminal-turn and privacy-safe lifecycle contracts.
- `apps/api/routes/student.py` — server-owned Student session and stream endpoints.
- `apps/web/tailwind.config.ts`, `apps/web/components.json`, `apps/web/package.json`, and checked-in `components/ui/*` — Tailwind and local shadcn-style baseline.
- `tests/test_student_page_contract.py`, `tests/test_tutor_stream_turn_protocol.mjs`, and `tests/test_tutor_stream_lifecycle_trace.mjs` — existing frontend/stream contracts.
- `docs/TECHNOLOGY_REUSE_CATALOG.md`, `docs/DAILY_USE_RELEASE_DECISIONS.md`, `AGENTS.md`, and Release task/state records — approved boundaries and reuse direction.

---

## 3. Code-grounded capability audit

### Already supported by the current UI

| Capability | Current evidence | FE-02 implication |
|---|---|---|
| Authenticated Student surface | `RoleSurface` requires the Student role; the page redirects the wrong role. | Preserve the existing role boundary; a chat library must not own authentication or route authority. |
| Server-owned session lifecycle | The client opens/resumes `/v1/student/math/session`; the browser does not invent authority. | Preserve the API path, session ownership, ordered persisted history, and cross-Student isolation. |
| Incremental Tutor streaming | The client reads SSE `delta` events into one provisional Tutor bubble, then accepts only terminal `turn` as durable UI completion. | Keep the terminal `turn` boundary. A pretty stream renderer must not mark a turn complete on the first delta or EOF. |
| Failed-stream recovery | A non-terminal EOF/error removes only the provisional Tutor message, keeps the Student message, returns the UI to an error/retry state, and records safe lifecycle events. | Preserve rollback and retry behavior; do not replace it with a generic optimistic-chat lifecycle. |
| Thinking, empty, and error states | Loading, Tutor thinking, welcoming empty, initial-open retry, and in-session retry states are present. | Improve presentation only; retain their behavioral distinctions. |
| Guided interaction | Latest Tutor suggested actions and Guided Learning Check choices are rendered as accessible buttons. | Keep server-provided action kinds and guided-check identifiers intact; no client-side reinterpretation. |
| Bilingual readiness | Message, action, and guided-check content use `dir="auto"`. | Retain direction-aware rendering for Arabic, English, and mixed content. |
| Responsive/local visual shell | Tailwind breakpoints, full-width mobile composer, rounded cards, distinct Tutor/Student identities, and decorative Math motifs exist. | Evolve one coherent system rather than replacing working layout/state plumbing. |
| Privacy-safe observability | Browser lifecycle storage excludes Student and Tutor content. | Preserve content-free trace behavior when changing stream presentation. |

### Architecture FE-02 must preserve

1. FastAPI owns authentication, Student/session truth, persistence, Tutor runtime, safety, AI execution, and the stream protocol.
2. The normal Tutor path remains one primary Tutor call. UI work must not introduce a model call, provider SDK, classifier, or hidden backend execution path.
3. `delta` is provisional. Terminal `turn` makes the UI ready; non-terminal failure removes only the provisional Tutor content.
4. Suggested actions and guided checks remain server-defined and are not learning evidence merely because the user clicks them.
5. Child-safety/Parent Boundary decisions remain upstream of Student-facing output. A frontend library must not bypass, recalculate, or mask those decisions.
6. Personal Facts, including PF-03's read-only Tutor context, remain backend/Tutor behavior. FE-02 must not query, display, derive, or alter Personal Facts.
7. Voice, image/attachment input, annotation, generated-image display, video, artifact rendering, and 3D modules remain later capability tasks. FE-02 must establish a Chat + Workspace structure that can host them without implementing, storing, generating, or executing them now.

### Visual direction

Use a single warm learning system: deep ink for reading confidence; lavender for Lina/self expression; mint/teal for Tutor guidance; restrained apricot/gold for learning accents; soft rounded surfaces; roomy message groups; clear labels; and quiet Math-shaped motifs. Motion, when later justified, must orient, acknowledge, focus, or celebrate learning—not decorate every surface. The visual system must work without motion and at narrow mobile widths.

---

## 4. Candidate decisions

The four labels below are task-scoped decisions: **ADOPT**, **PARTIAL ADOPT**, **VISUAL REFERENCE**, and **REJECT**. They do not add dependencies.

### 4.1 Existing Student visual shell — PARTIAL ADOPT

- **Rationale / supported capability:** It already satisfies the project-owned auth, session, streaming, rollback, action, guided-check, responsive, and direction-aware contracts. It provides a real visual starting point rather than a blank replacement.
- **Risks / integration constraints:** Styling and component extraction must not disturb the local stream lifecycle, server endpoints, `dir="auto"`, or privacy-safe tracing.
- **Allowed use:** Treat it as behavioral-contract evidence and regression-harness evidence for the backend/session/SSE/Tutor/Safety/PF-03 path.
- **Prohibited use:** Importing, wrapping, extracting from, restyling, modifying, or routing through StudentMathSession or the current /student page; replacing the API/session/stream protocol; or treating visual polish as permission to change Tutor, safety, PF-03, or evidence behavior.
- **FE-02 implication:** Build the separate greenfield /student/daily Chat + Workspace surface. Preserve the existing legacy contract tests and add focused daily-route coverage; all older evolve/reuse/reorganize-local-shell wording is superseded for FE-02 implementation.

### 4.2 shadcn/ui and Tailwind — ADOPT

- **Rationale / supported capability:** The repository already has Tailwind configuration, `components.json`, and local Button/Card primitives. These provide project-owned accessible component mechanics without imposing a visual identity.
- **Risks / integration constraints:** The default slate-oriented shadcn appearance is not Lina's design system; arbitrary copied blocks can fragment layout and interaction semantics.
- **Allowed use:** Extend checked-in primitives and compose them into a limited Student UI component set with shared tokens and accessible focus/disabled states.
- **Prohibited use:** Adding a second component system, copying a full dashboard/template, or leaving Student-facing surfaces in a generic default style.
- **FE-02 implication:** Use shadcn/Tailwind as the functional base; keep the Lina visual system local and coherent.

### 4.3 assistant-ui — EVALUATE FOR CHAT UI PRIMITIVES; REJECT AS RUNTIME REPLACEMENT

- **Rationale / supported capability:** It offers thread, message, composer, attachment, persistence-adapter, and custom-runtime primitives that could reduce FE-02 presentation plumbing. The current shell already provides the authoritative client behavior: Clerk token use, `/v1/student/math/session`, the terminal `turn` boundary, provisional-message rollback, guided-check/action parts, and privacy-safe lifecycle traces. No proof yet shows an assistant-ui adapter preserves all of those contracts.
- **Risks / integration constraints:** A full runtime adoption could duplicate or obscure client state, invent persistence assumptions, couple to provider-oriented behavior, or regress the accepted SSE lifecycle. A primitives-only evaluation must render the existing `delta`/terminal `turn`/error states and custom action/check parts without owning state authority.
- **Allowed use:** In a separately approved, no-commit fit check, evaluate presentation primitives/patterns against the existing client state and FastAPI/SSE contract. Adopt only the pieces that reduce local message/composer layout work while keeping the current state machine authoritative.
- **Prohibited use:** Replacing FastAPI, Clerk, server-owned session/persistence, Tutor execution, SafetyDecision behavior, lifecycle tracing, or custom message semantics; installing it speculatively; or treating future attachments as permission to change the current backend.
- **FE-02 implication:** The default safe alternative is a new greenfield React/Tailwind/shadcn surface plus a route-local custom SSE client using the accepted backend contract. It requires locally maintained message grouping, composer, streamed/provisional state, error rollback, custom actions/checks, and a Workspace handoff; that creates more UI-maintenance responsibility than a proven chat library, but avoids unproven adapter and authority-regression risk.

### 4.4 ThreeUI / Spline — VISUAL REFERENCE

- **Rationale / supported capability:** They can inspire a high-value visual moment, spatial composition, or Workspace presentation, but are not part of the installed stack and have no demonstrated runtime requirement.
- **Risks / integration constraints:** A distinctive showcase effect can hurt readability, motion comfort, mobile performance, and the single-system visual language.
- **Allowed use:** Borrow a restrained composition, depth, or background principle after verifying it works with the local Tailwind/React shell.
- **Prohibited use:** Importing a full design system, creating a parallel component architecture, using Spline as the application runtime, or making the Tutor surface depend on a decorative effect.
- **FE-02 implication:** No dependency or implementation is planned; apply visual ideas only through locally owned CSS/React if useful.

### 4.5 Three.js — EVALUATE FOR ISOLATED LEARNING WORKSPACE MODULES; REJECT AS APP ARCHITECTURE

- **Rationale / supported capability:** Three.js can support a future isolated Workspace representation such as a 3D shape, arrows, geometry object, science model, or interactive visual explanation. No FE-02 requirement justifies a global 3D runtime today, but the Workspace must leave a safe future module boundary for one.
- **Risks / integration constraints:** Unbounded WebGL adds runtime weight, accessibility and mobile-performance risk, and can compete with reading/teaching. Any later module must be lazy-loaded, disposable, keyboard/touch-considered, reduced-motion-safe, and fail without blocking Chat.
- **Allowed use:** A later separately approved proof may evaluate a specific learning representation in an isolated, lazy-loaded Workspace module with measured learning value and performance/accessibility evidence.
- **Prohibited use:** Application architecture, global app shell, default chat layer, always-on background, default WebGL, or a decorative scene that delays/obscures the Tutor interaction.
- **FE-02 implication:** Establish a Workspace module boundary and placeholder presentation only; add no Three.js dependency, canvas, or 3D scene.

### 4.6 Motion Primitives — VISUAL REFERENCE

- **Rationale / supported capability:** It is a source for small orientation, feedback, and group-transition patterns aligned with the catalog's purposeful-motion rule.
- **Risks / integration constraints:** It assumes motion tooling that is not currently installed and can introduce unnecessary overlap with CSS transitions.
- **Allowed use:** Use as a pattern reference; later adopt a single proven motion primitive only when FE-02 identifies a specific state transition it improves.
- **Prohibited use:** Adding it for generic animation, page-wide effects, or as a substitute for accessible static state communication.
- **FE-02 implication:** Start with existing CSS/Tailwind transitions; no package is preapproved.

### 4.7 Magic UI — VISUAL REFERENCE

- **Rationale / supported capability:** It offers ideas for a restrained success acknowledgement or warm accent.
- **Risks / integration constraints:** Sparkles/confetti and animated backgrounds can distract from explanation and make ordinary learning feel over-rewarded.
- **Allowed use:** Reference a single optional celebration or feedback pattern after a real FE-02 state warrants it.
- **Prohibited use:** Ambient visual noise, reward mechanics, or adding a dependency for decorative effects.
- **FE-02 implication:** Not a baseline dependency or required feature.

### 4.8 React Bits — VISUAL REFERENCE

- **Rationale / supported capability:** It is a discovery source for focused React transitions and interactions.
- **Risks / integration constraints:** Cursor-heavy, distorted, or effect-first components can damage readability and keyboard/touch usability.
- **Allowed use:** Borrow an interaction principle that has a clear orientation or feedback purpose.
- **Prohibited use:** Copying effects wholesale, creating inconsistent motion language, or adding a library merely for novelty.
- **FE-02 implication:** No dependency; preserve low-motion, keyboard-accessible fallbacks.

### 4.9 21st.dev — VISUAL REFERENCE

- **Rationale / supported capability:** It is useful for discovering React/Tailwind patterns for cards, profiles, chat composition, uploads, and onboarding.
- **Risks / integration constraints:** Combining unrelated snippets produces inconsistent semantics and styling; its upload patterns exceed FE-02 scope.
- **Allowed use:** Inspect individual page/layout patterns and adapt only those that fit the local component system.
- **Prohibited use:** Assembling the page from unrelated community blocks or importing attachment flow before the Voice/Vision tasks.
- **FE-02 implication:** A research source, not a dependency or architecture.

### 4.10 Aceternity UI — VISUAL REFERENCE

- **Rationale / supported capability:** It can inspire selective polish for a card, modal, or calm background treatment.
- **Risks / integration constraints:** Its strongest effects can overwhelm text, motion-sensitive users, and low-power devices.
- **Allowed use:** Reference a single subtle interaction only after it passes readability and reduced-motion review.
- **Prohibited use:** Effect-first chat bubbles, dominant hero-style treatments, or a new dependency without a demonstrated gap.
- **FE-02 implication:** No required capability or installation.

### 4.11 Cult UI — REJECT for FE-02

- **Rationale / supported capability:** It overlaps with the existing shadcn/Tailwind direction and does not fill a documented Release-1 gap.
- **Risks / integration constraints:** Adds another component/motion source without a differentiated need.
- **Allowed use:** None in FE-02; reconsider only when a specific accessible component is unavailable locally.
- **Prohibited use:** Installing it to collect options or overlapping basic primitives.
- **FE-02 implication:** Keep the component source set small.

### 4.12 Framer Education and Webflow Kids templates — VISUAL REFERENCE

- **Rationale / supported capability:** They can inform warm composition, illustration placement, card rhythm, typography hierarchy, and responsive child-facing layout.
- **Risks / integration constraints:** Many examples are marketing-led or preschool/daycare oriented and do not satisfy a private authenticated learning application.
- **Allowed use:** Extract high-level visual principles only.
- **Prohibited use:** Copying template code, adopting a marketing-template architecture, or using preschool motifs/interaction density.
- **FE-02 implication:** Use them to critique the local visual direction, not to replace it.

### 4.13 React/SVG, Motion, JSXGraph, React Konva, and MathLive — PARTIAL ADOPT

- **Rationale / supported capability:** These are catalog-approved renderer candidates for scoped learning capabilities. Native React/SVG already supports simple Math motifs without a new dependency.
- **Risks / integration constraints:** A generic Artifact Engine, editable Math input, graphing, canvas, and interactive scenes are not FE-02 scope. Artifact failure must never block conversation.
- **Allowed use:** FE-02 may use native React/SVG only for simple, safe, non-blocking visual seams, Workspace layout structure, and lightweight visual explanations.
- **Prohibited use:** Starting an Artifact Engine, graphing runtime, canvas runtime, MathLive integration, generated HTML/JavaScript renderer, video runtime, attachment pipeline, or 3D runtime.
- **FE-02 implication:** Motion, JSXGraph, React Konva, and MathLive remain catalog-approved candidates for later scoped capability tasks; they are not FE-02 dependencies or implementation targets unless separately approved.

---

## 5. Adaptive Learning Workspace model

The Workspace is a presentation surface, not a second Tutor, second backend, or new source of learner truth. The existing Learning Chat remains present and useful when no Workspace content exists. When visual/file/media/interactive content is available, the Workspace presents it beside or in place of a narrow Chat panel while the existing server-owned conversation remains the guidance layer.

### Desktop pattern

```text
Optional navigation/sidebar
        │
        ├── Learning Chat ─── conversational guidance, composer, state/retry
        │
        └── Adaptive Learning Workspace ─── visual/file/media/interactive content when available
```

The Chat and Workspace panels should be independently readable. A resizable or expandable divider is desirable only if it can be implemented accessibly and simply; it is not a prerequisite for the first FE-02 slice. When no Workspace content exists, the Chat may use the available width without a permanent empty panel.

### Mobile pattern

Mobile uses stacked or tabbed **Chat** and **Workspace** views. The active learning content must remain reachable without losing the current conversation, and switching views must not reset the draft, stream state, error state, or server-owned session.

### Workspace content contract direction

The Workspace must be able to host these content categories later, each through a project-owned typed message/content contract and a safe local renderer:

- uploaded file previews, including images and PDFs;
- generated images shown as Workspace content, not buried as ordinary chat text;
- React/SVG diagrams and safe visual explanations;
- a future video player area;
- isolated lazy-loaded 3D modules;
- interactive learning exercises and typed artifacts.

This is a required architectural direction, not authorization to implement uploads, storage, generation, video, 3D, or exercises in FE-02. Content absence, renderer failure, or an unsupported capability must leave Learning Chat usable.

---

## 6. FE-02 feature-capability map

| FE-02 feature | Product requirement | Approved implementation capability | Library-enabled / future capability | Must not change |
|---|---|---|---|---|
| Learning Chat / message layout | Required | Existing local message list, role distinction, bubbles, action/check placement, and Tailwind layout | assistant-ui primitives may be evaluated only behind the existing client contract | Server-owned session/message authority and order |
| Streaming response state | Required | Existing SSE reader, provisional Tutor bubble, terminal `turn` completion | None | `delta` remains provisional; non-terminal EOF/error rollback |
| Thinking/loading state | Required | Existing opening and `Tutor is thinking…` states | Optional later purposeful transition, not required | Input/error behavior and terminal-ready boundary |
| Empty state | Required | Existing Math welcome and prompt | Visual-reference-informed illustration/shape composition | No content-readiness block for Tutor |
| Error/safety state | Required | Existing role-alert retry states; server remains safety authority | Later visual refinement only | Safety decision semantics, raw error boundaries, and retry path |
| Arabic/English/mixed direction | Required | `dir="auto"` on dynamic Student/Tutor/action/check content | None | Direction-aware text rendering |
| Mobile/desktop responsiveness | Required | Existing Tailwind small/large breakpoints and mobile-width composer | Visual reference only | Usable composer, readable bubbles, touch targets |
| Keyboard/accessibility basics | Required | Native form, label, buttons, focus styling, `aria-live`, and alert roles | shadcn/Tailwind primitives | Semantic controls and keyboard submit/action paths |
| Tutor/Student identity | Required | Existing distinct Tutor/Lina avatars, labels, and color roles | Optional Parent-chosen photo/avatar in a later scoped task | Do not add identity collection/storage work |
| Warm learning visual system | Required | Existing ink/lavender/mint/soft-surface starting point and Math motifs | Visual references; local tokens/components | Do not become preschool, corporate, or decorative-first |
| Adaptive Learning Workspace composition | Required | New FE-02 local layout composition evolving the current shell | Resizable/expandable desktop split only if practical and accessible | Chat remains usable with no Workspace content; no second runtime/authority |
| Optional motion/visual effects | Nice to have | CSS/Tailwind transitions only if they add clarity | Motion-source research only; no package preapproved | Reduced-motion/static readability and performance |
| Attachments / uploaded images / PDFs | Required architectural direction; deferred implementation | Workspace content region and typed presentation seam only | Future project-owned object storage and preview renderer | Do not implement before TASK-033/storage approval; do not let a library own source/provenance |
| Generated images / safe SVG explanations | Required architectural direction; deferred implementation | Workspace content region; existing React/SVG direction | Later generated-image and safe renderer tasks | Do not bury visual output in plain chat or generate arbitrary runtime HTML/JS |
| Video player area | Required architectural direction; deferred implementation | Workspace region only | Later approved player/source contract | Do not add video runtime, hosting, or autoplay behavior |
| 3D modules / interactive exercises | Required architectural direction; deferred implementation | Isolated lazy-loadable Workspace module boundary only | Later measured Three.js/typed-artifact evaluation | Do not start WebGL, Artifact Engine, or exercise runtime |

---

## 7. Capability boundaries

### Product-required for FE-02

- A coherent, warm, readable Student learning surface.
- Current chat/session/stream behavior, including terminal-turn completion and recovery from incomplete streams.
- Clear loading, thinking, empty, error, and safety-compatible states.
- Responsive, touch-friendly, keyboard-accessible, direction-aware interaction.
- Distinct Tutor and Student identity presentation without new identity storage.
- Learning Chat + Adaptive Learning Workspace composition, with a usable Chat-only state when Workspace content is absent.

### Library-enabled but not required

- A locally customized shadcn/Tailwind component layer.
- Native React/SVG only for simple, safe, non-blocking visual seams, Workspace layout structure, and lightweight visual explanations.
- assistant-ui primitives only after a bounded compatibility evaluation proves they can remain presentation-only.
- A later single motion primitive only if it solves an identified orientation, feedback, focus, or celebration problem.

### Required architectural direction, deferred implementation

- Parent-chosen Student photo/avatar.
- Audio-to-STT input after TASK-032.
- Image/drawing attachment and original-image annotation after TASK-033/TASK-034 and durable storage approval.
- Uploaded file previews, generated images, safe SVG explanations, and a video player area in the Workspace after their own contracts/approval.
- Typed learning-artifact cards/interactive renderers and a specific 3D educational scene after their own reuse/gate work.

### Rejected or deferred capabilities

- assistant-ui as a runtime/backend/session replacement.
- ThreeUI as application architecture.
- Three.js as app architecture, default chat layer, or always-on WebGL.
- A generic Artifact Engine, graphing runtime, canvas runtime, MathLive integration, generated HTML/JavaScript renderer, video runtime, attachment pipeline, generated-image production, or 3D module implementation in FE-02.
- Additional UI/motion dependencies without a concrete FE-02 gap and separate approval.

---

## 8. FE-02 implementation guardrails and verification

FE-02 should build the separate greenfield /student/daily Learning Chat + Adaptive Learning Workspace composition and add only focused frontend tests required by its approved plan. It may create the layout and typed presentation seams, but must not implement a deferred Workspace capability merely because the region exists. The existing /student route and StudentMathSession remain behavioral-contract evidence and regression harnesses, not UI implementation material. Before acceptance, verify at minimum:

1. Existing Student page contract: authenticated `/v1/student/math/session`, no `/v1/demo`, server-owned stream endpoint, and no Tutor-readiness block.
2. Stream protocol: terminal `turn` releases UI before EOF; incomplete/error streams remove only the provisional Tutor message.
3. Lifecycle observability: no Student/Tutor content enters browser trace storage.
4. Functional UX: initial loading, empty, thinking, successful streamed response, retryable error, suggested actions, and guided checks.
5. Workspace composition: desktop Chat + Workspace behavior when content exists, Chat-only behavior when it does not, and stacked/tabbed mobile behavior without stream/draft/session loss.
6. Accessibility/responsiveness: keyboard form/action use, focus visibility, alert/live-region behavior, narrow/mobile layout, desktop layout, and Arabic/English/mixed-direction rendering.
7. Regression boundaries: no change to API routes, Tutor runtime, safety policy, PF-03/Personal Facts, Learning Intelligence, schema/migrations, Voice, Vision, attachments, generated-image production, video, or artifact/3D runtime.
8. `npm run typecheck`, `npm run build`, relevant frontend/contract tests, and `git diff --check`.

---

## 9. FE-01 acceptance checklist

- [x] Defines the visual direction.
- [x] Defines task-scoped library/reuse decisions.
- [x] Maps FE-02 features to approved local capabilities.
- [x] Defines Learning Chat + Adaptive Learning Workspace desktop/mobile direction and a future-ready Workspace capability map.
- [x] Prevents assistant-ui, ThreeUI, and Three.js from becoming architecture without proof.
- [x] Confirms the existing shadcn/Tailwind baseline.
- [x] Gives FE-02 implementation and verification guidance.
- [x] Adds no UI code or dependencies.
- [x] Does not alter PF-03 behavior or any protected backend authority.
- [x] Does not touch the dirty `main` worktree or `.acceptance-artifacts/`.

**FE-01 acceptance is recorded.** The `FE-02 remains BLOCKED / NOT STARTED`
statement records the then-current presentation slice. Current Studio readiness
is governed by `docs/STUDIO_IMPLEMENTATION_PLAN.md` and
`project-state/DAILY_USE_RELEASE_TASKS.md`; the uncommitted FE-02 shell remains
a protected, unaccepted prototype.
