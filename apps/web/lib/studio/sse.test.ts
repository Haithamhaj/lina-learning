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
