CANVAS_PRODUCTION_CAPABILITY_PACK_V1

This execution pack enables only the exact semantic pattern named by the
application-supplied frozen capability pack. It never authorizes an engine,
renderer, layout coordinate, executable content, persistence, grading, or Tutor
dialogue.

For SPATIAL_MANIPULATION, compose exactly one named semantic object and one
named semantic target. Use only the admitted INSIDE, MATCH, or GROUP
relation. Every object has exactly one initial semantic placement, which may be
unplaced. PLACE_OBJECT is the only permitted interaction.

For MATH_VISUALIZATION, compose exactly one CARTESIAN_POINT construction. Axes,
initial point, and target are exact integer mathematical content within the
frozen coordinate bounds. PLACE_POINT changes the construction and
SUBMIT_CONSTRUCTION explicitly sends the current construction to the Tutor.

For MATH_INPUT, compose one bounded LATEX expression objective. The initial
value may be empty or an admitted starting expression. SUBMIT_EXPRESSION is the
only durable interaction. Do not infer grading or correctness.

Every factual object, target, point, expression objective, and relation must
claim the exact admitted support identities. Use concise labels and preserve the
requested locale and direction; mathematical coordinates and expressions remain
left-to-right content under Arabic prose.
