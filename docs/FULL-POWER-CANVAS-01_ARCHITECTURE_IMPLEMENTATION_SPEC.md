# FULL-POWER-CANVAS-01 — Architecture & Implementation Specification

**Project:** Lina Personal Learning System  
**Status:** READY FOR PRODUCT OWNER APPROVAL  
**Scope:** Full-Power AI Learning Canvas, safe custom visual runtime, reusable visual artifact registry, Tutor explainability bridge, reuse/adapt/create execution model  
**Current implementation baseline:** `codex/canvas-visual-intelligence-01` @ `62df59bcc8c43074c223d79b73bcf97a0905ed4c`  
**Architectural parent:** completed STUDIO-AGENTIC-01 baseline @ `d0bbc17c6cb74ce6162ac4a465cd261e1dd61075`  
**Audience:** Product Owner, Codex, AI implementation agents, reviewers  

---

# 0. Executive Decision

Lina's Canvas is no longer governed as a finite catalogue of typed renderers with custom generation as a weak fallback.

The approved target is a **hybrid full-power visual composition system**:

```text
Primary Tutor
    ↓
CanvasBrief
+ server-filtered Visual Learner Context
    ↓
Full-Power Canvas Agent
    ↓
Search existing visual capability/artifact
    ↓
REUSE ── or ── ADAPT ── or ── CREATE
    ↓
Visual composition/runtime
    ↓
Safe validation + sandbox where generated code is used
    ↓
Browser render/preview
    ↓
Optional bounded visual review/refinement
    ↓
Final Learning Canvas
    ↓
Semantic Manifest + meaningful Studio events
    ↓
Same Primary Tutor
```

The governing product objective is:

> **Choose or create the representation that best helps the student understand, with visual quality appropriate to the learner, while minimizing latency and cost without sacrificing necessary learning quality.**

The following rule replaces the previous implicit visual ceiling:

> **Typed renderers are a fast path, not a capability ceiling.**

Custom generated visual composition becomes a **first-class escalation capability** inside a strict sandbox. It is not the default for every question, and it is not an exceptional last resort that should be avoided when it is the best educational representation.

The previous high-quality Canvas outputs are a **quality floor**, not templates. New visuals may look different and should be better when the educational problem calls for it.

---

# 1. Problem Being Solved

The current system has strong architecture around Tutor authority, source grounding, Studio persistence, typed Canvas blocks, tool provenance, safety, same-Tutor continuity, and generated-asset ownership. The latest Canvas work also restored filtered learner context and improved deterministic SVG rendering.

The remaining limitation is not model intelligence. It is **expressive visual authority**.

The existing Agent can reason about a representation, but it is largely forced into a small visual grammar and a small number of deterministic renderer shapes. This creates a mismatch:

```text
Strong model reasoning
+ good orchestration
+ safe runtime
+ narrow expressive visual grammar
= technically valid but visually weak Canvas
```

Examples of the failure mode include:

- a Science system becoming generic circles and arrows when an illustrated, layered, animated explanation would be clearer;
- a Math concept being forced into a renderer whose contract cannot express the required geometry;
- a language interaction collapsing into cards even when direct manipulation or spatial composition would teach better;
- an Agent deciding on visual hierarchy or motion while the renderer can express only a small fraction of that decision;
- repeated rebuilding of similar visual code because prior successful generated visuals are not available as reusable assets.

FULL-POWER-CANVAS-01 solves the visual ceiling without weakening Lina's safety, educational authority, persistence, provenance, or explainability.

---

# 2. Governing Product Principles

These principles are mandatory.

## 2.1 Learning value is the top criterion

The question is not "which renderer is cheapest?" or "which library do we already have?"

The question is:

> **What representation gives this learner the best chance of understanding this concept now?**

Cost and latency matter, but they optimize the chosen educational path rather than dictate a visibly inferior one.

## 2.2 Maximum visual authority, minimum system authority

The Canvas Agent may receive broad authority over **visual composition**, including the ability to create custom interactive visuals.

It does not receive broad authority over Lina's system.

It must not gain unrestricted access to:

- learner records;
- Personal Memory;
- Learning Intelligence;
- database credentials;
- cookies or browser identity;
- private application state;
- arbitrary network access;
- filesystem access;
- Studio writes outside the validated Studio boundary;
- Tutor authority;
- child-safety policy authority.

## 2.3 Tutor teaches; Canvas composes

The existing invariant remains:

```text
Tutor teaches.
Canvas Agent composes.
Tools establish exact truth.
Code validates and executes.
Studio persists.
Tutor understands the Canvas.
```

The Canvas Agent is not a second Tutor.

## 2.4 Reuse when good; create when necessary

Reuse is preferred because it can improve latency, consistency, cost, and reliability.

Reuse must never force a poor representation.

The routing principle is:

```text
REUSE if an existing artifact is genuinely fit
ADAPT if its structure is fit but parameters/presentation need change
CREATE if reuse/adaptation would compromise the learning representation
```

## 2.5 Creative output remains explainable

Regardless of whether a visual is built using SVG, React, Motion, JSXGraph, Konva, p5, generated imagery, or another approved capability, the educational meaning exposed to the Tutor must remain implementation-independent and inspectable.

## 2.6 Generated code is never application authority

Generated custom visual code may execute only inside the approved visual sandbox.

It cannot become arbitrary application code, modify Lina's core application state, or silently introduce new system capabilities.

---

# 3. Protected Areas — Must Remain Intact

FULL-POWER-CANVAS-01 must preserve the following unless a separate Product Owner decision explicitly changes them.

| Protected area | Required behavior |
|---|---|
| Primary Tutor authority | Only the Primary Tutor owns teaching, explanation, facts, pedagogical strategy, and student-facing educational reasoning. |
| CanvasBrief boundary | Educational request semantics remain Tutor-authored and implementation-independent. |
| Filtered learner context | Canvas receives only the already-approved bounded visual learner context, not broad memory/intelligence. |
| Student source safety | Raw student source material is not casually forwarded into custom visual code or reusable artifacts. |
| Child Safety Policy | Visuals, generated images, custom code, interactions, and tool use all remain downstream of the non-overridable safety policy. |
| Studio authority | Studio remains the persistent scene/event/snapshot/interaction authority. |
| Same-Tutor continuity | Meaningful Canvas state returns to the same Primary Tutor. |
| Evidence discipline | Meaningful semantic learning actions may become Candidate Events; raw clickstream does not become learner intelligence. |
| Generated asset ownership | Provider outputs must be adopted into project-owned storage before durable student-facing use. |
| Historical replay | Existing Studio/Agentic Canvas scene versions remain readable. |
| Current-behavior priority | Historical personalization must never override demonstrated current learner behavior. |
| No diagnosis | Visual choices do not create personality, intelligence, psychological, or learning-style labels. |

---

# 4. Scope

## 4.1 In scope

- Full-Power Canvas Agent authority over bounded visual composition.
- Reuse / Adapt / Create routing.
- Reusable Visual Registry.
- Generated custom visual packages.
- Sandboxed visual runtime.
- Allowlisted visual/runtime dependency capabilities.
- Browser preview and bounded visual review/refinement.
- Rich Semantic Manifest.
- Stable semantic IDs.
- Tutor explainability bridge.
- Semantic interaction bridge into Studio.
- Reuse/version/fork/promotion rules.
- Cost and latency routing.
- Generated-image composition with overlays/labels/interactions.
- Existing typed Agentic Canvas as a fast path.
- Migration and governance reconciliation.
- Real-provider and real-browser acceptance.

## 4.2 Out of scope

- Replacing the Primary Tutor with a multi-agent teaching system.
- Letting Canvas Agent write directly to Learning Intelligence.
- Arbitrary public internet access from generated visual code.
- Unsandboxed model-generated JavaScript in the Lina application.
- A generic website/app builder unrelated to learning.
- A marketplace of public user-created artifacts.
- Multi-tenant artifact sharing.
- Student-authored executable code runtime.
- New psychological personalization models.
- Automatic subject expansion beyond approved Lina learning domains merely because custom code is possible.
- A giant pre-authored catalog of lessons or visual templates.

The first supported educational domains remain Math, Science, Arabic, English/language learning, with the architecture remaining extensible to later approved subjects.

---

# 5. Current Architecture to Preserve

The current Agentic Canvas path already provides valuable infrastructure and should become one capability family inside the new system rather than being discarded.

Preserve and reuse:

- CanvasBrief and server audit/admission;
- `VisualLearnerContextV1` filtering and resolution;
- Canvas Agent via OpenAI Agents SDK;
- deterministic math/unit tools;
- typed block tools;
- Scene v1/v2 historical reading;
- presentation layout/palette/motion semantics;
- Studio Canvas Specialist run/job lifecycle;
- stale-result fencing;
- exact renderer admission;
- ObjectStorage/generated asset adoption;
- semantic Studio operation settlement;
- same-Tutor Studio observation path;
- browser-independent production `StudioRendererHost` harness pattern;
- existing visual-toolbelt components and established child-facing quality references.

The latest current branch should be treated as the **migration baseline**, not as the final visual architecture.

---

# 6. Target Architecture

```text
Student
   │
   ▼
Primary Tutor
   │  owns facts, teaching, grounding, pedagogy
   │
   ├── CanvasBriefV1
   └── bounded VisualLearnerContext
            │
            ▼
      Full-Power Canvas Agent
            │
            ├── Search Reusable Visual Registry
            │      ├── inspect candidate
            │      ├── REUSE
            │      └── ADAPT
            │
            ├── Existing typed visual tools
            ├── deterministic math/unit/data tools
            ├── generated image capability
            ├── Code Interpreter when analytically justified
            └── CREATE Custom Visual Package
                         │
                         ▼
              Visual Build / Validation Pipeline
                         │
                ┌────────┴────────┐
                │                 │
           Typed runtime     Custom sandbox runtime
                │                 │
                └────────┬────────┘
                         ▼
                  Production Browser
                         │
                         ├── deterministic technical checks
                         └── bounded visual AI review when required
                                   │
                                   ▼
                          Final Canvas Instance
                                   │
                         Semantic Manifest + State
                                   │
                                   ▼
                                 Studio
                                   │
                                   ▼
                            Same Primary Tutor
```

No additional teaching agent sits above or beside the Primary Tutor.

The Full-Power Canvas Agent may use sub-capabilities/tools internally, but it remains one composition authority from the product perspective.

---

# 7. Canvas Agent Authority Model

## 7.1 The Agent may decide

The Canvas Agent may decide, based on the Tutor's educational brief and bounded learner context:

- whether a Canvas is useful at all within the already-admitted request;
- representation type;
- composition strategy;
- whether an existing artifact is appropriate;
- whether to reuse or parameter-adapt it;
- whether a custom visual should be created;
- which approved visual libraries/capabilities should be used;
- layout and hierarchy;
- diagram topology;
- mathematical/spatial representation;
- image/illustration usage;
- interaction model;
- motion/reveal behavior;
- responsive behavior;
- labeling density;
- how learner age/grade should calibrate presentation;
- whether supporting text, labels, callouts, diagrams, or images are useful;
- whether one bounded visual review/refinement is justified.

## 7.2 The Agent may not decide

The Agent may not:

- change the Tutor's objective;
- invent academic facts to make a visual easier to draw;
- infer new learner traits;
- override source uncertainty;
- override safety policy;
- read broad student memory/intelligence;
- choose arbitrary external code dependencies at runtime;
- grant its own network permissions;
- persist arbitrary application state;
- create new Evidence categories;
- turn presentation preference into learning diagnosis;
- convert implementation detail into Tutor-visible teaching authority.

---

# 8. Capability Portfolio

The Canvas Agent should operate against an explicit **Visual Capability Registry**. This is different from the Reusable Visual Artifact Registry.

The Capability Registry answers:

> What execution/rendering capabilities are approved in this deployment?

Initial capability families include:

| Capability | Role |
|---|---|
| React | Component/runtime composition. |
| Native SVG | Precise scalable diagrams, overlays, shapes, paths, labels. |
| Motion | Finite meaningful animation, reveal, gesture and transition. |
| JSXGraph | Mathematical graphs, number lines, coordinates, geometry, sliders, exact math exploration. |
| React Konva | Direct manipulation, drag/drop, spatial tasks, canvas interaction. |
| MathLive | Mathematical input and editable notation. |
| Rough.js | Optional hand-drawn warmth where educationally appropriate. |
| Recharts | Data/chart representations when actual chart semantics are required. |
| p5.js | Simulations, particles, forces, motion and richer dynamic scientific behavior. |
| React Flow | Node/edge interaction where a real educational graph/system use case benefits. |
| Image Generation | Organic/naturalistic illustration and visual assets. |
| Code Interpreter | Bounded analytical/data transformation when deterministic local code is insufficient or impractical. |
| Existing typed Agentic Canvas tools | Fast-path known semantic representations. |
| Custom Visual Program | Generated custom React/SVG/interaction package in sandbox. |

The architecture must allow later approved capabilities without rewriting Tutor or Studio.

New third-party libraries require normal reuse/license/security/performance review before entering the runtime allowlist. The Agent cannot dynamically install arbitrary packages from the internet.

---

# 9. Reuse → Adapt → Create Routing

## 9.1 Search first, but do not force reuse

For each admitted Canvas need, the Canvas Agent receives a lightweight search capability.

The registry search should return only a small number of high-relevance candidates, normally 3–5, containing:

- artifact identity/version;
- semantic purpose;
- supported capabilities;
- parameter schema summary;
- interaction support;
- age/presentation flexibility;
- known limitations;
- quality/trust status;
- optional preview thumbnail/reference;
- cost/latency class if known.

The Agent does not need raw stored source code merely to evaluate fit.

## 9.2 REUSE

Use REUSE when:

- educational semantics match;
- required interaction is supported;
- parameter schema can represent the current values;
- learner presentation can be calibrated without structural change;
- visual quality is already strong.

Reuse should normally require no visual model review unless a runtime validation fails.

## 9.3 ADAPT

Use ADAPT when an artifact's core structure is good but the current instance needs:

- different values;
- labels/language;
- color/palette roles;
- density;
- age/grade presentation;
- optional imagery/theme;
- safe interaction parameters;
- layout parameters already supported by the artifact.

Parameter changes create an **instance**, not a new artifact version.

A structural change to reusable code/contract creates a new version or fork.

## 9.4 CREATE

Use CREATE when:

- no candidate expresses the required learning representation;
- adaptation would distort the concept;
- existing artifacts are materially weaker than a custom composition;
- a simulation/organic illustration/mixed interaction is required;
- the Agent has a novel but bounded educational representation that fits the Tutor brief better.

CREATE is not a failure. It is an approved first-class path.

---

# 10. Reusable Visual Registry

The Reusable Visual Registry is a project-owned memory of successful reusable visual capabilities.

It is not learner memory and must not contain student-specific private context.

## 10.1 Artifact definition

Recommended conceptual contract:

```text
ReusableVisualArtifact
  artifact_id
  stable_slug
  current_version_id
  semantic_purpose
  subject_applicability[]
  capability_tags[]
  runtime_kind
  parameter_schema
  interaction_schema
  manifest_contract
  dependency_capabilities[]
  responsive_support
  locale_direction_support
  quality_status
  lifecycle_status
  created_from
  created_at
```

## 10.2 Artifact version

```text
ReusableVisualArtifactVersion
  version_id
  artifact_id
  version_number
  parent_version_id?
  source_digest
  bundle_digest / typed_spec_digest
  runtime_contract_version
  parameter_schema_version
  manifest_schema_version
  dependency_versions
  validation_status
  quality_status
  technical_evidence
  created_at
```

Do not persist provider-temporary URLs or raw student context inside reusable definitions.

## 10.3 Artifact instance

A student-facing Canvas is an instance, not the reusable definition.

```text
VisualArtifactInstance
  instance_id
  artifact_version_id
  studio_scene_id
  Tutor brief lineage
  bound parameters
  current semantic state
  Semantic Manifest
  owned asset references
  locale/direction
  learner-context digest or bounded presentation inputs
```

If a personalized theme is used, the reusable artifact stores a generic parameter such as `illustration_theme`; the student-specific value exists only in the instance.

## 10.4 Build history vs reusable registry

Every generated custom visual may have a build record for reproducibility/audit.

Not every generated visual becomes reusable.

```text
Visual Build History
= every generated attempt/final build needed for traceability

Reusable Visual Registry
= artifacts worth finding and using again
```

---

# 11. Registry Lifecycle and Promotion

Avoid creating a junk drawer of thousands of one-off artifacts.

Use a small lifecycle:

```text
CANDIDATE → VALIDATED → TRUSTED → RETIRED
```

## 11.1 CANDIDATE

A newly created visual may become a candidate after:

- successful compile/runtime validation;
- valid Semantic Manifest;
- no forbidden/private data;
- successful browser render;
- custom-create visual review accepted;
- parameterization/reuse potential identified.

Candidates may be reused, but should rank below validated/trusted artifacts and normally receive a preview validation after adaptation.

## 11.2 VALIDATED

Promote when the artifact proves it can operate with multiple valid parameter sets or a second real reuse without structural breakage.

Do not require human approval for routine promotion if deterministic and AI quality gates are satisfied.

## 11.3 TRUSTED

A repeatedly successful reusable artifact may become trusted after project-defined technical reuse evidence. Trust means lower runtime verification cost, not educational authority.

## 11.4 RETIRED

Retire artifacts that become incompatible, unsafe, visually inferior, or superseded.

Historical instances remain replayable through pinned versions.

---

# 12. Fork, Version, and Adapt Rules

Use the following distinction:

| Change | Result |
|---|---|
| Value/label/language/theme parameter | New instance only |
| Age/grade density parameter within supported range | New instance only |
| Bug fix preserving contract | New artifact version |
| Structural visual improvement preserving purpose | New artifact version |
| New semantic capability or interaction contract | New version or fork, whichever preserves clearer lineage |
| Different educational purpose | New artifact |

The Agent may suggest/use a fork automatically when allowed by the registry tool, but project code controls version creation and validation.

Generated artifacts must never overwrite a trusted version in place.

---

# 13. Custom Visual Runtime

## 13.1 Purpose

The Custom Visual Runtime exists so model intelligence is not limited to predefined renderer vocabulary.

It allows the Canvas Agent to produce a bounded visual package using approved browser technologies while keeping generated code isolated from Lina's application authority.

## 13.2 Recommended visual package

A custom artifact should compile from a small package conceptually similar to:

```text
visual-package/
  entry.tsx        # or bounded HTML/SVG entry where simpler
  styles.css       # optional bounded local styles
  manifest.json    # Semantic Manifest / declarations
  params.schema.json
  artifact.json    # runtime/dependency metadata
```

The implementation does not have to use these exact filenames. The contract matters more than filesystem shape.

## 13.3 Approved import model

Generated custom code may import only packages/modules explicitly present in the Visual Capability Registry.

No runtime package installation.

No arbitrary URL imports.

No dynamic import from uncontrolled sources.

## 13.4 Compile path

Recommended implementation direction:

1. validate source size and package metadata;
2. parse/lint imports and reject non-allowlisted dependencies;
3. reject explicitly dangerous APIs where static detection is reliable;
4. compile/bundle without executing generated code server-side;
5. persist compiled bundle and source digests in project-owned storage;
6. mount compiled output only inside the visual sandbox;
7. perform browser/runtime validation there.

A lightweight bundler such as the project's approved Node build tooling or an `esbuild`-class build step is preferable to introducing a full new application framework.

The exact compiler is an implementation choice after repository inspection.

---

# 14. Sandbox Security Model

Custom code must run in an isolated browsing context that has **visual authority only**.

Recommended browser boundary:

```text
sandboxed iframe
  sandbox="allow-scripts"
  NO allow-same-origin
  NO popups
  NO downloads
  NO forms
  NO top navigation
  strict CSP
  connect-src 'none'
  project-controlled asset delivery only
```

## 14.1 Runtime permissions

The custom visual must not directly access:

- parent DOM;
- cookies;
- localStorage/sessionStorage of Lina app origin;
- secrets;
- application API credentials;
- database;
- arbitrary network;
- filesystem;
- clipboard without explicit future decision;
- camera/microphone;
- browser location;
- unrelated device APIs.

## 14.2 Asset delivery

Generated/project-owned images should be supplied through a controlled asset bridge or sandbox-safe project asset mechanism.

Do not persist provider-temporary URLs.

Do not expose general application object-storage credentials.

## 14.3 Runtime resource protection

Use bounded limits for:

- generated source size;
- compiled bundle size;
- compile time;
- initial render timeout;
- visual handshake timeout;
- event rate;
- Studio event payload size;
- total custom artifact blocks/elements where relevant.

A parent watchdog should be able to terminate/reload a non-responsive sandbox.

Do not build operating-system-level container infrastructure unless browser isolation proves insufficient for the approved use case.

## 14.4 Communication

The only normal communication channel between sandbox and application is an explicit versioned `postMessage`-style semantic bridge.

Every inbound event from sandbox must be validated against:

- current artifact instance;
- nonce/session identity;
- allowed semantic action;
- Semantic Manifest declaration;
- schema limits;
- current Studio scene version.

Unknown or malformed events are rejected.

---

# 15. Rich Visual Composition Model

FULL-POWER Canvas must not repeat the mistake of replacing six old renderers with a slightly larger finite list.

The custom path should be able to express, directly through code and/or a richer declarative layer:

- layers;
- groups;
- regions;
- shapes;
- paths;
- connectors;
- arrows;
- labels;
- callouts;
- icons;
- generated illustrations;
- background forms;
- z-order;
- anchors;
- alignment;
- semantic color roles;
- typography hierarchy;
- mathematical objects;
- graph/series data;
- spatial relationships;
- interaction controls;
- draggable/selectable/connecting objects;
- finite motion and progression;
- responsive composition;
- accessibility descriptions.

Do **not** build a giant custom DSL merely to enumerate these if generated custom React/SVG plus a strict Semantic Manifest is simpler and more expressive.

The implementation should choose the smallest architecture that gives the Agent genuine visual power while preserving validation and Tutor explainability.

---

# 16. Deterministic Truth Boundary

Visual freedom must not create mathematical/scientific hallucination.

The governing rule is:

```text
AI decides representation.
Deterministic tools/code establish exact computable truth.
Tutor/source grounding establishes educational facts.
Renderer/custom visual expresses those truths.
```

Examples:

- exact fractions/decimal comparisons are computed by deterministic math tools;
- unit conversion uses the approved conversion boundary;
- plotted coordinates come from typed/data values, never marker index or renderer guesses;
- physics simulation constants/initial conditions are explicit;
- chart values come from supplied/derived data;
- generated illustration may be aesthetically creative but labels/educational relationships remain grounded in the CanvasBrief/verified data.

If required geometry/data is unavailable, the visual must request a valid derived value through an approved tool or simplify/fail safely. It must not invent hidden coordinates simply to make the display look complete.

---

# 17. Browser Preview and Visual Feedback Loop

A major architectural change is that complex generated visual work can be **seen by the Canvas system before being finalized**.

## 17.1 Fast paths

For trusted typed/reusable artifacts:

```text
instantiate → deterministic validation → render
```

No extra AI visual critique by default.

## 17.2 Adapt path

For parameter adaptation:

```text
adapt → render smoke check → finalize
```

AI visual review is optional only when adaptation is structural/novel enough to warrant it.

## 17.3 Create path

For genuinely custom visuals:

```text
Generate custom package
→ compile/validate
→ browser preview
→ technical checks
→ same Canvas visual authority reviews screenshot/output
→ ACCEPT or one refinement
→ final validation
```

One visual review/refinement pass is the default maximum for custom CREATE.

A second correction is allowed only for a concrete validation/render failure, not endless aesthetic polishing.

## 17.4 Review inputs

The visual review should receive only what it needs:

- original CanvasBrief;
- bounded VisualLearnerContext;
- Semantic Manifest;
- screenshot/render result;
- technical validation findings.

It does not receive broad learner memory or application secrets.

## 17.5 Review criteria

The review asks:

- Is the representation educationally clear?
- Is the hierarchy obvious?
- Are labels/relationships readable?
- Does the layout fit the learner age/grade?
- Is the key idea visually dominant?
- Is motion useful rather than decorative?
- Is the artifact cluttered, confusing, childish, or corporate?
- Are there overlap/overflow/contrast/legibility problems?
- Does the visual appear to contradict the manifest or brief?

---

# 18. Semantic Manifest — Tutor Understanding Boundary

Every finalized Canvas instance must have a **Semantic Manifest** independent of rendering technology.

The Tutor does not need to understand generated React code. It needs to understand what the student sees and what the visual means.

Recommended contract:

```text
CanvasSemanticManifestV1
  version
  brief_digest
  objective
  representation_summary
  entities[]
  relations[]
  quantities[]
  presentation_steps[]
  interactions[]
  calculated_results[]
  visual_descriptions[]
  current_state_schema
  provenance
```

## 18.1 Entities

Each educationally meaningful entity has a stable semantic identity:

```text
semantic_id: condensation_cloud
kind: process_state
label: "Condensation"
educational_meaning: "Water vapor cools into liquid droplets"
visible_description: "cloud with inward blue arrows"
```

Do not use DOM IDs like `div-17` as educational identity.

## 18.2 Relations

Relations should describe meaning, not drawing implementation:

```text
source: evaporation
relation: leads_to
target: condensation
meaning: "Cooling follows rising water vapor in this representation"
```

## 18.3 Quantities and calculated results

Expose relevant exact values with provenance when the Tutor may need to explain them.

## 18.4 Presentation steps

For staged explanations/simulations, expose bounded semantic steps:

```text
step_1: show evaporation
step_2: connect vapor to condensation
step_3: show precipitation
```

The Tutor can explain the current step without knowing animation code.

## 18.5 Visual descriptions

The manifest may contain short bounded descriptions of visible appearance where deictic conversation matters, for example:

- "the blue curved arrow";
- "the large fraction bar on the left";
- "the highlighted verb token".

These descriptions are presentation context, not learner facts.

## 18.6 Screenshot fallback

The Tutor normally uses manifest + Studio semantic state.

A visual screenshot may be supplied to the same Primary Tutor only when needed to resolve a visual reference/ambiguity that the manifest cannot safely answer.

This should be exception/on-demand, not every Tutor turn.

---

# 19. Semantic Interaction Bridge

Custom visual interactions must map into a bounded semantic event vocabulary.

Recommended action families include existing actions and controlled extensions where proven necessary:

```text
FOCUS
SELECT
MOVE
SET_VALUE
CONNECT
SUBMIT
REORDER
TOGGLE
STEP
RESET_VIEW   # non-evidentiary unless a later explicit rule says otherwise
```

Do not expose raw DOM events as Studio learning events.

A semantic event should include only bounded fields such as:

```text
CanvasSemanticEventV1
  manifest_version
  artifact_instance_id
  semantic_action
  semantic_id
  related_semantic_id?
  from_value?
  to_value?
  step_id?
  idempotency_key
```

The server validates the event against the current manifest and Studio scene version before settlement.

Meaningful settled events become available to the same Primary Tutor as Studio observations.

Raw pointer movement, hover spam, animation frames, and arbitrary click telemetry do not become learner intelligence.

---

# 20. Tutor Continuity Contract

The same Primary Tutor must always be able to answer:

- what the Canvas is trying to show;
- what the visible major entities mean;
- which relationship or step is active;
- what the student just changed/selected/submitted;
- which exact quantities/results are being represented;
- how the Canvas relates to the current teaching objective;
- what to explain next.

Tutor context should receive a compact bounded view:

```text
CanvasTutorObservation
  objective
  representation_summary
  active_step
  active_focus
  relevant_entities
  relevant_relations
  relevant_quantities
  latest_meaningful_interaction
  calculated_results when relevant
  source/brief lineage
```

Do not inject the entire custom code package or large manifest on every Tutor turn. Build a compact observation from manifest + current state.

The Tutor remains the student-facing explanation authority even if the Canvas Agent generated the visual.

---

# 21. Learner Context and Age/Grade Calibration

The existing filtered learner context remains authoritative.

Canvas may receive:

- `age_years`;
- `grade_level`;
- up to the approved number of explicitly selected safe visual personalization facts;
- locale/direction through approved context/brief.

It must not receive broad Personal Memory or Learning Intelligence.

Age/grade may affect:

- visual density;
- label depth;
- target size;
- illustration emphasis;
- use of progressive reveal;
- amount of simultaneous information;
- interaction complexity;
- explanatory annotation density.

Age/grade may not change:

- mathematical/scientific truth;
- curriculum facts;
- safety baseline;
- interpretation of student intelligence;
- learner diagnosis.

The product target is not "childish for children". It is **age-appropriate, polished, intelligent, and engaging** from younger learners through youth.

---

# 22. Student Sources and Custom Visuals

Preserve the approved source boundary:

```text
Student source
→ safety / source handling
→ Primary Tutor understanding
→ distilled educational semantics
→ CanvasBrief
→ Canvas Agent
```

Do not forward arbitrary raw file bytes, OCR dumps, storage keys, filenames, or private source identifiers into reusable custom code.

If a visual genuinely needs a source-derived image region or owned image asset, use an explicit server-authorized asset/derived-artifact path rather than giving the custom sandbox general source access.

The original source remains authoritative. AI reconstruction remains derived.

---

# 23. Generated Images as Composition Material

Image Generation is a composition capability, not necessarily the final Canvas.

A strong educational Canvas may combine:

```text
owned generated illustration
+ semantic overlays
+ labels
+ arrows/vectors
+ hotspots
+ interactions
+ staged reveal
```

Examples:

- plant anatomy illustration + tappable labeled regions;
- digestive system illustration + pathway overlay;
- ecosystem scene + relation arrows;
- geometric story illustration + exact mathematical overlay.

Provider image bytes must continue through project-owned asset adoption before durable use.

The Semantic Manifest must map important overlays/regions to educational meaning.

---

# 24. Cost and Latency Strategy

The goal is not to make every Canvas cheap. The goal is to avoid spending expensive generation where reuse achieves the same or better educational quality.

## 24.1 Cost ladder

Typical relative cost/latency:

```text
Trusted reusable artifact instance        lowest
Parameter adaptation                      very low
Existing typed renderer composition       low
New custom code generation                medium
Browser visual AI review                  additional
Image generation                          higher / variable
Code Interpreter                          on-demand / variable
```

## 24.2 Routing policy

- Search registry before custom creation.
- Return few candidates, not a large prompt payload.
- Do not force reuse if visual fit is poor.
- Do not call Image Generation for visuals that SVG/geometry represents better.
- Do not call Code Interpreter for ordinary exact arithmetic already covered by deterministic tools.
- Do not run AI screenshot review for trusted routine reuse.
- Custom CREATE receives one visual review pass by default; repeated generations are bounded.
- Cache compiled reusable bundles and preview metadata.
- Persist artifact versions so future reuse avoids regeneration/compilation.
- Observe actual latency/token/cost rather than guessing from architecture alone.

## 24.3 Model routing

Model choice should remain configurable.

The system may use a faster/cheaper Canvas model for reuse/adapt/tool selection and a stronger visual/code-capable model for genuinely novel CREATE when measured quality justifies it.

Do not hardcode a permanent model/provider choice into reusable artifact contracts.

---

# 25. Failure and Recovery

Canvas failure must never block learning.

Recommended recovery order:

```text
Custom CREATE fails compile/runtime
→ retry once only if failure is concrete and cheaply correctable
→ otherwise use best safe reusable/typed representation
→ otherwise Tutor continues with explanation without Canvas
```

Possible fail-closed reasons include:

- unsafe package/import;
- sandbox handshake failure;
- runtime timeout;
- manifest mismatch;
- semantic event mismatch;
- generated asset adoption failure;
- invalid mathematical data;
- stale Studio run;
- policy rejection.

Failures must be logged with bounded technical metadata, not raw learner/private data.

---

# 26. Quality Model

`render succeeded` is not visual acceptance.

A finalized Canvas should be judged on:

1. **Educational usefulness** — representation materially supports understanding.
2. **Semantic correctness** — visible relationships/quantities do not contradict grounded truth.
3. **Visual clarity** — focal idea and hierarchy are obvious.
4. **Age suitability** — density and interaction fit learner context without infantilization.
5. **Interaction usefulness** — interaction teaches/checks something rather than existing for novelty.
6. **Relationship legibility** — arrows, grouping, topology and labels are understandable.
7. **Responsive integrity** — usable on supported narrow/wide layouts.
8. **Motion quality** — finite and explanatory when used.
9. **Accessibility** — meaningful text equivalents/labels and keyboard/touch behavior where applicable.
10. **Tutor explainability** — manifest/state are sufficient for the Tutor to discuss the Canvas.
11. **Visual polish** — should not regress to crude cards or generic developer-demo appearance when richer composition is appropriate.

The historical accepted Canvas visuals are a structural quality floor, not pixel targets.

---

# 27. Reuse Learning Loop

As the project is used, successful visual artifacts should reduce future cost and improve consistency.

```text
Novel need
→ create strong artifact
→ validate
→ candidate registry entry
→ reuse/adapt on later need
→ successful reuse evidence
→ higher registry trust
→ less repeated generation
```

This is an **operational reuse loop**, not learner-profile learning.

Do not infer that an artifact is pedagogically effective from raw clicks or one student's success. Future artifact-effectiveness analytics, if added, must use approved Learning Intelligence/evidence principles and must not claim causal effectiveness without evidence.

---

# 28. Data and Persistence Model

Prefer PostgreSQL + existing ObjectStorage. Do not add a new infrastructure service without demonstrated need.

Recommended new/extended persistence concepts:

- `visual_artifacts`
- `visual_artifact_versions`
- `visual_artifact_builds`
- `visual_artifact_instances` or equivalent linkage through Studio Scene/run records
- optional artifact capability/search metadata
- owned compiled bundle/source assets in ObjectStorage where necessary

Use existing pgvector only if semantic artifact search benefits from it; begin with deterministic metadata/lexical filtering when sufficient.

Do not introduce a dedicated vector database for this feature.

All reusable artifact versions must be immutable after publication/validation; fixes create new versions.

---

# 29. Search and Selection Strategy

Artifact retrieval should be lightweight and bounded.

Candidate filtering should prioritize:

- semantic purpose/capability match;
- subject applicability;
- required interaction support;
- parameter compatibility;
- locale/direction capability;
- runtime compatibility;
- quality/trust status;
- current deployment capability availability.

Optional ranking signals:

- semantic embedding similarity using existing pgvector;
- successful technical reuse count;
- recent compatibility validation;
- average render latency.

Do not rank based on private student identity.

The Agent decides educational fit from a small candidate summary. The server enforces compatibility and permissions.

---

# 30. Implementation Architecture Recommendations

These are strong recommendations, not a rigid recipe. Codex may choose a simpler equivalent after inspecting repository truth.

## 30.1 Keep one Canvas Agent

Do not create Math Agent, Science Agent, Design Manager, Reviewer Manager, and other standing agents by default.

One Full-Power Canvas Agent should have skills/tools covering the approved visual domain.

A bounded visual-review call may reuse the same Canvas Agent identity/instructions with screenshot input.

## 30.2 Add a visual artifact service boundary

Likely responsibilities:

```text
VisualArtifactService
  search()
  inspect()
  instantiate()
  create_candidate()
  validate_build()
  publish_version()
  fork_version()
  retire()
```

The exact module names are implementation choices.

## 30.3 Add custom visual build boundary

Likely responsibilities:

```text
CustomVisualBuilder
  validate_source()
  compile()
  store_bundle()
  create_sandbox_descriptor()
```

Generated code is data/artifact input to this boundary, not trusted app source code.

## 30.4 Add sandbox renderer to exact Renderer Host admission

The production renderer host should admit the custom visual runtime only through an exact server-owned contract/version, analogous to existing exact renderer admission.

The Agent does not write `renderer_key`, `payload_schema_version`, or other authority fields.

## 30.5 Add semantic bridge validator

A server/app-owned validator maps sandbox messages to Studio operations/events only when declared in the manifest and valid for the current scene/version.

---

# 31. Migration from Current Agentic Canvas

Do not rewrite or delete the current typed Canvas work.

Migration strategy:

```text
Current Agentic Canvas v1/v2
→ becomes Fast Typed Runtime capability

New Reusable Visual Registry
→ can reference typed or custom runtime artifacts

New Custom Visual Runtime
→ additional first-class runtime kind

Studio
→ remains shared persistence/event authority
```

## 31.1 Backward compatibility

- existing v1/v2 Agentic scenes remain readable;
- current renderer contracts remain admitted;
- existing generated image ownership remains valid;
- current VisualLearnerContext remains valid;
- current Tutor/CanvasBrief boundary remains valid.

## 31.2 New writes

The implementation may introduce new versioned contracts for custom artifact instances/manifest without rewriting old scene history.

## 31.3 Branch strategy

When implementation is approved, start a new isolated branch/worktree such as:

```text
codex/full-power-canvas-01
```

from the approved current Canvas baseline (`62df59b...`) unless repository/main state has since intentionally incorporated an equivalent or newer baseline.

Do not silently implement from older main if the current Canvas baseline is not merged.

---

# 32. Governance Reconciliation

The existing governing documents currently describe typed artifact specifications + reusable renderers as primary and custom AI-generated HTML/SVG as fallback-only. FULL-POWER-CANVAS-01 intentionally changes that policy.

After final Product Owner approval, governance must be reconciled before or as part of implementation so Codex does not receive conflicting instructions.

## 32.1 `docs/PROJECT_REFERENCE.md`

Update Interactive Learning Artifacts to state:

- typed/reusable renderers remain the preferred fast path;
- custom generated visual runtime is an approved first-class escalation path;
- generated custom code must be sandboxed;
- Tutor explainability requires Semantic Manifest;
- reusable artifact registry can retain validated generalized artifacts;
- artifact failure still never blocks learning.

Replace the old implication:

```text
custom generated HTML/SVG = fallback only
```

with:

```text
custom generated visual = first-class escalation when reuse/adapt is not educationally sufficient
```

## 32.2 `AGENTS.md`

Update Learning Artifact Rules so AI agents:

- preserve reuse-first evaluation;
- do not force reuse over learning quality;
- treat custom runtime as approved only through sandbox/manifest boundaries;
- do not embed generated custom code directly into Lina app components;
- do not use arbitrary dependencies/network;
- preserve exact Studio/Tutor boundaries.

## 32.3 `docs/IMPLEMENTATION_PLAN.md`

Update artifact phase and cost strategy:

- reusable deterministic renderer is preferred when fit;
- generated custom visual is permitted when it improves representation;
- registry and sandbox become explicit architecture components;
- visual review is bounded and cost-aware;
- no repeated model generation when a validated reusable artifact exists.

## 32.4 `docs/TECHNOLOGY_REUSE_CATALOG.md`

Update artifact architecture section from fixed typed-renderer flow to hybrid:

```text
Tutor Brief
→ Canvas Agent
→ Reuse / Adapt / Create
→ typed runtime OR sandboxed custom runtime
→ Studio/Tutor semantic bridge
```

Retain existing approved library statuses unless implementation requires a separate dependency decision.

Sandpack may remain dev-only unless a focused fit check proves it is the best production sandbox/build mechanism. Do not assume it becomes production runtime merely because generated code exists.

## 32.5 `TASKS.md`

Add `FULL-POWER-CANVAS-01` as the active/next approved work item only after Product Owner approves this final spec.

## 32.6 `project-state/PROJECT_STATE.md`

Update current goal, current reality, active decision, protected areas, risks, and next action concisely.

## 32.7 `SYSTEM_MAP.html`

Update only if the architecture map is used as an active visual reference. This change is significant enough that a new system map is justified after implementation direction is approved.

---

# 33. Security and Privacy Threat Review

Minimum threat cases to design against:

| Threat | Required defense |
|---|---|
| Generated code attempts `fetch()` | Sandbox CSP `connect-src 'none'` + optional static rejection. |
| Generated code reads parent cookies/storage | opaque-origin sandbox, no `allow-same-origin`. |
| Generated code calls Lina APIs | no credentials/network; parent bridge rejects unknown messages. |
| Generated code creates popup/navigation | sandbox capabilities omitted. |
| Infinite loop/high CPU | watchdog/timeout and bounded source/runtime; terminate sandbox. |
| Event spam | event rate and payload limits; semantic declaration validation. |
| Student-private literals promoted to reusable artifact | promotion privacy scan + parameterization requirement. |
| Provider image URL persisted | existing owned-asset adoption; durable artifact references owned IDs only. |
| Manifest says one thing, UI emits another action | event must match manifest declaration and current semantic IDs. |
| Custom code bypasses Child Safety Policy | Canvas admission happens after policy; generated output still receives applicable output/runtime validation. |

Do not claim perfect isolation from static code scanning alone. The browser sandbox/CSP/bridge are the primary runtime security boundary; static checks are defense-in-depth.

---

# 34. TDD and Verification Policy

Use **lightweight behavior-first TDD** for important new boundaries.

No Superpowers framework or `superpowers:*` skills.

Use native Codex capabilities.

## 34.1 RED → GREEN where valuable

Before implementing a major behavior, write or identify the smallest test that proves the approved contract and confirm it fails for the intended reason.

High-value TDD boundaries include:

- reusable artifact cannot contain student-specific private context;
- custom runtime rejects non-allowlisted imports;
- sandbox bridge rejects undeclared semantic action;
- artifact instance binds only valid parameters;
- artifact version is immutable once validated/published;
- Tutor observation is generated from manifest/state without code leakage;
- generated custom visual cannot acquire application authority;
- exact mathematical data is required where the visual claims exact geometry.

Do not build exhaustive matrices for every library or every visual style.

## 34.2 Development verification economy

During implementation:

- run focused tests around the seam being changed;
- use the existing disposable PostgreSQL runner only where persistence/lifecycle behavior requires it;
- use browser harnesses only for affected runtime/visual behavior;
- do not rerun full regression after every step;
- do not regenerate large screenshot suites repeatedly;
- ordinary bugs are for Codex to diagnose and fix autonomously.

## 34.3 Final acceptance is the main gate

One integrated acceptance wave near closure is the principal release gate.

---

# 35. Final Acceptance Scenarios

Use real provider output and exact production rendering. Do not prove Full-Power behavior only with hand-authored final scenes.

A compact set of high-leverage scenarios should prove the following distinct capabilities.

## 35.1 REUSE

A new student request matches an existing validated artifact.

Prove:

- Agent finds/selects it;
- no custom code regeneration occurs;
- parameters bind correctly;
- browser renders it;
- Tutor understands it through manifest/state.

## 35.2 ADAPT

Use the same reusable artifact with materially different values/language/learner presentation.

Prove:

- same artifact version can serve both instances;
- only parameters/presentation change;
- academic truth remains the same;
- learner-specific values do not enter reusable definition.

## 35.3 CREATE — novel Math/Science visual

Use an unseen request not adequately served by current typed renderers.

Prove:

- Agent chooses CREATE for a defensible reason;
- generated custom visual uses approved capabilities;
- compile/sandbox succeeds;
- exact quantitative truth comes from approved data/tools;
- one screenshot review/refinement at most;
- final screenshot is visibly strong;
- resulting artifact is stored as build history and eligible for candidate promotion if reusable.

## 35.4 Generated illustration + semantic overlay

Use a Science request where organic illustration materially improves teaching.

Prove:

- generated image becomes project-owned;
- overlay/labels/interactions remain semantically mapped;
- Tutor can explain visible entities without seeing implementation code.

## 35.5 Language interaction

Use Arabic or English/language content requiring ordering, highlighting, matching, or direct manipulation.

Prove:

- custom/typed path is chosen on educational need;
- RTL/LTR works;
- meaningful interaction returns to Tutor.

## 35.6 Age/grade calibration

Run the same educational truth/request with meaningfully different approved age/grade contexts.

Do not prescribe the exact layout to the Agent.

Prove:

- presentation differs appropriately in density/labeling/interaction/illustration when useful;
- academic truth does not change;
- no diagnosis/learning-style inference appears.

## 35.7 Tutor round-trip

Student performs a meaningful Canvas action.

Prove:

```text
Canvas action
→ semantic bridge
→ Studio event/state
→ same Primary Tutor observation
→ Tutor explains/continues correctly
```

## 35.8 Security negative case

Generated code attempts a forbidden action such as arbitrary network access or undeclared event.

Prove runtime rejects/contains it and Tutor remains available.

---

# 36. Visual Acceptance Evidence

For CREATE and representative REUSE/ADAPT cases, save bounded evidence such as:

```text
output/playwright/full-power-canvas/
  reuse-*.png
  adapt-*.png
  create-*.png
  age-younger-*.png
  age-older-*.png
  results.json
```

`results.json` should contain only bounded technical/semantic proof:

- request scenario label;
- Tutor/CanvasBrief lineage IDs/digests;
- allowed VisualLearnerContext fields;
- Agent trace ID/model/usage;
- route decision: REUSE/ADAPT/CREATE;
- artifact/version ID if applicable;
- selected capabilities/tools;
- manifest digest/summary;
- browser status;
- screenshot filenames;
- latency/cost metadata if available;
- no raw private source/memory payload.

Screenshots are review evidence, not authoritative learner state.

---

# 37. Definition of Done

FULL-POWER-CANVAS-01 is complete only when all of the following are true:

- Canvas Agent can choose REUSE, ADAPT, or CREATE.
- Existing typed Agentic Canvas remains a functional fast path.
- A project-owned Reusable Visual Registry exists with immutable versions and bounded search.
- At least one reusable artifact can be instantiated with new parameters without regeneration.
- At least one structural adaptation/version/fork path is proven.
- At least one novel custom visual is generated and executed in the approved sandbox.
- Generated code cannot access Lina application authority, arbitrary network, cookies, or secrets.
- Custom visual dependencies are allowlisted and versioned.
- Browser preview is part of custom CREATE.
- Custom CREATE receives at most the approved bounded visual review/refinement loop.
- Semantic Manifest is produced and validated.
- Stable semantic IDs connect visible elements/interactions to Tutor understanding.
- Meaningful custom visual action round-trips through Studio to the same Primary Tutor.
- Exact mathematical/scientific data is not invented by the renderer.
- Generated images remain project-owned.
- Student-specific private context cannot be promoted into reusable artifacts.
- Age/grade presentation calibration works without changing academic truth.
- Real-provider output, not only fixtures, reaches the exact production renderer/browser proof.
- Visual output is structurally at least at the prior accepted quality floor for comparable problems.
- Latency/token/cost evidence is observable.
- Existing safety, Studio persistence, stale fencing, ownership, replay, and Tutor continuity are not regressed.
- Governing project documents are reconciled with the new architecture.

---

# 38. Key Risks and Recommendations

## R1 — Generated code becomes unsafe application code

- **Recommendation:** sandboxed opaque-origin runtime + strict CSP + allowlisted imports + semantic bridge.
- **Reason:** static model instructions are not security boundaries.
- **Expected impact:** high visual freedom without application authority.
- **Mandatory:** Yes.
- **Priority:** P0.
- **Risk if ignored:** credential/state exposure or arbitrary app behavior.

## R2 — Reuse-first becomes quality-first's enemy

- **Recommendation:** reuse only when educational fit is genuinely strong; allow CREATE without stigma.
- **Reason:** forcing a weak artifact recreates today's visual ceiling.
- **Expected impact:** better learning visuals while still gaining cost benefits from reuse.
- **Mandatory:** Yes.
- **Priority:** P0.

## R3 — Registry becomes a junk drawer

- **Recommendation:** separate build history from reusable registry and use CANDIDATE/VALIDATED/TRUSTED lifecycle.
- **Reason:** storing every one-off output as a first-class reusable artifact destroys search quality.
- **Expected impact:** smaller, higher-quality reuse set.
- **Mandatory:** Yes.
- **Priority:** P1.

## R4 — Tutor cannot explain custom visuals

- **Recommendation:** Semantic Manifest is required for every final Canvas runtime kind.
- **Reason:** implementation code is not a teaching contract.
- **Expected impact:** same-Tutor continuity survives arbitrary visual composition.
- **Mandatory:** Yes.
- **Priority:** P0.

## R5 — Visual feedback loop burns cost/latency

- **Recommendation:** no AI visual review for trusted routine reuse; one review/refinement maximum for custom CREATE by default.
- **Reason:** quality needs feedback, but open-ended self-critique loops are expensive and slow.
- **Expected impact:** quality improvement with bounded cost.
- **Mandatory:** Yes.
- **Priority:** P1.

## R6 — Custom visual code invents math/science truth

- **Recommendation:** exact values/geometry/data must come from typed inputs or approved deterministic tools.
- **Reason:** prettier output is unacceptable if mathematically false.
- **Expected impact:** creative presentation with reliable academic truth.
- **Mandatory:** Yes.
- **Priority:** P0.

## R7 — Architecture becomes too large

- **Recommendation:** preserve current Studio/Tutor/Agent foundations; add only registry, custom build/sandbox, manifest bridge, and bounded routing needed for the approved behavior.
- **Reason:** FULL-POWER describes capability, not permission to rebuild Lina.
- **Expected impact:** faster implementation and lower maintenance risk.
- **Mandatory:** Yes.
- **Priority:** P0.

---

# 39. Execution Principles for Codex

When implementation begins:

1. **Use native Codex only. No Superpowers or `superpowers:*` workflows.**
2. Read repository truth and the governing documents before editing.
3. Treat this spec as outcome/boundary authority, not a mechanical micro-plan.
4. Reuse current Agentic Canvas, Studio, filtering, generated-assets, browser harness, and visual-toolbelt wherever they remain correct.
5. Prefer the smallest robust architecture that delivers the approved capability.
6. Use lightweight RED→GREEN TDD on major new boundaries.
7. Do not create large exhaustive test suites before implementation.
8. Do not repeatedly run full regression during development.
9. Solve ordinary engineering problems autonomously.
10. Stop for Product Owner only on genuine protected-area decisions or irreversible/destructive actions.
11. Do not merge to main or push remote changes without the approval rules active for the execution task.
12. Do not declare visual completion from unit tests alone; final real-Agent browser evidence is required.

---

# 40. Recommended Execution Workstreams

These are workstreams, not mandatory checkpoints.

## A. Governance + contracts

Reconcile project artifact policy and introduce versioned contracts for:

- registry identity/version;
- custom visual package metadata;
- Semantic Manifest;
- semantic bridge events;
- runtime/capability identity.

Use TDD for protected boundaries.

## B. Registry and reuse/adapt path

Implement lightweight search/inspect/instantiate/version behavior using existing PostgreSQL/ObjectStorage infrastructure.

Prove exact reuse with new values before custom generation.

## C. Custom build + sandbox

Implement allowlisted compilation, owned bundle persistence, isolated renderer, CSP/watchdog, and semantic event bridge.

Do not execute generated code server-side merely to compile it.

## D. Full-Power Canvas Agent tools/skills

Give the existing Canvas Agent access to:

- registry search/inspect/instantiate;
- existing visual tools;
- custom visual creation;
- owned image generation;
- deterministic truth tools;
- bounded preview/review path.

Do not create subject-specific standing agents.

## E. Tutor manifest/state continuity

Produce compact Canvas observation from manifest + Studio state and prove same-Tutor round trip.

## F. Final integrated acceptance

Run the compact real-provider scenarios, real production renderer/browser proof, security negative case, focused PostgreSQL lifecycle proof where affected, typecheck/build status, and one broad regression near closure.

---

# 41. Final Approved Direction Summary

If this specification is approved, the following becomes the project reference direction:

```text
Lina Canvas is not a fixed diagram renderer catalogue.

The Primary Tutor decides what must be taught.
The Full-Power Canvas Agent decides how best to represent it visually.

The Agent first looks for a strong reusable artifact.
It reuses or adapts when that preserves learning quality.
It creates a new visual when necessary.

Custom creation may use approved React/SVG/Motion/JSXGraph/Konva/MathLive/
chart/simulation/image capabilities, but generated code executes only inside
an isolated visual sandbox with no application authority.

Every final Canvas exposes a Semantic Manifest and stable semantic IDs so the
same Primary Tutor always understands what the student sees and does.

Successful generalized visuals can be stored, versioned, searched, reused,
and improved later, reducing future cost and latency without turning Lina's
personal data into templates.

The measure of success is student understanding and visual quality, not the
number of renderers, tools, tests, or abstractions.
```

---

# 42. Approval Effect

Approval of this document authorizes **execution planning/handoff**, not an immediate merge to main.

After approval:

1. reconcile the governing project starter-pack documents with this decision;
2. update project state/task queue;
3. prepare one compact Codex execution prompt using this spec as the attached authority;
4. start implementation from the approved current Canvas baseline in a separate worktree/branch;
5. require real-provider + real-browser final evidence before final acceptance.

