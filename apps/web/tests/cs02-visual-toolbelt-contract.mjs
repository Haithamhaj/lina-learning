import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const packageJson = JSON.parse(read("../package.json"));

test("CS-02 declares only the approved visual Toolbelt packages", () => {
  const dependencies = packageJson.dependencies;
  assert.ok(dependencies.motion);
  assert.match(dependencies["react-konva"], /^\^?18\./);
  assert.ok(dependencies.konva);
  assert.ok(dependencies.jsxgraph);
  assert.ok(dependencies.mathlive);
  assert.equal("motion-plus" in dependencies, false);
});

test("Toolbelt proofs preserve client isolation and semantic-only handoff", () => {
  const contracts = read("../lib/studio/visual-toolbelt/contracts.ts");
  const konva = read("../lib/studio/visual-toolbelt/konva/konva-proof.tsx");
  const jsxgraph = read("../lib/studio/visual-toolbelt/jsxgraph/jsxgraph-proof.tsx");
  const mathlive = read("../lib/studio/visual-toolbelt/mathlive/mathlive-proof.tsx");

  assert.match(contracts, /semanticPlacement/);
  assert.match(konva, /"target-region"/);
  assert.match(konva, /onSemanticPlacement/);
  assert.match(jsxgraph, /default: importedJXG/);
  assert.match(jsxgraph, /JXG\.JSXGraph\.freeBoard\(board\.current\)/);
  assert.doesNotMatch(jsxgraph, /window\.JXG/);
  assert.match(mathlive, /onValueChange/);
  assert.match(mathlive, /soundsDirectory = null/);
});
