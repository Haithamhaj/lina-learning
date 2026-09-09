# Tutor-Led Agentic Canvas Design

## Decision

The Primary Tutor remains Lina's only teaching authority. It may emit an additive,
strict `CanvasBriefV1`; this is educational meaning, never renderer, library,
provider, tool, or code control. One Canvas Agent uses OpenAI Agents SDK only as
a bounded composition loop. It can select and chain registered tools, but code
validates all tool input, records accepted draft blocks in a run-local registry,
and accepts only a final reference to those blocks.

## Durable flow

`Tutor v11 -> CanvasBrief -> existing Canvas Specialist run/job -> Canvas Agent
-> validated block registry -> agentic-canvas-scene-v1 -> existing Studio Scene,
Event, Snapshot and reducer -> semantic Tutor projection -> same Tutor`.

The existing Runtime, Scene, Event, Snapshot, StudentInteraction, Tutor
Observation, subject registry, job lifecycle, ownership, stale-result fencing,
SSE and frontend admission are retained. Historical capability-pack runs stay
readable. New agentic runs never select a tool from authored problems, activity
IDs, finite composition patterns, or renderer identities.

## Boundaries

- No subject/manager/Canvas teaching agents, arbitrary browser code, or second
  job, session, SSE, storage, or AI-runtime authority.
- Exact SymPy and Pint tools own mathematical and dimensional truth; the model
  only chooses bounded operations and composition.
- Scene blocks are `MATH_BOARD`, `SCENE_2D`, `DIAGRAM`, `TEXT_INTERACTION`,
  `MATH_INPUT`, and project-owned `IMAGE` references; no embedded binaries.
- Generated images use existing ObjectStorage and a separate derived Studio
  asset record, never StudentSourceAsset or a durable provider URL.
- Safety is evaluated before scheduling and remains effective for every tool
  and generated asset. The agent's trace stores bounded metadata/digests only.
- Existing global Scene/Snapshot capacity remains unchanged.

## Compatibility and proof

Tutor v8/v9/v10 readers and persisted messages remain valid. New exact subject
contracts coexist with historical profiles. Reducer actions stay a finite,
typed semantic vocabulary. The projection is compact, reconstructable from
Studio state and events, and contains no renderer/browser internals. Tests use
runtime-generated Math, Physics, Science, Arabic/English and process inputs;
they assert outcomes and forbidden routing rather than authored fixtures or a
prescribed tool sequence.

## Real-provider acceptance

Mocks and static providers remain valid only for deterministic unit and
failure-recovery tests. They are never acceptance evidence for Tutor brief
creation, Agents SDK tool choice, multi-tool composition, hosted tools, or the
Tutor-to-Canvas-to-Tutor loop. Before closure, one dedicated live harness must
use the configured real Tutor/provider and Agents SDK, retain bounded lineage
(Tutor execution, run, trace, tools, Scene), and prove Tutor brief creation,
unseen Math, multi-tool autonomy, Physics, dynamic Science, Arabic/English,
Image Generation, Code Interpreter when used, interaction continuation, active
Canvas Chat reference, update/stale handling, and replay. No secrets or raw
child content may be emitted in trace evidence.
