const { test } = require("node:test");
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const { mkdtempSync } = require("node:fs");
const path = require("node:path");

const out = mkdtempSync("/tmp/canvas-selection-");
execFileSync(process.execPath, [
  require.resolve("typescript/bin/tsc"),
  path.resolve(__dirname, "../../lib/studio/visual-toolbelt/visual-selection.ts"),
  "--outDir", out,
  "--target", "es2020",
  "--module", "commonjs",
  "--skipLibCheck",
  "--strict",
]);
const { resolveCanvasPattern, selectCanvasCapability } = require(path.join(out, "visual-selection.js"));

test("application selects each finalized Canvas pattern from semantic intent", () => {
  assert.equal(resolveCanvasPattern({ type: "explain_process", topology: "sequence" }), "PROCESS");
  assert.equal(resolveCanvasPattern({ type: "explain_process", topology: "cycle" }), "PROCESS");
  assert.equal(resolveCanvasPattern({ type: "place_object", relation: "inside" }), "SPATIAL_MANIPULATION");
  assert.equal(resolveCanvasPattern({ type: "construct_coordinate", domain: "integer_grid" }), "MATH_VISUALIZATION");
  assert.equal(resolveCanvasPattern({ type: "author_math", format: "latex" }), "MATH_INPUT");
});

test("application owns the local adapter choice behind each pattern", () => {
  assert.deepEqual(selectCanvasCapability({ type: "explain_process", topology: "cycle" }), { pattern: "PROCESS", adapter: "process-view" });
  assert.deepEqual(selectCanvasCapability({ type: "place_object", relation: "inside" }), { pattern: "SPATIAL_MANIPULATION", adapter: "spatial-placement" });
  assert.deepEqual(selectCanvasCapability({ type: "construct_coordinate", domain: "integer_grid" }), { pattern: "MATH_VISUALIZATION", adapter: "coordinate-construction" });
  assert.deepEqual(selectCanvasCapability({ type: "author_math", format: "latex" }), { pattern: "MATH_INPUT", adapter: "math-expression-input" });
  assert.equal(selectCanvasCapability({ type: "mathlive" }), null);
});

test("selection rejects implementation and renderer choices", () => {
  for (const value of [
    { type: "konva" },
    { type: "author_math", format: "latex", renderer: "mathlive" },
    { type: "explain_process", topology: "sequence", technology: "svg" },
    { type: "construct_coordinate", domain: "decimal" },
    null,
  ]) assert.equal(resolveCanvasPattern(value), null);
});
