import assert from "node:assert/strict";
import test from "node:test";

import {
  createAgenticCanvasOperation,
  parseAgenticCanvasScene,
} from "./agentic-canvas-contract.ts";
import { resolveApprovedStudioRenderer } from "./renderer-host.ts";

const commonBlock = {
  meaning: "Compare the quantities without changing the Tutor's objective.",
  title: "Compare quantities",
  accessibility: {
    text_equivalent: "A safe visual comparison of two quantities.",
    aria_label: "Quantity comparison",
  },
  allowed_actions: ["FOCUS"] as const,
  elements: [
    { id: "item-a", label: "Quantity A", current_value: "3/5" },
  ],
};

const validScene = {
  version: "agentic-canvas-scene-v1",
  objective: "Compare the two quantities visually.",
  subject_key: "MATH",
  blocks: [
    { ...commonBlock, block_id: "math-board", type: "MATH_BOARD", board_kind: "NUMBER_LINE", axis_min: "0", axis_max: "1" },
    { ...commonBlock, block_id: "scene-2d", type: "SCENE_2D", viewport_width_units: 100, viewport_height_units: 100 },
    { ...commonBlock, block_id: "diagram", type: "DIAGRAM", topology: "COMPARISON", layout: "HORIZONTAL" },
    { ...commonBlock, block_id: "text", type: "TEXT_INTERACTION", interaction_family: "ANNOTATION" },
    { ...commonBlock, block_id: "math-input", type: "MATH_INPUT", notation: "LATEX" },
    { ...commonBlock, block_id: "image", type: "IMAGE", studio_generated_asset_id: "asset-123" },
  ],
};

const exactAgenticContract = {
  scene_id: "studio-scene-1",
  scene_version: 1,
  subject_key: "CANVAS",
  subject_profile_version: "agentic-canvas-profile-v1",
  activity_key: "agentic_canvas",
  activity_contract_version: "agentic-canvas-activity-v1",
  renderer_key: "agentic-canvas",
  renderer_version: "agentic-canvas-renderer-v1",
  payload_schema_version: "agentic-canvas-scene-v1",
  locale: "en",
  direction: "ltr" as const,
};

test("Renderer Host admits only the exact registered Agentic Canvas contract", () => {
  assert.equal(resolveApprovedStudioRenderer(exactAgenticContract), "AGENTIC_CANVAS");
  assert.equal(resolveApprovedStudioRenderer({ ...exactAgenticContract, subject_key: "MATH" }), null);
  assert.equal(resolveApprovedStudioRenderer({ ...exactAgenticContract, renderer_version: "agentic-canvas-renderer-v2" }), null);
  assert.equal(resolveApprovedStudioRenderer({ ...exactAgenticContract, payload_schema_version: "agentic-canvas-scene-v2" }), null);
});

test("Agentic Canvas admission accepts only the exact registered declarative block union", () => {
  const parsed = parseAgenticCanvasScene(validScene);
  assert(parsed);
  assert.deepEqual(parsed.blocks.map((block) => block.type), [
    "MATH_BOARD",
    "SCENE_2D",
    "DIAGRAM",
    "TEXT_INTERACTION",
    "MATH_INPUT",
    "IMAGE",
  ]);
});

test("Agentic Canvas admission rejects unknown blocks and unknown fields at every boundary", () => {
  assert.equal(parseAgenticCanvasScene({ ...validScene, renderer_key: "model-picked-renderer" }), null);
  assert.equal(parseAgenticCanvasScene({ ...validScene, blocks: [{ ...commonBlock, block_id: "video", type: "VIDEO" }] }), null);
  assert.equal(parseAgenticCanvasScene({
    ...validScene,
    blocks: [{ ...validScene.blocks[0], jsx: "<Component />" }],
  }), null);
  assert.equal(parseAgenticCanvasScene({
    ...validScene,
    blocks: [{
      ...validScene.blocks[0],
      accessibility: { ...validScene.blocks[0].accessibility, engine: "browser" },
    }],
  }), null);
});

test("Agentic Canvas admission rejects executable, provider URL, base64 and binary content", () => {
  const withMeaning = (meaning: string) => ({
    ...validScene,
    blocks: [{ ...validScene.blocks[0], meaning }],
  });
  assert.equal(parseAgenticCanvasScene(withMeaning("<script>alert(1)</script>")), null);
  assert.equal(parseAgenticCanvasScene(withMeaning("javascript:alert(1)")), null);
  assert.equal(parseAgenticCanvasScene(withMeaning("Use https://provider.example/temporary-output.png")), null);
  assert.equal(parseAgenticCanvasScene(withMeaning("data:image/png;base64,iVBORw0KGgo=")), null);
  assert.equal(parseAgenticCanvasScene(withMeaning("A".repeat(96))), null);
  assert.equal(parseAgenticCanvasScene(withMeaning("fetch('/execute-model-output')")), null);
  assert.equal(parseAgenticCanvasScene(withMeaning("safe\u0000binary")), null);
});

test("Agentic Canvas emits one exact semantic Studio operation and no renderer authority", () => {
  const parsed = parseAgenticCanvasScene(validScene);
  assert(parsed);
  const operation = createAgenticCanvasOperation({
    sceneId: "studio-scene-1",
    sceneVersion: 3,
    block: parsed.blocks[0],
    action: "FOCUS",
    elementId: "item-a",
    idempotencyKey: "focus-1",
  });
  assert.deepEqual(operation, {
    scene_id: "studio-scene-1",
    base_scene_version: 3,
    action_key: "FOCUS",
    payload: { block_id: "math-board", element_id: "item-a" },
    idempotency_key: "focus-1",
  });
  assert(!JSON.stringify(operation).match(/renderer|provider|component|pixel|tool/i));
  assert.throws(() => createAgenticCanvasOperation({
    sceneId: "studio-scene-1",
    sceneVersion: 3,
    block: parsed.blocks[0],
    action: "MOVE",
    elementId: "item-a",
    idempotencyKey: "move-1",
  }), /not allowed/);
  assert.throws(() => createAgenticCanvasOperation({
    sceneId: "studio-scene-1",
    sceneVersion: 3,
    block: parsed.blocks[0],
    action: "FOCUS",
    elementId: "unknown-element",
    idempotencyKey: "focus-2",
  }), /unknown element/);
});
