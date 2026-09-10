# Tutor-Led Agentic Canvas Implementation Plan

> **Execution mode:** Execute continuously through final verification and closure. Use subagent-driven development where available; commits, tests, and live proofs are internal steps, not Product Owner checkpoints.

**Goal:** Replace new Canvas composition writes with one bounded, Tutor-led Agentic Canvas while retaining Studio as durable state authority.

**Architecture:** The Tutor emits an additive semantic CanvasBrief. The existing Canvas Specialist job owns lifecycle and invokes a bounded Agents SDK runner whose registered tools create validated draft blocks in a run-local registry. Existing Studio service/reducer settles the resulting declarative Scene and exposes a compact semantic projection to the same Tutor.

**Tech Stack:** Python/FastAPI/SQLAlchemy/PostgreSQL, Pydantic, OpenAI Agents SDK, SymPy, Pint, existing React/TypeScript, JSXGraph, Konva, Motion, MathLive.

**Spec:** `docs/superpowers/specs/2026-09-10-tutor-led-agentic-canvas-design.md`

## Global Constraints

- Primary Tutor is the sole teaching authority and retains its normal Model Gateway path.
- Preserve existing Runtime/Scene/Event/Snapshot/reducer/ownership/SSE/job contracts and historical replay.
- No finite authored problem, activity, capability-pack, renderer, tool, provider, or code control enters CanvasBrief.
- Tools are bounded and validated; scenes are declarative, compact, and contain no executable code or base64 assets.
- Safety precedes scheduling; generated assets are derived Studio assets in existing ObjectStorage, never student originals.
- Use RED → GREEN → REFACTOR and retain exact 16KB-equivalent scene/snapshot limits.
- Unit/failure tests may be deterministic, but no Tutor, Agent, hosted-tool, or
  end-to-end AI-behavior acceptance claim is valid without the configured real
  provider and actual lineage/trace evidence.

---

### Task 1: Add the additive Tutor v11 CanvasBrief boundary

**Files:** `services/tutor/runtime.py`, `services/tutor/context.py`, `services/studio/workspace_intent.py`, `tests/test_tutor_runtime_contract.py`, `tests/test_studio_workspace_intent.py`

- [ ] Write RED tests that accept v8-v10 unchanged; accept a valid semantic CanvasBrief; reject `renderer_key`, `tool_name`, `jsx`, `provider`, and arbitrary-code fields.
- [ ] Run focused tests and confirm failure is missing v11 normalization.
- [ ] Implement strict `CanvasBriefV1`, provider/local normalization, persistence metadata, and subject-aware Primary Learning Tutor instruction. Keep WorkspaceIntent independently parsed.
- [ ] Re-run focused tests and commit `feat: add tutor canvas brief v11`.

### Task 2: Define Agentic scene, technical actions, and projection contracts

**Files:** `services/studio/agentic_canvas.py` (new), `services/studio/contracts.py`, `services/studio/protocol.py`, `services/studio/reducer.py`, `services/studio/tutor_context.py`, `tests/test_agentic_canvas_contract.py` (new), `tests/test_studio_tutor_context.py`

- [ ] Write RED tests for strict block union, unknown block rejection, bounded manifest, `FOCUS/SELECT/MOVE/SET_VALUE/CONNECT/SUBMIT` semantic actions, and renderer-free Tutor projection.
- [ ] Run tests and confirm absent contract/reducer handling.
- [ ] Implement Pydantic scene/block/projection types, exact action validation, reducer adapter, and projection from Scene plus committed Event state.
- [ ] Re-run tests and commit `feat: add agentic canvas contracts`.

### Task 3: Build deterministic composition tools and run-local block registry

**Files:** `services/studio/canvas_agent/registry.py` (new), `services/studio/canvas_agent/tools.py` (new), `services/studio/canvas_agent/contracts.py` (new), `tests/test_canvas_agent_tools.py` (new), `apps/api/requirements.txt`

- [ ] Write RED tests for exact `0.6 > 0.45` rational comparison, invalid dimensional conversion, each tool's bounded schema, unknown block IDs, and a multi-tool registry result.
- [ ] Run tests and confirm unavailable tools/dependencies.
- [ ] Pin compatible `openai-agents`, `sympy`, and `pint`; implement `compute_math`, `convert_units`, `create_math_board`, `create_2d_scene`, `create_diagram`, `create_text_interaction`, and `create_math_input`. Tools store accepted DraftBlocks and return only `block_id` plus compact summary.
- [ ] Re-run tests and commit `feat: add bounded canvas composition tools`.

### Task 4: Add one Agents SDK Canvas runner and skill pack

**Files:** `services/studio/canvas_agent/runner.py` (new), `services/studio/canvas-agent/AGENT.md` (new), `services/studio/canvas-agent/skills/*.md` (new), `tests/test_canvas_agent_runner.py` (new)

- [ ] Write RED tests for required final block IDs, fabricated-ID rejection, tool-call/turn ceilings, safe tool failure, and a fake runner choosing two registered tools without fixed sequence assertions.
- [ ] Run tests and confirm runner is absent.
- [ ] Implement one runner with SDK tracing payloads disabled by default, metadata/digests correlation, explicit tool registry, final-reference validation, and deterministic test adapter. Add focused instruction modules for selection, composition, math, diagrams, spatial, text, image, accessibility, and bilingual layout.
- [ ] Re-run tests and commit `feat: add canvas agent runner`.

### Task 5: Integrate agentic runs into existing Specialist lifecycle

**Files:** `services/studio/canvas_specialist.py`, `workers/studio_handlers.py`, `services/studio/router.py`, `services/studio/workspace_capabilities.py`, `tests/test_canvas_specialist_execution_postgres.py`, `tests/test_studio_workspace_router.py`

- [ ] Write RED tests that CanvasBrief schedules Agentic V2 without `problem_for`, authored IDs, or capability-pattern selection; prove stale/failure leaves last valid scene intact.
- [ ] Run tests and confirm legacy routing is selected.
- [ ] Add an additive Agentic run identity/schema and worker dispatch; preserve existing runs and fencing. Route only when brief + safety + Studio availability permit, retaining close/source/annotation/no-change behavior.
- [ ] Re-run tests and commit `feat: integrate agentic specialist runs`.

### Task 6: Persist derived generated assets and resolve images

**Files:** `services/platform/db/models.py`, `migrations/versions/<revision>_studio_generated_assets.py`, `services/studio/generated_assets.py` (new), `apps/api/routes/studio.py`, `tests/test_studio_generated_assets_postgres.py` (new)

- [ ] Write RED ownership, checksum, no-provider-URL, failed-persistence, and private-read-path tests.
- [ ] Run tests and confirm the derived asset model is absent.
- [ ] Add a non-destructive migration and `StudioGeneratedAsset`; persist bytes through existing ObjectStorage, validate/adopt image outputs, replace temporary handles with owned IDs, and authorize reads by the existing Student ownership model.
- [ ] Re-run tests and commit `feat: persist generated studio assets`.

### Task 7: Add exact frontend Agentic renderer admission

**Files:** `apps/web/lib/studio/contracts.ts`, `apps/web/lib/studio/renderer-host.ts`, `apps/web/components/daily-student/studio-renderer-host.tsx`, `apps/web/lib/studio/agentic-canvas.tsx` (new), `apps/web/lib/studio/agentic-canvas.test.ts` (new)

- [ ] Write RED tests allowing only `AGENTIC_CANVAS` and registered block types, rejecting executable/binary/unknown payloads, and emitting semantic operations only.
- [ ] Run the Node tests and confirm resolver rejection.
- [ ] Implement the allowlisted block dispatcher using existing visual-toolbelt wrappers; keep renderer implementation detail out of persisted scene and Tutor projection.
- [ ] Re-run tests/typecheck and commit `feat: render agentic canvas blocks`.

### Task 8: Prove Tutor continuity, compatibility, and acceptance journeys

**Files:** `tests/test_agentic_canvas_acceptance_postgres.py` (new), `tests/test_studio_tutor_context_postgres.py`, `tests/test_canvas_specialist_alignment_postgres.py`, `docs/REUSE_DECISIONS.md`

- [ ] Write RED runtime-generated journeys for decimal, physics units, 5+ stage science, Arabic/English, process, image asset, multi-tool autonomy, interaction-to-Tutor, chat-with-active-canvas, update/stale handling, replay, failures, and historical scenes.
- [ ] Run focused suites and confirm each missing behavior fails for the intended seam.
- [ ] Implement only the minimal compatibility fixes exposed by those tests. Record the bounded OpenMAIC `ADOPT/PARTIAL ADOPT/REJECT` decision and rationale.
- [ ] Run focused/PostgreSQL suites, web tests/typecheck/build, `git diff --check`, and full Python suite when available; commit `test: prove agentic canvas acceptance`.
- [ ] Add and run `scripts/prove_studio_agentic_live.py` against the real API
  key. Record LIVE-01 through LIVE-12: Tutor brief, unseen Math, autonomous
  multi-tool choice, Physics, dynamic Science, Arabic/English, image generation,
  Code Interpreter when used, Canvas-to-Tutor continuation, active-Canvas Chat,
  Tutor-triggered update, and replay. Each result records only bounded lineage,
  selected tools, Scene contract, deterministic check, and pass/fail.
