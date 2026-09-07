"use client";

import { useEffect, useId, useRef } from "react";

export function JsxGraphProof() {
  const id = useId().replace(/:/g, ""); const board = useRef<any>(null);
  useEffect(() => { let active = true; let JXG: any; import("jsxgraph").then(({ default: importedJXG }) => { if (!active) return; JXG = importedJXG; board.current = JXG.JSXGraph.initBoard(id, { boundingbox: [-5, 1, 5, -1], axis: true, showNavigation: false, showCopyright: false, keepaspectratio: true }); board.current.create("point", [2, 0], { name: "2", fixed: true, size: 4 }); }); return () => { active = false; if (board.current && JXG) JXG.JSXGraph.freeBoard(board.current); board.current = null; JXG = null; }; }, [id]);
  return <section data-engine="jsxgraph" dir="rtl"><h2>خط الأعداد / Number line</h2><p dir="ltr">Mathematical direction remains left-to-right.</p><div id={id} className="jxgbox" style={{ height: 180, width: "100%" }} /><output>Board cleanup calls freeBoard on unmount.</output></section>;
}
