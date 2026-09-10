import type {
  AgenticCanvasAction,
  AgenticCanvasAccessibility,
  AgenticCanvasBlock,
  AgenticCanvasDiagramEdge,
  AgenticCanvasDiagramNode,
  AgenticCanvasElement,
  AgenticCanvasLogicalPoint,
  AgenticCanvasMathAxis,
  AgenticCanvasMathExpression,
  AgenticCanvasMathMarker,
  AgenticCanvasScene,
  AgenticCanvasSpatialObject,
  AgenticCanvasSpatialRelation,
  AgenticCanvasTextGroup,
  AgenticCanvasTextItem,
  AgenticCanvasTextRelation,
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

const EXACT_NUMBER = /^[+-]?(?:\d+(?:\.\d+)?|\d+\/\d+)$/;

function exactNumber(value: unknown): value is string {
  if (typeof value !== "string" || value.length < 1 || value.length > 40 || !EXACT_NUMBER.test(value)) return false;
  const [numerator, denominator = "1"] = value.split("/");
  return Number.isFinite(Number(numerator)) && Number.isFinite(Number(denominator)) && Number(denominator) !== 0;
}

function rationalValue(value: string): number {
  const [numerator, denominator = "1"] = value.split("/");
  return Number(numerator) / Number(denominator);
}

function parseMathAxis(value: unknown): AgenticCanvasMathAxis | null {
  if (!isRecord(value) || !exactKeys(value, ["axis", "minimum", "maximum", "step"])) return null;
  if (!enumValue(value.axis, ["X", "Y"] as const) || !exactNumber(value.minimum) || !exactNumber(value.maximum)) return null;
  if (value.step !== null && !exactNumber(value.step)) return null;
  if (rationalValue(value.minimum) >= rationalValue(value.maximum)) return null;
  if (value.step !== null && rationalValue(value.step) <= 0) return null;
  return { axis: value.axis, minimum: value.minimum, maximum: value.maximum, step: value.step as string | null };
}

function parseMathMarker(value: unknown): AgenticCanvasMathMarker | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "label", "value", "marker_kind", "draggable"])) return null;
  if (!identifier(value.id) || !safeText(value.label, 1, 120) || !exactNumber(value.value)) return null;
  if (!enumValue(value.marker_kind, ["POINT", "OPEN_ENDPOINT", "CLOSED_ENDPOINT"] as const) || typeof value.draggable !== "boolean") return null;
  return { id: value.id, label: value.label, value: value.value, marker_kind: value.marker_kind, draggable: value.draggable };
}

function parseMathExpression(value: unknown): AgenticCanvasMathExpression | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "label", "latex", "role"])) return null;
  if (!identifier(value.id) || !safeText(value.label, 1, 120) || !safeText(value.latex, 1, 300)) return null;
  if (!enumValue(value.role, ["GIVEN", "DERIVED", "TARGET"] as const)) return null;
  return { id: value.id, label: value.label, latex: value.latex, role: value.role };
}

function parseLogicalPoint(value: unknown): AgenticCanvasLogicalPoint | null {
  if (!isRecord(value) || !exactKeys(value, ["x", "y"]) || !exactNumber(value.x) || !exactNumber(value.y)) return null;
  if ([value.x, value.y].some((coordinate) => rationalValue(coordinate) < 0 || rationalValue(coordinate) > 100)) return null;
  return { x: value.x, y: value.y };
}

function parseSpatialObject(value: unknown): AgenticCanvasSpatialObject | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "label", "object_kind", "position", "draggable"])) return null;
  const position = parseLogicalPoint(value.position);
  if (!identifier(value.id) || !safeText(value.label, 1, 120) || position === null || typeof value.draggable !== "boolean") return null;
  if (!enumValue(value.object_kind, ["POINT", "CIRCLE", "RECTANGLE", "POLYGON", "ARROW", "LABEL"] as const)) return null;
  return { id: value.id, label: value.label, object_kind: value.object_kind, position, draggable: value.draggable };
}

function parseSpatialRelation(value: unknown): AgenticCanvasSpatialRelation | null {
  const relations = ["NEAR", "ABOVE", "BELOW", "LEFT_OF", "RIGHT_OF", "CONTAINS", "CONNECTED_TO", "ACTS_ON", "MOVES_TOWARD", "PART_OF"] as const;
  if (!isRecord(value) || !exactKeys(value, ["source_id", "target_id", "relation", "label"])) return null;
  if (!identifier(value.source_id) || !identifier(value.target_id) || !enumValue(value.relation, relations)) return null;
  if (value.label !== null && !safeText(value.label, 1, 120)) return null;
  return { source_id: value.source_id, target_id: value.target_id, relation: value.relation, label: value.label as string | null };
}

function parseDiagramNode(value: unknown): AgenticCanvasDiagramNode | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "label", "node_kind"])) return null;
  if (!identifier(value.id) || !safeText(value.label, 1, 160) || !enumValue(value.node_kind, ["CONCEPT", "STATE", "PROCESS", "ENTITY", "DECISION", "OUTCOME"] as const)) return null;
  return { id: value.id, label: value.label, node_kind: value.node_kind };
}

function parseDiagramEdge(value: unknown): AgenticCanvasDiagramEdge | null {
  const relations = ["NEXT", "CAUSES", "RETURNS_TO", "PART_OF", "COMPARES", "RELATES_TO", "DEPENDS_ON"] as const;
  if (!isRecord(value) || !exactKeys(value, ["source_id", "target_id", "relation", "label"])) return null;
  if (!identifier(value.source_id) || !identifier(value.target_id) || !enumValue(value.relation, relations)) return null;
  if (value.label !== null && !safeText(value.label, 1, 120)) return null;
  return { source_id: value.source_id, target_id: value.target_id, relation: value.relation, label: value.label as string | null };
}

function parseTextItem(value: unknown): AgenticCanvasTextItem | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "text", "group_id"])) return null;
  if (!identifier(value.id) || !safeText(value.text, 1, 300) || (value.group_id !== null && !identifier(value.group_id))) return null;
  return { id: value.id, text: value.text, group_id: value.group_id as string | null };
}

function parseTextGroup(value: unknown): AgenticCanvasTextGroup | null {
  if (!isRecord(value) || !exactKeys(value, ["id", "label"]) || !identifier(value.id) || !safeText(value.label, 1, 120)) return null;
  return { id: value.id, label: value.label };
}

function parseTextRelation(value: unknown): AgenticCanvasTextRelation | null {
  if (!isRecord(value) || !exactKeys(value, ["source_id", "target_id", "relation"])) return null;
  if (!identifier(value.source_id) || !identifier(value.target_id) || !enumValue(value.relation, ["BEFORE", "MATCHES", "BELONGS_TO", "RELATES_TO"] as const)) return null;
  return { source_id: value.source_id, target_id: value.target_id, relation: value.relation };
}

function parseArray<T>(value: unknown, maximum: number, parser: (item: unknown) => T | null): T[] | null {
  if (!Array.isArray(value) || value.length > maximum) return null;
  const parsed = value.map(parser);
  return parsed.some((item) => item === null) ? null : parsed as T[];
}

function parseBlock(value: unknown): AgenticCanvasBlock | null {
  if (!isRecord(value) || !enumValue(value.type, BLOCK_TYPES)) return null;
  if (value.type === "MATH_BOARD") {
    const common = parseCommonBlock(value, ["board_kind", "axis_min", "axis_max", "axes", "markers", "expressions"]);
    const boardKinds = ["NUMBER_LINE", "CARTESIAN", "PLOT"] as const;
    if (!common || !enumValue(value.board_kind, boardKinds)) return null;
    if (value.axis_min !== null && !exactNumber(value.axis_min)) return null;
    if (value.axis_max !== null && !exactNumber(value.axis_max)) return null;
    const axes = parseArray(value.axes, 2, parseMathAxis);
    const markers = parseArray(value.markers, 24, parseMathMarker);
    const expressions = parseArray(value.expressions, 12, parseMathExpression);
    if (axes === null || markers === null || expressions === null) return null;
    const semanticIds = [...markers, ...expressions].map((item) => item.id);
    if (new Set(axes.map((axis) => axis.axis)).size !== axes.length || new Set(semanticIds).size !== semanticIds.length) return null;
    return { ...common, type: value.type, board_kind: value.board_kind, axis_min: value.axis_min as string | null, axis_max: value.axis_max as string | null, axes, markers, expressions };
  }
  if (value.type === "SCENE_2D") {
    const common = parseCommonBlock(value, ["viewport_width_units", "viewport_height_units", "objects", "relations"]);
    if (!common || value.viewport_width_units !== 100 || value.viewport_height_units !== 100) return null;
    const objects = parseArray(value.objects, 24, parseSpatialObject);
    const relations = parseArray(value.relations, 32, parseSpatialRelation);
    if (objects === null || relations === null) return null;
    const ids = objects.map((item) => item.id);
    const known = new Set(ids);
    if (known.size !== ids.length || relations.some((relation) => !known.has(relation.source_id) || !known.has(relation.target_id))) return null;
    return { ...common, type: value.type, viewport_width_units: 100, viewport_height_units: 100, objects, relations };
  }
  if (value.type === "DIAGRAM") {
    const common = parseCommonBlock(value, ["topology", "layout", "nodes", "edges"]);
    const topologies = ["SEQUENCE", "CYCLE", "FLOW", "CAUSE_EFFECT", "COMPARISON", "HIERARCHY", "SYSTEM", "CONCEPT_MAP"] as const;
    const layouts = ["HORIZONTAL", "VERTICAL", "RADIAL", "TREE", "GRID", "AUTO"] as const;
    if (!common || !enumValue(value.topology, topologies) || !enumValue(value.layout, layouts)) return null;
    const nodes = parseArray(value.nodes, 24, parseDiagramNode);
    const edges = parseArray(value.edges, 36, parseDiagramEdge);
    if (nodes === null || edges === null) return null;
    const ids = nodes.map((node) => node.id);
    const known = new Set(ids);
    if (known.size !== ids.length || edges.some((edge) => !known.has(edge.source_id) || !known.has(edge.target_id))) return null;
    return { ...common, type: value.type, topology: value.topology, layout: value.layout, nodes, edges };
  }
  if (value.type === "TEXT_INTERACTION") {
    const common = parseCommonBlock(value, ["interaction_family", "prompt", "items", "groups", "relations"]);
    const families = ["ORDERING", "MATCHING", "CLASSIFICATION", "GROUPING", "HIGHLIGHT", "ANNOTATION", "RELATION", "TOKEN_MANIPULATION"] as const;
    if (!common || !enumValue(value.interaction_family, families) || !safeText(value.prompt, 1, 300)) return null;
    const items = parseArray(value.items, 24, parseTextItem);
    const groups = parseArray(value.groups, 12, parseTextGroup);
    const relations = parseArray(value.relations, 36, parseTextRelation);
    if (items === null || groups === null || relations === null) return null;
    const itemIds = items.map((item) => item.id);
    const groupIds = groups.map((group) => group.id);
    const knownGroups = new Set(groupIds);
    const known = new Set([...itemIds, ...groupIds]);
    if (known.size !== itemIds.length + groupIds.length || items.some((item) => item.group_id !== null && !knownGroups.has(item.group_id)) || relations.some((relation) => !known.has(relation.source_id) || !known.has(relation.target_id))) return null;
    return { ...common, type: value.type, interaction_family: value.interaction_family, prompt: value.prompt, items, groups, relations };
  }
  if (value.type === "MATH_INPUT") {
    const common = parseCommonBlock(value, ["notation", "prompt", "constraints"]);
    if (!common || value.notation !== "LATEX" || !safeText(value.prompt, 1, 300)) return null;
    if (!Array.isArray(value.constraints) || value.constraints.length > 8 || !value.constraints.every((item) => safeText(item, 1, 200))) return null;
    return { ...common, type: value.type, notation: "LATEX", prompt: value.prompt, constraints: value.constraints as string[] };
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
  payload.version = "agentic-canvas-action-v1";
  payload.action = input.action;
  payload.element_id = input.elementId ?? null;
  payload.from_value = input.fromValue ?? null;
  payload.to_value = input.toValue ?? null;
  return {
    scene_id: input.sceneId,
    base_scene_version: input.sceneVersion,
    action_key: input.action,
    payload,
    idempotency_key: input.idempotencyKey,
  };
}

/** Resolve an operation promise so UI event handlers never leak a rejection. */
export async function settleAgenticCanvasOperation(
  onOperation: (operation: StudioOperation) => Promise<void>,
  operation: StudioOperation,
): Promise<boolean> {
  try {
    await onOperation(operation);
    return true;
  } catch {
    return false;
  }
}
