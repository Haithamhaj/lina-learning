import type { AgenticCanvasDiagramNode, AgenticCanvasPresentation, AgenticCanvasSpatialObject } from "./contracts";

type Point = { x: number; y: number };

export function mathSurfaceKind(kind: "NUMBER_LINE" | "CARTESIAN" | "PLOT") {
  return kind === "NUMBER_LINE" ? "number-line" : kind === "CARTESIAN" ? "cartesian" : "plot";
}

export function spatialPrimitive(kind: AgenticCanvasSpatialObject["object_kind"]) {
  return kind === "POINT" || kind === "CIRCLE" ? "circle" : kind === "RECTANGLE" ? "rectangle" : kind.toLowerCase();
}

export function presentationLayout(
  layout: AgenticCanvasPresentation["layout"],
  role: AgenticCanvasPresentation["placements"][number]["role"],
  span: AgenticCanvasPresentation["placements"][number]["span"],
) {
  const wide = span === "FULL" || span === "WIDE";
  if (layout === "FOCUS") return { container: "space-y-4", region: role === "PRIMARY" ? "focus" : "support-row", className: role === "PRIMARY" || wide ? "w-full" : "sm:flex-1" };
  if (layout === "FOCUS_SUPPORT") return { container: "grid gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(15rem,0.75fr)]", region: role === "PRIMARY" ? "focus" : "support-rail", className: role === "PRIMARY" ? "lg:row-span-2" : "" };
  if (layout === "SPLIT") return { container: "grid gap-4 md:grid-cols-2", region: role === "PRIMARY" ? "split-primary" : "split-secondary", className: wide ? "md:col-span-2" : "" };
  if (layout === "GRID") return { container: "grid gap-4 sm:grid-cols-2 xl:grid-cols-3", region: "grid", className: wide ? "sm:col-span-2 xl:col-span-3" : "" };
  if (layout === "OVERLAY") return { container: "relative grid gap-3 lg:block", region: role === "PRIMARY" ? "overlay-base" : "overlay-support", className: role === "PRIMARY" ? "lg:pr-[15rem]" : "lg:absolute lg:right-3 lg:top-3 lg:w-60" };
  return { container: "space-y-4", region: "stack", className: wide ? "w-full" : "" };
}

export function diagramPositions(topology: "SEQUENCE" | "CYCLE" | "FLOW" | "CAUSE_EFFECT" | "COMPARISON" | "HIERARCHY" | "SYSTEM" | "CONCEPT_MAP", count: number): Point[] {
  const safeCount = Math.max(count, 1);
  const horizontal = (index: number) => ({ x: 80 + (index * 560) / Math.max(safeCount - 1, 1), y: 145 });
  if (topology === "CYCLE") return Array.from({ length: safeCount }, (_, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / safeCount;
    return { x: 360 + Math.cos(angle) * 210, y: 205 + Math.sin(angle) * 125 };
  });
  if (topology === "CAUSE_EFFECT") return Array.from({ length: safeCount }, (_, index) => ({ x: index < Math.ceil(safeCount / 2) ? 180 : 540, y: 72 + ((index % Math.ceil(safeCount / 2)) * 145) / Math.max(Math.ceil(safeCount / 2) - 1, 1) }));
  if (topology === "COMPARISON") return Array.from({ length: safeCount }, (_, index) => ({ x: index % 2 === 0 ? 190 : 530, y: 65 + (Math.floor(index / 2) * 165) / Math.max(Math.ceil(safeCount / 2) - 1, 1) }));
  if (topology === "HIERARCHY") return Array.from({ length: safeCount }, (_, index) => index === 0 ? ({ x: 360, y: 52 }) : ({ x: 100 + ((index - 1) * 520) / Math.max(safeCount - 2, 1), y: 230 }));
  if (topology === "SYSTEM") return Array.from({ length: safeCount }, (_, index) => index === 0 ? ({ x: 360, y: 150 }) : ({ x: 360 + Math.cos((Math.PI * 2 * (index - 1)) / Math.max(safeCount - 1, 1)) * 220, y: 150 + Math.sin((Math.PI * 2 * (index - 1)) / Math.max(safeCount - 1, 1)) * 95 }));
  if (topology === "CONCEPT_MAP") return Array.from({ length: safeCount }, (_, index) => index === 0 ? ({ x: 360, y: 150 }) : ({ x: 130 + ((index - 1) % 3) * 230, y: index <= 3 ? 65 : 245 }));
  if (topology === "FLOW") return Array.from({ length: safeCount }, (_, index) => ({ x: 80 + (index * 560) / Math.max(safeCount - 1, 1), y: index % 2 === 0 ? 105 : 205 }));
  return Array.from({ length: safeCount }, (_, index) => horizontal(index));
}

export function diagramHeight(topology: Parameters<typeof diagramPositions>[0]) {
  return topology === "CYCLE" || topology === "SYSTEM" ? 410 : topology === "HIERARCHY" || topology === "CONCEPT_MAP" ? 330 : 290;
}

export function diagramNodeShape(node: AgenticCanvasDiagramNode["node_kind"]) {
  return node === "DECISION" ? "diamond" : node === "OUTCOME" ? "rounded" : "circle";
}
