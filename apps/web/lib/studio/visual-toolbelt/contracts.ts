/** Local application inputs/results. Never part of the Specialist proposal schema. */
export type SemanticPlacement = { objectId: string; targetId: string | null };
export type GridPoint = { x: number; y: number };
export type RelationFocus = "source" | "target";
export type MathInput = { format: "latex"; value: string };

export const semanticPlacement = (
  insideTarget: boolean,
  objectId = "object-a",
  targetId = "target-b",
): SemanticPlacement => ({
  objectId, targetId: insideTarget ? targetId : null,
});

// Private presentation-space hit testing. Only the semantic IDs leave the adapter.
export function placementFromPoint(
  x: number,
  y: number,
  objectId = "object-a",
  targetId = "target-b",
): SemanticPlacement {
  return semanticPlacement(
    Number.isFinite(x) && Number.isFinite(y) && x >= 210 && x <= 295 && y >= 45 && y <= 130,
    objectId,
    targetId,
  );
}

export function exactGridPoint(x: number, y: number): GridPoint {
  if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error("Coordinates must be finite");
  const integer = (value: number) => Math.max(-4, Math.min(4, Math.round(value))) || 0;
  return { x: integer(x), y: integer(y) };
}

/** Preserve the exact emitted LaTeX; not an answer, evaluator or grading result. */
export function serializeMathInput(value: string): MathInput {
  if (!value.trim() || value.length > 200) throw new Error("Enter an expression of 1–200 characters");
  return { format: "latex", value };
}
