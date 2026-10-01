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

function safeOrderingSeed(block: TextBlock): AgenticCanvasTextItem[] {
  const ordered = [...block.items].sort((left, right) => left.id.localeCompare(right.id));
  if (ordered.length < 2) return ordered;
  const position = new Map(ordered.map((item, index) => [item.id, index]));
  const accidentallySolved = block.relations
    .filter((relation) => relation.relation === "BEFORE")
    .every((relation) => {
      const left = position.get(relation.source_id);
      const right = position.get(relation.target_id);
      return left !== undefined && right !== undefined && left < right;
    });
  return accidentallySolved ? [...ordered.slice(1), ordered[0]] : ordered;
}

export function orderingPresentation(block: TextBlock): {
  items: AgenticCanvasTextItem[];
  move: (itemId: string, direction: "UP" | "DOWN") => string | null;
} {
  const seed = safeOrderingSeed(block);
  const seedRank = new Map(seed.map((item, index) => [item.id, index * 1024]));
  const elementState = new Map(block.elements.map((element) => [element.id, element.current_value]));
  const rank = new Map(seed.map((item) => {
    const persisted = elementState.get(item.id);
    const parsed = persisted === null || persisted === undefined ? Number.NaN : Number(persisted);
    return [item.id, Number.isFinite(parsed) ? parsed : seedRank.get(item.id)!] as const;
  }));
  const items = [...seed].sort((left, right) => {
    const delta = rank.get(left.id)! - rank.get(right.id)!;
    return delta || seedRank.get(left.id)! - seedRank.get(right.id)!;
  });
  const move = (itemId: string, direction: "UP" | "DOWN"): string | null => {
    const index = items.findIndex((item) => item.id === itemId);
    if (index < 0) return null;
    if (direction === "UP") {
      if (index === 0) return null;
      const previous = rank.get(items[index - 1].id)!;
      const beforePrevious = index > 1 ? rank.get(items[index - 2].id)! : previous - 1024;
      return String((beforePrevious + previous) / 2);
    }
    if (index === items.length - 1) return null;
    const next = rank.get(items[index + 1].id)!;
    const afterNext = index + 2 < items.length ? rank.get(items[index + 2].id)! : next + 1024;
    return String((next + afterNext) / 2);
  };
  return { items, move };
}

export function textInteractionPresentation(block: TextBlock): {
  groups: Array<{ id: string; label: string; items: AgenticCanvasTextItem[] }>;
  unassigned: AgenticCanvasTextItem[];
} {
  const elementState = new Map(block.elements.map((element) => [element.id, element.current_value]));
  const groupIds = new Set(block.groups.map((group) => group.id));
  const groups = block.groups.map((group) => ({
    ...group,
    items: block.items.filter((item) => elementState.get(item.id) === group.id),
  }));
  const unassigned = block.items.filter((item) => !groupIds.has(elementState.get(item.id) ?? ""));
  return { groups, unassigned };
}
