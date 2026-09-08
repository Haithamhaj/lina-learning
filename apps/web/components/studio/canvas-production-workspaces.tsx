"use client";

import { useEffect, useState } from "react";
import type { StudioOperation } from "@/lib/studio/contracts";
import { CoordinateConstruction, MathExpressionInput, SpatialPlacement, type GridPoint, type MathInput, type SemanticPlacement } from "@/lib/studio/visual-toolbelt";

type CommonProps = {
  sceneId: string;
  sceneVersion: number;
  seed: Record<string, unknown>;
  state: Record<string, unknown> | null;
  onOperation: (operation: StudioOperation) => Promise<void>;
  onReload: () => void;
};

const action = "rounded-xl border border-[#b7d0c9] bg-[#f0f7f4] px-4 py-2 text-sm font-semibold text-[#234d46] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:opacity-40";

function operation(sceneId: string, sceneVersion: number, action_key: string, payload: Record<string, unknown>): StudioOperation {
  return { scene_id: sceneId, base_scene_version: sceneVersion, action_key, payload, idempotency_key: crypto.randomUUID() };
}

function Failure({ onReload }: Pick<CommonProps, "onReload">) {
  return <section role="alert" className="rounded-2xl bg-rose-50 p-4 text-rose-900"><p>تعذّر فتح نشاط Canvas بأمان. المحادثة ما زالت متاحة.</p><button type="button" className={`${action} mt-3`} onClick={onReload}>أعد تحميل مساحة العمل</button></section>;
}

export function CanvasSpatialWorkspace(props: CommonProps) {
  const objects = Array.isArray(props.seed.objects) ? props.seed.objects : [];
  const targets = Array.isArray(props.seed.targets) ? props.seed.targets : [];
  const object = objects[0] as { semantic_key?: unknown; label?: unknown } | undefined;
  const target = targets[0] as { semantic_key?: unknown; label?: unknown } | undefined;
  const placements = props.state?.placements;
  if (props.seed.pattern !== "SPATIAL_MANIPULATION" || typeof object?.semantic_key !== "string" || typeof object.label !== "string" || typeof target?.semantic_key !== "string" || typeof target.label !== "string" || typeof placements !== "object" || placements === null) return <Failure onReload={props.onReload}/>;
  const value: SemanticPlacement = { objectId: object.semantic_key, targetId: (placements as Record<string, unknown>)[object.semantic_key] === target.semantic_key ? target.semantic_key : null };
  return <SpatialPlacement
    value={value}
    object={{ id: object.semantic_key, label: object.label }}
    target={{ id: target.semantic_key, label: target.label }}
    title={String(props.seed.title)}
    prompt={String(props.seed.prompt)}
    allowReturn={false}
    onSemanticPlacement={(next) => { if (next.targetId) void props.onOperation(operation(props.sceneId, props.sceneVersion, "PLACE_OBJECT", { object_id: next.objectId, target_id: next.targetId })); }}
  />;
}

export function CanvasMathVisualizationWorkspace(props: CommonProps) {
  const pointSeed = props.seed.point as { semantic_key?: unknown; label?: unknown } | undefined;
  const pointState = props.state?.point as { x?: unknown; y?: unknown } | undefined;
  const current = pointState && Number.isInteger(pointState.x) && Number.isInteger(pointState.y) ? { x: pointState.x as number, y: pointState.y as number } : null;
  const [draft, setDraft] = useState<GridPoint>(current ?? { x: 0, y: 0 });
  useEffect(() => { if (current) setDraft(current); }, [props.sceneId, props.sceneVersion, current?.x, current?.y]);
  if (props.seed.pattern !== "MATH_VISUALIZATION" || typeof pointSeed?.semantic_key !== "string" || typeof pointSeed.label !== "string" || current === null) return <Failure onReload={props.onReload}/>;
  const dirty = draft.x !== current.x || draft.y !== current.y;
  return <section className="space-y-3">
    <CoordinateConstruction value={draft} onValueChange={setDraft} title={String(props.seed.title)} prompt={String(props.seed.prompt)} pointLabel={pointSeed.label}/>
    <div className="flex flex-wrap gap-2">
      <button type="button" className={action} disabled={!dirty} onClick={() => void props.onOperation(operation(props.sceneId, props.sceneVersion, "PLACE_POINT", { point_id: pointSeed.semantic_key, x: draft.x, y: draft.y }))}>احفظ موضع النقطة</button>
      <button type="button" className={action} disabled={dirty} onClick={() => void props.onOperation(operation(props.sceneId, props.sceneVersion, "SUBMIT_CONSTRUCTION", { point_id: pointSeed.semantic_key, x: current.x, y: current.y }))}>أرسل البناء إلى المعلّم</button>
    </div>
  </section>;
}

export function CanvasMathInputWorkspace(props: CommonProps) {
  const submitted = props.state?.submitted as { format?: unknown; value?: unknown } | null | undefined;
  const persistedValue = submitted?.format === "latex" && typeof submitted.value === "string"
    ? submitted.value
    : typeof props.seed.initial_latex === "string" ? props.seed.initial_latex : "";
  const [draft, setDraft] = useState(persistedValue);
  useEffect(() => { setDraft(persistedValue); }, [props.sceneId, props.sceneVersion, persistedValue]);
  if (props.seed.pattern !== "MATH_INPUT" || props.seed.expected_form !== "LATEX" || typeof props.seed.expression_max_length !== "number") return <Failure onReload={props.onReload}/>;
  const expressionMaxLength = props.seed.expression_max_length;
  const submit = (value: MathInput) => { if (value.value.length <= expressionMaxLength) void props.onOperation(operation(props.sceneId, props.sceneVersion, "SUBMIT_EXPRESSION", value)); };
  return <MathExpressionInput value={draft} onValueChange={(value) => { if (value.length <= expressionMaxLength) setDraft(value); }} onSubmit={submit} title={String(props.seed.title)} prompt={String(props.seed.prompt)}/>;
}
