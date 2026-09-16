import assert from "node:assert/strict";
import test from "node:test";

import { createStudioController } from "./controller.ts";

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

test("controller retrieves a Custom Visual build through the authenticated Studio boundary", async () => {
  const calls: Array<{ url: string; init: RequestInit | undefined }> = [];
  const controller = createStudioController({
    apiBaseUrl: "https://api.example.test/",
    getToken: async () => "student-token",
    fetch: async (url, init) => {
      calls.push({ url: String(url), init });
      return new Response(JSON.stringify({ source: "window.mount=() => {}", manifest: { interactions: [] } }), { status: 200 });
    },
  });

  const build = await controller.customVisualBuild("scene/id", "build id");

  assert.deepEqual(build, { source: "window.mount=() => {}", manifest: { interactions: [] } });
  assert.equal(calls[0]?.url, "https://api.example.test/v1/student/studio/scenes/scene%2Fid/custom-visual-builds/build%20id");
  assert.equal((calls[0]?.init?.headers as Headers).get("Authorization"), "Bearer student-token");
});

test("controller retains composition identity rather than reducing it to a status flag", async () => {
  const controller = createStudioController({
    apiBaseUrl: "https://api.example.test",
    getToken: async () => "student-token",
    fetch: async () => new Response(JSON.stringify({
      version: "canvas-composition-view-v1",
      observed_at: "2026-09-16T00:00:00Z",
      runtime_id: "runtime-1",
      run_id: "run-1",
      run_created_at: "2026-09-16T00:00:00Z",
      source_message_id: "message-1",
      run_status: "PENDING",
      job_status: "PENDING",
      objective: "Compare decimals.",
      scene_id: null,
      scene_ready: false,
      active_scene_id: null,
      active_scene_version: null,
      deadline_at: null,
      failure_code: null,
    }), { status: 200 }),
  });

  const view = await controller.compositionStatus("runtime-1");

  assert.equal(view.run_status, "PENDING");
  assert.equal(view.run_id, "run-1");
  assert.equal(view.objective, "Compare decimals.");
});

test("controller fails closed when a Custom Visual build is unauthorized or unavailable", async () => {
  for (const status of [401, 403, 500]) {
    const controller = createStudioController({
      apiBaseUrl: "https://api.example.test",
      getToken: async () => "student-token",
      fetch: async () => new Response(null, { status }),
    });

    await assert.rejects(() => controller.customVisualBuild("scene-1", "build-1"), new RegExp(`\\(${status}\\)`));
  }
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
