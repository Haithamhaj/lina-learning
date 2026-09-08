export type CanvasPattern =
  | "PROCESS"
  | "SPATIAL_MANIPULATION"
  | "MATH_VISUALIZATION"
  | "MATH_INPUT";

export type CanvasVisualIntent =
  | { type: "explain_process"; topology: "sequence" | "cycle" }
  | { type: "place_object"; relation: "inside" }
  | { type: "construct_coordinate"; domain: "integer_grid" }
  | { type: "author_math"; format: "latex" };

export type CanvasCapabilitySelection = {
  pattern: CanvasPattern;
  adapter: "process-view" | "spatial-placement" | "coordinate-construction" | "math-expression-input";
};

const exactKeys = (value: Record<string, unknown>, keys: readonly string[]) => (
  Object.keys(value).length === keys.length
  && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key))
);

/**
 * Application-owned selection from semantic need to a local visual pattern.
 * Engine names and renderer identifiers are deliberately not accepted.
 */
export function resolveCanvasPattern(value: unknown): CanvasPattern | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const intent = value as Record<string, unknown>;
  if (!exactKeys(intent, ["type", intent.type === "explain_process" ? "topology" : intent.type === "place_object" ? "relation" : intent.type === "construct_coordinate" ? "domain" : "format"])) return null;

  if (intent.type === "explain_process" && (intent.topology === "sequence" || intent.topology === "cycle")) return "PROCESS";
  if (intent.type === "place_object" && intent.relation === "inside") return "SPATIAL_MANIPULATION";
  if (intent.type === "construct_coordinate" && intent.domain === "integer_grid") return "MATH_VISUALIZATION";
  if (intent.type === "author_math" && intent.format === "latex") return "MATH_INPUT";
  return null;
}

/** Resolve the private local adapter after semantic validation. */
export function selectCanvasCapability(value: unknown): CanvasCapabilitySelection | null {
  const pattern = resolveCanvasPattern(value);
  if (pattern === null) return null;
  const adapters: Record<CanvasPattern, CanvasCapabilitySelection["adapter"]> = {
    PROCESS: "process-view",
    SPATIAL_MANIPULATION: "spatial-placement",
    MATH_VISUALIZATION: "coordinate-construction",
    MATH_INPUT: "math-expression-input",
  };
  return { pattern, adapter: adapters[pattern] };
}
