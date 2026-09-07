# Canvas Specialist Acceptance & Verification Specification

**Status:** GOVERNING VERIFICATION SPEC — prepared from the Product Owner-accepted Canvas Specialist contract on 2026-09-07.  
**Contract:** `docs/CANVAS_SPECIALIST_EXECUTION_CONTRACT.md`  
**Plan:** `docs/CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md`

## 1. Purpose

Define what evidence is required before any Canvas Specialist task may be called complete or promoted. Passing tests is necessary but not sufficient. The priority order is:

> **1. Quality → 2. Speed → 3. Cost**

Quality failures block acceptance. Speed and cost are measured from the first real execution, but no arbitrary target may cause an accepted-quality regression before a baseline exists.

## 2. Evidence categories

Keep these categories distinct in every implementation record:

1. **Static/code review** — contracts, scope, dependency and authority review.
2. **Unit/contract tests** — pure schema/parser/reducer/adapter behavior.
3. **PostgreSQL integration** — durable Job/Run/Scene/Event/Snapshot/lineage/replay/locking/idempotency behavior.
4. **Mock-model verification** — deterministic provider call counts and model-boundary payloads.
5. **Live Luna verification** — actual configured GPT-5.6 Luna provider route/structured output; never substitute mock success.
6. **Production build/typecheck** — Next.js/server build and static compatibility.
7. **Real browser verification** — Chromium/browser behavior, keyboard/touch/reduced-motion/responsive/engine lifecycle.
8. **Controlled Student journey** — natural `/student/daily` end-to-end flow with isolated Student unless real Lina use is separately authorized.
9. **Real Lina use** — only when explicitly authorized; distinct from isolated acceptance.
10. **Longitudinal learning benefit** — not part of CS-01→CS-07 acceptance unless separately promoted.

A task report must say exactly which evidence categories were and were not executed.

## 3. Global blocking invariants

These must remain true across CS-01→CS-07.

| Invariant | Required proof |
|---|---|
| Primary Tutor remains sole Student-facing teacher | contract tests + payload/instruction inspection + journey review |
| `workspace_intent-v1` meaning unchanged | compatibility tests; no implementation terms/scene body admitted |
| Chat-only uses 0 Specialist calls | mock call-count + end-to-end proof |
| Compatible reuse uses 0 Specialist calls | routing/admission + call-count proof |
| Supported update uses 0 Specialist calls | operation/call-count proof |
| New composition uses max 1 Specialist generation | Job/Gateway provider-attempt assertion |
| No automatic critic/repair/hidden retry | route/provider config + failure tests |
| Specialist does not select renderer/engine | proposal schema + Registry/admission tests |
| No DB lock/transaction spans inference | concurrency/paused-provider test or equivalent transaction proof |
| Browser state is not durable authority | reload/replay/Snapshot proof |
| Late/stale/superseded run cannot resurrect Scene | Postgres concurrency/stale tests |
| Failed replacement preserves prior usable Scene | atomic replacement integration test |
| Same Primary Tutor explains object/relation | Runtime-03 provenance + one Tutor call proof |
| Canvas/Specialist creates no direct Evidence/PF/LI | protected-table counts and source inspection |
| Personal Facts used for visuals are read-only, bounded and optional | projection tests + no-write counts |
| Core Profile remains age/Grade authority | projection/authority tests |

Any failed invariant blocks acceptance regardless of visual quality.

## 4. Semantic Alignment acceptance

### Required checks

- Tutor Visual Order contains bounded objective and stable semantic support identities.
- Every required semantic relation/object needed for the visual is either represented or the proposal is rejected.
- Specialist claims reference permitted support identities.
- `must_not_imply` constraints are testable in the bounded proposal contract and violated proposals are rejected.
- A source reference alone is never treated as proof of entailment or rights.
- Application validation is named **semantic-support validation**, not generic deterministic factual understanding.
- No third runtime critic model is required for V1 acceptance.

### Quality review

For live/controlled Process scenes, reviewer checks:

- Does the visual preserve the Tutor's intended instructional meaning?
- Are relations scientifically/mathematically truthful for the admitted facts?
- Is any attractive but unsupported content introduced?
- Does the visual make the central relationship easier to understand than a text dump?

A visually attractive but semantically wrong scene fails.

## 5. Visual Learner Context acceptance

The transient projection may include authoritative Core Profile fields and a small relevant current Personal Fact subset.

Blocking checks:

- age/Grade are sourced from Student Core Profile, never copied from competing Personal Fact fields;
- Personal Fact selection is Student-scoped and current-value aware;
- no observation history/support counts/full memory/transcript are passed by default;
- no extra normal-turn model call is introduced to select visual facts;
- sensitive/private excluded categories remain excluded;
- personalization cannot modify required instructional semantics;
- absence of Personal Facts does not block composition;
- irrelevant facts do not need to be forced into the visual.

For CS-06 quality review, at least one scenario should show useful optional personalization and one should deliberately use none because it would be distracting.

## 6. CS-01 acceptance — Runtime Specialist Skill

### Required evidence

- runtime `SKILL.md` exists and matches the accepted authority split;
- development Skill remains development-only;
- Specialist Skill/capability pack is not loaded into Primary Tutor instructions;
- Skill covers objective-first composition, hierarchy/grouping/relations, meaningful motion, Arabic/mixed direction, accessibility, responsive/narrow behavior, optional personalization and self-review;
- Skill explicitly forbids competing teaching dialogue, renderer choice, raw executable content, persistence/Safety/Evidence/PF/LI authority;
- focused tests pass;
- no model route, dependency, database or Student behavior changed.

### Documentation gate

`docs/reviews/CS-01/IMPLEMENTATION_RECORD.md` complete and independently reviewable.

## 7. CS-02 acceptance — Visual Toolbelt

### Required dependency decisions

Record installed versions and fit result for:

- Motion;
- `react-konva@18` + Konva;
- JSXGraph;
- MathLive.

### Required evidence

- install/lockfile deterministic;
- TypeScript passes;
- production build passes;
- no SSR/window/document import failure;
- adapters own lifecycle cleanup;
- unused heavy engines can remain lazy/client-loaded;
- Motion demonstrates meaningful SVG/DOM motion without rewriting accepted ProcessView;
- Konva demonstrates bounded pointer interaction and mount/unmount in a real browser;
- JSXGraph demonstrates bounded math construction and cleanup in a real browser;
- MathLive demonstrates controlled editable math value/event flow and asset/font/sound handling;
- no production routing/Studio authority change;
- existing Studio/Process regressions remain green.

A library may not be called integrated merely because npm installation succeeded.

## 8. CS-03 acceptance — Tutor ↔ Specialist alignment

### Positive cases

- Chat result with null visual order persists normally.
- New Process need produces one valid bounded visual order after complete Tutor parse.
- Frozen Pack contains exact admitted objective/support/source/capability/locale and bounded Visual Learner Context.
- order digest/idempotency identity is application-derived.

### Negative cases

- missing required new-schema field is not silently converted to null;
- invalid visual order cannot mutate Scene or enqueue work;
- Tutor cannot name React/SVG/Konva/JSXGraph/renderer IDs in educational fields;
- unauthorized source references rejected;
- Personal Facts cannot supply/override authoritative age/Grade;
- no Specialist/Gateway/Job generation occurs yet.

### Compatibility

Historical accepted Tutor/WorkspaceIntent behavior must pass unchanged or through explicit version-compatible readers.

## 9. CS-04 acceptance — Specialist execution runtime

### Call-count proof

Normal admitted composition must produce:

```text
1 accepted Primary Tutor call
1 logical Specialist Job
1 CanvasSpecialistRun
max 1 provider generation attempt
0 critic calls
0 repair calls
0 automatic third Tutor calls
```

### Persistence/causality proof

- duplicate admission resolves idempotently;
- wrong Student/session/source lineage rejected before provider execution;
- job uses `max_attempts=1`;
- Worker provider call occurs outside DB lock/transaction;
- provider success/failure recorded in AIExecution lineage;
- timeout/cancel/supersede terminal state cannot accept late result;
- crash-window reconciliation never regenerates after accepted effect;
- ambiguous provider outcome is disclosed, not reported as zero cost/call.

### Live model proof

When configured, execute at least one live GPT-5.6 Luna strict structured-output Specialist request and record model/provider, safe bounded input shape, success/failure, tokens, latency and cost. Do not publish secrets or private payloads.

## 10. CS-05 acceptance — Process production integration

### Structural coverage

Verify sequence and cycle within the accepted 2–8 stage boundary, including minimum and maximum safe shapes.

Reject:

- duplicate/invalid semantic IDs;
- invalid endpoints/topology;
- unsupported art handles;
- missing required support identity;
- unsupported cycle return;
- oversized/unknown fields;
- stale/cancelled/superseded result.

### Atomic Scene proof

- valid proposal creates accepted then active Scene through existing Studio lifecycle;
- old active Scene is superseded only inside successful replacement unit;
- acceptance failure leaves old Scene usable;
- Event/Snapshot/replay/reload reconstruct exact authoritative state;
- the persisted ADMITTED visual order and Frozen Composition Pack are the authorization snapshot: Safety, Parent Boundary, and source rights were resolved by the Primary Tutor/admission path and are not re-evaluated at Scene acceptance;
- acceptance rechecks only run eligibility, exact source/order identity, supersession, capability/profile identity, proposal structure and semantic support, allowed art handles, and the causal Scene read set; later policy-setting changes affect future visual orders only;
- feed refreshes committed state without new transport.

### Renderer proof

- existing accepted ProcessView is the rendered view;
- production adapter parses exact server Scene/state;
- no second visual implementation of Process is introduced;
- wide/narrow, Arabic/English/mixed direction, keyboard/touch, focus/reveal/trace and reduced motion verified in browser.

### Interaction proof

- focus/reveal/trace = 0 Specialist calls;
- object `REQUEST_EXPLANATION` = one same-Primary-Tutor Runtime-03 continuation;
- relation `REQUEST_EXPLANATION` = one same-Primary-Tutor Runtime-03 continuation;
- no fake Student message and no direct learning-intelligence/PF writes.

## 11. CS-06 acceptance — Real Daily trial

CS-06 cannot close on mocks alone.

### Minimum scenario matrix

1. source-grounded Process cycle;
2. non-cycle Process sequence;
3. Arabic or mixed-direction Process;
4. Chat-only case with zero Specialist call;
5. reuse/update case with zero composition call;
6. controlled invalid/provider-failure/stale case with safe preservation;
7. optional personalization case where a relevant safe Personal Fact genuinely improves the visual;
8. non-personalized case where available personal facts are deliberately ignored because they add no learning value.

### Quality — blocking review

For each applicable visual, reviewer records:

- semantic fidelity to admitted objective/facts/relations;
- no unsupported teaching claim;
- pedagogical usefulness versus plain text;
- immediate visual comprehensibility;
- relation direction/readability;
- appropriate information density for age/Grade;
- concise labels and focused details;
- Arabic/English/mixed-direction correctness;
- narrow/mobile usefulness;
- keyboard/touch/reduced-motion equivalence;
- personalization naturalness/non-forcing;
- same Tutor/Canvas semantic alignment.

A structural pass with poor or misleading visual communication is **not accepted**.

### Speed — measured second

Capture timestamps/latencies for:

- Student submit/admission;
- first useful Tutor text;
- terminal Tutor result;
- Job availability/queue delay;
- Specialist provider generation;
- validation/Scene transaction;
- first committed Snapshot with new Scene;
- first useful Canvas render.

Report per scenario and summarize when enough runs exist. No pass/fail threshold is invented before baseline.

### Cost — measured third

Record Tutor and Specialist separately:

- input tokens;
- cached input tokens when available;
- output tokens;
- estimated/actual cost when available;
- provider attempts;
- composition calls avoided by Chat/reuse/update.

Cost optimization may be proposed only after quality acceptance. A cheaper/faster configuration is accepted only if it preserves the accepted quality bar.

## 12. CS-07 acceptance — Visual Specialist Lab

Each engine lab is evaluated independently as **KILL / MODIFY / KEEP** before any production promotion.

Each lab must record independent findings for **Technical Capability** and
**Visual Quality / Lina Visual Language**. Technical Capability covers
correctness, interaction capability, semantic state handoff, lifecycle,
accessibility, browser/mobile behavior, performance, bundle/loading
implications, reliability and appropriate engine fit. Visual Quality covers
attractiveness, hierarchy, clarity, Grade-appropriate information density,
typography, spacing, shape/control language, focus/de-emphasis, motion
character, Arabic/English/mixed-direction appearance, consistency with Lina's
visual system, application-owned wrapper/design-token integration, and whether
the result is clearer than a simpler React/SVG alternative when relevant.

A technically capable engine does not qualify for production promotion merely
because it works. It must also be capable of producing a visually coherent,
child-appropriate Lina experience through application-owned styling/wrappers.
Native/default library styling need not itself look like Lina; engines such as
JSXGraph, Konva and MathLive may remain internal beneath the application-owned
wrapper. Every KILL / MODIFY / KEEP justification must include separate
Technical and Visual findings.

### Motion Lab

Check whether motion clarifies relationship/transformation rather than decoration, handles interruption/reduced motion, and does not introduce unnecessary complexity.

### Konva Lab

Check spatial drag/place/group interaction, pointer/touch/keyboard strategy, authoritative semantic submission and mobile/browser performance.

### JSXGraph Lab

Check mathematical correctness, coordinate/number-line direction, exact state handoff, Arabic surrounding prose and engine lifecycle.

### MathLive Lab

Check editable fractions/expressions, age-appropriate keyboard/input, controlled semantic value handoff, directionality and asset loading.

CS-07 does not automatically production-enable any engine-backed learning activity.

## 13. Documentation protocol for every task

Before implementation create:

`docs/reviews/<TASK-ID>/IMPLEMENTATION_RECORD.md`

Required sections:

1. Status and baseline SHA.
2. Purpose and explicit non-scope.
3. Governing references.
4. Protected invariants.
5. Planned/actual changed paths.
6. Implementation decisions and why.
7. Verification commands/results by evidence category.
8. Model-call counts and AIExecution evidence when applicable.
9. Browser/screenshots when applicable.
10. Quality findings when applicable.
11. Latency/token/cost measurements when applicable.
12. Known unverified evidence / blockers.
13. Independent review findings.
14. Scope review and protected-area confirmation.
15. Product Owner disposition.

### Review index

Add one row to `docs/reviews/README.md` when a CS task is submitted for review. Keep DRAFT / AWAITING REVIEW / DONE / ACCEPTED distinct.

### State transition

After Product Owner acceptance:

- mark task DONE / ACCEPTED in `project-state/DAILY_USE_RELEASE_TASKS.md`;
- update `project-state/PROJECT_STATE.md` current reality/next action;
- update decision register only when a new product/architecture decision was actually made;
- promote the next CS task only with explicit Product Owner authorization;
- do not rewrite `TASKS.md` merely to duplicate the current overlay.

## 14. Final acceptance philosophy

The system is not accepted because it generated a Canvas. It is accepted when the Canvas is **correct, useful, understandable, aligned with the same Tutor, operationally safe and reproducible**. Only after that do we optimize latency; only after latency is understood do we optimize cost.
