import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  agenticCanvasSemanticControls,
  createAgenticCanvasOperation,
  parseAgenticCanvasScene,
  settleAgenticCanvasOperation,
} from "./agentic-canvas-contract.ts";
import type { AgenticCanvasAction } from "./contracts.ts";
import { AgenticCanvasWorkspace } from "./agentic-canvas.tsx";
import { clippedLinearExpression, textInteractionPresentation } from "./agentic-canvas-presentation.ts";
import { activeSceneRendererState, resolveApprovedStudioRenderer } from "./renderer-host.ts";

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
    {
      ...commonBlock, block_id: "math-board", type: "MATH_BOARD", board_kind: "NUMBER_LINE", axis_min: "0", axis_max: "1",
      axes: [{ axis: "X", minimum: "0", maximum: "1", step: "1/10" }],
      markers: [{ id: "fraction-a", label: "3/5", value: "3/5", marker_kind: "POINT", draggable: true }],
      expressions: [{ id: "comparison", label: "Comparison", latex: "3/5 > 1/2", role: "DERIVED" }],
    },
    {
      ...commonBlock, block_id: "scene-2d", type: "SCENE_2D", viewport_width_units: 100, viewport_height_units: 100,
      objects: [{ id: "cart", label: "Cart", object_kind: "RECTANGLE", position: { x: "40", y: "50" }, draggable: false }],
      relations: [],
    },
    {
      ...commonBlock, block_id: "diagram", type: "DIAGRAM", topology: "COMPARISON", layout: "HORIZONTAL",
      nodes: [{ id: "whole", label: "Whole", node_kind: "CONCEPT" }], edges: [],
    },
    {
      ...commonBlock, block_id: "text", type: "TEXT_INTERACTION", interaction_family: "ANNOTATION",
      prompt: "Highlight the key phrase.", items: [{ id: "phrase", text: "three equal parts", group_id: null }], groups: [], relations: [],
    },
    { ...commonBlock, block_id: "math-input", type: "MATH_INPUT", notation: "LATEX", prompt: "Enter a fraction.", constraints: ["Use a fraction."] },
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
  assert.equal(parsed.blocks[0].type === "MATH_BOARD" && parsed.blocks[0].markers[0].value, "3/5");
  assert.equal(parsed.blocks[1].type === "SCENE_2D" && parsed.blocks[1].objects[0].position.x, "40");
});

test("Agentic Canvas v2 preserves semantic presentation while rejecting hidden context", () => {
  const scene = {
    ...validScene,
    version: "agentic-canvas-scene-v2",
    presentation: {
      layout: "FOCUS_SUPPORT", palette: "COOL", motion: "REVEAL",
      placements: validScene.blocks.map((block, order) => ({ block_id: block.block_id, role: order === 0 ? "PRIMARY" : "SUPPORT", order, span: order === 0 ? "FULL" : "NORMAL" })),
      reveal_order: ["math-board"],
    },
  };
  const parsed = parseAgenticCanvasScene(scene);
  assert(parsed?.presentation);
  assert.equal(parsed.presentation?.layout, "FOCUS_SUPPORT");
  assert.equal(parseAgenticCanvasScene({ ...scene, visual_learner_context: { age_years: 10 } }), null);
  assert.equal(parseAgenticCanvasScene({ ...scene, presentation: { ...scene.presentation, placements: [] } }), null);
});

test("Full-Power v3 admits durable build references and rejects inline executable packages", () => {
  const scene = {
    version: "agentic-canvas-scene-v3",
    objective: "Compare two fractions.", subject_key: "MATH",
    presentation: { layout: "FOCUS", palette: "COOL", motion: "NONE", placements: [{ block_id: "custom", role: "PRIMARY", order: 0, span: "FULL" }], reveal_order: [] },
    blocks: [{
      ...commonBlock, block_id: "custom", type: "CUSTOM_VISUAL", allowed_actions: ["MOVE"],
      elements: [{ id: "fraction-a", label: "One half", current_value: null }], artifact_instance_id: "fraction-instance", bridge_nonce: "nonce-123",
      package: {
        version: "custom-visual-package-v1", runtime_kind: "custom-visual", dependencies: ["native-svg-v1"],
        source: "window.mount=(root,params,bridge)=>{root.textContent=params.label}", parameter_schema: { type: "object" },
        manifest: {
          version: "canvas-semantic-manifest-v1", brief_digest: "a".repeat(64), objective: "Compare two fractions.", representation_summary: "A shared exact fraction line.",
          entities: [{ semantic_id: "fraction-a", kind: "quantity", label: "One half", educational_meaning: "An exact fraction.", visible_description: "A blue marker." }],
          relations: [], quantities: [{ semantic_id: "fraction-a", value: "1/2", unit: null, provenance: "tutor-brief" }], presentation_steps: [],
          interactions: [{ semantic_id: "fraction-a", action: "MOVE", meaning: "Move the marker.", value_required: true }], calculated_results: [], visual_descriptions: ["A blue marker."], current_state_schema: {}, provenance: { runtime_kind: "custom-visual" },
        },
      }, parameters: { label: "1/2" },
    }],
  };
  // Durable Scenes contain owned Build references, never executable packages.
  assert.equal(parseAgenticCanvasScene(scene), null);
  const { package: inlinePackage, ...block } = scene.blocks[0];
  const durableBlock = {
    ...block,
    custom_visual_build_id: "11111111-1111-4111-8111-111111111111",
    manifest_digest: "a".repeat(64),
  };
  assert.equal(parseAgenticCanvasScene({ ...scene, blocks: [durableBlock] })?.blocks[0].type, "CUSTOM_VISUAL");
  assert.equal(parseAgenticCanvasScene({ ...scene, blocks: [{ ...durableBlock, package: inlinePackage }] }), null);
  assert.equal(parseAgenticCanvasScene({ ...scene, blocks: [{ ...scene.blocks[0], package: { ...scene.blocks[0].package, source: "window.mount=()=>fetch('https://bad.example')" } }] }), null);
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
  assert.equal(parseAgenticCanvasScene({
    ...validScene,
    blocks: [{
      ...validScene.blocks[0],
      markers: [{ id: "fraction-a", label: "3/5", value: "3/5", marker_kind: "POINT", draggable: true, provider_url: "https://provider.invalid/x" }],
    }],
  }), null);
  assert.equal(parseAgenticCanvasScene({
    ...validScene,
    blocks: [{ ...validScene.blocks[2], edges: [{ source_id: "whole", target_id: "missing", relation: "RELATES_TO", label: null }] }],
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
    payload: {
      version: "agentic-canvas-action-v1",
      action: "FOCUS",
      block_id: "math-board",
      element_id: "item-a",
      from_value: null,
      to_value: null,
    },
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

test("Agentic Canvas SELECT controls require an explicit target while SUBMIT stays block-level", () => {
  const parsed = parseAgenticCanvasScene(validScene);
  assert(parsed);
  const mathBlock = parsed.blocks[0];
  if (mathBlock.type !== "MATH_BOARD") assert.fail("Expected the Math Board fixture.");
  const twoTargets = {
    ...mathBlock,
    allowed_actions: ["SELECT", "SUBMIT"] as AgenticCanvasAction[],
    elements: [
      { id: "item-a", label: "Quantity A", current_value: "3/5" },
      { id: "item-b", label: "Quantity B", current_value: "1/2" },
    ],
  };
  assert.deepEqual(agenticCanvasSemanticControls(twoTargets), [
    { action: "SELECT", elementId: "item-a", label: "Select Quantity A" },
    { action: "SELECT", elementId: "item-b", label: "Select Quantity B" },
    { action: "SUBMIT", label: "Submit" },
  ]);
  assert.deepEqual(agenticCanvasSemanticControls({
    ...twoTargets,
    allowed_actions: ["SELECT"] as AgenticCanvasAction[],
    elements: [],
  }), []);
  assert.deepEqual(agenticCanvasSemanticControls({
    ...twoTargets,
    board_kind: "PLOT",
  }), [{ action: "SUBMIT", label: "Submit" }]);
});

test("Agentic Canvas renders the current reduced Scene after Snapshot reload", () => {
  const updated = structuredClone(validScene);
  updated.blocks[0].elements[0].current_value = "4/5";
  const rendererState = activeSceneRendererState({
    active_scene_contract: exactAgenticContract,
    active_scene_seed: validScene,
    state_payload: { agentic_canvas: updated },
  });
  const parsed = parseAgenticCanvasScene(rendererState);
  assert.equal(parsed?.blocks[0].elements[0].current_value, "4/5");
});

test("Agentic Canvas settles rejected Studio operations without an unhandled rejection", async () => {
  const accepted = await settleAgenticCanvasOperation(async () => { throw new Error("stale scene"); }, {
    scene_id: "studio-scene-1",
    base_scene_version: 3,
    action_key: "FOCUS",
    payload: {},
    idempotency_key: "focus-failed",
  });
  assert.equal(accepted, false);
});

test("bounded plot expressions parse and clip exact live linear forms", () => {
  assert.deepEqual(clippedLinearExpression("line-a", "y=3", { minimumX: -2, maximumX: 2, minimumY: -1, maximumY: 4 }), {
    id: "line-a", slope: 0, intercept: 3, start: { x: -2, y: 3 }, end: { x: 2, y: 3 },
  });
  assert.deepEqual(clippedLinearExpression("line-b", "y=0.4x+1", { minimumX: -5, maximumX: 5, minimumY: -1, maximumY: 4 }), {
    id: "line-b", slope: 0.4, intercept: 1, start: { x: -5, y: -1 }, end: { x: 5, y: 3 },
  });
  const clipped = clippedLinearExpression("line-c", "y=0.9x+1", { minimumX: -5, maximumX: 5, minimumY: -2, maximumY: 4 });
  assert(clipped);
  assert.equal(clipped.id, "line-c"); assert.equal(clipped.slope, 0.9); assert.equal(clipped.intercept, 1);
  assert(Math.abs(clipped.start.x + 10 / 3) < 1e-9); assert.deepEqual(clipped.start.y, -2);
  assert(Math.abs(clipped.end.x - 10 / 3) < 1e-9); assert.deepEqual(clipped.end.y, 4);
  assert.equal(clippedLinearExpression("unsafe", "y=Math.sin(x)", { minimumX: -5, maximumX: 5, minimumY: -5, maximumY: 5 }), null);
  assert.equal(clippedLinearExpression("outside", "y=8", { minimumX: -5, maximumX: 5, minimumY: -5, maximumY: 5 }), null);
  assert.deepEqual(clippedLinearExpression("negative", "y=-2x", { minimumX: -2, maximumX: 2, minimumY: -4, maximumY: 4 })?.start, { x: -2, y: 4 });
  assert.deepEqual(clippedLinearExpression("negative", "y=-2x", { minimumX: -2, maximumX: 2, minimumY: -4, maximumY: 4 })?.end, { x: 2, y: -4 });
  assert.deepEqual(clippedLinearExpression("zero", "y=0x+2.5", { minimumX: -1, maximumX: 3, minimumY: -3, maximumY: 3 })?.end, { x: 3, y: 2.5 });
  assert.equal(clippedLinearExpression("quadratic", "y=x^2", { minimumX: -5, maximumX: 5, minimumY: -5, maximumY: 5 }), null);
});

test("Plot renderer draws all supported live expressions and keeps unsupported text truthful", () => {
  const plotScene: any = structuredClone(validScene);
  plotScene.blocks = [{
    ...validScene.blocks[0], board_kind: "PLOT", axis_min: "-5", axis_max: "5",
    axes: [
      { axis: "X", minimum: "-5", maximum: "5", step: "1" },
      { axis: "Y", minimum: "-5", maximum: "5", step: "1" },
    ],
    markers: [],
    expressions: [
      { id: "constant", label: "Constant", latex: "y=3", role: "GIVEN" },
      { id: "decimal-a", label: "Decimal A", latex: "y=0.4x+1", role: "GIVEN" },
      { id: "decimal-b", label: "Decimal B", latex: "y=0.9x+1", role: "GIVEN" },
      { id: "unsupported", label: "Unsupported", latex: "y=x^2", role: "GIVEN" },
    ],
    allowed_actions: ["SELECT"],
  }];
  const html = renderToStaticMarkup(React.createElement(AgenticCanvasWorkspace, { sceneId: "scene", sceneVersion: 1, seed: plotScene, onOperation: async () => {}, onReload: () => {} }));
  assert.match(html, /data-expression-id="constant"/);
  assert.match(html, /data-expression-id="decimal-a"/);
  assert.match(html, /data-expression-id="decimal-b"/);
  assert.match(html, /Unsupported:.*y=x\^2/);
  assert.match(html, /not drawn/);
  assert.match(html, /<title>Constant: y=3<\/title>/);
  assert.match(html, />Reload Workspace<\/button>/);
  assert.doesNotMatch(html, />Select /);
});

test("Text interaction presentation uses only saved learner state, never solution grouping", () => {
  const parsed = parseAgenticCanvasScene(validScene);
  assert(parsed && parsed.blocks[3].type === "TEXT_INTERACTION");
  const block = {
    ...parsed.blocks[3], interaction_family: "CLASSIFICATION" as const,
    items: [
      { id: "solid", text: "Solid", group_id: "matter" },
      { id: "rain", text: "Rain", group_id: "water" },
    ],
    groups: [{ id: "matter", label: "Matter" }, { id: "water", label: "Water" }],
    elements: [
      { id: "solid", label: "Solid", current_value: null },
      { id: "rain", label: "Rain", current_value: "water" },
    ],
  };
  const state = textInteractionPresentation(block);
  assert.deepEqual(state.groups.map((group) => [group.id, group.items.map((item) => item.id)]), [
    ["matter", []], ["water", ["rain"]],
  ]);
  assert.deepEqual(state.unassigned.map((item) => item.id), ["solid"]);
});

test("Unsupported ordering fails closed without authored order or actionable controls", () => {
  const parsed = parseAgenticCanvasScene(validScene);
  assert(parsed && parsed.blocks[3].type === "TEXT_INTERACTION");
  const block = {
    ...parsed.blocks[3], interaction_family: "ORDERING" as const,
    items: [
      { id: "first", text: "First", group_id: null },
      { id: "second", text: "Second", group_id: null },
      { id: "third", text: "Third", group_id: null },
    ],
    allowed_actions: ["REORDER", "SUBMIT"] as AgenticCanvasAction[],
    elements: [
      { id: "first", label: "First", current_value: null },
      { id: "second", label: "Second", current_value: null },
      { id: "third", label: "Third", current_value: null },
    ],
  };
  const presentation = textInteractionPresentation(block);
  assert.deepEqual(presentation.groups, []);
  assert.deepEqual(presentation.unassigned, []);

  const scene: any = structuredClone(validScene);
  scene.blocks = [block];
  const html = renderToStaticMarkup(React.createElement(AgenticCanvasWorkspace, { sceneId: "scene", sceneVersion: 1, seed: scene, onOperation: async () => {}, onReload: () => {} }));
  assert.match(html, /Ordering is not available safely in Canvas yet/);
  assert.match(html, /Continue with Tutor chat/);
  assert.doesNotMatch(html, /First|Second|Third|>Submit<|Current order/);
});

test("Grouping, matching and relation presentations all start without solved placement", () => {
  const parsed = parseAgenticCanvasScene(validScene);
  assert(parsed && parsed.blocks[3].type === "TEXT_INTERACTION");
  for (const family of ["GROUPING", "MATCHING", "RELATION"] as const) {
    const block = {
      ...parsed.blocks[3], interaction_family: family,
      groups: [{ id: "left", label: "Left" }, { id: "right", label: "Right" }],
      items: [{ id: "choice", text: "Choice", group_id: "right" }],
      elements: [{ id: "choice", label: "Choice", current_value: null }],
    };
    const state = textInteractionPresentation(block);
    assert.deepEqual(state.groups.map(group => group.items), [[], []]);
    assert.deepEqual(state.unassigned.map(item => item.id), ["choice"]);
  }
});

test("Classification renderer separates empty category targets from unassigned choices", () => {
  const scene: any = structuredClone(validScene);
  scene.blocks = [{
    ...scene.blocks[3], interaction_family: "CLASSIFICATION", allowed_actions: ["MOVE"],
    groups: [{ id: "fastest", label: "Fastest" }, { id: "not-fastest", label: "Not fastest" }],
    items: [{ id: "steep", text: "Steep line", group_id: "fastest" }, { id: "flat", text: "Flat line", group_id: "not-fastest" }],
    elements: [{ id: "steep", label: "Steep line", current_value: null }, { id: "flat", label: "Flat line", current_value: null }],
  }];
  const html = renderToStaticMarkup(React.createElement(AgenticCanvasWorkspace, { sceneId: "scene", sceneVersion: 1, seed: scene, onOperation: async () => {}, onReload: () => {} }));
  const categoryRegion = html.slice(html.indexOf('data-text-group="fastest"'), html.indexOf('data-unassigned-choices="true"'));
  assert.doesNotMatch(categoryRegion, /Steep line|Flat line/);
  assert.match(html.slice(html.indexOf('data-unassigned-choices="true"')), /Steep line.*Flat line/);
});
