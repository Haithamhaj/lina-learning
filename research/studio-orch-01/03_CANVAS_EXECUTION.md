# STUDIO-ORCH-01 — Canvas Execution Study

**Status:** Research only. This does not authorize an Artifact Engine, a new
renderer dependency, generated active code, or a Canvas model call.

## Facts

Lina's governing reference treats visual explanation as part of learning rather
than decoration. It calls for typed artifact specifications and reusable
renderers, with an expandable Learning Canvas in the same session/page. The
approved MVP renderer direction is native React/SVG, Motion, JSXGraph, React
Konva, and MathLive; a generated HTML/SVG fallback must be sandboxed and must
never block Tutor conversation. `TASK-035` remains blocked pending the required
OpenMAIC package-level evaluation.

Current Studio-shell Workspace content is message-derived: it can organize the
latest learner question, Tutor guidance, actions, and guided check, but has no
durable scene record, renderer registry, interaction protocol, or source
turn/version link. It is a proof of composition, not Canvas architecture.

Accessibility is first-class. SVG requires meaningful text alternatives and
semantic DOM companions where needed. Raw canvas output is not independently
available to assistive technology; interactive visual tools need equivalent
controls and outcome text. MathLive's keyboard behavior can be valuable later,
but it does not authorize mathematical input now.

## Assumptions

The first useful Canvas need is a small, truthful set of learning views, not a
general drawing product. The server remains the authority for session, safety,
visible Tutor response, and learning outcomes. A Canvas may display or rearrange
approved Tutor/session state; it may not manufacture a second answer, Evidence,
Personal Fact, safety decision, or persistence mutation.

## Risks

- A free-form scene generator can create ungrounded instructional content,
  inaccessible controls, unsafe output, and hard-to-reproduce rendering.
- Treating visual clicks as learning evidence violates the observable-outcome
  boundary.
- A generic Canvas SDK can conceal state, undo history, collaboration, or code
  execution choices outside the protected session contract.
- Rich renderers add bundle size, keyboard, RTL, and device failure modes.

## Contradictions

The product wants rich Canvas behavior, but normal Tutor turns retain a
single-primary-call baseline and generated HTML/JS is restricted. The resolution
cannot be model control of the browser: model semantics, if later used, must be
proposals that app validation and a renderer registry accept or reject.

## Options

| Option | What executes | Fit now | Principal limitation |
| --- | --- | --- | --- |
| Deterministic typed renderers | App selects allowlisted React/SVG from session state | Strongest | Repertoire grows deliberately |
| Constrained declarative GenUI | Model proposes a small typed scene schema | Later | Needs schema, validation, evals |
| Agent-authored scene graph | Specialist proposes graph/patch plan | Later | Extra call and conflict risk |
| Education artifact DSL | Typed pedagogical primitives compose artifacts | Strong later direction | Substantial design; OpenMAIC gate |
| Generated SVG | Model emits sanitized SVG | Narrow fallback only | Hard semantic/a11y guarantee |
| Sandboxed HTML/CSS/JS | Isolated generated document executes | Not normal flow | Security/focus/messaging burden |
| Generated images | Static visual aid | Later support | Weak inspectability/interaction |
| Simulation | Typed domain model | Later, topic-by-topic | Validated models required |
| 3D | Domain-specific spatial renderer | Deferred | High bundle/a11y/pedagogy cost |

### Practical capability ladder

1. **Orientation:** latest question, guidance, path; no new semantic content.
2. **Typed guided views:** allowlisted React/SVG diagrams, highlights, checks
   sourced from a terminal Tutor turn.
3. **Controlled interaction:** renderer-specific manipulations with explicit
   semantic operation events and accessible equivalents.
4. **Specialist adapters:** evaluate JSXGraph, MathLive, or Konva per use case.
5. **Bounded declarative specialist planning:** validated scene specs with
   deterministic fallback.
6. **Images, simulations, and 3D:** only with learner-benefit, safety, and
   accessibility evidence.

## Recommendations

### 1. Renderer-first Canvas

- **Recommendation:** Use a small app-owned registry of typed, source-bound
  React/SVG renderers as the future Canvas baseline.
- **Reason:** It produces truthful, inspectable learning views without a second
  Tutor call or browser-controlled generated code.
- **Expected impact:** A reliable Studio Canvas that evolves by renderer.
- **Mandatory / Optional:** Mandatory architectural baseline.
- **Priority:** P0.
- **Direct view:** Strongly recommended.
- **Risk of ignoring:** A generic Canvas or uncontrolled generator becomes the
  de facto teaching authority.
- **Confidence:** High.

### 2. Versioned scene state and operations

- **Recommendation:** Define app-owned `ArtifactIntent`, `ScenePlan`,
  `ArtifactInstance`, and `StudioOperation` contracts before interaction.
- **Reason:** Source lineage, expected revisions, renderer allowlists,
  locale/RTL, accessibility text, and safe rejection need explicit homes.
- **Expected impact:** Rebuildable, testable state with safe rollback.
- **Mandatory / Optional:** Mandatory before interactive Canvas.
- **Priority:** P0.
- **Direct view:** Strongly recommended.
- **Risk of ignoring:** Stale/conflicting Canvas state becomes unmanageable.
- **Confidence:** High.

### 3. Accessibility as renderer contract

- **Recommendation:** Require keyboard behavior, focus return, readable state,
  text alternative, and Arabic/English `dir` behavior for every renderer.
- **Reason:** Visual comprehension cannot be the only path to the learning step.
- **Expected impact:** Inclusive visuals and less retrofit risk.
- **Mandatory / Optional:** Mandatory.
- **Priority:** P0.
- **Direct view:** Strongly recommended.
- **Risk of ignoring:** Expensive exclusion of keyboard, screen-reader, or RTL
  learners.
- **Confidence:** High.

### 4. Evaluate specialist tools by learning outcome

- **Recommendation:** Evaluate JSXGraph, MathLive, and Konva only for specific
  renderer needs after the typed baseline; complete OpenMAIC evaluation before a
  custom generic artifact engine.
- **Reason:** Each solves a different problem; none replaces Studio authority.
- **Expected impact:** Smaller bundle and less framework capture.
- **Mandatory / Optional:** Mandatory evaluation; adoption optional.
- **Priority:** P1.
- **Direct view:** Do not add a Canvas library merely to look advanced.
- **Risk of ignoring:** Unnecessary dependency and inaccessible-interaction debt.
- **Confidence:** High.

## External evidence consulted

- [JSXGraph accessibility](https://jsxgraph.org/home/documentation/accessibility/)
  — official docs accessed 2026-09-02.
- [Konva documentation](https://konvajs.org/docs/) and its
  [Canvas editor example](https://konvajs.org/docs/sandbox/Canvas_Editor.html)
  — official docs accessed 2026-09-02.
- [MathLive keyboard guide](https://mathlive.io/mathfield/guides/virtual-keyboard/)
  — official guide accessed 2026-09-02.
- [MDN iframe sandbox](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe#sandbox)
  and [MDN SVG title](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/title)
  — standards guidance accessed 2026-09-02.
