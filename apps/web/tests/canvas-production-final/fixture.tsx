import React, { StrictMode, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import Konva from "konva";
import JXG from "jsxgraph";

import { StudioRendererHost } from "../../components/daily-student/studio-renderer-host";
import type { StudioOperation, StudioSnapshotFrame } from "../../lib/studio/contracts";

type Pattern = "PROCESS" | "SPATIAL_MANIPULATION" | "MATH_VISUALIZATION" | "MATH_INPUT";

const definitions: Record<Pattern, {
  subject: string; profile: string; activity: string; activityVersion: string;
  renderer: string; rendererVersion: string; seedVersion: string;
  seed: Record<string, unknown>; state: Record<string, unknown>;
}> = {
  PROCESS: {
    subject: "SCIENCE", profile: "process-visual-production-profile-v1", activity: "process_visual_production",
    activityVersion: "process-visual-production-activity-v1", renderer: "process-visual-production",
    rendererVersion: "process-visual-production-renderer-v1", seedVersion: "process-visual-production-seed-v1",
    seed: { title: "دورة الماء · The water cycle", subtitle: "تتبّع حركة الماء بين الأرض والسماء.", locale: "ar", topology: "cycle", sourceLabel: "Tutor-approved Process explanation", sourceUrl: "https://lina.local/process", motion_intents: ["REVEAL_IN_ORDER", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"], stages: [
      { id: "evaporation", label: "التبخر", detail: "تسخّن الشمس الماء فيتحول إلى بخار.", art: "drop" },
      { id: "condensation", label: "التكاثف", detail: "يبرد البخار ويتجمع في قطرات صغيرة.", art: "filter" },
      { id: "collection", label: "التجمع", detail: "يعود الماء ويتجمع على سطح الأرض.", art: "vessel" },
    ], relations: [
      { id: "evaporation-to-condensation", from: "evaporation", to: "condensation", label: "يبرد" },
      { id: "condensation-to-collection", from: "condensation", to: "collection", label: "يهطل" },
      { id: "collection-to-evaporation", from: "collection", to: "evaporation", label: "تسخّنه الشمس من جديد" },
    ] },
    state: { selected_stage_id: null, focused_stage_id: null, active_explanation_stage_id: null, revealed_stage_ids: [], highlighted_relation_ids: [], tracing_relation_id: null },
  },
  SPATIAL_MANIPULATION: {
    subject: "MATH", profile: "canvas-production-profile-v1", activity: "canvas_spatial_manipulation",
    activityVersion: "canvas-spatial-activity-v1", renderer: "canvas-spatial-placement",
    rendererVersion: "canvas-spatial-placement-renderer-v1", seedVersion: "canvas-spatial-scene-v1",
    seed: { pattern: "SPATIAL_MANIPULATION", title: "صنّف الكسر · Classify the fraction", prompt: "ضع ٣⁄٤ داخل مجموعة الكسور الأصغر من واحد.", text_equivalent: "Three quarters is less than one.", locale: "ar", direction: "rtl", objects: [{ semantic_key: "three-quarters", label: "٣⁄٤" }], targets: [{ semantic_key: "less-than-one", label: "أصغر من ١", relation: "INSIDE" }], initial_placements: [{ object_semantic_key: "three-quarters", target_semantic_key: null }] },
    state: { status: "IN_PROGRESS", placements: { "three-quarters": null } },
  },
  MATH_VISUALIZATION: {
    subject: "MATH", profile: "canvas-production-profile-v1", activity: "canvas_math_visualization",
    activityVersion: "canvas-math-visualization-activity-v1", renderer: "canvas-coordinate-construction",
    rendererVersion: "canvas-coordinate-construction-renderer-v1", seedVersion: "canvas-math-visualization-scene-v1",
    seed: { pattern: "MATH_VISUALIZATION", title: "حدّد النقطة A · Plot point A", prompt: "حرّك A إلى الإحداثيين (-3, 5)، ثم احفظ وأرسل.", text_equivalent: "Point A belongs at (-3, 5).", locale: "ar", direction: "rtl", point: { semantic_key: "point-a", label: "A", initial_x: 0, initial_y: 0 }, target: { x: -3, y: 5 }, x_range: { minimum: -10, maximum: 10 }, y_range: { minimum: -10, maximum: 10 } },
    state: { status: "IN_PROGRESS", point: { x: 0, y: 0 }, submitted: null },
  },
  MATH_INPUT: {
    subject: "MATH", profile: "canvas-production-profile-v1", activity: "canvas_math_input",
    activityVersion: "canvas-math-input-activity-v1", renderer: "canvas-math-expression-input",
    rendererVersion: "canvas-math-expression-input-renderer-v1", seedVersion: "canvas-math-input-scene-v1",
    seed: { pattern: "MATH_INPUT", title: "اكتب جمع كسرين · Write a fraction sum", prompt: "اكتب ثلاثة أرباع زائد ربع، ثم أرسل التعبير.", text_equivalent: "Enter three quarters plus one quarter.", locale: "ar", direction: "rtl", initial_latex: "", expected_form: "LATEX", expression_max_length: 120 },
    state: { status: "IN_PROGRESS", submitted: null },
  },
};

function snapshot(pattern: Pattern, version = 1, state = definitions[pattern].state): StudioSnapshotFrame {
  const value = definitions[pattern];
  const sceneId = `production-${pattern.toLowerCase()}`;
  return { protocol_version: "studio-protocol-v1", type: "STUDIO_SNAPSHOT", latest_event_sequence: version - 1,
    snapshot_schema_version: "studio-snapshot-v1", current_scene_id: sceneId, current_scene_version: version,
    active_subject_key: value.subject, active_activity_key: value.activity, active_step_key: null,
    state_payload: { [value.activity]: state }, active_scene_seed: value.seed,
    active_scene_contract: { scene_id: sceneId, scene_version: version, subject_key: value.subject,
      subject_profile_version: value.profile, activity_key: value.activity, activity_contract_version: value.activityVersion,
      renderer_key: value.renderer, renderer_version: value.rendererVersion, payload_schema_version: value.seedVersion,
      locale: "ar", direction: "rtl" },
  };
}

function App() {
  const [pattern, setPattern] = useState<Pattern>("PROCESS");
  const [snapshots, setSnapshots] = useState<Record<Pattern, StudioSnapshotFrame>>(() => Object.fromEntries((Object.keys(definitions) as Pattern[]).map(key => [key, snapshot(key)])) as Record<Pattern, StudioSnapshotFrame>);
  const [hostKey, setHostKey] = useState(0);
  const [operations, setOperations] = useState<Record<Pattern, StudioOperation[]>>({ PROCESS: [], SPATIAL_MANIPULATION: [], MATH_VISUALIZATION: [], MATH_INPUT: [] });
  const [continuations, setContinuations] = useState<Record<Pattern, string>>({ PROCESS: "", SPATIAL_MANIPULATION: "", MATH_VISUALIZATION: "", MATH_INPUT: "" });
  const current = snapshots[pattern];
  const labels: Record<Pattern, string> = { PROCESS: "العملية", SPATIAL_MANIPULATION: "المكان", MATH_VISUALIZATION: "الإحداثيات", MATH_INPUT: "التعبير" };
  const tutorActions = new Set(["REQUEST_EXPLANATION", "PLACE_OBJECT", "SUBMIT_CONSTRUCTION", "SUBMIT_EXPRESSION"]);

  const onOperation = async (operation: StudioOperation) => {
    setOperations(previous => ({ ...previous, [pattern]: [...previous[pattern], operation] }));
    setSnapshots(previous => {
      const prior = previous[pattern];
      const activity = definitions[pattern].activity;
      const state = structuredClone(prior.state_payload[activity]) as Record<string, any>;
      if (pattern === "PROCESS") {
        const target = operation.payload.target_id as string;
        if (["FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL"].includes(operation.action_key)) {
          state.selected_stage_id = target; state.focused_stage_id = target; state.active_explanation_stage_id = target;
          if (!state.revealed_stage_ids.includes(target)) state.revealed_stage_ids.push(target);
          state.highlighted_relation_ids = (definitions.PROCESS.seed.relations as Array<any>).filter(item => item.from === target).map(item => item.id);
        } else if (operation.action_key === "TRACE_RELATION") { state.highlighted_relation_ids = [target]; state.tracing_relation_id = target; }
      } else if (pattern === "SPATIAL_MANIPULATION") state.placements[operation.payload.object_id as string] = operation.payload.target_id;
      else if (pattern === "MATH_VISUALIZATION") {
        state.point = { x: operation.payload.x, y: operation.payload.y };
        if (operation.action_key === "SUBMIT_CONSTRUCTION") { state.submitted = operation.payload; state.status = "SUBMITTED"; }
      } else { state.submitted = operation.payload; state.status = "SUBMITTED"; }
      return { ...previous, [pattern]: snapshot(pattern, prior.current_scene_version! + 1, state) };
    });
    if (tutorActions.has(operation.action_key)) setContinuations(previous => ({ ...previous, [pattern]: `المعلّم تابع من ${operation.action_key} باستخدام نفس جلسة التعلّم.` }));
  };

  const operationSummary = useMemo(() => operations[pattern].at(-1), [operations, pattern]);
  return <main className="production-proof" data-pattern={pattern}>
    <header><span>مسار Canvas الإنتاجي</span><h1>مساحة لينا اليومية</h1><p>مشهد خادمي معتمد ← محوّل التطبيق ← تفاعل دلالي ← متابعة المعلّم</p></header>
    <nav aria-label="Canvas patterns">{(Object.keys(definitions) as Pattern[]).map(key => <button key={key} aria-pressed={pattern === key} onClick={() => setPattern(key)}>{labels[key]}</button>)}</nav>
    <section className="proof-meta"><strong>{pattern}</strong><span>Scene v{current.current_scene_version}</span><button onClick={() => setHostKey(value => value + 1)}>أعد التحميل من Snapshot</button></section>
    <div className="daily-shell"><StudioRendererHost key={`${pattern}-${hostKey}`} snapshot={current} operationPending={false} onOperation={onOperation} onReload={() => setHostKey(value => value + 1)}/></div>
    <aside className="proof-audit" aria-live="polite">
      <p data-operation>{operationSummary ? `${operationSummary.action_key}: ${JSON.stringify(operationSummary.payload)}` : "لم يُسجل تفاعل بعد"}</p>
      <p data-tutor>{continuations[pattern] || "المعلّم ينتظر تفاعلاً تعليمياً ذا معنى."}</p>
    </aside>
  </main>;
}

Object.assign(window, {
  canvasEngineCounts: () => ({ stages: Konva.stages.length, boards: Object.keys(JXG.boards as Record<string, unknown>).length }),
  canvasCoordinateBounds: () => Object.values(JXG.boards as Record<string, { getBoundingBox: () => number[] }>)[0]?.getBoundingBox(),
});
createRoot(document.getElementById("root")!).render(<StrictMode><App/></StrictMode>);
