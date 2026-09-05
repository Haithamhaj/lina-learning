import assert from "node:assert/strict";
import test from "node:test";

import {
  SUBMIT_CONFIGURATION_ACTION_KEY,
  TRANSFER_ITEM_ACTION_KEY,
  applyMockMakeTenOperation,
  makeSubmitOperation,
  makeTenReviewState,
  makeTransferOperation,
  readMakeTenState,
} from "./make-ten";

test("Make-Ten renderer model emits typed transfer and submit operations", () => {
  const initial = makeTenReviewState();
  const transfer = makeTransferOperation(initial, "scene-1", 2, "ones-group-01", "transfer-key");
  assert.equal(transfer?.action_key, TRANSFER_ITEM_ACTION_KEY);
  assert.deepEqual(transfer?.payload, {
    item_id: "ones-group-01",
    from_group_id: "ones-group",
    to_group_id: "ten-frame",
  });

  const moved = applyMockMakeTenOperation(initial, transfer!);
  assert.equal(moved.groups["ten-frame"].item_ids.length, 10);
  assert.equal(moved.groups["ones-group"].item_ids.length, 5);
  const submit = makeSubmitOperation(moved, "scene-1", 3, "submit-key");
  assert.equal(submit?.action_key, SUBMIT_CONFIGURATION_ACTION_KEY);
  assert.equal((submit?.payload.ten_frame_item_ids as string[]).length, 10);
  assert.equal((submit?.payload.ones_group_item_ids as string[]).length, 5);
});

test("Make-Ten renderer refuses malformed authoritative state or an unknown item", () => {
  const initial = makeTenReviewState();
  assert.equal(readMakeTenState({ groups: {}, total_count: 15 }), null);
  assert.equal(makeTransferOperation(initial, "scene-1", 2, "unknown-item", "key"), null);
  assert.equal(readMakeTenState(initial)?.groups["ten-frame"].item_ids.length, 9);
});
