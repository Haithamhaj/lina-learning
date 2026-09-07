# LINA-VISUAL-INTELLIGENCE-01 — Implementation record

Status: DONE / ACCEPTED — direct Product Owner approval in chat on 2026-09-07.
Baseline: `da63850ef951a38f7e4ebe19bfa47692b2d9d13d`, `codex/ctx-03`.

## Implementation map recorded before code

- A: `docs/LINA_EDUCATIONAL_VISUALS_GUIDE.md` is canonical composition guidance.
- B: `skills/lina-educational-visuals/SKILL.md` is a compact development-only derivative.
- C/D: `runtime/tutor/visual-guidance-v1.md` and `runtime/canvas-specialist/visual-capability-pack-v1.md`; no existing file-based prompt convention supersedes these paths. Only C is loaded into the existing shared Tutor instructions; D stays disabled.
- E: extend `services/studio/tutor_context.py` selection/serialization, using locked Student-owned Scene/Snapshot and existing observation lifecycle. Add one exact `process_visual_context` Activity/profile contract in the existing Subject Registry, explicitly AWARENESS_ONLY and absent from current-profile routing. Reuse the accepted Process semantic shape; application reducers own focus/reveal/trace and REQUEST_EXPLANATION validation. No new table, latest-profile promotion, renderer-host claim or automatic activation.
- Existing `services/tutor/capacity.py` serialized-request character accounting removes optional whole visual units before protected immediate input can fail. Local visual cap derives from the existing 4,000-character question convention; full request remains governed by configured capacity. Runtime-03 retains its 32 KiB source bound and gains the same final request measurement for this visual contract.
- F: isolated disposable PostgreSQL acceptance/replay, normal TutorRuntime and existing Runtime-03 continuation with a capturing mock Gateway provider; source interaction remains immutable after a later record-only focus. Actual accepted ProcessView consumes the same prepared seed in a deterministic render proof. No Vision, natural composition, provider call or application-account mutation.
- Reuse decision: retain accepted React/SVG/DOM and native motion. Extend existing typed Registry/Studio/Tutor boundaries; no new visual engine, OpenMAIC DSL, retrieval system or dependency is needed.
- Verification: TDD for new contracts/projection, existing Runtime-01/03 and Tutor capacity regressions, guarded disposable DB suite; final independent diff review. Protected legacy UI and accepted Process frontend remain unchanged.

## Verified A–F outputs

| Output | Resolved path |
|---|---|
| A — canonical grammar | [LINA_EDUCATIONAL_VISUALS_GUIDE.md](../../LINA_EDUCATIONAL_VISUALS_GUIDE.md) |
| B — development-only skill | [SKILL.md](../../../skills/lina-educational-visuals/SKILL.md) |
| C — loaded shared Tutor subset | [visual-guidance-v1.md](../../../runtime/tutor/visual-guidance-v1.md) |
| D — disabled specialist subset | [visual-capability-pack-v1.md](../../../runtime/canvas-specialist/visual-capability-pack-v1.md) |
| E — existing Studio/Tutor awareness | `services/studio/subjects/process_visual.py`, `services/studio/tutor_context.py`, `services/studio/interactions.py`, `services/tutor/capacity.py` |
| F — actual accepted-state proofs | `tests/test_process_visual_awareness_postgres.py`, `tests/test_process_visual_awareness.py`, `tests/process_visual_render_proof.cjs` |

## Contract and ownership

Exact SCIENCE profile `process-visual-awareness-profile-v1` registers Activity
`process_visual_context` / `process-visual-context-v1`, seed `process-visual-seed-v1`,
Renderer `process-visual-awareness` / `process-visual-awareness-v1`, event
`process-visual-event-v1` and target payload `process-visual-action-v1`.
Renderer status is **AWARENESS_ONLY**, absent from current-profile routing and
explicitly rejected by renderer-need matching. No production Host adapter,
automatic activation or natural composition is claimed.

The server contract follows the reviewed 2–8-stage Process shape, exact topology,
unique IDs, bounded plain labels/details and approved artwork handles. Provenance
fields are mandatory in this narrower server seed. Structural validation is not
scientific truth; only the reviewed source-supported butterfly content is used.
FOCUS_OBJECT, REVEAL_OBJECT_DETAIL and TRACE_RELATION are RECORD_ONLY.
REQUEST_EXPLANATION alone triggers the existing Runtime-03 continuation with an
exact declared object/relation target; no grading or fake Student prose.

Existing Studio acceptance, Event/Snapshot, reducer/replay, permission and version
boundaries remain authoritative. Locked selection checks Student/session/runtime,
exact profile/activity/renderer/schema, current Scene version/status and equality
between Scene seed and Snapshot seed. Absent, malformed, inactive, unsupported or
mismatched-version Process context is omitted. Browser state never becomes truth.

The additive `snapshot.visual_scene` in existing `studio-tutor-context-v1` contains
versioned `process-visual-context-v1` semantics. Opaque Scene/version/sequence remain
in the existing outer envelope. Raw seed, SVG, artwork handles, source URLs/private
paths, CSS, coordinates and timing are excluded. Unseen Process Events retain safe
action targets and their selected range, without duplicating seeds. Runtime-03
source target is resolved from immutable replay; current Workspace is separate,
even for cross-activity pending explanations.

## Serialized example and capacity

Butterfly projection: **1,055 serialized characters**. Example normal Tutor request:
**27,823 characters**, under the existing default configured **64,000-character**
request limit. Local visual cap: **4,000 serialized characters**, using the existing
question-character convention. Runtime-03 retains its 32 KiB source-context limit.
These measurements are JSON characters, not provider tokens or latency.

```json
{
  "schema_version": "process-visual-context-v1",
  "pattern": "process_cycle",
  "objective": "Four life stages. The return begins a new generation, not the same butterfly becoming an egg.",
  "objects": [
    {
      "id": "egg",
      "label": "Egg",
      "detail": "A female lays eggs on a suitable plant."
    },
    {
      "id": "larva",
      "label": "Caterpillar",
      "detail": "The larva hatches, feeds and grows."
    },
    {
      "id": "pupa",
      "label": "Chrysalis",
      "detail": "The butterfly develops inside the pupa."
    },
    {
      "id": "adult",
      "label": "Adult butterfly",
      "detail": "The adult emerges. After mating, a female can lay eggs."
    }
  ],
  "relations": [
    {
      "id": "egg-to-larva",
      "from": "egg",
      "to": "larva",
      "meaning": "Hatches into"
    },
    {
      "id": "larva-to-pupa",
      "from": "larva",
      "to": "pupa",
      "meaning": "Develops into"
    },
    {
      "id": "pupa-to-adult",
      "from": "pupa",
      "to": "adult",
      "meaning": "Adult emerges"
    },
    {
      "id": "adult-to-egg",
      "from": "adult",
      "to": "egg",
      "meaning": "Female lays eggs · new generation"
    }
  ],
  "state": {
    "selected_stage_id": "pupa",
    "focused_stage_id": "pupa",
    "active_explanation_stage_id": "pupa",
    "revealed_stage_ids": [
      "pupa"
    ],
    "highlighted_relation_ids": [
      "pupa-to-adult"
    ]
  }
}
```

Capacity removes whole optional nonfocused details, unrelated relations/unneeded
objects and wider objective before remaining relations/details and final omission.
Focus/selection/active detail outrank wider context. Labels/relations remain whole,
with valid endpoints. Existing optional Tutor layers retain their reduction order;
visual units reduce before protected current question/immediate exchange can fail.
Protected input is never dropped. Runtime-03 retains the immutable target/meaning
while reducing separate current visual context. Cross-activity current Process
context is sanitized and capacity-checked independently of the source activity.

## Proof paths

**Normal Chat:** real StudioStateService accepts/activates butterfly data and pupa
focus. Normal TutorRuntime receives “Why does the chrysalis come after the
caterpillar?” Capture asserts four objects, actual relations/new-generation return,
and current focus in the existing request. Projection tests separately verify
highlight/reveal state. The mock forms an answer from
actual larva→pupa relation meaning and pupa detail. Exactly **one TUTOR call**, zero
Canvas/Vision/extra pre-Tutor calls; normal Student Chat message and Tutor reply.

**Runtime-03:** REQUEST_EXPLANATION targets pupa, then a later RECORD_ONLY action
focuses adult. Immutable source still exposes:

```json
{"current_interaction":{"action":"REQUEST_EXPLANATION","target_id":"pupa","target_kind":"object","label":"Chrysalis","detail":"The butterfly develops inside the pupa."}}
```

Current Canvas truthfully reports adult focus and a later Scene version. Existing
admit/stream/persist/finalize completes one Tutor continuation and observation,
**no fake Student LearningMessage**. Candidate/Learning Event/Evidence/Personal
Facts/Current State/Pattern/Specialist-run counts remain unchanged.

**Actual ProcessView:** the server-accepted/replayed seed exactly matches the
reviewed frontend butterfly data and renders through unchanged ProcessView with
React server rendering. Stable IDs, focus explanation and Stage 3 of 4 are checked.
This is renderer/semantic consistency, not a fresh browser or production Host proof.

**No real provider call was used.** Capturing mocks exercise actual database state,
request construction and ModelGateway execution. Deterministic mock answers prove
protocol/context availability, not live-model pedagogical quality or learning benefit.
No application accounts/auth settings or production Student traffic were touched.

## Verification and fresh independent review

- Final focused context/capacity/database/render set: **36 passed**.
- Final proportional isolated Python regression: **403 passed across 32 files**,
  covering Tutor, Runtime-01/03, four accepted exact subjects, Gateway, capacity and
  Parent Boundary behavior. Existing guarded `lina_learning_test` only; no reset,
  migration or application database access. Disposable fixture rows were used.
- Accepted Process Node tests: **13 passed**. Web source/contracts unchanged;
  web typecheck/build/browser matrix were not rerun for this runtime-only task.
- New Python source/tests pass Ruff. Compact skill validator passes. TDD recorded
  missing-contract RED, edge failures and review-finding regressions before fixes.
- Independent review initially found **0 Critical / 1 Important / 1 Minor**.
  Cross-activity raw-state/capacity leak fixed; inherited filtration accessibility
  metadata replaced with accurate Process semantics. Final recheck: **0 Critical /
  0 Important / 0 Minor open**. Compact skill scenario behavior/authority also checked.

## Delivery gate and limits

Schema/migrations: **NONE**. Dependencies/installations: **NONE**. No natural
specialist generation, Worker activation, reusable-content library, Tutor v10,
new retrieval/embedding pipeline, images/Vision/Voice, other pattern renderers,
production Host adapter, deployment or learning-benefit claim.

Historical delivery gate: automatic approval review rejected the acceptance-record
mutation twice because attachment authorization was insufficient for that approval.
No workaround or publication followed. The Product Owner subsequently approved
DONE / ACCEPTED directly in chat, based on the reported A–F implementation and
verification, and explicitly authorized this exact 18-file commit and normal push
to `origin` / `refs/heads/codex/ctx-03`. This resolves the delivery gate only; no
additional implementation or next task is authorized. The accepted scope and
remaining exclusions above remain unchanged.

Recommended next only: one bounded Process specialist composition through existing
Worker/Gateway → validated accepted Scene → this same awareness path, proving
factual grounding, admission/permissions, causal rejection, provider cost and real
Host integration. Not READY or started. Preserve unrelated work and raw evidence.

## Exact accepted commit inventory

- `docs/LINA_EDUCATIONAL_VISUALS_GUIDE.md`
- `skills/lina-educational-visuals/SKILL.md`
- `runtime/tutor/visual-guidance-v1.md`
- `runtime/canvas-specialist/visual-capability-pack-v1.md`
- `services/studio/subjects/process_visual.py`
- `services/studio/subjects/__init__.py`
- `services/studio/tutor_context.py`
- `services/studio/interactions.py`
- `services/studio/router.py`
- `services/studio/workspace_capabilities.py`
- `services/tutor/capacity.py`
- `services/tutor/runtime.py`
- `tests/test_process_visual_awareness.py`
- `tests/test_process_visual_awareness_postgres.py`
- `tests/process_visual_render_proof.cjs`
- `docs/reviews/LINA-VISUAL-INTELLIGENCE-01/IMPLEMENTATION_RECORD.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `project-state/PROJECT_STATE.md`

Before closure staging, baseline HEAD and origin matched
`da63850ef951a38f7e4ebe19bfa47692b2d9d13d`; the index was empty. All 864
pre-existing untracked entries were preserved, with nine new task files bringing
the pre-commit count to 873. Only the 18 paths above are authorized for this commit.
Actual commit SHA and verified remote parity are returned in the delivery response;
this record does not invent a self-referential commit identifier.
