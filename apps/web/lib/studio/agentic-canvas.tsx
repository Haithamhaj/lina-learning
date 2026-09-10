"use client";

import { useEffect, useState } from "react";

import type { AgenticCanvasAction, AgenticCanvasBlock, StudioOperation } from "./contracts";
import { createAgenticCanvasOperation, parseAgenticCanvasScene, settleAgenticCanvasOperation } from "./agentic-canvas-contract";
import {
  CoordinateConstruction,
  isExactGridPoint,
  MathExpressionInput,
  SpatialPlacement,
  type GridPoint,
  type MathInput,
  type SemanticPlacement,
} from "./visual-toolbelt";

type Props = {
  sceneId: string;
  sceneVersion: number;
  seed: Record<string, unknown>;
  onOperation: (operation: StudioOperation) => Promise<void>;
  onReload: () => void;
  loadGeneratedAsset?: (assetId: string) => Promise<Blob>;
};

const actionClass = "rounded-xl border border-[#b7d0c9] bg-[#f0f7f4] px-3 py-2 text-sm font-semibold text-[#234d46] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

function nextOperation(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation">, block: AgenticCanvasBlock, action: AgenticCanvasAction, options: { elementId?: string; fromValue?: string; toValue?: string } = {}) {
  const operation = createAgenticCanvasOperation({
    sceneId: props.sceneId,
    sceneVersion: props.sceneVersion,
    block,
    action,
    ...options,
    idempotencyKey: crypto.randomUUID(),
  });
  void props.onOperation(operation);
}

function Failure({ onReload }: Pick<Props, "onReload">) {
  return <section role="alert" className="rounded-2xl bg-rose-50 p-4 text-rose-900">
    <p>This Canvas scene could not be opened safely. Tutor chat is still available.</p>
    <button type="button" className={`${actionClass} mt-3`} onClick={onReload}>Reload Workspace</button>
  </section>;
}

function BlockFrame({ block, children }: { block: AgenticCanvasBlock; children: React.ReactNode }) {
  return <article aria-label={block.accessibility.aria_label ?? block.accessibility.text_equivalent} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
    {block.title ? <h3 className="font-display text-xl font-semibold text-slate-900" dir="auto">{block.title}</h3> : null}
    <p className="mt-1 text-sm leading-6 text-slate-600" dir="auto">{block.meaning}</p>
    <div className="mt-3">{children}</div>
  </article>;
}

function SemanticButtons(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: AgenticCanvasBlock }) {
  const element = props.block.elements[0];
  const actions = props.block.allowed_actions.filter((action) => action === "FOCUS" || action === "SELECT" || action === "SUBMIT");
  if (actions.length === 0) return null;
  return <div className="mt-3 flex flex-wrap gap-2">{actions.map((action) => <button
    key={action}
    type="button"
    className={actionClass}
    onClick={() => nextOperation(props, props.block, action, element ? { elementId: element.id } : {})}
  >{action === "FOCUS" ? "Focus" : action === "SELECT" ? "Select" : "Submit"}</button>)}</div>;
}

function ElementList({ block }: { block: AgenticCanvasBlock }) {
  if (block.elements.length === 0) return <p className="text-sm text-slate-500">No interactive elements.</p>;
  return <ul className="grid gap-2">{block.elements.map((element) => <li key={element.id} className="rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
    <span dir="auto">{element.label}</span>{element.current_value !== null ? <span dir="auto">: {element.current_value}</span> : null}
  </li>)}</ul>;
}

const rational = (value: string) => {
  const [numerator, denominator = "1"] = value.split("/");
  return Number(numerator) / Number(denominator);
};

function NumberLineSurface({ block }: { block: Extract<AgenticCanvasBlock, { type: "MATH_BOARD" }> }) {
  const axis = block.axes.find((candidate) => candidate.axis === "X");
  if (!axis) return <ElementList block={block}/>;
  const minimum = rational(axis.minimum); const maximum = rational(axis.maximum); const width = 720; const left = 52; const right = 668;
  const point = (value: string) => left + ((rational(value) - minimum) / (maximum - minimum)) * (right - left);
  const step = axis.step === null ? null : rational(axis.step);
  const ticks = step ? Array.from({ length: Math.min(21, Math.floor((maximum - minimum) / step) + 1) }, (_, index) => minimum + index * step) : [minimum, maximum];
  return <svg viewBox="0 0 720 180" className="w-full overflow-visible rounded-xl bg-sky-50" role="img" aria-label={block.accessibility.aria_label ?? block.accessibility.text_equivalent}>
    <defs><marker id={`${block.block_id}-arrow`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#284b63"/></marker></defs>
    <line x1={left} y1="100" x2={right} y2="100" stroke="#284b63" strokeWidth="3" markerEnd={`url(#${block.block_id}-arrow)`}/>
    {ticks.map((tick) => <g key={tick}><line x1={point(String(tick))} y1="93" x2={point(String(tick))} y2="107" stroke="#587087"/><text x={point(String(tick))} y="126" textAnchor="middle" className="fill-slate-600 text-[13px]">{tick}</text></g>)}
    {block.markers.map((marker, index) => <g key={marker.id}><line x1={point(marker.value)} y1="95" x2={point(marker.value)} y2={54 - (index % 2) * 20} stroke="#2563eb" strokeWidth="2"/><circle cx={point(marker.value)} cy="100" r="8" fill={marker.marker_kind === "OPEN_ENDPOINT" ? "white" : "#2563eb"} stroke="#1d4ed8" strokeWidth="3"/><text x={point(marker.value)} y={40 - (index % 2) * 20} textAnchor="middle" className="fill-blue-950 text-[15px] font-semibold" direction="ltr">{marker.label}</text></g>)}
  </svg>;
}

function DiagramSurface({ block }: { block: Extract<AgenticCanvasBlock, { type: "DIAGRAM" }> }) {
  const count = Math.max(block.nodes.length, 1); const width = 720; const height = block.topology === "CYCLE" ? 410 : 260;
  const nodePosition = (index: number) => {
    if (block.topology === "CYCLE" || block.layout === "RADIAL") { const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count; return { x: 360 + Math.cos(angle) * 220, y: 200 + Math.sin(angle) * 130 }; }
    if (block.layout === "VERTICAL" || block.topology === "HIERARCHY") return { x: 360, y: 42 + (index * 170) / Math.max(count - 1, 1) };
    return { x: 70 + (index * 580) / Math.max(count - 1, 1), y: 130 };
  };
  const positions = new Map(block.nodes.map((node, index) => [node.id, nodePosition(index)]));
  return <svg viewBox={`0 0 ${width} ${height}`} className="w-full rounded-xl bg-violet-50" role="img" aria-label={block.accessibility.aria_label ?? block.accessibility.text_equivalent}>
    <defs><marker id={`${block.block_id}-arrow`} markerWidth="9" markerHeight="9" refX="7" refY="3.5" orient="auto"><path d="M0,0 L0,7 L7,3.5 z" fill="#7c3aed"/></marker></defs>
    {block.edges.map((edge, index) => { const source = positions.get(edge.source_id); const target = positions.get(edge.target_id); if (!source || !target) return null; const curved = block.topology === "CYCLE" || edge.relation === "RETURNS_TO"; const midX = (source.x + target.x) / 2; const midY = Math.min(source.y, target.y) - (curved ? 65 : 0); return <g key={`${edge.source_id}-${edge.target_id}-${index}`}><path d={curved ? `M ${source.x} ${source.y} Q ${midX} ${midY} ${target.x} ${target.y}` : `M ${source.x} ${source.y} L ${target.x} ${target.y}`} fill="none" stroke="#7c3aed" strokeWidth="3" markerEnd={`url(#${block.block_id}-arrow)`}/>{edge.label ? <text x={midX} y={midY - 8} textAnchor="middle" className="fill-violet-900 text-[12px]">{edge.label}</text> : null}</g>; })}
    {block.nodes.map((node) => { const position = positions.get(node.id)!; return <g key={node.id}><circle cx={position.x} cy={position.y} r="43" fill="#fff" stroke="#8b5cf6" strokeWidth="3"/><text x={position.x} y={position.y - 4} textAnchor="middle" className="fill-slate-900 text-[14px] font-semibold">{node.label}</text><text x={position.x} y={position.y + 16} textAnchor="middle" className="fill-violet-700 text-[10px]">{node.node_kind}</text></g>; })}
  </svg>;
}

function SpatialSurface({ block }: { block: Extract<AgenticCanvasBlock, { type: "SCENE_2D" }> }) {
  const point = (position: { x: string; y: string }) => ({ x: rational(position.x) * 6.6 + 30, y: rational(position.y) * 3.4 + 20 });
  const positions = new Map(block.objects.map((object) => [object.id, point(object.position)]));
  return <svg viewBox="0 0 720 390" className="w-full rounded-xl bg-sky-50" role="img" aria-label={block.accessibility.aria_label ?? block.accessibility.text_equivalent}>
    <defs><marker id={`${block.block_id}-arrow`} markerWidth="9" markerHeight="9" refX="7" refY="3.5" orient="auto"><path d="M0,0 L0,7 L7,3.5 z" fill="#0284c7"/></marker></defs>
    {block.relations.map((relation, index) => { const source = positions.get(relation.source_id); const target = positions.get(relation.target_id); return source && target ? <g key={`${relation.source_id}-${relation.target_id}-${index}`}><line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#0284c7" strokeWidth="2" markerEnd={`url(#${block.block_id}-arrow)`}/>{relation.label ? <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 8} textAnchor="middle" className="fill-sky-900 text-[12px]">{relation.label}</text> : null}</g> : null; })}
    {block.objects.map((object) => { const position = positions.get(object.id)!; const isCircle = object.object_kind === "CIRCLE" || object.object_kind === "POINT"; return <g key={object.id}>{isCircle ? <circle cx={position.x} cy={position.y} r={object.object_kind === "POINT" ? 8 : 28} fill="#bae6fd" stroke="#0369a1" strokeWidth="3"/> : <rect x={position.x - 38} y={position.y - 22} width="76" height="44" rx="10" fill="#e0f2fe" stroke="#0369a1" strokeWidth="3"/>}<text x={position.x} y={position.y + 5} textAnchor="middle" className="fill-slate-900 text-[13px] font-semibold">{object.label}</text></g>; })}
  </svg>;
}

function Scene2DBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "SCENE_2D" }> }) {
  const [object, target] = props.block.elements;
  const interactive = object && target && props.block.allowed_actions.includes("MOVE");
  if (!interactive) return <BlockFrame block={props.block}>
    <SpatialSurface block={props.block}/>
    <SemanticButtons {...props}/>
  </BlockFrame>;
  const value: SemanticPlacement = { objectId: object.id, targetId: object.current_value === target.id ? target.id : null };
  return <SpatialPlacement
    value={value}
    object={{ id: object.id, label: object.label }}
    target={{ id: target.id, label: target.label }}
    title={props.block.title ?? "Explore the spatial relation"}
    prompt={props.block.meaning}
    onSemanticPlacement={(next) => nextOperation(props, props.block, "MOVE", {
      elementId: object.id,
      fromValue: object.current_value ?? "",
      toValue: next.targetId ?? "",
    })}
  />;
}

function parseGridPoint(value: string | null): GridPoint | null {
  if (value === null) return null;
  const match = /^\s*\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?\s*$/.exec(value);
  if (!match) return null;
  const point = { x: Number(match[1]), y: Number(match[2]) };
  return isExactGridPoint(point) ? point : null;
}

function CartesianMathBoard(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "MATH_BOARD" }> }) {
  const element = props.block.elements[0];
  const persisted = parseGridPoint(element?.current_value ?? null);
  const [draft, setDraft] = useState<GridPoint>(persisted ?? { x: 0, y: 0 });
  useEffect(() => { if (persisted) setDraft(persisted); }, [persisted?.x, persisted?.y]);
  if (!element || !persisted || !props.block.allowed_actions.includes("MOVE")) {
    return <BlockFrame block={props.block}><ElementList block={props.block}/><SemanticButtons {...props}/></BlockFrame>;
  }
  return <section className="space-y-3">
    <CoordinateConstruction value={draft} onValueChange={setDraft} title={props.block.title ?? "Explore coordinates"} prompt={props.block.meaning} pointLabel={element.label}/>
    {draft.x !== persisted.x || draft.y !== persisted.y ? <button type="button" className={actionClass} onClick={() => nextOperation(props, props.block, "MOVE", {
      elementId: element.id,
      fromValue: `(${persisted.x},${persisted.y})`,
      toValue: `(${draft.x},${draft.y})`,
    })}>Save point</button> : null}
  </section>;
}

function MathBoardBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "MATH_BOARD" }> }) {
  if (props.block.board_kind === "CARTESIAN") return <CartesianMathBoard {...props}/>;
  return <BlockFrame block={props.block}>
    <NumberLineSurface block={props.block}/>
    {props.block.expressions.length ? <div className="mt-3 space-y-2">{props.block.expressions.map((expression) => <p key={expression.id} className="rounded-xl bg-emerald-50 px-3 py-2 text-sm" dir="auto">{expression.label}: <span dir="ltr">{expression.latex}</span></p>)}</div> : null}
    <SemanticButtons {...props}/>
  </BlockFrame>;
}

function MathInputBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "MATH_INPUT" }> }) {
  const element = props.block.elements[0];
  const persisted = element?.current_value ?? "";
  const [draft, setDraft] = useState(persisted);
  useEffect(() => setDraft(persisted), [persisted]);
  if (!element) return <BlockFrame block={props.block}><ElementList block={props.block}/><SemanticButtons {...props}/></BlockFrame>;
  const action = props.block.allowed_actions.includes("SUBMIT") ? "SUBMIT" : props.block.allowed_actions.includes("SET_VALUE") ? "SET_VALUE" : null;
  return <MathExpressionInput
    value={draft}
    onValueChange={setDraft}
    onSubmit={action ? (value: MathInput) => nextOperation(props, props.block, action, { elementId: element.id, fromValue: persisted, toValue: value.value }) : undefined}
    title={props.block.title ?? element.label}
    prompt={props.block.prompt}
  />;
}

function DiagramBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "DIAGRAM" }> }) {
  return <BlockFrame block={props.block}>
    <DiagramSurface block={props.block}/>
    <SemanticButtons {...props}/>
  </BlockFrame>;
}

function TextInteractionBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "TEXT_INTERACTION" }> }) {
  return <BlockFrame block={props.block}>
    <p className="mb-3 text-sm font-medium text-slate-700" dir="auto">{props.block.prompt}</p>
    <div className={props.block.interaction_family === "MATCHING" || props.block.interaction_family === "RELATION" ? "grid gap-3 sm:grid-cols-2" : props.block.interaction_family === "ORDERING" ? "flex flex-wrap gap-2 border-l-4 border-amber-400 pl-3" : "grid gap-3 sm:grid-cols-2"}>
      {props.block.groups.map((group) => <section key={group.id} className="rounded-xl border-2 border-dashed border-amber-300 bg-amber-50 p-3"><p className="text-xs font-bold uppercase text-amber-800" dir="auto">{group.label}</p>{props.block.items.filter((item) => item.group_id === group.id).map((item) => <p key={item.id} className="mt-2 rounded-lg bg-white px-3 py-2 text-sm" dir="auto">{item.text}</p>)}</section>)}
      {props.block.items.filter((item) => item.group_id === null).map((item, index) => <div key={item.id} className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm shadow-sm" dir="auto"><span className="mr-2 text-xs font-bold text-amber-700">{props.block.interaction_family === "ORDERING" ? index + 1 : ""}</span>{item.text}</div>)}
    </div>
    <SemanticButtons {...props}/>
  </BlockFrame>;
}

function GeneratedImage({ block, loadGeneratedAsset }: { block: Extract<AgenticCanvasBlock, { type: "IMAGE" }>; loadGeneratedAsset?: Props["loadGeneratedAsset"] }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    let localUrl: string | null = null;
    setObjectUrl(null);
    setFailed(false);
    if (!loadGeneratedAsset) return () => { active = false; };
    void loadGeneratedAsset(block.studio_generated_asset_id).then((blob) => {
      if (!active) return;
      localUrl = URL.createObjectURL(blob);
      setObjectUrl(localUrl);
    }).catch(() => { if (active) setFailed(true); });
    return () => {
      active = false;
      if (localUrl) URL.revokeObjectURL(localUrl);
    };
  }, [block.studio_generated_asset_id, loadGeneratedAsset]);
  if (objectUrl) return <img src={objectUrl} alt={block.accessibility.text_equivalent} className="max-h-[32rem] max-w-full rounded-xl object-contain"/>;
  return <div role="status" className="grid min-h-40 place-items-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-sm leading-6 text-slate-600">
    {failed ? "Generated visual unavailable. Tutor chat is still available." : "Loading generated visual…"}
  </div>;
}

function DeclarativeBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation" | "loadGeneratedAsset"> & { block: AgenticCanvasBlock }) {
  if (props.block.type === "SCENE_2D") return <Scene2DBlock {...props} block={props.block}/>;
  if (props.block.type === "MATH_BOARD") return <MathBoardBlock {...props} block={props.block}/>;
  if (props.block.type === "MATH_INPUT") return <MathInputBlock {...props} block={props.block}/>;
  if (props.block.type === "DIAGRAM") return <DiagramBlock {...props} block={props.block}/>;
  if (props.block.type === "TEXT_INTERACTION") return <TextInteractionBlock {...props} block={props.block}/>;
  if (props.block.type === "IMAGE") return <BlockFrame block={props.block}>
    <GeneratedImage block={props.block} loadGeneratedAsset={props.loadGeneratedAsset}/>
    <SemanticButtons {...props}/>
  </BlockFrame>;
  return <BlockFrame block={props.block}><ElementList block={props.block}/><SemanticButtons {...props}/></BlockFrame>;
}

/** Exact allowlisted renderer for one server-owned Agentic Canvas Scene. */
export function AgenticCanvasWorkspace(props: Props) {
  const scene = parseAgenticCanvasScene(props.seed);
  const [operationFailed, setOperationFailed] = useState(false);
  if (scene === null) return <Failure onReload={props.onReload}/>;
  const safeOperation = async (operation: StudioOperation) => {
    const accepted = await settleAgenticCanvasOperation(props.onOperation, operation);
    setOperationFailed(!accepted);
  };
  const placements = new Map(scene.presentation?.placements.map((placement) => [placement.block_id, placement]) ?? []);
  const orderedBlocks = [...scene.blocks].sort((left, right) => (placements.get(left.block_id)?.order ?? 0) - (placements.get(right.block_id)?.order ?? 0));
  const layout = scene.presentation?.layout ?? "STACK";
  const palette = scene.presentation?.palette ?? "AUTO";
  const layoutClass = layout === "GRID" || layout === "SPLIT" ? "grid gap-3 md:grid-cols-2" : "space-y-3";
  const paletteClass = palette === "NATURE" ? "bg-emerald-50" : palette === "WARM" ? "bg-amber-50" : palette === "COOL" ? "bg-sky-50" : "bg-[#f2f7ff]";
  return <section aria-label="Learning canvas" className="space-y-3">
    <header className={`rounded-2xl px-4 py-3 ${paletteClass}`}>
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#496a8b]">Canvas</p>
      <h2 className="mt-1 font-display text-xl text-slate-900" dir="auto">{scene.objective}</h2>
    </header>
    {operationFailed ? <p role="alert" className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-900">That Canvas action was not saved. The current Studio state has been restored, and Tutor chat remains available.</p> : null}
    <div className={layoutClass}>{orderedBlocks.map((block) => <div key={block.block_id} className={placements.get(block.block_id)?.span === "FULL" || placements.get(block.block_id)?.role === "PRIMARY" ? "md:col-span-2" : undefined}><DeclarativeBlock {...props} onOperation={safeOperation} block={block}/></div>)}</div>
  </section>;
}
