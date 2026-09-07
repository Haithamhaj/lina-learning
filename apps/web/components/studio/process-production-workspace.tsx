"use client";

import { ProcessView } from "@/components/studio/visual-explanation/process-view";
import { initialProcessState, readProcessScene, type ProcessViewAction, type ProcessViewState } from "@/components/studio/visual-explanation/process-model";
import type { StudioOperation } from "@/lib/studio/contracts";

function readState(value: Record<string, unknown> | null, scene: NonNullable<ReturnType<typeof readProcessScene>>): ProcessViewState | null {
  if (!value) return initialProcessState();
  const allowed = new Set(["selected_stage_id", "focused_stage_id", "active_explanation_stage_id", "revealed_stage_ids", "highlighted_relation_ids", "tracing_relation_id"]);
  if (Object.keys(value).some((key) => !allowed.has(key))) return null;
  const stageIds = new Set(scene.stages.map((stage) => stage.id)); const relationIds = new Set(scene.relations.map((relation) => relation.id));
  const ids = (key: string, permitted: Set<string>) => Array.isArray(value[key]) && value[key].every((id) => typeof id === "string" && permitted.has(id)) && new Set(value[key] as string[]).size === value[key].length ? value[key] as string[] : null;
  const nullable = (key: string) => value[key] === null || value[key] === undefined ? null : typeof value[key] === "string" && stageIds.has(value[key] as string) ? value[key] as string : null;
  const revealed = ids("revealed_stage_ids", stageIds); const highlighted = ids("highlighted_relation_ids", relationIds);
  if (revealed === null || highlighted === null || ["selected_stage_id", "focused_stage_id", "active_explanation_stage_id"].some((key) => value[key] !== null && value[key] !== undefined && nullable(key) === null)) return null;
  return { selectedId: nullable("selected_stage_id"), focusedStageId: nullable("focused_stage_id"),
    activeExplanationStageId: nullable("active_explanation_stage_id"), revealedIds: revealed,
    highlightedRelationIds: highlighted, highlightedStageIds: nullable("focused_stage_id") ? [nullable("focused_stage_id")!] : [], tracingRelationId: value.tracing_relation_id === null || value.tracing_relation_id === undefined ? null : typeof value.tracing_relation_id === "string" && relationIds.has(value.tracing_relation_id) ? value.tracing_relation_id : null };
}

export function ProcessProductionWorkspace({ sceneId, sceneVersion, seed, state, onOperation }: { sceneId: string; sceneVersion: number; seed: Record<string, unknown>; state: Record<string, unknown> | null; onOperation: (operation: StudioOperation) => Promise<void> }) {
  const scene = readProcessScene(seed); const viewState = scene ? readState(state, scene) : null;
  if (!scene || !viewState) return null;
  const send = (actionKey: string, targetId: string) => onOperation({ scene_id: sceneId, base_scene_version: sceneVersion, action_key: actionKey, payload: { target_id: targetId }, idempotency_key: `process-production:${sceneId}:${sceneVersion}:${actionKey}:${targetId}` });
  const action = (value: ProcessViewAction) => {
    if (value.type === "focus") return send("FOCUS_OBJECT", value.id);
    if (value.type === "reveal") return send("REVEAL_OBJECT_DETAIL", value.id);
    if (value.type === "trace") return send("TRACE_RELATION", value.id);
  };
  return <ProcessView scene={scene} state={viewState} onAction={action} onExplain={(id) => send("REQUEST_EXPLANATION", id)} />;
}
