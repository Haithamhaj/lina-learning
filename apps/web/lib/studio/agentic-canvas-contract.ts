import type {
  AgenticCanvasAction,
  AgenticCanvasAccessibility,
  AgenticCanvasBlock,
  AgenticCanvasElement,
  AgenticCanvasScene,
  StudioOperation,
} from "./contracts";

const ACTIONS = ["FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT"] as const;
const BLOCK_TYPES = ["MATH_BOARD", "SCENE_2D", "DIAGRAM", "TEXT_INTERACTION", "MATH_INPUT", "IMAGE"] as const;
const COMMON_BLOCK_KEYS = ["block_id", "type", "meaning", "title", "accessibility", "allowed_actions", "elements"] as const;

const isRecord = (value: unknown): value is Record<string, unknown> => (
  typeof value === "object" && value !== null && !Array.isArray(value)
);

const exactKeys = (value: Record<string, unknown>, keys: readonly string[]) => (
  Object.keys(value).length === keys.length
  && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key))
);

const enumValue = <T extends readonly string[]>(value: unknown, choices: T): value is T[number] => (
  typeof value === "string" && choices.includes(value as T[number])
);

const safeText = (value: unknown, minLength: number, maxLength: number): value is string => {
  if (typeof value !== "string" || value.length < minLength || value.length > maxLength) return false;
  if (/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) return false;
  if (/(?:https?|javascript|data|blob|file):/i.test(value) || /;base64,/i.test(value)) return false;
  if (/(?:^|\s)[A-Za-z0-9+/]{80,}={0,2}(?:\s|$)/.test(value)) return false;
  if (/<\s*\/?\s*(?:script|iframe|object|embed|style)\b/i.test(value)) return false;
  if (/\bon[a-z]+\s*=|\b(?:eval|fetch|require)\s*\(|\bnew\s+Function\s*\(|\bimport\s*\(|\b(?:window|document)\s*\./i.test(value)) return false;
  return true;
};

const identifier = (value: unknown): value is string => safeText(value, 1, 64) && /^[a-z][a-z0-9_-]*$/.test(value);

function parseAccessibility(value: unknown): AgenticCanvasAccessibility | null {
  if (!isRecord(value) || !exactKeys(value, ["text_equivalent", "aria_label"])) return null;
  if (!safeText(value.text_equivalent, 1, 600)) return null;
  if (value.aria_label !== null && !safeText(value.aria_label, 1, 160)) return null;
  return { text_equivalent: value.text_equivalent, aria_label: value.aria_label as string | null };
}

function parseElement(value: unknown): AgenticCanvasElement | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "label", "current_value"])) return null;
  if (!identifier(value.id) || !safeText(value.label, 1, 160)) return null;
  if (value.current_value !== null && !safeText(value.current_value, 0, 240)) return null;
  return { id: value.id, label: value.label, current_value: value.current_value };
}

function parseCommonBlock(value: Record<string, unknown>, subtypeKeys: readonly string[]): {
  block_id: string;
  meaning: string;
  title: string | null;
  accessibility: AgenticCanvasAccessibility;
  allowed_actions: AgenticCanvasAction[];
  elements: AgenticCanvasElement[];
} | null {
  if (!exactKeys(value, [...COMMON_BLOCK_KEYS, ...subtypeKeys])) return null;
  if (!identifier(value.block_id) || !safeText(value.meaning, 1, 500)) return null;
  if (value.title !== null && !safeText(value.title, 1, 120)) return null;
  const accessibility = parseAccessibility(value.accessibility);
  if (accessibility === null || !Array.isArray(value.allowed_actions) || value.allowed_actions.length > 6) return null;
  if (!value.allowed_actions.every((action) => enumValue(action, ACTIONS)) || new Set(value.allowed_actions).size !== value.allowed_actions.length) return null;
  if (!Array.isArray(value.elements) || value.elements.length > 32) return null;
  const elements = value.elements.map(parseElement);
  if (elements.some((element) => element === null)) return null;
  const acceptedElements = elements as AgenticCanvasElement[];
  if (new Set(acceptedElements.map((element) => element.id)).size !== acceptedElements.length) return null;
  return {
    block_id: value.block_id,
    meaning: value.meaning,
    title: value.title as string | null,
    accessibility,
    allowed_actions: value.allowed_actions as AgenticCanvasAction[],
    elements: acceptedElements,
  };
}

function parseBlock(value: unknown): AgenticCanvasBlock | null {
  if (!isRecord(value) || !enumValue(value.type, BLOCK_TYPES)) return null;
  if (value.type === "MATH_BOARD") {
    const common = parseCommonBlock(value, ["board_kind", "axis_min", "axis_max"]);
    const boardKinds = ["NUMBER_LINE", "CARTESIAN", "PLOT"] as const;
    if (!common || !enumValue(value.board_kind, boardKinds)) return null;
    if (value.axis_min !== null && !safeText(value.axis_min, 1, 80)) return null;
    if (value.axis_max !== null && !safeText(value.axis_max, 1, 80)) return null;
    return { ...common, type: value.type, board_kind: value.board_kind, axis_min: value.axis_min as string | null, axis_max: value.axis_max as string | null };
  }
  if (value.type === "SCENE_2D") {
    const common = parseCommonBlock(value, ["viewport_width_units", "viewport_height_units"]);
    if (!common || value.viewport_width_units !== 100 || value.viewport_height_units !== 100) return null;
    return { ...common, type: value.type, viewport_width_units: 100, viewport_height_units: 100 };
  }
  if (value.type === "DIAGRAM") {
    const common = parseCommonBlock(value, ["topology", "layout"]);
    const topologies = ["SEQUENCE", "CYCLE", "FLOW", "CAUSE_EFFECT", "COMPARISON", "HIERARCHY", "SYSTEM", "CONCEPT_MAP"] as const;
    const layouts = ["HORIZONTAL", "VERTICAL", "RADIAL", "TREE", "GRID", "AUTO"] as const;
    if (!common || !enumValue(value.topology, topologies) || !enumValue(value.layout, layouts)) return null;
    return { ...common, type: value.type, topology: value.topology, layout: value.layout };
  }
  if (value.type === "TEXT_INTERACTION") {
    const common = parseCommonBlock(value, ["interaction_family"]);
    const families = ["ORDERING", "MATCHING", "CLASSIFICATION", "GROUPING", "HIGHLIGHT", "ANNOTATION", "RELATION", "TOKEN_MANIPULATION"] as const;
    if (!common || !enumValue(value.interaction_family, families)) return null;
    return { ...common, type: value.type, interaction_family: value.interaction_family };
  }
  if (value.type === "MATH_INPUT") {
    const common = parseCommonBlock(value, ["notation"]);
    if (!common || value.notation !== "LATEX") return null;
    return { ...common, type: value.type, notation: "LATEX" };
  }
  const common = parseCommonBlock(value, ["studio_generated_asset_id"]);
  if (!common || !safeText(value.studio_generated_asset_id, 1, 64)) return null;
  return { ...common, type: value.type, studio_generated_asset_id: value.studio_generated_asset_id };
}

/** Fail-closed browser admission for the exact server-owned Scene schema. */
export function parseAgenticCanvasScene(value: unknown): AgenticCanvasScene | null {
  if (!isRecord(value) || !exactKeys(value, ["version", "objective", "subject_key", "blocks"])) return null;
  if (value.version !== "agentic-canvas-scene-v1" || !safeText(value.objective, 1, 500) || !safeText(value.subject_key, 1, 64)) return null;
  if (!Array.isArray(value.blocks) || value.blocks.length < 1 || value.blocks.length > 12) return null;
  const blocks = value.blocks.map(parseBlock);
  if (blocks.some((block) => block === null)) return null;
  const acceptedBlocks = blocks as AgenticCanvasBlock[];
  if (new Set(acceptedBlocks.map((block) => block.block_id)).size !== acceptedBlocks.length) return null;
  return { version: value.version, objective: value.objective, subject_key: value.subject_key, blocks: acceptedBlocks };
}

type OperationInput = {
  sceneId: string;
  sceneVersion: number;
  block: AgenticCanvasBlock;
  action: AgenticCanvasAction;
  elementId?: string;
  fromValue?: string;
  toValue?: string;
  idempotencyKey: string;
};

/** Build only the finite semantic action vocabulary accepted by Studio. */
export function createAgenticCanvasOperation(input: OperationInput): StudioOperation {
  if (!input.block.allowed_actions.includes(input.action)) throw new Error(`Action ${input.action} is not allowed for this block.`);
  if (input.elementId !== undefined && !input.block.elements.some((element) => element.id === input.elementId)) throw new Error("Action references an unknown element.");
  if (!safeText(input.sceneId, 1, 128) || !Number.isInteger(input.sceneVersion) || input.sceneVersion < 0 || !safeText(input.idempotencyKey, 1, 200)) {
    throw new Error("Invalid Studio operation identity.");
  }
  if (input.fromValue !== undefined && !safeText(input.fromValue, 0, 240)) throw new Error("Invalid semantic from-value.");
  if (input.toValue !== undefined && !safeText(input.toValue, 0, 240)) throw new Error("Invalid semantic to-value.");
  const payload: Record<string, unknown> = { block_id: input.block.block_id };
  if (input.elementId !== undefined) payload.element_id = input.elementId;
  if (input.fromValue !== undefined) payload.from_value = input.fromValue;
  if (input.toValue !== undefined) payload.to_value = input.toValue;
  return {
    scene_id: input.sceneId,
    base_scene_version: input.sceneVersion,
    action_key: input.action,
    payload,
    idempotency_key: input.idempotencyKey,
  };
}
