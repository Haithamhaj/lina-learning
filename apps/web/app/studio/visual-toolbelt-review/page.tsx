"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import { MotionProof } from "@/lib/studio/visual-toolbelt/motion/motion-proof";

const KonvaProof = dynamic(() => import("@/lib/studio/visual-toolbelt/konva/konva-proof").then((m) => m.KonvaProof), { ssr: false });
const JsxGraphProof = dynamic(() => import("@/lib/studio/visual-toolbelt/jsxgraph/jsxgraph-proof").then((m) => m.JsxGraphProof), { ssr: false });
const MathLiveProof = dynamic(() => import("@/lib/studio/visual-toolbelt/mathlive/mathlive-proof").then((m) => m.MathLiveProof), { ssr: false });

export default function VisualToolbeltReviewPage() {
  const [message, setMessage] = useState("No semantic handoff yet.");
  const onSemanticPlacement = useCallback((value: string) => setMessage(`Semantic placement: ${value}`), []);
  const onMathValueChange = useCallback((value: string) => setMessage(`Browser math input: ${value}`), []);

  return <main className="min-h-screen bg-slate-100 p-6 text-slate-900"><link rel="stylesheet" href="/visual-toolbelt/jsxgraph.css" /><div className="mx-auto grid max-w-4xl gap-5"><p className="rounded-xl bg-white p-4 text-sm">Isolated CS-02 review proof. It is not a Student route, Studio runtime, persistence, or learning-state authority.</p><MotionProof /><KonvaProof onSemanticPlacement={onSemanticPlacement} /><JsxGraphProof /><MathLiveProof onValueChange={onMathValueChange} /><output aria-live="polite" className="rounded-xl bg-white p-4">{message}</output></div></main>;
}
