# Lina Personal Learning System — Project State

**Updated:** 2026-09-07  
**Execution branch:** `codex/ctx-03`  
**Documentation baseline before this sync:** `bc74667e3627529771b513cb834bdf2635264ee4`

## Current goal

Reach the first real natural Canvas-Specialist learning journey in `/student/daily` without reopening accepted Tutor/Studio/Process architecture.

Target milestone:

```text
Student question
→ Primary Tutor decides a new Process visual helps
→ one bounded GPT-5.6 Luna Canvas Specialist composition
→ validated accepted/active Process Scene
→ existing ProcessView renders
→ Student selects object/relation
→ same Primary Tutor explains through existing Runtime-03
```

The active bounded path is `CS-01 → CS-06`. `CS-07` is a controlled post-proof visual Toolbelt lab, not required before the first real Process trial.

## Current reality

### Accepted foundation

- `LINA-VISUAL-INTELLIGENCE-01` — DONE / ACCEPTED: canonical visual grammar, development-only visual Skill, Primary Tutor visual guidance, disabled future Specialist capability pack, semantic Tutor Canvas awareness and Process awareness proofs.
- `STUDIO-VISUAL-PROCESS-01` — DONE / ACCEPTED: Checkpoint-2 Process visual direction and reusable prepared-data ProcessView foundation; sequence/radial cycle, stable IDs, focus/de-emphasis, reveal, relation trace, keyboard/tap, narrow/Arabic and reduced-motion behavior.
- Studio State/Subject Registry/Protocol/Runtime-01/02/03 and `/student/daily` Studio integration are DONE / ACCEPTED.
- Existing deterministic activities and accepted Math renderers remain protected.
- Student Core Profile, Personal Facts, PF-03 Personal Memory Tutor context, Learning Intelligence, Retrieval and Child Safety authorities are accepted and remain separate.
- Worker, PostgreSQL Jobs, Model Gateway, AIExecution ledger and dormant `StudioCanvasSpecialistRun` persistence seam exist.

### Not yet implemented/proven

- no natural Canvas Specialist dispatch/execution;
- no runtime `runtime/canvas-specialist/SKILL.md`;
- no additive Tutor Visual Order / Semantic Alignment Envelope;
- no frozen Specialist Composition Pack / Visual Learner Context;
- no `ModelTask.CANVAS_SPECIALIST` live route;
- no full Specialist Run stale/cancel/settlement lifecycle;
- no production natural-composition Process profile/Host adapter;
- no real Luna Specialist quality proof;
- Motion/Konva/JSXGraph/MathLive are approved Toolbelt targets but are not yet installed/proven in the current web package;
- no real Lina Student history/use has been started by this work.

## Active decisions

1. **Primary Tutor remains the sole Student-facing teacher.**
2. **Canvas Specialist is a Visual Learning Composer only.** It composes semantic visual structure from an admitted Tutor order; it does not own teaching, grading, persistence, Safety, Evidence, Personal Facts, Learner Intelligence, renderer or engine selection.
3. **`workspace_intent-v1` meaning is protected.** New composition uses an additive versioned sibling visual-order contract.
4. **Chat / compatible reuse / supported update = 0 Specialist calls. New admitted composition = max 1 Specialist generation.** No automatic critic, repair or hidden inference retry.
5. **Semantic Alignment Envelope is mandatory** to bind Specialist output to Tutor objective/facts/relations and must-not-imply constraints.
6. Application performs bounded semantic-support validation; do not claim deterministic general natural-language factual entailment.
7. **Visual Learner Context is a transient projection, not a new profile authority:** Core Profile supplies authoritative identity/age/Grade when useful; a small relevant current subset of safe Personal Facts may optionally personalize visuals.
8. Current Specialist/Tutor model decision is **GPT-5.6 Luna** through the existing Model Gateway architecture.
9. Approved Toolbelt to install/prove in CS-02: React/SVG baseline + Motion + `react-konva@18`/Konva + JSXGraph + MathLive. Specialist never selects these technologies by name; application Registry/adapters own engine selection.
10. First production natural-composition capability is **Process sequence/cycle, 2–8 stages**, reusing the accepted ProcessView. Konva/JSXGraph/MathLive production learning activities remain later than the first Process proof.
11. Optimization order is **Quality → Speed → Cost**. Quality is the blocking acceptance gate; latency/token/cost are measured from the start and optimized only after a real baseline.
12. `STUDIO-ACCEPT-01`, deployment, Voice/Vision, generated images/3D, generic Artifact Engine, generic multi-agent platform and reusable-content DB remain outside this bounded track unless separately promoted.

## Protected areas

Do not break or silently reinterpret:

- Primary Tutor one-call teaching authority and current Safety/Parent Boundary behavior;
- `workspace_intent-v1` and deterministic Workspace Router semantics;
- Studio Runtime/Scene/Event/Snapshot/Protocol/feed authority;
- Runtime-03 exact Canvas interaction provenance and same-Tutor continuation;
- accepted ProcessView visual language;
- older deterministic `process_sequence_workspace` filtration activity;
- Student Core Profile vs Personal Facts vs Learning Intelligence authority separation;
- no direct Canvas/Specialist → Candidate/Evidence/PF/LI writes;
- browser state is never durable truth;
- provider calls go through Model Gateway; no secret/provider logic in routes/components.

## Active risks

| Risk | Current control |
|---|---|
| Tutor/Specialist semantic drift | Semantic Alignment Envelope + support IDs + no third critic |
| Async Specialist uses changed grounding | Frozen Composition Pack; no silent post-turn Retrieval replacement |
| Late result overwrites newer learning state | causal/stale recheck before atomic Scene acceptance |
| Visual personalization becomes stereotyping/noise | bounded relevant current safe Personal Facts; optional use only |
| Deterministic validation overclaims factual intelligence | semantic-support validation wording and bounded contract |
| Extra AI calls hurt latency/cost | zero-call Chat/reuse/update; max-one new compose; Luna; no repair/retry |
| Toolbelt dependencies destabilize web build | isolated adapters, lazy/client loading, CS-02 build/browser proof |
| Process work accidentally redesigns accepted visuals | existing ProcessView is protected and reused |

## Next action

**CS-01 — Contract + Runtime Specialist Skill: READY.**

Implement only CS-01 from `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md` and verify it against `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md`. CS-01 must not enable a Specialist model call, install Toolbelt dependencies, modify WorkspaceIntent semantics, change database/schema, or alter Student production behavior.

Stop after CS-01 verification and review. Do not promote or execute CS-02 in the same run without explicit Product Owner authorization.

## Critical references

Read in this order for the active track:

1. `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md` — accepted authority/behavior contract.
2. `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md` — CS-01→CS-07 sequencing and task boundaries.
3. `docs/CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md` — evidence, quality/speed/cost and documentation gates.
4. `docs/DAILY_USE_RELEASE_DECISIONS.md` — accepted Product Owner decisions.
5. `docs/STUDIO_VISUAL_EXPLANATION_SPEC.md` — broader accepted hybrid Studio visual design source.
6. `docs/LINA_EDUCATIONAL_VISUALS_GUIDE.md` — canonical visual grammar.
7. `docs/reviews/STUDIO-VISUAL-PROCESS-01/VISUAL_CHECKPOINT_2.md` — accepted Process visual closure.
8. `runtime/tutor/visual-guidance-v1.md` and `runtime/canvas-specialist/visual-capability-pack-v1.md` — current runtime boundaries.
9. `docs/PERSONAL_FACTS_SPEC.md` and Student Core Profile implementation — personalization authority boundaries.
10. `docs/CHILD_SAFETY_POLICY.md`, `docs/LEARNING_INTELLIGENCE_SPEC.md`, `docs/STUDIO_IMPLEMENTATION_PLAN.md` — protected system authorities.

Historical execution details remain in `TASKS.md`, accepted closure documents and `docs/reviews/`; `PROJECT_STATE.md` is intentionally only the current operational snapshot.
