# STUDIO-ORCH-01 — Canvas Execution Study (Rebuilt)

**Status:** Research only. This is a comparison and hypothesis, not approval for
an Artifact Engine, dependency, generated browser code, or Canvas model call.

## Facts

The project reference already treats visual explanation as learning, not
decoration: typed Artifact Specifications and reusable renderers are the
long-term direction, and artifact failure must not block Tutor conversation.
TASK-035 remains blocked pending OpenMAIC evaluation. The current FE-02
Workspace is message-derived presentation only; it has no durable scene
lifecycle, renderer registry, action semantics, or source-turn lineage.

A safe Studio Canvas has two layers. The application owns Studio history, scene
snapshots, validation, learner authorization, Safety/Parent Boundaries, and
semantic event extraction. A renderer or Canvas specialist receives a
source-bound projection and produces an allowlisted result. It cannot create a
second Tutor answer, Evidence, Personal Fact, safety decision, or direct durable
write.

Every interactive representation requires keyboard operation, focus return,
meaningful DOM/text alternative, and Arabic/English/mixed direction behavior.
Raw canvas or image output cannot be the sole learning path.

## Assumptions

- Timing classes are hypotheses: Immediate (current stream), Post-turn
  (terminal Tutor turn committed), Async (tracked Canvas job), and Rich-ready
  (validated complex visual state).
- A future Canvas specialist receives a fixed Tutor/application objective and
  may plan a scene; it never independently changes the learning objective.
- The first proof is a narrow math/science use case and allowlisted catalog, not
  a freeform board or arbitrary browser-code executor.

## Risks

- Free-form scene/code generation creates ungrounded teaching content, unsafe
  execution, and inaccessible interaction.
- Canvas SDKs can hide browser-only state and defeat Tutor reconstruction.
- Rich images can fail math correctness, accessibility, and action extraction.
- Heavy libraries add bundle/mobile cost before learner value is proven.

## Contradictions

The product asks for an active Canvas while the normal Tutor baseline is one
call and current streaming is chat-only. Bounded prompt context must not mean
discarding learning-relevant Canvas history: full semantic history remains
application-owned and queryable. Richness must come from validated execution
layers, not uncontrolled model browser authority.

## Options

## Canvas Execution Matrix

| Option | Learning case / output contract / owner | Timing and streaming | Student actions / extraction | Correctness, accessibility, RTL, mobile | Validation, security, fallback | Effort / provider dependence |
| --- | --- | --- | --- | --- | --- | --- |
| Deterministic typed React/SVG | Make-ten, number line, fraction bars, step cards; application selects typed ArtifactIntent plus renderer data | Post-turn; app can progressively update committed state; rich-ready immediate for supported view | Buttons/drags have keyboard equivalents and emit typed semantic operations | Highest inspectability; DOM/SVG labels and dir auto; strong mobile; math supplied by state | Schema/allowlist/source-turn check; text/diagram fallback | Low-medium; provider independent |
| JSXGraph | Points, constructions, graphs; typed geometry model/config | Post-turn and committed operation updates | Named geometry operations, not pointer noise | Need keyboard/a11y test and bidi labels; moderate mobile | Allowed constructions/parameters; static SVG/text fallback | Medium; provider independent |
| React Konva | Spatial manipulatives, annotated diagram, constrained drag layout; typed scene graph | Post-turn or async layout; validated patches only | Drag/drop becomes committed placement/transform | Canvas needs DOM alternative; RTL app work; weaker small screen | Scene/action limits; DOM/SVG fallback | Medium-high; provider independent |
| MathLive | Equation editing and practice answer fields; typed expression/answer contract | Immediate local entry; post-turn feedback | Submit/edit commits expression/answer; keystrokes do not | Strong structured math; test keyboard/virtual-keyboard/focus/Arabic; moderate mobile | Parser and server validation; text input fallback | Medium; provider independent |
| A2UI declarative surfaces | Cards, forms, stepper/check surfaces; messages, catalog, data updates/actions | Transport-agnostic progressive messages; rich-ready as valid messages arrive | Registered actions map to Studio events | Catalog must provide a11y/RTL/mobile; protocol does not prove pedagogy | Validate message/catalog/action; typed Lina fallback | Medium; renderer dependency |
| Specialist typed ScenePlan | Complex bounded explanation; scene kind, renderer key, data, expected revision, a11y metadata | Async specialist/post-turn; never render before validation | Renderer-specific typed operations stay app owned | Depends on selected renderer; no invented inaccessible primitive | Objective/source/revision/catalog validation; deterministic fallback | Medium-high; model/provider quality |
| tldraw scene/action architecture | Future freeform spatial work and shared boards; shapes/actions/snapshots | Local interaction; validated agent actions may stream | Create/update/delete actions can be semantic after filtering | Accessibility improvements exist, but learning RTL/mobile proof remains | App owns history/auth/version; production-license review; typed fallback | High; product dependency |
| OpenMAIC packages | Lesson/PBL/interactive widgets; package DSL/renderer contract | Generation can be async or parallel; renderer after plan | Translate widget event into Lina Studio event | Audit each package and prove Lina a11y/RTL | Contract boundary, iframe hardening, provider injection; own renderer fallback | Medium-high; generation adapter dependent |
| Generated SVG | One-off illustrative diagram; sanitized SVG AST/string | Async/post-turn; fragments not useful until valid | Usually static; separate typed controls for interaction | Text alternative/bidi labels difficult; responsive mobile | Sanitizer/type/size limits; static description fallback | Medium; provider dependent |
| Sandboxed HTML/CSS/JS | Rare isolated interactive widget; sandbox plus narrow message protocol | Async; no trusted progressive code execution | Only allowlisted semantic messages cross boundary | Highest a11y/RTL/mobile burden | iframe sandbox, CSP, origin/message validation; typed fallback | High; provider/security heavy |
| Generated images | Supporting real-world Science visual; image plus description/alt | Async; placeholder may state preparing | No native semantic manipulation | Never sole path; responsive mobile plus text | Safety/provenance/rights; text/diagram fallback | Medium; media provider dependent |
| Simulations | Constrained forces/circuits/rates; validated domain parameter model | Post-turn/local after load; rich-ready after initialize | Typed parameter/answer event | Keyboard/control/text state and mobile performance proof | Domain tests/range limits/deterministic replay; static fallback | High; provider independent after authored model |
| Optional 3D | Truly spatial solids/molecules/vectors; typed model/scene | Async asset load; slowest rich-ready | Meaningful camera/object operations only | Highest device/a11y risk; mandatory 2D/text alternative | Asset/camera/performance limits; 2D fallback | High; provider independent after authored model |

## Hypothesized escalation ladder

1. Orientation and typed static views: source-bound React/SVG summaries,
   number/fraction diagrams, paths, and checks.
2. Controlled typed interaction: answer/selection/manipulation events with
   semantic extraction and accessible equivalents.
3. Domain adapters: evaluate MathLive, JSXGraph, or Konva only for a named
   learning task.
4. Declarative surfaces: evaluate A2UI-style messages against a Lina-owned
   catalog for structured Canvas/practice panels.
5. Specialist ScenePlan: only if a proof shows model-composed visual planning
   beats deterministic renderer selection.
6. Freeform and advanced media: tldraw, generated SVG, isolated widgets,
   images, simulations, and 3D behind separate value/safety/a11y gates.

This is a **hypothesis**, not an implementation order or approval.

## Timeline examples

### Make-ten: 9 + 6

Student asks or manipulates counters → Tutor establishes a fixed make-ten
objective → deterministic ten-frame shows nine plus six → student moves one
counter → application commits one semantic regroup event → Tutor sees current
snapshot plus event since watermark and explains fifteen. Chat: immediate.
Canvas: post-turn. No specialist needed.

### Fraction comparison

Student compares fractions → Tutor establishes comparison goal → typed fraction
bars receive normalized values and shared-denominator view → student selects or
submits check → application records answer submission → Tutor reacts. Specialist
only if the required visual is absent from the typed repertoire. Canvas:
post-turn; preparation state may be progressive.

### Canvas-first geometry

Student opens approved construction → application loads typed geometry scene →
student commits point/segment transformation → event/snapshot update → Tutor
receives all events since observation watermark and can query older history →
Tutor requests the next construction. JSXGraph is an adapter candidate, not a
default. Canvas can be immediate after scene load; Tutor stream is independent.

### Interactive quiz/manipulation

Tutor creates a server-validated guided check → Canvas renders a typed question
or manipulative → student submits structured answer → application writes one
semantic operation and validates active source turn → Tutor responds. This is
learning-first practice, not Exam Mode. No Canvas model call is necessary.

### Custom Science visual

Tutor has a fixed objective but no typed renderer fits → eligibility rule may
dispatch specialist with objective, allowed catalog and base scene → specialist
returns typed ScenePlan, not code → application validates/renders. Chat stays
immediate; base Canvas is post-turn; custom rich-ready is async. Timeout leaves
Tutor guidance and a truthful typed/last-valid fallback.

## A2UI comparison

Official A2UI material now describes v0.9.1 as Current Production and v1.0 as
Candidate. It has a stable React renderer path, transport-agnostic message
delivery, component catalogs, data-model updates, progressive rendering,
client actions, and validation/recovery messages. That corrects prior maturity
language; it does not make A2UI a required runtime.

| Choice | Flow | Strength | Lina risk | Research position |
| --- | --- | --- | --- | --- |
| Actual A2UI adoption | Canvas specialist → A2UI messages → Lina-owned catalog/React Canvas → Student action → Studio event | Mature declarative surface/state/action semantics | Dependency/protocol/version lifecycle; catalog still needs safety/a11y governance | Proof spike only |
| Small Lina spec inspired by A2UI | Specialist/renderer writes minimal Lina Scene spec → catalog → event | Source-bound and small | Lina maintains processor/schema | Leading first-proof candidate |
| A2UI reference only | Reuse catalog/data/action/progressive-render patterns | No runtime commitment | Local implementation work | Valid baseline |

## External evidence consulted

- [A2UI renderer development guide](https://github.com/a2ui-project/a2ui/blob/main/docs/public/guides/renderer-development.md)
  — v0.9.1 Current Production, v1.0 Candidate, React/web core, actions and
  validation/recovery; accessed 2026-09-02.
- [A2UI repository](https://github.com/a2ui-project/a2ui).
- [JSXGraph accessibility](https://jsxgraph.org/home/documentation/accessibility/).
- [Konva documentation](https://konvajs.org/docs/).
- [MathLive keyboard guide](https://mathlive.io/mathfield/guides/virtual-keyboard/).
- [MDN iframe sandbox](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe#sandbox).
- [tldraw license](https://tldraw.dev/community/license).

## Recommendations

### 1. Make typed renderers the control

- **Recommendation:** Use deterministic React/SVG plus semantic Studio events as
  the baseline against every richer option.
- **Reason:** It proves learning value and full observability without model,
  framework, or browser-code authority.
- **Expected impact:** A measurable control for specialist/DSL evaluation.
- **Mandatory / Optional:** Mandatory baseline.
- **Priority:** P0.
- **Direct view:** Rich appearance is not reason to bypass typed contracts.
- **Risk of ignoring:** The proof cannot attribute value to orchestration versus
  presentation.
- **Confidence:** High.
### 2. Separate A2UI and ScenePlan proof choices

- **Recommendation:** Compare a small Lina Scene spec with A2UI only after the
  deterministic baseline proves a concrete gap.
- **Reason:** Both solve declarative composition but carry different dependency
  and ownership costs.
- **Expected impact:** Bounded adoption decision rather than generic GenUI.
- **Mandatory / Optional:** Mandatory comparison before A2UI adoption.
- **Priority:** P1.
- **Direct view:** Current A2UI maturity supports evaluation, not adoption.
- **Risk of ignoring:** A protocol becomes accidental runtime authority.
- **Confidence:** Medium-high.

### 3. Defer executable/high-complexity paths

- **Recommendation:** Keep sandboxed code, generated images, simulations, and
  3D behind separate learning-value, security, accessibility, and mobile gates.
- **Reason:** They add surface area faster than they establish coordination value.
- **Expected impact:** Safer staged expansion.
- **Mandatory / Optional:** Mandatory guardrail.
- **Priority:** P1.
- **Direct view:** Canvas richness follows pedagogy, not the reverse.
- **Risk of ignoring:** Unbounded security and accessibility debt.
- **Confidence:** High.
