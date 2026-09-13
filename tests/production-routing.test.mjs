import assert from "node:assert/strict";
import test from "node:test";

import nextConfig from "../apps/web/next.config.mjs";

test("production API rewrite keeps browser API paths on the private FastAPI origin", async () => {
  const rewrites = await nextConfig.rewrites();

  assert.deepEqual(rewrites, [
    {
      source: "/api/:path((?!__clerk(?:/|$)).*)",
      destination: "http://127.0.0.1:8000/api/:path*",
    },
  ]);
});

test("Clerk's same-origin proxy is excluded from the FastAPI rewrite", async () => {
  const [rewrite] = await nextConfig.rewrites();
  const pathPattern = new RegExp(`^${rewrite.source.slice("/api/:path(".length, -1)}$`);

  assert.equal(pathPattern.test("__clerk/npm/@clerk/clerk-js@5/dist/clerk.browser.js"), false);
  assert.equal(pathPattern.test("v1/status"), true);
});