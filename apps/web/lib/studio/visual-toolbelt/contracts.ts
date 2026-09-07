export type SemanticPlacement = "target-region" | "outside-target";

export const semanticPlacement = (insideTarget: boolean): SemanticPlacement =>
  insideTarget ? "target-region" : "outside-target";
