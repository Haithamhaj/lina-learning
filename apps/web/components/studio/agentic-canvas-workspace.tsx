"use client";

import type { StudioOperation } from "@/lib/studio/contracts";

type Block = { block_id?: unknown; type?: unknown; meaning?: unknown; title?: unknown; accessibility?: { text_equivalent?: unknown }; elements?: Array<{ id?: unknown; label?: unknown; current_value?: unknown }> };

export function AgenticCanvasWorkspace({ sceneId, sceneVersion, seed, onOperation }: { sceneId: string; sceneVersion: number; seed: Record<string, unknown>; onOperation: (operation: StudioOperation) => Promise<void> }) {
  const blocks = Array.isArray(seed.blocks) ? seed.blocks.filter((value): value is Block => typeof value === "object" && value !== null) : [];
  return <section aria-label="Learning canvas" className="space-y-3">{blocks.map((block) => {
    if (typeof block.block_id !== "string" || !["MATH_BOARD", "SCENE_2D", "DIAGRAM", "TEXT_INTERACTION", "MATH_INPUT", "IMAGE"].includes(String(block.type))) return null;
    const label = typeof block.title === "string" ? block.title : typeof block.meaning === "string" ? block.meaning : "Learning representation";
    const equivalent = typeof block.accessibility?.text_equivalent === "string" ? block.accessibility.text_equivalent : label;
    return <article key={block.block_id} aria-label={equivalent} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-semibold text-slate-900">{label}</h3><p className="mt-1 text-sm text-slate-600">{String(block.type)}</p>
      <ul className="mt-3 space-y-1 text-sm text-slate-700">{Array.isArray(block.elements) && block.elements.map((item) => typeof item?.id === "string" ? <li key={item.id}>{typeof item.label === "string" ? item.label : item.id}{typeof item.current_value === "string" ? `: ${item.current_value}` : ""}</li> : null)}</ul>
      <button type="button" className="mt-3 rounded-lg border px-3 py-2 text-sm" onClick={() => void onOperation({ scene_id: sceneId, base_scene_version: sceneVersion, action_key: "FOCUS", payload: { block_id: block.block_id }, idempotency_key: `agentic-focus:${sceneId}:${sceneVersion}:${block.block_id}` })}>Focus</button>
    </article>;
  })}</section>;
}
