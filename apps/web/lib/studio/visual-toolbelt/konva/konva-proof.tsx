"use client";

import { useEffect, useRef, useState } from "react";
import { Circle, Group, Layer, Rect, Stage, Text } from "react-konva";
import { placementFromPoint, semanticPlacement, type SemanticPlacement } from "../contracts";

/** Bounded A→B placement. Canvas coordinates never leave this component. */
export function KonvaProof({
  value,
  onSemanticPlacement,
  object = { id: "object-a", label: "A" },
  target = { id: "target-b", label: "B" },
  allowReturn = true,
  title = "ضع A في B · Place and explore",
  prompt = "اسحب الدائرة إلى المنطقة الخضراء، أو استخدم الأزرار.",
}: {
  value: SemanticPlacement;
  onSemanticPlacement: (value: SemanticPlacement) => void;
  object?: { id: string; label: string };
  target?: { id: string; label: string };
  allowReturn?: boolean;
  title?: string;
  prompt?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(320);
  useEffect(() => {
    if (!host.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(1, Math.min(640, entry.contentRect.width))));
    observer.observe(host.current);
    return () => observer.disconnect();
  }, []);
  const placed = value.targetId === target.id;
  const position = { x: placed ? 252 : 70, y: 90 };
  return <section className="toolbelt-card" data-engine="konva">
    <span className="toolbelt-eyebrow">المكان والتجميع</span><h2>{title}</h2>
    <p>{prompt}</p>
    <div className="toolbelt-surface" ref={host} dir="ltr" role="img" aria-label={placed ? `${object.label} in ${target.label}` : `${object.label} outside ${target.label}`}>
      <Stage width={width} height={width * 180 / 320} scaleX={width / 320} scaleY={width / 320}><Layer>
        <Rect x={210} y={45} width={85} height={85} fill="#d4f2e3" stroke="#559c80" cornerRadius={16}/>
        <Text x={232} y={140} width={42} align="center" text={target.label} fontSize={16} fill="#23674e"/>
        <Group {...position} draggable onDragEnd={(event) => {
          const next = placementFromPoint(event.target.x(), event.target.y(), object.id, target.id);
          onSemanticPlacement(next);
          // Restore the controlled value until the application accepts the result.
          event.target.position(position);
        }}>
          <Circle radius={23} fill="#3563b5"/>
          <Text x={-19} y={-7} width={38} align="center" text={object.label} fill="white" fontSize={15} listening={false}/>
        </Group>
      </Layer></Stage>
    </div>
    <div className="toolbelt-actions"><button aria-label={`Place ${object.label} in ${target.label}`} aria-pressed={placed} onClick={() => onSemanticPlacement(semanticPlacement(true, object.id, target.id))}>ضع {object.label} في {target.label}</button>{allowReturn ? <button aria-label={`Return ${object.label}`} onClick={() => onSemanticPlacement(semanticPlacement(false, object.id, target.id))}>أعد {object.label}</button> : null}</div>
    <output aria-live="polite">{placed ? `${object.label} داخل ${target.label}` : `${object.label} خارج ${target.label}`}</output>
  </section>;
}
