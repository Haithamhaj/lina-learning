import assert from "node:assert/strict";
import test from "node:test";

import {
  REORDER_STAGE_ACTION_KEY,
  SUBMIT_CONFIGURATION_ACTION_KEY,
  applyMockProcessSequenceOperation,
  makeReorderOperation,
  makeSubmitOperation,
  processSequenceReviewState,
  readProcessSequenceState,
} from "./process-sequence";

test("Process-sequence renderer model emits exact typed reorder and submit operations", () => {
  const initial = processSequenceReviewState();
  const reorder = makeReorderOperation(initial, "scene-1", 2, "prepare-filter-funnel", 1, 0, "reorder-key");
  assert.equal(reorder?.action_key, REORDER_STAGE_ACTION_KEY);
  assert.deepEqual(reorder?.payload, { stage_id: "prepare-filter-funnel", from_index: 1, to_index: 0 });
  const moved = applyMockProcessSequenceOperation(initial, reorder!);
  assert.deepEqual(moved.stage_ids, [
    "prepare-filter-funnel",
    "allow-water-to-filter",
    "collect-filtered-water",
    "pour-sand-water-mixture",
  ]);
  const submit = makeSubmitOperation(moved, "scene-1", 3, "submit-key");
  assert.equal(submit?.action_key, SUBMIT_CONFIGURATION_ACTION_KEY);
  assert.deepEqual(submit?.payload, { stage_ids: moved.stage_ids });
});

test("Process-sequence renderer model refuses malformed state and mismatched reorders", () => {
  const initial = processSequenceReviewState();
  assert.equal(readProcessSequenceState({ fixture_key: "sand_water_filtration", stages: [], stage_ids: [] }), null);
  assert.equal(makeReorderOperation(initial, "scene-1", 2, "unknown-stage", 0, 1, "bad-stage"), null);
  assert.equal(makeReorderOperation(initial, "scene-1", 2, "prepare-filter-funnel", 0, 1, "wrong-source"), null);
});
