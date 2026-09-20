import assert from "node:assert/strict";
import test from "node:test";

import { acquireForegroundGate, releaseForegroundGate } from "./daily-foreground-gate";

test("rapid foreground acquisition admits exactly one browser action", () => {
  const gate = { current: false };
  let writes = 0;
  const click = () => {
    if (!acquireForegroundGate(gate)) return;
    writes += 1;
  };
  click();
  click();
  assert.equal(writes, 1);
  releaseForegroundGate(gate);
  assert.equal(acquireForegroundGate(gate), true);
});
