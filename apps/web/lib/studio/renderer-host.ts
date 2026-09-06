import type { StudioActiveSceneContract } from "./contracts";

export type ApprovedStudioRenderer =
  | "MATH_MAKE_TEN"
  | "SCIENCE_PROCESS_SEQUENCE"
  | "ENGLISH_SENTENCE_ORDERING"
  | "ARABIC_SENTENCE_ORDERING";

type ApprovedContract = Omit<StudioActiveSceneContract, "scene_id" | "scene_version" | "locale" | "direction"> & {
  renderer: ApprovedStudioRenderer;
};

const approvedContracts: readonly ApprovedContract[] = [
  {
    renderer: "MATH_MAKE_TEN",
    subject_key: "MATH",
    subject_profile_version: "subject-profile-v2",
    activity_key: "ten_frame_group_transfer",
    activity_contract_version: "ten-frame-group-transfer-activity-v1",
    renderer_key: "ten-frame-group-transfer",
    renderer_version: "ten-frame-group-transfer-renderer-v1",
    payload_schema_version: "ten-frame-group-transfer-scene-v1",
  },
  {
    renderer: "SCIENCE_PROCESS_SEQUENCE",
    subject_key: "SCIENCE",
    subject_profile_version: "subject-profile-v2",
    activity_key: "process_sequence_workspace",
    activity_contract_version: "process-sequence-workspace-activity-v1",
    renderer_key: "process-sequence-workspace",
    renderer_version: "process-sequence-workspace-renderer-v1",
    payload_schema_version: "process-sequence-workspace-scene-v1",
  },
  {
    renderer: "ENGLISH_SENTENCE_ORDERING",
    subject_key: "ENGLISH",
    subject_profile_version: "subject-profile-v2",
    activity_key: "sentence_ordering_workspace",
    activity_contract_version: "sentence-ordering-workspace-activity-v1",
    renderer_key: "sentence-ordering-workspace",
    renderer_version: "sentence-ordering-workspace-renderer-v1",
    payload_schema_version: "sentence-ordering-workspace-scene-v1",
  },
  {
    renderer: "ARABIC_SENTENCE_ORDERING",
    subject_key: "ARABIC",
    subject_profile_version: "subject-profile-v2",
    activity_key: "arabic_sentence_ordering_workspace",
    activity_contract_version: "arabic-sentence-ordering-workspace-activity-v1",
    renderer_key: "arabic-sentence-ordering-workspace",
    renderer_version: "arabic-sentence-ordering-workspace-renderer-v1",
    payload_schema_version: "arabic-sentence-ordering-workspace-scene-v1",
  },
];

/**
 * The application-owned host recognizes only accepted, exact production
 * contracts. There is intentionally no subject-text heuristic, latest-version
 * fallback, or generic artifact execution path.
 */
export function resolveApprovedStudioRenderer(
  scene: StudioActiveSceneContract,
): ApprovedStudioRenderer | null {
  const match = approvedContracts.find((contract) => (
    contract.subject_key === scene.subject_key
    && contract.subject_profile_version === scene.subject_profile_version
    && contract.activity_key === scene.activity_key
    && contract.activity_contract_version === scene.activity_contract_version
    && contract.renderer_key === scene.renderer_key
    && contract.renderer_version === scene.renderer_version
    && contract.payload_schema_version === scene.payload_schema_version
  ));
  return match?.renderer ?? null;
}

type ActiveSceneSnapshot = {
  active_scene_contract: StudioActiveSceneContract | null;
  active_scene_seed: Record<string, unknown> | null;
  state_payload: Record<string, unknown>;
};

/** Combine one active Scene's persisted safe seed with its server-reduced state. */
export function activeSceneRendererState(snapshot: ActiveSceneSnapshot): Record<string, unknown> | null {
  const scene = snapshot.active_scene_contract;
  const seed = snapshot.active_scene_seed;
  if (scene === null || seed === null) return null;
  const activityState = snapshot.state_payload[scene.activity_key];
  if (!isRecord(activityState)) return { ...seed };
  return { ...seed, ...activityState };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
