"use client";

import { useState } from "react";
import { RelationFocusView, SpatialPlacement, CoordinateConstruction, MathExpressionInput, type RelationFocus, type SemanticPlacement, type GridPoint } from "@/lib/studio/visual-toolbelt";
import "@/lib/studio/visual-toolbelt/toolbelt.css";

export default function VisualToolbeltReviewPage() {
  const [focus, setFocus] = useState<RelationFocus>("source");
  const [placement, setPlacement] = useState<SemanticPlacement>({objectId: "object-a", targetId: null});
  const [point, setPoint] = useState<GridPoint>({x: 2, y: 1});
  const [math, setMath] = useState("\\frac{3}{4}");
  return <main className="toolbelt-review" dir="rtl">
    <link rel="stylesheet" href="/visual-toolbelt/jsxgraph.css"/>
    <h1>أدوات الاستكشاف · Lina</h1><p>معاينة أدوات بصرية مستقلة · Isolated visual capability review</p>
    <RelationFocusView focus={focus} onFocusChange={setFocus}/>
    <SpatialPlacement value={placement} onSemanticPlacement={setPlacement}/>
    <CoordinateConstruction value={point} onValueChange={setPoint}/>
    <MathExpressionInput value={math} onValueChange={setMath}/>
  </main>;
}
