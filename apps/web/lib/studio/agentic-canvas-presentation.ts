import type { AgenticCanvasBlock, AgenticCanvasTextItem } from "./contracts";

type PlotBounds = { minimumX: number; maximumX: number; minimumY: number; maximumY: number };
type PlotPoint = { x: number; y: number };

export type ClippedLinearExpression = {
  id: string;
  slope: number;
  intercept: number;
  start: PlotPoint;
  end: PlotPoint;
};

function parseLinearExpression(latex: string): { slope: number; intercept: number } | null {
  const normalized = latex.replace(/[\s{}]/g, "").replace(/−/g, "-");
  if (normalized.length > 48 || !/^[yY]=[xX0-9.+-]+$/.test(normalized)) return null;
  const right = normalized.slice(2).toLowerCase();
  const linear = /^([+-]?(?:\d+(?:\.\d+)?)?)x(?:([+-]\d+(?:\.\d+)?))?$/.exec(right);
  if (linear) {
    const coefficient = linear[1] === "" || linear[1] === "+" ? 1 : linear[1] === "-" ? -1 : Number(linear[1]);
    const intercept = linear[2] === undefined ? 0 : Number(linear[2]);
    return Number.isFinite(coefficient) && Number.isFinite(intercept) ? { slope: coefficient, intercept } : null;
  }
  if (!/^[+-]?\d+(?:\.\d+)?$/.test(right)) return null;
  const intercept = Number(right);
  return Number.isFinite(intercept) ? { slope: 0, intercept } : null;
}

export function clippedLinearExpression(id: string, latex: string, bounds: PlotBounds): ClippedLinearExpression | null {
  const parsed = parseLinearExpression(latex);
  if (!parsed || !(bounds.minimumX < bounds.maximumX) || !(bounds.minimumY < bounds.maximumY)) return null;
  const { slope, intercept } = parsed;
  const epsilon = 1e-9;
  const inside = (point: PlotPoint) => point.x >= bounds.minimumX - epsilon && point.x <= bounds.maximumX + epsilon && point.y >= bounds.minimumY - epsilon && point.y <= bounds.maximumY + epsilon;
  const candidates: PlotPoint[] = [
    { x: bounds.minimumX, y: slope * bounds.minimumX + intercept },
    { x: bounds.maximumX, y: slope * bounds.maximumX + intercept },
  ];
  if (slope !== 0) {
    candidates.push({ x: (bounds.minimumY - intercept) / slope, y: bounds.minimumY });
    candidates.push({ x: (bounds.maximumY - intercept) / slope, y: bounds.maximumY });
  }
  const points = candidates.filter(inside).filter((point, index, all) => all.findIndex((other) => Math.abs(other.x - point.x) < epsilon && Math.abs(other.y - point.y) < epsilon) === index);
  if (points.length < 2) return null;
  let start = points[0]; let end = points[1]; let distance = -1;
  for (let left = 0; left < points.length; left += 1) for (let right = left + 1; right < points.length; right += 1) {
    const next = (points[left].x - points[right].x) ** 2 + (points[left].y - points[right].y) ** 2;
    if (next > distance) { distance = next; start = points[left]; end = points[right]; }
  }
  return { id, slope, intercept, start, end };
}

type TextBlock = Extract<AgenticCanvasBlock, { type: "TEXT_INTERACTION" }>;

export function textInteractionPresentation(block: TextBlock): {
  groups: Array<{ id: string; label: string; items: AgenticCanvasTextItem[] }>;
  unassigned: AgenticCanvasTextItem[];
} {
  // The v1 reducer has no durable list-position contract for generic ORDERING.
  // Fail closed: do not expose the authored solution order as learner state.
  if (block.interaction_family === "ORDERING") return { groups: [], unassigned: [] };
  const elementState = new Map(block.elements.map((element) => [element.id, element.current_value]));
  const groupIds = new Set(block.groups.map((group) => group.id));
  const groups = block.groups.map((group) => ({
    ...group,
    items: block.items.filter((item) => elementState.get(item.id) === group.id),
  }));
  const unassigned = block.items.filter((item) => !groupIds.has(elementState.get(item.id) ?? ""));
  return { groups, unassigned };
}
