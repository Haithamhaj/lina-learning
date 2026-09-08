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
