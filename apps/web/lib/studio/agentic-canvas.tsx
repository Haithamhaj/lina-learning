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

function Scene2DBlock(props: Pick<Props, "sceneId" | "sceneVersion" | "onOperation"> & { block: Extract<AgenticCanvasBlock, { type: "SCENE_2D" }> }) {
  const [object, target] = props.block.elements;
  const interactive = object && target && props.block.allowed_actions.includes("MOVE");
  if (!interactive) return <BlockFrame block={props.block}><ElementList block={props.block}/><SemanticButtons {...props}/></BlockFrame>;
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
  return <BlockFrame block={props.block}><ElementList block={props.block}/><SemanticButtons {...props}/></BlockFrame>;
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
    prompt={props.block.meaning}
  />;
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
  return <section aria-label="Learning canvas" className="space-y-3">
    <header className="rounded-2xl bg-[#f2f7ff] px-4 py-3">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#496a8b]">Canvas</p>
      <h2 className="mt-1 font-display text-xl text-slate-900" dir="auto">{scene.objective}</h2>
    </header>
    {operationFailed ? <p role="alert" className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-900">That Canvas action was not saved. The current Studio state has been restored, and Tutor chat remains available.</p> : null}
    {scene.blocks.map((block) => <DeclarativeBlock key={block.block_id} {...props} onOperation={safeOperation} block={block}/>)}
  </section>;
}
