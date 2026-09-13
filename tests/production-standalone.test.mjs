import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import nextConfig from "../apps/web/next.config.mjs";

test("production packaging creates a self-contained Next standalone artifact", async () => {
  const script = await readFile("scripts/build_replit_production.sh", "utf8");

  assert.equal(nextConfig.output, "standalone");
  assert.match(script, /UV_NO_CACHE=1/);
  assert.match(script, /npm ci/);
  assert.match(script, /NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY/);
  assert.match(script, /apps\/web\/\.next\/standalone/);
  assert.match(script, /\.next\/static/);
  assert.match(script, /rm -rf -- .*"node_modules"/);
  assert.match(script, /\.venv-production/);
});
