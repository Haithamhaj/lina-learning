# Canvas Specialist Execution Contract & First Production Slice

**Status:** ACCEPTED — direct Product Owner approval in chat on 2026-09-07  
**Scope:** Governing execution contract for bounded Canvas Specialist activation and the first natural Process production slice.  
**Execution priority:** **Quality → Speed → Cost.**  
**Repository baseline when accepted:** `codex/ctx-03` at `bc74667e3627529771b513cb834bdf2635264ee4`.

## 1. Authority and relationship to existing Studio documents

This contract operationalizes the accepted hybrid direction in `docs/DAILY_USE_RELEASE_DECISIONS.md` and the accepted visual foundation in `docs/STUDIO_VISUAL_EXPLANATION_SPEC.md`, `docs/LINA_EDUCATIONAL_VISUALS_GUIDE.md`, and `docs/reviews/STUDIO-VISUAL-PROCESS-01/VISUAL_CHECKPOINT_2.md`.

For this bounded execution track, this document is authoritative when an older Studio visual design proposal conflicts with the decisions below. It does **not** reopen accepted Studio State, Subject Registry, Protocol, Runtime-01/02/03, FE-02 Daily, accepted activities, ProcessView, Learning Intelligence, Personal Facts, or Safety contracts.

Implementation sequencing lives in `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md`. Verification and review gates live in `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`.

## 2. Protected invariants

1. **Primary Tutor is the sole Student-facing teacher.** It owns teaching objective, explanation, scaffolding, dialogue, and the educational decision that a visual would help.
2. **Canvas Specialist is a Visual Learning Composer, not a second Tutor.** It fulfills an admitted visual order; it does not choose a separate lesson, assessment, teaching strategy, or grading rule.
3. **Studio/Application owns execution authority.** Models do not own renderer/engine selection, layout coordinates, executable code, persistence, Safety, permissions, Evidence, Personal Facts, Learner Intelligence, or final Scene state.
4. **`workspace_intent-v1` keeps its accepted meaning.** It remains a bounded educational Workspace need. Do not smuggle scene bodies, implementation terms, renderer identity, or Specialist execution through `learning_goal`, `activity_hint`, or other v1 fields.
5. **New visual composition is additive.** Use a sibling versioned visual-order contract rather than rewriting existing WorkspaceIntent semantics.
6. **Known work remains cheaper than composition.** Chat, compatible reuse, and supported updates use zero Canvas Specialist calls.
7. **One admitted new composition uses at most one Specialist generation.** No automatic semantic repair model and no invisible inference retry.
8. **Browser state is not authority.** Accepted Studio Scene/Event/Snapshot state remains durable truth.
9. **Canvas actions do not directly create Learning Evidence, Personal Facts, or Learner Intelligence.** Existing learning-review authorities remain intact.
10. **Accepted ProcessView is protected.** First production composition reuses it; no visual redesign is implied.

## 3. Responsibility model

| Concern | Primary Tutor | Canvas Specialist | Application / Studio |
|---|---|---|---|
| Student teaching/dialogue | Owns | None | Delivers |
| Instructional objective | Owns | Must follow | Validates envelope |
| Whether a visual helps | Owns educational decision | None | Rechecks capability/admission |
| Chat-only outcome | May choose | No call | Preserves current state |
| Reuse current/known content | Expresses need | No call | Owns eligibility/execution |
| Simple supported update | Expresses semantic need | No call | Owns exact action/state mutation |
| New composition | Emits compact visual order | Composes semantic proposal | Admits and validates |
| Visual hierarchy/grouping | No full scene body | Owns semantic composition | Enforces registered capability |
| Renderer/engine | No | No | Owns |
| Layout/coordinates/code | No | No | Owns |
| Motion implementation | May state instructional need | May propose semantic motion intent | Owns engine/easing/duration |
| Safety/permissions/rights | Cannot bypass | No authority | Owns |
| Persistence/final Scene | No | No | Owns |
| Evidence/PF/LI | Existing Tutor/review rules | None | Existing authorities |

## 4. Runtime flow

```text
Student question
      ↓
Primary Tutor
      ↓
visual useful?
 ┌────┼───────────────────────────────┐
 │    │                               │
No   existing/reusable            new visual
 │    │                               │
Chat reuse/update                Visual Order
 │    │                               ↓
 │    └──────────────→ Application admission
 │                                    ↓
 │                              Canvas Specialist
 │                                    ↓
 │                              Semantic Proposal
 │                                    ↓
 │                         Application validation
 │                                    ↓
 └────────────────────────→ accepted + active Scene
                                      ↓
                               Student interaction
                                      ↓
                               existing Runtime-03
                                      ↓
                               same Primary Tutor
```

## 5. Visual Order and Semantic Alignment Envelope

The Primary Tutor result may add one required-nullable, versioned sibling visual-order field. Exact implementation name/version is decided in CS-03 without changing `workspace_intent-v1`.

A COMPOSE order contains only bounded educational meaning:

- one registered representation/pattern need;
- instructional objective;
- essential terminology/facts/values;
- essential relationships;
- optional semantic focus;
- locale/direction intent;
- authorized source references;
- bounded constraints.

It does **not** contain a full object graph, renderer identity, implementation technology, coordinates, SVG/HTML/JS/CSS, callbacks, formulas-as-code, or model-controlled database IDs.

### 5.1 Semantic Alignment Envelope

Essential meaning receives stable bounded support identities so the Specialist cannot drift silently.

Example:

```yaml
objective: Understand the butterfly life cycle.
required_semantics:
  F1: Egg hatches into larva.
  F2: Larva develops into pupa.
  F3: Adult emerges from pupa.
required_relations:
  R1: F1
  R2: F2
  R3: F3
must_not_imply:
  - The same adult butterfly turns back into an egg.
```

The Specialist proposal references the relevant support identities for instructional claims/relations. Application validation checks bounded support coverage and unauthorized additions; it does not pretend deterministic code can prove arbitrary natural-language entailment.

There is no V1 Tutor → Specialist → Critic model chain.

## 6. Visual Learner Context

Do not create a new learner authority. Build one **transient application-owned projection** from existing authorities.

### 6.1 Student Core Profile

Parent/System-authoritative fields may include only what is useful for presentation, such as:

- `display_name` when natural and necessary;
- `age_years`;
- `grade_level`.

Core Profile remains the authority for identity/age/Grade. Do not duplicate these into Personal Facts.

### 6.2 Relevant safe Personal Facts

Optional visual personalization may use a small current subset from safe Personal Fact categories, normally:

- `PREFERENCE`;
- `FAVORITE`;
- `ACTIVITY`;
- `PET`.

Examples: likes drawing, favorite color, likes horses, has a cat. Personalization is optional and must improve clarity or engagement; it must never be forced into every visual or change instructional truth.

Default Specialist context must not include Personal Fact observation history, support counts, full Personal Memory, full transcripts, psychological/personality inference, learning-style labels, or broad Learner Intelligence history.

A bounded selector should pass only a few current facts relevant to the visual objective. Exact selection mechanics are an application concern and must not add a normal-turn model call.

## 7. Frozen Composition Pack

Because Specialist execution is asynchronous, the admitted order is frozen before the Worker runs. The pack contains only what the run needs:

- instructional objective;
- Semantic Alignment Envelope;
- exact relevant source excerpts when available;
- source identity/version/provenance;
- locale/direction;
- bounded Visual Learner Context;
- relevant current Scene meaning when required;
- approved semantic/art handles;
- exact registered capability and limits;
- allowed interaction affordances;
- Safety/content constraints.

The Worker does not silently rerun Retrieval and substitute different grounding after the Tutor decision. No full memory/history dump is supplied by default.

Book/retrieval availability improves grounding but is not permission to teach or visualize. When no curriculum excerpt exists, accepted model-knowledge teaching may still be represented, but the Specialist may not invent instructional claims outside the admitted envelope.

## 8. Canvas Specialist Runtime Skill

CS-01 creates `runtime/canvas-specialist/SKILL.md`, separate from the existing development-only `skills/lina-educational-visuals/SKILL.md`.

The runtime Skill teaches the Specialist to:

1. understand the admitted learning objective before composing;
2. choose visual hierarchy, grouping, relation emphasis, progressive detail, and interaction semantics that clarify that objective;
3. preserve concise primary labels and longer focused detail;
4. use motion only for attention, relationship, sequence, transformation, or conserved equivalence;
5. respect Arabic/English/mixed direction, accessibility, keyboard/touch equivalence, narrow layouts, and reduced motion;
6. use personalization only when it naturally helps;
7. remain inside the exact Capability Pack;
8. self-review clutter, unsupported relations, missing required meaning, forced personalization, readability, and capability violations.

The Skill never grants persistence, renderer, Safety, Evidence, PF, LI, or Tutor authority.

## 9. Visual Toolbelt and engine authority

The approved installed/tested Toolbelt target is:

- React / DOM / SVG — baseline;
- Motion — semantic animation;
- React Konva / Konva — spatial manipulation;
- JSXGraph — mathematical visualization/construction;
- MathLive — editable mathematical input.

The Specialist does **not** select these technologies by name. It requests semantic capabilities such as directed-relation visualization, semantic motion, spatial manipulation, mathematical construction, or editable math input. Application-owned registered adapters map those needs to engines.

Presence in the Toolbelt does not make a capability production-enabled. The per-run Capability Pack controls what is available.

Konva, JSXGraph, and MathLive should be lazy/client-loaded behind their adapters so unused engines do not inflate every Student path.

## 10. Call policy and model route

Current model decision: **GPT-5.6 Luna** for Primary Tutor and Canvas Specialist through the existing provider-neutral Model Gateway architecture.

Add a dedicated Canvas Specialist task identity/route rather than calling the provider directly from Studio/Worker code.

```text
Chat only          → 0 Specialist calls
Compatible reuse   → 0
Supported update   → 0
New composition    → max 1
Automatic critic   → 0
Automatic repair   → 0
Automatic inference retry → 0
```

Specialist inference Job must explicitly use `max_attempts=1`. Provider/SDK behavior for the route must not silently perform a second generation/fallback. Ambiguous provider outcome is recorded as unknown/failure rather than invisibly resent.

## 11. Admission and asynchronous execution

No dispatch from partial streaming prose, provisional model output, or an invalid primary result.

```text
complete Tutor result
→ strict primary contract validation
→ applicable Safety/Parent Boundary handling
→ visual-order semantic/capability admission
→ persist Tutor message and lineage
→ freeze Composition Pack/order identity
→ atomically enqueue Job + pending CanvasSpecialistRun
→ COMMIT
→ Worker may claim
```

The primary Tutor response does not await Specialist completion. The Worker must not keep a database lock/transaction open across inference.

## 12. Specialist proposal contract

The Specialist returns typed semantic data only. A Process proposal may include:

- title/objective/subtitle;
- topology;
- 2–8 semantic stages;
- bounded candidate semantic IDs;
- concise labels and focused details;
- explicit relations and support IDs;
- approved art handles;
- text equivalent;
- allowed interaction affordances;
- optional semantic motion intent.

Forbidden: executable SVG/HTML/JavaScript/CSS, arbitrary paths, React/Konva/JSXGraph code, callbacks, remote scripts, unrestricted URLs, private storage paths, renderer IDs, and database mutation instructions.

## 13. Application validation and causal acceptance

Validation is layered:

### Structural
Schema, IDs, count/size bounds, exact topology, relation endpoints, duplicates, registered action/seed versions.

### Semantic support
Required semantic IDs are represented; declared relations reference admitted support; `must_not_imply` constraints are respected; no unauthorized instructional claim is accepted.

### Capability
All handles/actions/motion intents are allowed by the exact registered pack; model output cannot grant new capabilities.

### Safety / permissions / rights
Current Student scope, source/asset permissions, current Safety/Parent Boundary rules, provenance and serving rights remain application-owned.

### Causal / stale
Recheck source Tutor message/order identity, capability/content versions, deadline, target/current Scene state and relevant semantic read set. If compatibility with newer state cannot be proven, reject rather than overwrite/rebase.

## 14. Atomic Scene replacement

A valid Specialist proposal still does not become visible directly.

```text
validated proposal
→ short acceptance transaction
→ lock current Studio state
→ recheck causality/permissions/run state
→ supersede prior ACTIVE Scene when replacement is required
→ accept new Scene
→ activate new Scene
→ Event + Snapshot
→ complete accepted run link
→ commit
```

Failure of the replacement unit leaves the prior usable Scene intact. A cancelled, failed, expired, superseded, or stale run cannot resurrect a late Scene.

## 15. First production slice — Process

First naturally composed production pattern is Process only:

- `sequence`;
- `cycle`;
- 2–8 stages;
- approved application-owned art handles;
- focus;
- reveal;
- relation trace;
- object/relation explanation.

Reuse the accepted Checkpoint-2 ProcessView. Add only the strict production adapter/Host registration needed to map authoritative active Process Scene/state into that existing view.

The accepted older `process_sequence_workspace` filtration activity remains separate and must not be conflated with generic Process visual composition.

## 16. Student interaction and Tutor awareness

FOCUS/REVEAL/TRACE remain record-only semantic Studio actions. `REQUEST_EXPLANATION` may target an exact Process object or relation and uses the existing Runtime-03 continuation.

Specialist completion creates no automatic Tutor call, fake Student message, or observation-watermark advance. After accepted Scene state is actually available, the existing semantic Canvas-awareness path lets the **same Primary Tutor** understand objects/relations/state without Vision and explain the selected target.

## 17. Failure behavior

- Invalid Tutor visual order: no Specialist dispatch; valid Chat remains usable where the existing transaction boundary permits.
- Specialist provider/schema/support failure: fail/reject run; no partial Scene; prior Chat/Scene survives.
- Stale/late result: reject; never resurrect older objective/state.
- Asset denial/failure: permitted static/semantic/text fallback only.
- Unsupported capability: remain in Chat or existing accepted capability; no model improvisation around the Registry.
- No automatic third Tutor call, critic, semantic repair, or model retry.

## 18. Learning Intelligence / Personal Facts boundary

Specialist and Canvas interactions do not directly write Candidate Events, Learning Events, Evidence, Current State, Patterns, Learner Intelligence Cards, Personal Facts, or Personal Fact Observations. Personal Facts used for visual personalization are read-only advisory input. Existing Tutor/Segment/Session review authorities remain the only accepted learning-meaning path.

## 19. Explicit non-scope before the first real trial

- generic Artifact Engine or unrestricted visual DSL;
- generic multi-agent framework;
- reusable-content database;
- arbitrary generated executable code;
- unrestricted graph editor;
- generated images or 3D runtime;
- Voice/Vision changes;
- automatic post-render narration;
- direct Canvas-to-Evidence path;
- production promotion of Konva/JSXGraph/MathLive learning activities before their later controlled Lab/proof.

## 20. Governing optimization rule

The execution track optimizes in this order:

1. **Quality:** semantic fidelity, pedagogical usefulness, visual clarity, age/grade appropriateness, Arabic/English correctness, natural—not forced—personalization.
2. **Speed:** measure Tutor first text/terminal, queue, Specialist generation, validation/commit and first visible Canvas; optimize the measured bottleneck only after quality is acceptable.
3. **Cost:** measure Tutor/Specialist tokens and cost; reduce unnecessary calls/context/repeated composition and later compare cheaper configurations only without lowering accepted quality.

No arbitrary latency/cost target may override the quality gate before a real baseline exists.
