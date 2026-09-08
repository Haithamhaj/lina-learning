import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Konva from "konva";
import JXG from "jsxgraph";

import { CanvasFinalReview } from "../../components/studio/canvas-final-review";

Object.assign(window, {
  canvasEngineCounts: () => ({
    stages: Konva.stages.length,
    boards: Object.keys(JXG.boards as Record<string, unknown>).length,
  }),
});

createRoot(document.getElementById("root")!).render(<StrictMode><CanvasFinalReview/></StrictMode>);
