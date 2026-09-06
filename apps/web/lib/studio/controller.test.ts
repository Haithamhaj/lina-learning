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
  assert.equal(calls[0]?.url, "https://api.example.test/v1/student/studio/session/session-1/open");
  assert.equal((calls[0]?.init?.headers as Headers).get("Authorization"), "Bearer secret-token");
});

test("a direct authoritative Snapshot advances the existing feed resume cursor", async () => {
  const calls: string[] = [];
  const controller = createStudioController({
    apiBaseUrl: "https://api.example.test",
    getToken: async () => "secret-token",
    fetch: async (url) => {
      calls.push(String(url));
      if (calls.length === 1) {
        return new Response(JSON.stringify({ runtime_id: "runtime-1", learning_session_id: "session-1", status: "OPEN", latest_event_sequence: 1 }), { status: 200 });
      }
      if (calls.length === 2) {
        return new Response(JSON.stringify({
          protocol_version: "studio-protocol-v1", type: "STUDIO_SNAPSHOT", latest_event_sequence: 4,
          snapshot_schema_version: "studio-snapshot-v1", current_scene_id: null, current_scene_version: null,
          active_subject_key: null, active_activity_key: null, active_step_key: null, state_payload: {}, active_scene_contract: null, active_scene_seed: null,
        }), { status: 200 });
      }
      return new Response(null, { status: 200 });
    },
  });

  await controller.open("session-1");
  await controller.snapshot("runtime-1");
  const connection = controller.connect("runtime-1");
  await connection.done;

  assert.equal(controller.latestSequence(), 4);
  assert.match(calls[2] ?? "", /after_sequence=4$/);
});
