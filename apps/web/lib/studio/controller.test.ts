import assert from "node:assert/strict";
import test from "node:test";

import { createStudioController } from "./controller";

test("controller sends bearer token in headers and never appends it to URLs", async () => {
  const calls: Array<{ url: string; init: RequestInit | undefined }> = [];
  const controller = createStudioController({
    apiBaseUrl: "https://api.example.test",
    getToken: async () => "secret-token",
    fetch: async (url, init) => {
      calls.push({ url: String(url), init });
      return new Response(JSON.stringify({ runtime_id: "runtime-1", learning_session_id: "session-1", status: "OPEN", latest_event_sequence: 0 }), { status: 200 });
    },
  });

  await controller.open("session-1");
  assert.equal(calls[0]?.url, "https://api.example.test/api/v1/student/studio/session/session-1/open");
  assert.equal((calls[0]?.init?.headers as Headers).get("Authorization"), "Bearer secret-token");
});
