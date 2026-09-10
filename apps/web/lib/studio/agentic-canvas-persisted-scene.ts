/**
 * Persisted Scene copy from tests/test_agentic_canvas_lifecycle_postgres.py.
 * This is deliberately kept as server-shaped JSON: the renderer must consume
 * the reduced Scene rather than an Agent tool response or a component hint.
 */
export const persistedAgenticCanvasScene = {
  version: "agentic-canvas-scene-v1",
  objective: "Compare two decimals on a number line.",
  subject_key: "MATH",
  blocks: [
    {
      block_id: "decimal-line",
      type: "MATH_BOARD",
      meaning: "A number line compares the two decimal positions.",
      title: "Decimal positions",
      accessibility: {
        text_equivalent: "A number line containing zero point four five and zero point six.",
        aria_label: "Decimal comparison number line",
      },
      allowed_actions: ["SELECT"],
      elements: [
        { id: "first", label: "0.6", current_value: "0.6" },
        { id: "second", label: "0.45", current_value: "0.45" },
      ],
      board_kind: "NUMBER_LINE",
      axis_min: "0",
      axis_max: "1",
      axes: [{ axis: "X", minimum: "0", maximum: "1", step: "0.05" }],
      markers: [
        { id: "first-marker", label: "0.6", value: "0.6", marker_kind: "POINT", draggable: false },
        { id: "second-marker", label: "0.45", value: "0.45", marker_kind: "POINT", draggable: false },
      ],
      expressions: [],
    },
  ],
} as const;
