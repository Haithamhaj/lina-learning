import type { StudioOperation } from "./contracts";

export const MAKE_TEN_ACTIVITY_KEY = "ten_frame_group_transfer" as const;
export const TRANSFER_ITEM_ACTION_KEY = "TRANSFER_ITEM" as const;
export const SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION" as const;

export type MakeTenGroupId = "ten-frame" | "ones-group";

export type MakeTenGroup = {
  id: MakeTenGroupId;
  item_ids: string[];
};

export type MakeTenState = {
  groups: Record<MakeTenGroupId, MakeTenGroup>;
  total_count: 15;
};

export type MakeTenActionKey =
  | typeof TRANSFER_ITEM_ACTION_KEY
  | typeof SUBMIT_CONFIGURATION_ACTION_KEY;

export type MakeTenOperation = StudioOperation & {
  action_key: MakeTenActionKey;
};

const tenFrameIds = Array.from({ length: 9 }, (_, index) => `ten-frame-${String(index + 1).padStart(2, "0")}`);
const onesGroupIds = Array.from({ length: 6 }, (_, index) => `ones-group-${String(index + 1).padStart(2, "0")}`);
const stableItemIds = new Set([...tenFrameIds, ...onesGroupIds]);

export function makeTenReviewState(): MakeTenState {
  return {
    groups: {
      "ten-frame": { id: "ten-frame", item_ids: [...tenFrameIds] },
      "ones-group": { id: "ones-group", item_ids: [...onesGroupIds] },
    },
    total_count: 15,
  };
}

export function readMakeTenState(value: unknown): MakeTenState | null {
  if (!isRecord(value) || !isRecord(value.groups) || value.total_count !== 15) return null;
  const tenFrame = readGroup(value.groups["ten-frame"], "ten-frame");
  const onesGroup = readGroup(value.groups["ones-group"], "ones-group");
  if (!tenFrame || !onesGroup) return null;
  const itemIds = [...tenFrame.item_ids, ...onesGroup.item_ids];
  if (itemIds.length !== 15 || new Set(itemIds).size !== 15 || itemIds.some((itemId) => !stableItemIds.has(itemId))) return null;
  return { groups: { "ten-frame": tenFrame, "ones-group": onesGroup }, total_count: 15 };
}

export function groupForItem(state: MakeTenState, itemId: string): MakeTenGroupId | null {
  if (state.groups["ten-frame"].item_ids.includes(itemId)) return "ten-frame";
  if (state.groups["ones-group"].item_ids.includes(itemId)) return "ones-group";
  return null;
}

export function otherGroup(groupId: MakeTenGroupId): MakeTenGroupId {
  return groupId === "ten-frame" ? "ones-group" : "ten-frame";
}

export function makeTransferOperation(
  state: MakeTenState,
  sceneId: string,
  sceneVersion: number,
  itemId: string,
  idempotencyKey: string,
): MakeTenOperation | null {
  const fromGroupId = groupForItem(state, itemId);
  if (!fromGroupId || !sceneId || !Number.isInteger(sceneVersion) || sceneVersion < 0 || !idempotencyKey) return null;
  return {
    scene_id: sceneId,
    base_scene_version: sceneVersion,
    action_key: TRANSFER_ITEM_ACTION_KEY,
    payload: { item_id: itemId, from_group_id: fromGroupId, to_group_id: otherGroup(fromGroupId) },
    idempotency_key: idempotencyKey,
  };
}

export function makeSubmitOperation(
  state: MakeTenState,
  sceneId: string,
  sceneVersion: number,
  idempotencyKey: string,
): MakeTenOperation | null {
  if (!sceneId || !Number.isInteger(sceneVersion) || sceneVersion < 0 || !idempotencyKey) return null;
  return {
    scene_id: sceneId,
    base_scene_version: sceneVersion,
    action_key: SUBMIT_CONFIGURATION_ACTION_KEY,
    payload: {
      ten_frame_item_ids: [...state.groups["ten-frame"].item_ids],
      ones_group_item_ids: [...state.groups["ones-group"].item_ids],
    },
    idempotency_key: idempotencyKey,
  };
}

/** Review-mount-only state echo. Production callers must wait for Studio Snapshot/feed authority. */
export function applyMockMakeTenOperation(state: MakeTenState, operation: MakeTenOperation): MakeTenState {
  if (operation.action_key !== TRANSFER_ITEM_ACTION_KEY) return state;
  const itemId = operation.payload.item_id;
  const fromGroupId = operation.payload.from_group_id;
  const toGroupId = operation.payload.to_group_id;
  if (
    typeof itemId !== "string" ||
    (fromGroupId !== "ten-frame" && fromGroupId !== "ones-group") ||
    (toGroupId !== "ten-frame" && toGroupId !== "ones-group") ||
    fromGroupId === toGroupId ||
    !state.groups[fromGroupId].item_ids.includes(itemId)
  ) return state;
  return {
    total_count: 15,
    groups: {
      ...state.groups,
      [fromGroupId]: { id: fromGroupId, item_ids: state.groups[fromGroupId].item_ids.filter((id) => id !== itemId) },
      [toGroupId]: { id: toGroupId, item_ids: [...state.groups[toGroupId].item_ids, itemId] },
    },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readGroup(value: unknown, id: MakeTenGroupId): MakeTenGroup | null {
  if (!isRecord(value) || value.id !== id || !Array.isArray(value.item_ids) || !value.item_ids.every((item) => typeof item === "string")) return null;
  return { id, item_ids: [...value.item_ids] };
}
