"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { Board, Point } from "jsxgraph";
import { exactGridPoint, type GridPoint } from "../contracts";

/** Integer coordinate construction, not a replacement for the decimal SVG number line. */
export function JsxGraphProof({ value, onValueChange }: { value: GridPoint; onValueChange: (value: GridPoint) => void }) {
  const id = useId().replace(/:/g, "");
  const host = useRef<HTMLDivElement>(null);
  const board = useRef<Board | null>(null);
  const point = useRef<Point | null>(null);
  const current = useRef({ value, onValueChange }); current.current = { value, onValueChange };
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    let dispose: (() => void) | undefined;
    import("jsxgraph").then(({ default: importedJXG }) => {
      if (!active || !host.current) return;
      const JXG = importedJXG;
      const next = JXG.JSXGraph.initBoard(id, { boundingbox: [-5, 5, 5, -5], axis: true, grid: true, showNavigation: false, showCopyright: false, keepaspectratio: true, pan: {enabled: false}, zoom: {wheel: false, pinchHorizontal: false, pinchVertical: false, min: 1, max: 1} });
      board.current = next;
      dispose = () => { if (board.current) JXG.JSXGraph.freeBoard(board.current); board.current = null; point.current = null; };
      const initial = exactGridPoint(current.current.value.x, current.current.value.y);
      const marker = next.create("point", [initial.x, initial.y], { name: "P", size: 5, fillColor: "#3563b5", strokeColor: "#3563b5", snapToGrid: true, snapSizeX: 1, snapSizeY: 1 });
      point.current = marker;
      const release = () => {
        const semantic = exactGridPoint(marker.X(), marker.Y());
        const accepted = exactGridPoint(current.current.value.x, current.current.value.y);
        marker.moveTo([accepted.x, accepted.y], 0);
        current.current.onValueChange(semantic);
      };
      marker.on("up", release);
      marker.on("keydrag", release);
      const observer = new ResizeObserver(([entry]) => {
        if (entry.contentRect.width > 0) next.resizeContainer(entry.contentRect.width, entry.contentRect.width, true);
      });
      observer.observe(host.current);
      const free = dispose;
      dispose = () => { observer.disconnect(); marker.off("up", release); marker.off("keydrag", release); free(); };
    }).catch(() => { dispose?.(); if (active) setFailed(true); });
    return () => { active = false; dispose?.(); };
  }, [id]);
  useEffect(() => { const exact = exactGridPoint(value.x, value.y); point.current?.moveTo([exact.x, exact.y], 0); }, [value.x, value.y]);
  const exact = exactGridPoint(value.x, value.y);
  return <section className="toolbelt-card" data-engine="jsxgraph">
    <span className="toolbelt-eyebrow">03 · الإحداثيات</span><h2>حرّك النقطة · Explore coordinates</h2>
    <p>حرّك P إلى تقاطع، أو غيّر القيم الصحيحة من −4 إلى 4.</p>
    <div ref={host} id={id} className="jxgbox toolbelt-graph" dir="ltr" role="img" aria-label={`Coordinate plane. P at (${exact.x}, ${exact.y})`}/>
    {failed && <p role="status">تعذر تحميل الرسم. استخدم حقول الإحداثيات.</p>}
    <div className="toolbelt-actions" dir="ltr">{(["x", "y"] as const).map(axis => <label key={axis}>{axis.toUpperCase()}<input aria-label={`${axis.toUpperCase()} coordinate`} type="number" min={-4} max={4} step={1} value={exact[axis]} onChange={event => {
      const number = event.currentTarget.valueAsNumber;
      if (Number.isFinite(number)) onValueChange(exactGridPoint(axis === "x" ? number : exact.x, axis === "y" ? number : exact.y));
    }}/></label>)}</div>
    <output dir="ltr" aria-live="polite">P = ({exact.x}, {exact.y})</output>
  </section>;
}
