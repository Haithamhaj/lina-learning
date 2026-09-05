import assert from "node:assert/strict";
import test from "node:test";

import {
  REORDER_TOKEN_ACTION_KEY,
  SUBMIT_CONFIGURATION_ACTION_KEY,
  applyMockSentenceOrderingOperation,
  makeReorderOperation,
  makeSubmitOperation,
  readSentenceOrderingState,
  sentenceOrderingReviewState,
} from "./sentence-ordering";

const birds = "tok-c820";
const fly = "tok-43bd";
const over = "tok-7f2c";
const clouds = "tok-a91e";
const canonicalOrder = [birds, fly, over, clouds];

test("Sentence-ordering renderer model emits exact typed reorder and submit operations", () => {
  const initial = sentenceOrderingReviewState();
  const reorder = makeReorderOperation(initial, "scene-1", 2, birds, 1, 0, "reorder-key");
  assert.equal(reorder?.action_key, REORDER_TOKEN_ACTION_KEY);
  assert.deepEqual(reorder?.payload, { token_id: birds, from_index: 1, to_index: 0 });
  const moved = applyMockSentenceOrderingOperation(initial, reorder!);
  assert.deepEqual(moved.token_ids, [birds, clouds, over, fly]);
  const submit = makeSubmitOperation(moved, "scene-1", 3, "submit-key");
  assert.equal(submit?.action_key, SUBMIT_CONFIGURATION_ACTION_KEY);
  assert.deepEqual(submit?.payload, { token_ids: moved.token_ids });
});

test("Sentence-ordering renderer model keeps durable identities separate from visible labels", () => {
  const initial = sentenceOrderingReviewState();
  const duplicatedVisibleText = {
    ...initial,
    tokens: initial.tokens.map((token) => token.id === birds || token.id === fly ? { ...token, text: "the" } : token),
  };
  const parsed = readSentenceOrderingState(duplicatedVisibleText);
  assert(parsed);
  assert.deepEqual(parsed.tokens.filter((token) => token.id === birds || token.id === fly).sort((left, right) => left.id.localeCompare(right.id)), [
    { id: fly, text: "the" },
    { id: birds, text: "the" },
  ]);
  const reorder = makeReorderOperation(parsed, "scene-1", 2, fly, 3, 0, "separate-durable-id");
  assert.deepEqual(reorder?.payload, { token_id: fly, from_index: 3, to_index: 0 });
});

test("Sentence-ordering renderer model exposes no answer ordering through its token data", () => {
  const state = sentenceOrderingReviewState();
  const catalogIds = state.tokens.map((token) => token.id);
  assert.notDeepEqual(catalogIds, canonicalOrder);
  assert.notDeepEqual([...catalogIds].sort(), canonicalOrder);
  assert.notDeepEqual(state.token_ids, canonicalOrder);
  assert(state.tokens.every((token) => /^tok-[0-9a-f]{4}$/.test(token.id) && !token.id.includes(token.text.toLowerCase())));
  assert(!Object.keys(state).some((key) => /answer|accepted|valid/i.test(key)));
});

test("Sentence-ordering renderer model refuses malformed state and mismatched reorders", () => {
  const initial = sentenceOrderingReviewState();
  assert.equal(readSentenceOrderingState({ fixture_key: "english_sentence_ordering_fixture_slate", tokens: [], token_ids: [] }), null);
  assert.equal(makeReorderOperation(initial, "scene-1", 2, "unknown-token", 0, 1, "bad-token"), null);
  assert.equal(makeReorderOperation(initial, "scene-1", 2, birds, 0, 1, "wrong-source"), null);
});
