import assert from "node:assert/strict";
import test from "node:test";

import nextConfig from "../apps/web/next.config.mjs";

test("production API rewrite keeps browser API paths on the private FastAPI origin", async () => {
  const rewrites = await nextConfig.rewrites();

  assert.deepEqual(rewrites, [
    {
      source: "/api/:path*",
      destination: "http://127.0.0.1:8000/api/:path*",
    },
  ]);
});