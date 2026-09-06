import assert from "node:assert/strict";
import test from "node:test";

import { StudioSseParser } from "./sse";

test("StudioSseParser preserves event ids across fragmented protocol frames", () => {
  const parser = new StudioSseParser();
  const first = parser.push('id: 4\nevent: STUDIO_EVENT_COMMITTED\ndata: {"protocol_version":"studio-protocol-v1",');
  const second = parser.push('"type":"STUDIO_EVENT_COMMITTED","sequence":4,"event":{"sequence":4,"event_kind":"fixture.event"}}\n\n');

  assert.deepEqual(first, []);
  assert.equal(second.length, 1);
  assert.equal(second[0]?.id, 4);
  assert.equal(second[0]?.frame.type, "STUDIO_EVENT_COMMITTED");
});

test("StudioSseParser accepts the bounded safe server error frame", () => {
  const parser = new StudioSseParser();
  const frames = parser.push('event: STUDIO_ERROR\ndata: {"protocol_version":"studio-protocol-v1","type":"STUDIO_ERROR","code":"STUDIO_FEED_UNAVAILABLE"}\n\n');

  assert.equal(frames[0]?.frame.type, "STUDIO_ERROR");
});

test("StudioSseParser accepts only an exact active Scene descriptor", () => {
  const parser = new StudioSseParser();
  const frames = parser.push('event: STUDIO_SNAPSHOT\ndata: {"protocol_version":"studio-protocol-v1","type":"STUDIO_SNAPSHOT","latest_event_sequence":4,"snapshot_schema_version":"studio-snapshot-v1","current_scene_id":"scene-1","current_scene_version":3,"active_subject_key":"ENGLISH","active_activity_key":"sentence_ordering_workspace","active_step_key":null,"state_payload":{},"active_scene_contract":{"scene_id":"scene-1","scene_version":3,"subject_key":"ENGLISH","subject_profile_version":"subject-profile-v2","activity_key":"sentence_ordering_workspace","activity_contract_version":"sentence-ordering-workspace-activity-v1","renderer_key":"sentence-ordering-workspace","renderer_version":"sentence-ordering-workspace-renderer-v1","payload_schema_version":"sentence-ordering-workspace-scene-v1","locale":"en","direction":"ltr"},"active_scene_seed":{}}\n\n');

  assert.equal(frames[0]?.frame.type, "STUDIO_SNAPSHOT");
});

test("StudioSseParser rejects a snapshot whose descriptor differs from active Scene identity", () => {
  const parser = new StudioSseParser();

  assert.throws(() => parser.push('event: STUDIO_SNAPSHOT\ndata: {"protocol_version":"studio-protocol-v1","type":"STUDIO_SNAPSHOT","latest_event_sequence":4,"snapshot_schema_version":"studio-snapshot-v1","current_scene_id":"scene-1","current_scene_version":3,"active_subject_key":"ENGLISH","active_activity_key":"sentence_ordering_workspace","active_step_key":null,"state_payload":{},"active_scene_contract":{"scene_id":"other-scene","scene_version":3,"subject_key":"ENGLISH","subject_profile_version":"subject-profile-v2","activity_key":"sentence_ordering_workspace","activity_contract_version":"sentence-ordering-workspace-activity-v1","renderer_key":"sentence-ordering-workspace","renderer_version":"sentence-ordering-workspace-renderer-v1","payload_schema_version":"sentence-ordering-workspace-scene-v1","locale":"en","direction":"ltr"},"active_scene_seed":{}}\n\n'));
});
