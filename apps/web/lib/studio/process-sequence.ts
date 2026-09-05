import type { StudioOperation } from "./contracts";

export const PROCESS_SEQUENCE_ACTIVITY_KEY = "process_sequence_workspace" as const;
export const REORDER_STAGE_ACTION_KEY = "REORDER_STAGE" as const;
export const SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION" as const;

export type ProcessSequenceStageId =
  | "prepare-filter-funnel"
  | "pour-sand-water-mixture"
  | "allow-water-to-filter"
  | "collect-filtered-water";

export type ProcessSequenceStage = {
  id: ProcessSequenceStageId;
  label_en: string;
  label_ar: string;
};

export type ProcessSequenceState = {
  fixture_key: "sand_water_filtration";
  fixture_version: "sand-water-filtration-fixture-v1";
  stages: ProcessSequenceStage[];
  stage_ids: ProcessSequenceStageId[];
};

type ReorderPayload = {
  stage_id: ProcessSequenceStageId;
  from_index: number;
  to_index: number;
};

type SubmitPayload = {
  stage_ids: ProcessSequenceStageId[];
};

type ProcessSequenceOperationBase = Omit<StudioOperation, "action_key" | "payload">;

export type ReorderStageOperation = ProcessSequenceOperationBase & {
  action_key: typeof REORDER_STAGE_ACTION_KEY;
  payload: ReorderPayload;
};

export type SubmitConfigurationOperation = ProcessSequenceOperationBase & {
  action_key: typeof SUBMIT_CONFIGURATION_ACTION_KEY;
  payload: SubmitPayload;
};

export type ProcessSequenceOperation = ReorderStageOperation | SubmitConfigurationOperation;

// Labels are browser-safe Scene content. The accepted process order remains
// server-owned and is never represented by this renderer model.
const reviewStages: ProcessSequenceStage[] = [
  {
    id: "allow-water-to-filter",
    label_en: "Let the water pass through the filter",
    label_ar: "اترك الماء يمر عبر المرشح",
  },
  {
    id: "collect-filtered-water",
    label_en: "Collect the filtered water",
    label_ar: "اجمع الماء المُرشَّح",
  },
  {
    id: "prepare-filter-funnel",
    label_en: "Set the filter paper in the funnel",
    label_ar: "جهّز القمع وورق الترشيح",
  },
  {
    id: "pour-sand-water-mixture",
    label_en: "Pour the sand-and-water mixture",
    label_ar: "اسكب خليط الرمل والماء",
  },
];

const stageIds = new Set<ProcessSequenceStageId>(reviewStages.map((stage) => stage.id));

export function processSequenceReviewState(): ProcessSequenceState {
  return {
    fixture_key: "sand_water_filtration",
    fixture_version: "sand-water-filtration-fixture-v1",
    stages: reviewStages.map((stage) => ({ ...stage })),
    stage_ids: ["allow-water-to-filter", "prepare-filter-funnel", "collect-filtered-water", "pour-sand-water-mixture"],
  };
}

export function readProcessSequenceState(value: unknown): ProcessSequenceState | null {
  if (!isRecord(value) || value.fixture_key !== "sand_water_filtration" || value.fixture_version !== "sand-water-filtration-fixture-v1") return null;
  if (!Array.isArray(value.stages) || !Array.isArray(value.stage_ids)) return null;
  const stages = value.stages.map(readStage);
  if (stages.some((stage): stage is null => stage === null) || !sameStageCatalog(stages as ProcessSequenceStage[])) return null;
  if (!validStageIds(value.stage_ids)) return null;
  return {
    fixture_key: "sand_water_filtration",
    fixture_version: "sand-water-filtration-fixture-v1",
    stages: stages as ProcessSequenceStage[],
    stage_ids: [...value.stage_ids],
  };
}

export function stageAt(state: ProcessSequenceState, index: number): ProcessSequenceStageId | null {
  return Number.isInteger(index) && index >= 0 && index < state.stage_ids.length ? state.stage_ids[index] : null;
}

export function makeReorderOperation(
  state: ProcessSequenceState,
  sceneId: string,
  sceneVersion: number,
  stageId: string,
  fromIndex: number,
  toIndex: number,
  idempotencyKey: string,
): ReorderStageOperation | null {
  if (
    !sceneId ||
    !Number.isInteger(sceneVersion) ||
    sceneVersion < 0 ||
    !idempotencyKey ||
    !stageIds.has(stageId as ProcessSequenceStageId) ||
    !Number.isInteger(fromIndex) ||
    !Number.isInteger(toIndex) ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= state.stage_ids.length ||
    toIndex >= state.stage_ids.length ||
    fromIndex === toIndex ||
    state.stage_ids[fromIndex] !== stageId
  ) return null;
  return {
    scene_id: sceneId,
    base_scene_version: sceneVersion,
    action_key: REORDER_STAGE_ACTION_KEY,
    payload: { stage_id: stageId as ProcessSequenceStageId, from_index: fromIndex, to_index: toIndex },
    idempotency_key: idempotencyKey,
  };
}

export function makeSubmitOperation(
  state: ProcessSequenceState,
  sceneId: string,
  sceneVersion: number,
  idempotencyKey: string,
): SubmitConfigurationOperation | null {
  if (!sceneId || !Number.isInteger(sceneVersion) || sceneVersion < 0 || !idempotencyKey || !validStageIds(state.stage_ids)) return null;
  return {
    scene_id: sceneId,
    base_scene_version: sceneVersion,
    action_key: SUBMIT_CONFIGURATION_ACTION_KEY,
    payload: { stage_ids: [...state.stage_ids] },
    idempotency_key: idempotencyKey,
  };
}

/** Review-mount-only echo. Production renderers must await Studio authority. */
export function applyMockProcessSequenceOperation(
  state: ProcessSequenceState,
  operation: ProcessSequenceOperation,
): ProcessSequenceState {
  if (operation.action_key !== REORDER_STAGE_ACTION_KEY) return state;
  const { stage_id: stageId, from_index: fromIndex, to_index: toIndex } = operation.payload;
  if (
    state.stage_ids[fromIndex] !== stageId ||
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= state.stage_ids.length ||
    toIndex >= state.stage_ids.length
  ) return state;
  const stageIdsAfter = [...state.stage_ids];
  stageIdsAfter.splice(fromIndex, 1);
  stageIdsAfter.splice(toIndex, 0, stageId);
  return { ...state, stage_ids: stageIdsAfter };
}

function validStageIds(value: unknown[]): value is ProcessSequenceStageId[] {
  return value.length === reviewStages.length && value.every((id): id is ProcessSequenceStageId => typeof id === "string" && stageIds.has(id as ProcessSequenceStageId)) && new Set(value).size === reviewStages.length;
}

function readStage(value: unknown): ProcessSequenceStage | null {
  if (!isRecord(value) || !stageIds.has(value.id as ProcessSequenceStageId) || typeof value.label_en !== "string" || typeof value.label_ar !== "string") return null;
  return { id: value.id as ProcessSequenceStageId, label_en: value.label_en, label_ar: value.label_ar };
}

function sameStageCatalog(stages: ProcessSequenceStage[]): boolean {
  return stages.length === reviewStages.length && stages.every((stage) => {
    const authored = reviewStages.find((candidate) => candidate.id === stage.id);
    return authored?.label_en === stage.label_en && authored.label_ar === stage.label_ar;
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
