import assert from "node:assert/strict";
import test from "node:test";

import { activeSceneRendererState, resolveApprovedStudioRenderer } from "./renderer-host";
import { processSequenceReviewState, readProcessSequenceState } from "./process-sequence";
import { readSentenceOrderingState, sentenceOrderingReviewState } from "./sentence-ordering";

const englishScene = {
  scene_id: "scene-1",
  scene_version: 1,
  subject_key: "ENGLISH",
  subject_profile_version: "subject-profile-v2",
  activity_key: "sentence_ordering_workspace",
  activity_contract_version: "sentence-ordering-workspace-activity-v1",
  renderer_key: "sentence-ordering-workspace",
  renderer_version: "sentence-ordering-workspace-renderer-v1",
  payload_schema_version: "sentence-ordering-workspace-scene-v1",
  locale: "en",
  direction: "ltr" as const,
};

test("the renderer host resolves only the accepted exact English contract", () => {
  assert.equal(resolveApprovedStudioRenderer(englishScene), "ENGLISH_SENTENCE_ORDERING");
});

test("the renderer host resolves the accepted exact Math and Science contracts", () => {
  assert.equal(resolveApprovedStudioRenderer({
    ...englishScene,
    subject_key: "MATH",
    activity_key: "ten_frame_group_transfer",
    activity_contract_version: "ten-frame-group-transfer-activity-v1",
    renderer_key: "ten-frame-group-transfer",
    renderer_version: "ten-frame-group-transfer-renderer-v1",
    payload_schema_version: "ten-frame-group-transfer-scene-v1",
  }), "MATH_MAKE_TEN");
  assert.equal(resolveApprovedStudioRenderer({
    ...englishScene,
    subject_key: "SCIENCE",
    activity_key: "process_sequence_workspace",
    activity_contract_version: "process-sequence-workspace-activity-v1",
    renderer_key: "process-sequence-workspace",
    renderer_version: "process-sequence-workspace-renderer-v1",
    payload_schema_version: "process-sequence-workspace-scene-v1",
  }), "SCIENCE_PROCESS_SEQUENCE");
});

test("the renderer host fails closed when an otherwise familiar activity has a new renderer version", () => {
  assert.equal(
    resolveApprovedStudioRenderer({
      ...englishScene,
      renderer_version: "sentence-ordering-workspace-renderer-v2",
    }),
    null,
  );
});

test("the Science renderer receives its persisted safe stage catalog and current ordering from one active Snapshot", () => {
  const seed = processSequenceReviewState();
  const snapshot = {
    active_scene_contract: {
      ...englishScene,
      subject_key: "SCIENCE",
      activity_key: "process_sequence_workspace",
      activity_contract_version: "process-sequence-workspace-activity-v1",
      renderer_key: "process-sequence-workspace",
      renderer_version: "process-sequence-workspace-renderer-v1",
      payload_schema_version: "process-sequence-workspace-scene-v1",
    },
    active_scene_seed: seed,
    state_payload: {
      process_sequence_workspace: {
        stage_ids: ["prepare-filter-funnel", "allow-water-to-filter", "collect-filtered-water", "pour-sand-water-mixture"],
      },
    },
  };

  assert.deepEqual(readProcessSequenceState(activeSceneRendererState(snapshot)), {
    ...seed,
    stage_ids: snapshot.state_payload.process_sequence_workspace.stage_ids,
  });
});

test("the English renderer receives opaque tokens without any answer ordering from its active Scene seed", () => {
  const seed = sentenceOrderingReviewState();
  const snapshot = {
    active_scene_contract: englishScene,
    active_scene_seed: seed,
    state_payload: {
      sentence_ordering_workspace: { token_ids: ["tok-c820", "tok-a91e", "tok-7f2c", "tok-43bd"] },
    },
  };

  const state = activeSceneRendererState(snapshot);
  assert.deepEqual(readSentenceOrderingState(state), {
    ...seed,
    token_ids: snapshot.state_payload.sentence_ordering_workspace.token_ids,
  });
  assert(!Object.keys(state ?? {}).some((key) => /answer|accepted|valid/i.test(key)));
});

test("the Renderer Host fails closed when its active Scene seed is absent", () => {
  assert.equal(activeSceneRendererState({ active_scene_contract: englishScene, active_scene_seed: null, state_payload: {} }), null);
});
