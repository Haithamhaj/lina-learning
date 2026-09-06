import assert from "node:assert/strict";
import test from "node:test";

import { parseStudioFrame } from "./contracts";

test("an accepted but inactive current Scene remains a valid Chat-only Snapshot", () => {
  const frame = parseStudioFrame({
    protocol_version: "studio-protocol-v1",
    type: "STUDIO_SNAPSHOT",
    latest_event_sequence: 1,
    snapshot_schema_version: "studio-snapshot-v1",
    current_scene_id: "accepted-scene",
    current_scene_version: 1,
    active_subject_key: "SCIENCE",
    active_activity_key: "process_sequence_workspace",
    active_step_key: null,
    state_payload: { scene_status: "ACCEPTED" },
    active_scene_contract: null,
    active_scene_seed: null,
  });
  assert.equal(frame.type, "STUDIO_SNAPSHOT");
  if (frame.type === "STUDIO_SNAPSHOT") assert.deepEqual(frame.active_scene_contract, null);
});
