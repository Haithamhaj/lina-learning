import assert from "node:assert/strict";
import test from "node:test";

import { activeSceneRendererState } from "./renderer-host";
import { readArabicSentenceOrderingState, makeArabicReorderOperation, makeArabicSubmitOperation } from "./arabic-sentence-ordering";

const exactSeed = {
  fixture_key: "arabic_sentence_ordering_fixture_orchid",
  fixture_version: "arabic-sentence-ordering-fixture-orchid-v1",
  token_schema_version: "arabic-sentence-ordering-token-v1",
  tokens: [
    { id: "tok-2b7e", text: "الدرسَ" },
    { id: "tok-6d3a", text: "تكتبُ" },
    { id: "tok-f18c", text: "الطالبةُ" },
  ],
  token_ids: ["tok-f18c", "tok-2b7e", "tok-6d3a"],
};

test("Arabic reader rejects an extra duplicate catalog entry and changed visible text", () => {
  assert.equal(readArabicSentenceOrderingState({ ...exactSeed, tokens: [...exactSeed.tokens, exactSeed.tokens[0]] }), null);
  assert.equal(readArabicSentenceOrderingState({ ...exactSeed, tokens: exactSeed.tokens.map((token) => token.id === "tok-6d3a" ? { ...token, text: "بديل" } : token) }), null);
});

test("Arabic reader rejects repeated IDs at exact length and undeclared token fields", () => {
  assert.equal(readArabicSentenceOrderingState({ ...exactSeed, tokens: [exactSeed.tokens[0], exactSeed.tokens[0], exactSeed.tokens[2]] }), null);
  assert.equal(readArabicSentenceOrderingState({ ...exactSeed, tokens: exactSeed.tokens.map(token => ({ ...token, answer: true })) }), null);
});

test("Arabic host reader accepts exact safe seed with any structurally valid current order", () => {
  const state = activeSceneRendererState({
    active_scene_contract: { scene_id: "scene-ar", scene_version: 2, subject_key: "ARABIC", subject_profile_version: "subject-profile-v2", activity_key: "arabic_sentence_ordering_workspace", activity_contract_version: "arabic-sentence-ordering-workspace-activity-v1", renderer_key: "arabic-sentence-ordering-workspace", renderer_version: "arabic-sentence-ordering-workspace-renderer-v1", payload_schema_version: "arabic-sentence-ordering-workspace-scene-v1", locale: "ar", direction: "rtl" as const },
    active_scene_seed: exactSeed,
    state_payload: { arabic_sentence_ordering_workspace: { token_ids: ["tok-2b7e", "tok-f18c", "tok-6d3a"] } },
  });
  assert.deepEqual(readArabicSentenceOrderingState(state), { ...exactSeed, token_ids: ["tok-2b7e", "tok-f18c", "tok-6d3a"] });
});

test("Arabic reader validates versions, exact fields, permutations and reduced submission state", () => {
  assert(readArabicSentenceOrderingState(exactSeed));
  for (const key of ["fixture_key", "fixture_version", "token_schema_version"]) assert.equal(readArabicSentenceOrderingState({...exactSeed,[key]:"unsupported"}),null);
  for (const token_ids of [[],["tok-6d3a"],["tok-6d3a","tok-6d3a","tok-f18c"],["unknown","tok-f18c","tok-2b7e"],[...exactSeed.token_ids,"extra"]]) assert.equal(readArabicSentenceOrderingState({...exactSeed,token_ids}),null);
  assert.equal(readArabicSentenceOrderingState({...exactSeed,extra:true}),null);
  assert.equal(readArabicSentenceOrderingState({...exactSeed,last_submission:{token_ids:[],extra:true}}),null);
  for(const token_ids of [["tok-6d3a","tok-f18c","tok-2b7e"],["tok-6d3a","tok-2b7e","tok-f18c"],["tok-2b7e","tok-6d3a","tok-f18c"]]) assert(readArabicSentenceOrderingState({...exactSeed,token_ids,last_submission:{token_ids:exactSeed.token_ids}}));
});

test("Arabic operation builders preserve source IDs and reject invalid destinations without mutation", () => {
  const state = readArabicSentenceOrderingState(exactSeed)!;
  const before=JSON.stringify(state);
  assert.deepEqual(makeArabicReorderOperation(state,"scene",2,"tok-6d3a",2,0,"move")?.payload,{token_id:"tok-6d3a",from_index:2,to_index:0});
  for(const destination of [-1,3,2,0.5]) assert.equal(makeArabicReorderOperation(state,"scene",2,"tok-6d3a",2,destination,"move"),null);
  assert.equal(makeArabicReorderOperation(state,"scene",2,"tok-6d3a",0,1,"move"),null);
  assert.deepEqual(makeArabicSubmitOperation(state,"scene",2,"submit")?.payload,{token_ids:state.token_ids});
  assert.equal(JSON.stringify(state),before);
});
