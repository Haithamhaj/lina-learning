# Frontend Skill Pack — Lina Personal Learning System

**Status:** Approved project frontend playbook, updated for FE-02 greenfield
scope, assistant-ui rejection, named contracts, and the first-screen visual
brief gate; not implementation authorization.
**Purpose:** Versioned, project-usable frontend execution guidance before Daily
Student App or Public Landing work.
**Authority:** This playbook applies current product and reuse decisions. It does
not override product, safety, architecture, or project-state authorities.

### Reuse authority split

docs/TECHNOLOGY_REUSE_CATALOG.md is the exhaustive library and reuse decision
reference. This Skill Pack is the task-facing enforcement and completion-checklist
layer: it cites the catalog decision for a candidate and must not duplicate,
silently revise, or contradict that decision.

## 1. Activation and shared direction

Read this playbook before Daily Student App or Public Landing frontend work. Use
the relevant skill section for the change; use more than one when a task spans
their concerns. This playbook does not make a task READY, authorize a
dependency, or authorize work outside the approved task scope.

### Product surfaces

| Surface | Direction | Boundary |
|---|---|---|
| **Daily Student App** | Release 1 priority: **Learning Chat + Adaptive Learning Workspace** for real daily learning. | Preserve local auth, FastAPI/SSE, server-owned session truth, Tutor, safety, PF-03, and privacy-safe lifecycle behavior. |
| **Public Landing** | Separate later marketing and product-storytelling track. | It may use stronger visual or isolated 3D hero treatments, but must not constrain, slow, or become the Daily Student App architecture. |

### Shared visual and implementation baseline

- Design for learners roughly **10–18**. Lina is the first private daily-use
  Student, not the only design target.
- The desired character is **warm, intelligent, personal, and visually
  engaging**. It is not preschool, cartoonish, corporate, or visually noisy.
- Existing local React, Tailwind, and shadcn/ui components are the functional
  baseline. Customize locally; do not introduce a second component system by
  default.
- Learning Chat is conversational guidance. The Workspace is the visual, media,
  file, and interactive learning layer, and opens only when useful content
  exists. Chat uses the available width when it does not.
- Existing stream, safety, session, and Tutor behavior are protected
  implementation contracts, not visual implementation details.

### Product Owner FE-02 Greenfield Scope Clarification — 2026-09-02

For FE-02, the current /student UI and StudentMathSession are protected experimental/legacy functional shell and behavioral-regression-harness assets. They are reference evidence, not implementation material. The real Daily Student App must be built as a separate greenfield surface at /student/daily.

Frontend work for that route may reuse approved backend, authenticated session, FastAPI/SSE, Tutor, Safety, and PF-03 contracts. It must not import, wrap, extract from, restyle, modify, or route through StudentMathSession or the current /student page. This clarification supersedes only earlier playbook phrasing that could be read as evolving or reorganizing the local Student shell.

assistant-ui is rejected for FE-02 after its no-commit presentation-primitives
fit check: it remains prohibited as a runtime, backend, session, safety, or
stream-lifecycle replacement. React, Tailwind, and shadcn/ui remain available
baseline primitives for the greenfield surface. Consult the catalog for the
component-source fit-check decisions before use. ThreeUI/Spline remain visual
references; Three.js/React Three Fiber, attachments, image/PDF handling,
generated images, video, Artifact Engine, MathLive, JSXGraph, and Konva remain
deferred unless separately approved.

### Shared library boundary

- assistant-ui is REJECTED for FE-02. It may be reconsidered only in a later,
  separately approved task with a concrete presentation gap; it must never
  replace runtime, FastAPI/SSE protocol, backend, session authority, safety
  behavior, or lifecycle trace.
- ThreeUI and Spline are visual references only.
- Three.js or React Three Fiber are later candidates only for isolated,
  lazy-loaded Learning Workspace modules with a specific learning need. They
  are not the Daily App shell, default chat layer, or always-on WebGL.
- Motion, JSXGraph, React Konva, MathLive, video players, upload interfaces,
  generated-image presentation, and artifact renderers require their own
  approved capability task. They are not FE-02 dependencies or implied work.
- FE-CHAT-UI-01 is complete: use existing local React/Tailwind/shadcn primitives
  and borrow official shadcn chat presentation patterns only. AI Elements,
  VLLNT, and shadcn.io are UX references; 21st.dev Agent Elements is rejected.
  Cite the catalog for the full decision table.
- Apply the approved visual-reference translation in the FE-02 Greenfield plan:
  shadcn chat composition is the primary component reference and AI Elements is
  hierarchy-only. Do not copy AI SDK/useChat, `UIMessage`, transport, backend,
  runtime/session/persistence, provider, or state-machine assumptions. The
  plan's screenshot checklist is a required FE-02 review gate.

### FE-02 contracts and gates

Before FE-02 code, read the named contracts and first-screen visual brief in
docs/FE-02_GREENFIELD_SURFACE_PLAN.md. They are mandatory task checks:
FE-02-UI-01, FE-02-STREAM-01, FE-02-DATA-01, FE-02-WORKSPACE-01,
FE-02-I18N-01, and FE-02-SSE-01. Implementation is blocked until the Product
Owner approves the concrete first-screen visual brief.

## 2. adaptive-learning-product-frontend

### When to use it

Use for Daily Student App page composition, Chat/Workspace layout, responsive
behavior, navigation that affects learning flow, or a future content-region
seam. Use it for Landing work only to preserve the separation between surfaces.

### What it enforces

- Daily Student App work follows the approved **Learning Chat + Adaptive
  Learning Workspace** model, not a cosmetic chat restyle.
- Learning Chat remains useful and full width when Workspace content is absent.
- A desktop split is conditional on real approved Workspace content; mobile
  uses a clear stacked or tabbed presentation when content exists.
- The Workspace is a presentation region, never a second Tutor, backend, or
  source of learner truth.

### What it prevents

- A permanent empty Workspace panel, fake preview cards, or placeholder
  attachments used to simulate future capability.
- Deferred capability creep: attachment pipelines, image/PDF handling,
  generated images, arbitrary HTML/JavaScript rendering, video, 3D, Artifact
  Engine, graphing/canvas runtime, MathLive, JSXGraph, or Konva work in FE-02.
- Landing designs, templates, or performance budgets becoming Daily App
  architecture.

### Allowed libraries and patterns

- Existing neutral React, Tailwind, and shadcn/ui primitives, plus approved
  backend/session/SSE contract utilities. The local Student shell is reference
  evidence and a regression harness, not implementation material.
- Native React/SVG only for simple, safe, non-blocking visual seams, layout
  structure, and lightweight visual explanations within an approved task.
- Local composition with an optional Workspace slot or equivalent typed
  presentation seam, without inventing a Tutor/SSE payload field.

### Prohibited libraries and patterns

- New UI dependencies without separate approval.
- assistant-ui as runtime/backend/session replacement, global Three.js or React
  Three Fiber, Spline/ThreeUI application architecture, a generic Artifact
  Engine, or a generic attachment platform.
- A copied marketing/dashboard template as the authenticated Student shell.

### Required checks before completion

- Review the task against the FE-01 decision record and technology reuse
  catalog.
- Verify approved desktop, mobile, Chat-only, and conditional-Workspace
  behavior appropriate to the changed slice.
- Run focused contract tests, npm run typecheck, npm run build, and git diff
  --check; state any unavailable browser verification plainly.

### Daily Student App application

For FE-02, build only the first safe structural slice: a local Chat surface and
an optional Workspace region. Do not make the Workspace visible without content
and do not implement a source or renderer for future content merely because the
region exists.

### Public Landing application

Use the same visual character, not the same component architecture. Landing may
show a product story or non-authoritative visual concept, but must not embed,
simulate, or replace the live Daily Student App session flow.

### Pressure test

> **Prompt:** “Show an empty Workspace now so learners know attachments are
> coming.”
> **Response:** Stop. Chat remains full width until meaningful approved content
> exists; future capability is not a reason to add a dead panel.

## 3. frontend-visual-quality

### When to use it

Use when designing or reviewing a visible Student or Landing surface, including
tokens, typography, responsive composition, component selection, feedback, or
motion.

### What it enforces

- A coherent local visual system: warm surfaces, readable hierarchy, clear
  learner/Tutor identity, accessible focus and disabled states, and purposeful
  motion.
- Mature, calm learning clarity for learners roughly 10–18 rather than a
  preschool aesthetic or generic corporate dashboard.
- Motion supports orientation, feedback, focus, celebration, or a learning
  objective; static and reduced-motion readability remain complete experiences.

### What it prevents

- Generic default shadcn styling left unadapted for the Student surface.
- Competing community components, decorative effects, cursor-heavy behavior, or
  high-motion treatments that fragment design or distract from learning.
- Treating a visually impressive Landing reference as evidence that it belongs
  in the Daily App.

### Allowed libraries and patterns

- Checked-in shadcn/ui components and Tailwind tokens, customized locally.
- Purposeful local CSS/Tailwind transitions.
- Visual principles selectively borrowed from approved references, including
  Motion Primitives, Magic UI, React Bits, 21st.dev, and Aceternity, without
  importing their visual systems wholesale.
- ThreeUI/Spline references for later Landing composition only.

### Prohibited libraries and patterns

- A second component system, a copied full template, or a dependency added only
  for decoration.
- Always-on WebGL, default 3D chat backgrounds, preschool illustration language,
  or motion that obscures content, keyboard focus, or error state.

### Required checks before completion

- Review desktop and narrow/mobile hierarchy, focus visibility, contrast, and
  reduced-motion/static readability for the changed surface.
- Review Arabic, English, and mixed-direction content when the surface displays
  learner or Tutor text.
- Run the changed task's checks plus npm run typecheck, npm run build, and git
  diff --check.

### Daily Student App application

Make Chat and any present Workspace independently readable. Keep the Tutor
exchange and learner input primary; visual polish must not hide loading, error,
or safety-compatible states.

### Public Landing application

Landing may use a stronger hero, animation, or later isolated 3D visual moment
after its own approval. It still uses the same age-appropriate character,
accessibility discipline, and performance judgment.

### Pressure test

> **Prompt:** “Make it feel younger with cartoon mascots, confetti, and moving
> backgrounds everywhere.”
> **Response:** Redirect to warm, mature visual cues and one purposeful feedback
> moment. Do not trade learning clarity for child-coded decoration.

## 4. chat-learning-interface

### When to use it

Use when changing the Student message list, composer, Tutor/Student identity,
opening/loading/error states, SSE presentation, suggested actions, guided
checks, or a Chat-to-Workspace handoff.

### What it enforces

- The local client state machine presents server-owned authority: Clerk token
  use, Student session endpoint, FastAPI/SSE stream, safety-compatible output,
  and persistence remain outside a chat library.
- delta content remains provisional; terminal turn is the ready boundary. A
  non-terminal EOF or error removes only provisional Tutor content.
- Suggested actions and guided checks remain server-defined; they are not
  client-created learner evidence.
- Learner and Tutor content preserve `dir="auto"`, accessible live/error feedback,
  keyboard form behavior, and content-free lifecycle tracing.

### What it prevents

- assistant-ui or another library owning message/session truth, persistence,
  safety behavior, Tutor execution, stream lifecycle, or custom message
  semantics.
- Extra Tutor calls, backend payload changes, client-side safety decisions, or
  Personal Facts display/derivation.
- Fake attachment, image, video, artifact, or 3D messages used to imply an
  unsupported feature.

### Allowed libraries and patterns

- A new route-local custom SSE reader and local React state that preserve the
  existing backend/session/SSE contract, plus neutral shadcn/Tailwind
  presentation components. Do not reuse the local Student shell.
- No assistant-ui use in FE-02. A later separately approved task may revisit it
  only for a concrete presentation gap without changing the catalog decision.

### Prohibited libraries and patterns

- assistant-ui runtime, transport, session, backend, or persistence adoption
  without explicit proof and approval.
- A new Tutor/SSE field merely to make a Workspace demo appear; an attachment
  pipeline; arbitrary HTML/JavaScript execution; video or 3D runtime.

### Required checks before completion

- Run Student page contract and stream protocol/lifecycle tests relevant to the
  change, including terminal-turn retention, incomplete-stream rollback, and
  privacy-safe trace behavior.
- Verify loading, error, retry, action/check, keyboard, and Arabic/English/
  mixed-direction behavior for the changed interaction.
- Review the approved first-screen visual brief and its screenshot checklist:
  centered readable desktop chat, calm mobile chat, distinct stable identity
  rows, the approved empty/thinking/error states, no unsupported composer
  controls, and no empty Workspace.
- Run npm run typecheck, npm run build, and git diff --check.

### Daily Student App application

FE-02 builds the separate greenfield /student/daily presentation into a
Learning Chat component and optional Workspace handoff. It reuses the
backend/session/SSE contract and neutral utilities only; /student and
StudentMathSession remain reference evidence and regression harnesses. Chat
must remain usable when Workspace is absent or unsupported.

### Public Landing application

Do not present a marketing mockup as a live Tutor session. A future interactive
demo remains non-authoritative unless a separately approved, authenticated
product flow supplies the real server contract.

### Pressure test

> **Prompt:** “Install assistant-ui now; it will handle streaming and make
> attachments easy later.”
> **Response:** Stop. The completed FE-02 fit check rejected assistant-ui:
> its runtime-bound/adapted state would threaten the current SSE/session/safety
> contract. Future attachments do not authorize a runtime replacement.

## 5. frontend-verification-safety

### When to use it

Use before claiming any frontend task complete, and whenever a proposed frontend
change could affect a protected contract, dependency boundary, or learner-facing
safety-compatible state.

### What it enforces

- Verification is proportional to the changed path and distinguishes code,
  contract, browser, and real-Lina evidence.
- No learner or Tutor content enters lifecycle telemetry/storage used for UI
  observability.
- Frontend work cannot silently change Tutor, safety, PF-03, Learning
  Intelligence, backend, schema, migration, or dependency behavior.

### What it prevents

- Declaring a visual change accepted without stream, accessibility, or
  direction-aware regression coverage.
- Treating an unavailable check as a pass, or inferring runtime verification
  from static source inspection.
- Letting a UI library bypass product/safety authority or expanding FE-02 into
  deferred capability work.

### Allowed libraries and patterns

- Existing project test/contract commands, focused browser checks when
  available, npm run typecheck, npm run build, and git diff --check.
- Manual visual inspection for layout, keyboard flow, visible focus, error
  feedback, and Arabic/English/mixed-direction rendering.

### Prohibited libraries and patterns

- New verification, telemetry, analytics, UI, or runtime dependencies without
  task-specific approval.
- Logging learner/Tutor content merely to diagnose a frontend state.

### Required checks before completion

- Identify the changed surface and run its focused checks first.
- For Daily Student App stream-affecting work, include Student page contract,
  terminal-turn behavior, incomplete-stream rollback, and lifecycle privacy
  trace coverage.
- For responsive/interface work, include desktop and mobile layout, keyboard/
  accessibility basics, and Arabic/English/mixed-direction checks.
- Run npm run typecheck, npm run build, and git diff --check; report any
  unavailable check as unverified.

### Daily Student App application

FE-02 verification must prove a new layout does not alter API routes,
server-owned session authority, safety behavior, PF-03, or terminal stream
lifecycle. A Workspace layout seam does not excuse missing Chat regressions.

### Public Landing application

Landing verification emphasizes responsive performance, accessibility, visual
clarity, and separation from live Student/Tutor infrastructure. It does not
claim Daily App runtime validation.

### Pressure test

> **Prompt:** “The layout looks good, so skip stream tests.”
> **Response:** Stop. A chat layout can regress terminal rendering, rollback, or
> content-free tracing. Run applicable contract checks before completion.

## 6. Cross-skill pressure tests

| Likely overbuild request | Required stop or redirect |
|---|---|
| “Add Three.js to the whole app so it feels modern.” | Reject as app architecture and always-on WebGL. Consider only a later isolated, lazy-loaded Workspace module with a learning objective. |
| “Put a disabled upload control in FE-02 so the future is visible.” | Do not create fake attachment support. Keep Chat-only behavior until an approved content capability exists. |
| “Use the Landing hero design as the Student shell.” | Preserve separate surfaces. Landing visual freedom cannot dictate Daily App architecture or performance. |
| “Add a graphing/canvas/MathLive engine while making the Workspace slot.” | Defer. FE-02 may establish a safe layout seam, not an Artifact Engine or renderer runtime. |

## 7. Reference order for frontend work

1. project-state/PROJECT_STATE.md and project-state/DAILY_USE_RELEASE_TASKS.md
   for current execution authority.
2. docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md for accepted Student visual,
   Workspace, library, and FE-02 boundaries.
3. docs/TECHNOLOGY_REUSE_CATALOG.md for reuse and fit-check requirements.
4. This playbook for task-facing frontend execution guardrails.
5. The changed component and its existing tests/contracts before implementation.

**Current boundary:** FE-02 remains blocked/not started until separately
authorized. This playbook creates no UI, dependency, backend, or runtime
authorization.
