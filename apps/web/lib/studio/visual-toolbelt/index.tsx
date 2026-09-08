"use client";

import dynamic from "next/dynamic";

// Application imports capabilities here. Engine modules never execute during SSR.
// This boundary is intentionally local; it is not a model-facing registry.
export const RelationFocusView = dynamic(() => import("./motion/motion-proof").then(m => m.MotionProof), { ssr: false });
export const SpatialPlacement = dynamic(() => import("./konva/konva-proof").then(m => m.KonvaProof), { ssr: false });
export const CoordinateConstruction = dynamic(() => import("./jsxgraph/jsxgraph-proof").then(m => m.JsxGraphProof), { ssr: false });
export const MathExpressionInput = dynamic(() => import("./mathlive/mathlive-proof").then(m => m.MathLiveProof), { ssr: false });
export type { SemanticPlacement, GridPoint, RelationFocus, MathInput } from "./contracts";
export { resolveCanvasPattern, selectCanvasCapability } from "./visual-selection";
export type { CanvasCapabilitySelection, CanvasPattern, CanvasVisualIntent } from "./visual-selection";
