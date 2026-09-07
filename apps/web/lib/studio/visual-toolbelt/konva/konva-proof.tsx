"use client";

import { useState } from "react";
import { Circle, Layer, Rect, Stage, Text } from "react-konva";
import { semanticPlacement, type SemanticPlacement } from "../contracts";

export function KonvaProof({ onSemanticPlacement }: { onSemanticPlacement?: (value: SemanticPlacement) => void }) {
  const [result, setResult] = useState<SemanticPlacement>("outside-target");
  return <section data-engine="konva"><h2>Spatial placement</h2><p>Drag the blue object into the green region. Pixels are not academic truth.</p><Stage width={320} height={180} aria-label="Konva placement proof"><Layer><Rect x={210} y={45} width={85} height={85} fill="#d1fae5" cornerRadius={12} /><Text x={220} y={78} text="Target" fill="#065f46" /><Circle x={70} y={90} radius={24} fill="#2563eb" draggable onDragEnd={(event) => { const position = event.target.position(); const next = semanticPlacement(position.x >= 210 && position.x <= 295 && position.y >= 45 && position.y <= 130); setResult(next); onSemanticPlacement?.(next); event.target.position({ x: 70, y: 90 }); }} /></Layer></Stage><output>{result === "target-region" ? "Object A moved to target region B." : "Object A has not reached target region B."}</output></section>;
}
