import assert from "node:assert/strict";
import test from "node:test";

import nextConfig from "../apps/web/next.config.mjs";

test("browser /api requests rewrite to private FastAPI but Clerk proxy does not", async () => {
  const rewrites = await nextConfig.rewrites();

  assert.deepEqual(rewrites, [
    {
      source: "/api/:path((?!__clerk(?:/|$)).*)",
      destination: "http://127.0.0.1:8000/api/:path*",
    },
  ]);
});
