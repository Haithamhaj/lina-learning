import assert from "node:assert/strict";
import test from "node:test";

import { persistedAgenticCanvasScene } from "./agentic-canvas-persisted-scene.ts";
import { parseAgenticCanvasScene } from "./agentic-canvas-contract.ts";

test("renderer admission consumes the persisted real-Agent Scene shape", () => {
  const scene = parseAgenticCanvasScene(persistedAgenticCanvasScene);
  assert(scene);
  assert.equal(scene.version, "agentic-canvas-scene-v1");
  assert.equal(scene.blocks[0].type, "MATH_BOARD");
  assert.deepEqual(scene.blocks[0].elements.map((element) => element.current_value), ["0.6", "0.45"]);
});
