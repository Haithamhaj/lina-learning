import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { AgenticCanvasWorkspace } from "../../lib/studio/agentic-canvas";

// Deterministic host regression only. This is never a live-provider acceptance artifact.
const source = `window.mount=(root,p,b)=>{let n=b.read('amount',0);const e=document.createElement('button');root.appendChild(e);const h=b.control(e,'amount','SET_VALUE');const render=()=>e.textContent='Amount '+n;e.onclick=()=>{n++;h.emit(n);render()};render()}`;
window.fetch = async () => new Response(JSON.stringify({ source, manifest: { interactions: [{ action: "SET_VALUE", semantic_id: "amount", value_required: true }] } }));
function App() {
  const [value, setValue] = useState("0"), [version, setVersion] = useState(1);
  const [pending, setPending] = useState(false), [calls, setCalls] = useState(0);
  const [failure, setFailure] = useState("");
  const seed = { version: "agentic-canvas-scene-v3", objective: "Adjust a quantity", subject_key: "MATH",
    presentation: { layout: "FOCUS", palette: "COOL", motion: "NONE", placements: [{ block_id: "quantity", role: "PRIMARY", order: 0, span: "FULL" }], reveal_order: [] },
    blocks: [{ block_id: "quantity", type: "CUSTOM_VISUAL", title: "Quantity", meaning: "Adjust the quantity", accessibility: { text_equivalent: "Interactive quantity", aria_label: "Quantity" },
      allowed_actions: ["SET_VALUE"], elements: [{ id: "amount", label: "Amount", current_value: value }], artifact_instance_id: "quantity-instance", bridge_nonce: "nonce-1234",
      custom_visual_build_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", manifest_digest: "a".repeat(64), parameters: {},
      semantic_interactions: [{ semantic_id: "amount", action: "SET_VALUE", value_required: true }] }] };
  return <><output data-saved>{value}</output><output data-calls>{calls}</output><output data-failure>{failure}</output>
    <AgenticCanvasWorkspace sceneId="scene-1" sceneVersion={version} seed={seed} onReload={() => {}} onOperation={async operation => {
      setCalls(n => n + 1);
      if (pending || operation.base_scene_version !== version || operation.payload.from_value !== value) {
        setFailure("concurrent or stale operation"); throw Error("stale");
      }
      setPending(true);
      await new Promise(resolve => setTimeout(resolve, 120));
      setPending(false);
      if (location.search.includes("reject")) throw Error("server rejection");
      setValue(String(operation.payload.to_value)); setVersion(n => n + 1);
    }}/></>;
}
createRoot(document.getElementById("root")!).render(<App/>);
