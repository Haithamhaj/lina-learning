# CURR-RENDER-MATH-01 — Coverage and Priority

## Coverage method

**Denominator:** the **35 concept nodes** in [01_GRADE5_CONCEPT_MAP.md](01_GRADE5_CONCEPT_MAP.md), including two explicitly marked prerequisite bridge nodes because their representation invariants are required to make Grade 5 fraction and area work correct. This is a capability-planning denominator, not a percentage of a textbook, time-on-task, school lessons, or learner benefit.

`Direct coverage` means a renderer has a documented primary representation for the node and, where bounded mathematical state exists, a deterministic validator path. A context-dependent word-problem answer can be represented but remains reference-grounded rather than fully machine-graded. A node may have more than one renderer; the union is counted once. The **Core set directly covers 30/35 nodes (85.7%)**. The five remaining nodes are best handled by a Second-Wave surface (`expression_pattern`, `shape_property_explorer`). The figure is a mapping count, not a claim that 85.7% of Grade 5 learning should use Canvas.

## Renderer scorecard

| Renderer | Direct concept nodes | Standards areas touched | Interaction reuse | Complexity | Homework/photo reconstruction | Cross-grade reuse | Priority |
|---|---:|---|---|---|---|---|---|
| `fraction_model_workspace` | 10 | 5.NF | partition, group, compare, submit | medium | high | high (Grades 3–6) | Core 1 |
| `place_value_workspace` | 6 | 5.NBT | transfer, compose, compare | medium | high | high (Grades 3–6) | Core 2 |
| `area_array_model` | 6 | 5.NBT, 5.NF | partition, fill, enter value | medium | high | high (Grades 3–6) | Core 3 |
| `number_line` | 6 | 5.NBT, 5.NF | plot, compare, manipulate | low–medium | medium | high (Grades 1–8) | Core 4 |
| `long_division_workspace` | 3 | 5.NBT | submit step, enter value | medium–high | very high | high (Grades 4–6) | Core 5 |
| `measurement_data_workspace` | 3 | 5.MD | convert, plot, enter value | medium | medium | medium–high (Grades 3–6) | Core 6 |
| `volume_composer` | 3 | 5.MD | construct, split, submit | medium–high | high | medium (Grades 4–6) | Core 7 |
| `coordinate_geometry_plane` | 3 | 5.G, 5.OA | plot, label, enter value | medium | medium | high (Grades 4–8) | Core 8 |
| `shape_property_explorer` | 3 | 5.G | sort, label, compare | medium | low | high (Grades 2–8) | Second wave |
| `expression_pattern` | 2 | 5.OA | reorder, enter expression | low–medium | low | high (Grades 4–8) | Second wave |

The union above is 30 nodes because renderer columns intentionally overlap. The remaining five nodes are `G5-OA-NUMERICAL-EXPRESSIONS`, `G5-OA-PATTERN-RULES`, `G5-G-CLASSIFY-2D`, `G5-G-SHAPE-HIERARCHY`, and `G5-G-ANGLE-PROPERTIES`.

## Recommended Grade 5 Math Renderer Foundation

### Core renderer families — 8

1. `fraction_model_workspace` — fraction whole/equivalence/operation/sharing/scaling; partition/group/compare; fraction structure and operation validators; React/SVG; medium complexity; high cross-grade and photo-reconstruction value.
2. `place_value_workspace` — powers of ten, decimal notation, comparison/rounding and decimal-operation bridge; transfer/compose; place-value validator; React DOM/SVG; medium complexity; high cross-grade/photo value.
3. `area_array_model` — multi-digit/decimal multiplication, fraction scaling and fractional area; partition/partial-product actions; decomposition validator; React/SVG; medium complexity; high cross-grade/photo value.
4. `number_line` — comparison, rounding, estimates, fractional magnitude and coordinate foundations; plot/interval actions; numeric relation validator; React/SVG; low–medium complexity; highest cross-grade reuse.
5. `long_division_workspace` — multi-digit and decimal-by-whole division; step submission; transition validator; React DOM/SVG; medium–high complexity; strong Grade 4–6 and photo value.
6. `measurement_data_workspace` — conversions and fractional line plots; conversion/plot actions; unit and data validators; React/SVG; medium complexity; medium–high cross-grade reuse.
7. `volume_composer` — units, layers, formulas and composite prisms; build/split actions; occupancy/additivity validator; React/SVG first; medium–high complexity; medium cross-grade reuse and high reconstruction value.
8. `coordinate_geometry_plane` — axes, points and coordinate problems; plot/label actions; coordinate validator; React/SVG first; medium complexity; high Grades 4–8 reuse.

### Recommended initial build batch

Names only, deliberately diverse in representation and validation:

- `number_line`
- `place_value_workspace`
- `fraction_model_workspace`
- `long_division_workspace`

This batch covers continuous magnitude, discrete place-value structure, fraction-whole invariants, and multistep state validation. It is a recommendation, not a task list or implementation authorization.

## Deferred renderer families

| Classification | Families / cases | Reason |
|---|---|---|
| Second wave | `shape_property_explorer`, `expression_pattern` | useful cross-grade capabilities, but the first batch already proves stronger renderer/validator/event differences and avoids premature MathLive adoption |
| Specialized | rich measurement instruments, advanced angle construction, complex composite geometry | smaller Grade 5 frequency or need a confirmed use case/configuration |
| Specialist/custom only | novel multi-renderer composition, source-specific annotations, complex spatial simulations | requires deterministic-gap proof, safety/typed-plan gate, or separately approved Vision path |
| No Canvas by default | direct arithmetic explanation, short recall, simple notation correction | representation cost exceeds learning value |

## Canvas Specialist gaps

The catalog deliberately does not solve novel source-specific layouts, a handwritten page interpretation, or an unusually composed multi-representation explanation. These remain candidates only after the future application rule confirms: an allowed Math capability, a real deterministic catalog gap, a safe renderer/validator, a fixed Tutor objective, and non-blocking scheduling. The specialist cannot write Studio state or replace Tutor.

## Technology mapping

- **React DOM + SVG:** default for every Core renderer; preserves deterministic state, responsive layout, testability, text alternatives, and low dependency cost.
- **Motion:** optional orientation/feedback only, with reduced-motion behavior; never a correctness channel.
- **JSXGraph:** evaluate only for a later coordinate/geometry proof where plain SVG cannot meet interaction or accuracy needs.
- **React Konva:** evaluate only if constrained spatial editing for annotation/cubes materially beats DOM/SVG; not needed for the catalog foundation.
- **MathLive:** evaluate only for a demonstrated structured-expression input gap in `expression_pattern`; it is not needed for numerical fields or renderer display.

## Cross-grade estimate

`number_line`, `place_value_workspace`, `area_array_model`, `fraction_model_workspace`, `coordinate_geometry_plane`, `shape_property_explorer`, and `expression_pattern` are **HIGH** reuse. `long_division_workspace` and `measurement_data_workspace` are **MEDIUM–HIGH**. `volume_composer` is **MEDIUM**. These are estimates from mathematical progression, not a research claim about later curricula.
