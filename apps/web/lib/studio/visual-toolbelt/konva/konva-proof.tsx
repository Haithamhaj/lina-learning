"use client";

import { useEffect, useRef, useState } from "react";
import { Circle, Group, Layer, Rect, Stage, Text } from "react-konva";
import { placementFromPoint, semanticPlacement, type SemanticPlacement } from "../contracts";

/** Bounded A→B placement. Canvas coordinates never leave this component. */
export function KonvaProof({ value, onSemanticPlacement }: {
  value: SemanticPlacement; onSemanticPlacement: (value: SemanticPlacement) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(320);
  useEffect(() => {
    if (!host.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(1, Math.min(640, entry.contentRect.width))));
    observer.observe(host.current);
    return () => observer.disconnect();
  }, []);
  const placed = value.targetId === "target-b";
  const position = { x: placed ? 252 : 70, y: 90 };
  return <section className="toolbelt-card" data-engine="konva">
    <span className="toolbelt-eyebrow">02 · المكان والتجميع</span><h2>ضع A في B · Place and explore</h2>
    <p>اسحب الدائرة إلى المنطقة الخضراء، أو استخدم الأزرار.</p>
    <div className="toolbelt-surface" ref={host} dir="ltr" role="img" aria-label={placed ? "Object A in target B" : "Object A outside target B"}>
      <Stage width={width} height={width * 180 / 320} scaleX={width / 320} scaleY={width / 320}><Layer>
        <Rect x={210} y={45} width={85} height={85} fill="#d4f2e3" stroke="#559c80" cornerRadius={16}/>
        <Text x={242} y={140} text="B" fontSize={16} fill="#23674e"/>
        <Group {...position} draggable onDragEnd={(event) => {
          const next = placementFromPoint(event.target.x(), event.target.y());
          onSemanticPlacement(next);
          // Restore the controlled value until the application accepts the result.
          event.target.position(position);
        }}>
          <Circle radius={23} fill="#3563b5"/>
          <Text x={-5} y={-7} text="A" fill="white" fontSize={15} listening={false}/>
        </Group>
      </Layer></Stage>
    </div>
    <div className="toolbelt-actions"><button aria-label="Place A in B" aria-pressed={placed} onClick={() => onSemanticPlacement(semanticPlacement(true))}>ضع A في B</button><button aria-label="Return A" onClick={() => onSemanticPlacement(semanticPlacement(false))}>أعد A</button></div>
    <output aria-live="polite">{placed ? "A داخل B · A is in B" : "A خارج B · A is outside B"}</output>
  </section>;
}
