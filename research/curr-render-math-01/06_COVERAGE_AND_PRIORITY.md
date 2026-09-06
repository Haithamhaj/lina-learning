# CURR-RENDER-MATH-01 — Coverage and Priority

## Coverage method

**LINA DESIGN RECOMMENDATION, not standards-mandated taxonomy.** The corrected universe is the original 35 stable keys plus node 36, decimal addition/subtraction. Both prerequisite bridges remain in the primary capability-planning denominator. A separate Grade-5-target-only denominator removes only those same two bridges from both numerator and denominator. No nodes were removed to improve results. Node 1 covers two explicitly distinguished expression requirements but is counted once; node 11 keeps its historical key with broader method meaning.

These are coverage of the declared planning nodes, not percentages of a textbook, lessons, standards achieved, fluency, time-on-task or learner benefit. In particular, node 12 is only the decimal-by-whole subset of 5.NBT.B.7; neither a direct node nor all mapped nodes imply full standard attainment. Make-Ten is excluded from every numerator and denominator.

- **D / direct:** a proposed primary representation plus bounded actions and a deterministic state/answer validation path addresses the declared node's mathematical capability. This credits the full-family proposal, not implemented code, pedagogical explanation quality, fluency or arbitrary language interpretation.
- **P / partial:** only a subcapability, auxiliary representation or restricted numeric/method slice is specified. Displaying decimals is not arithmetic support; two partial renderers do not automatically add up to D.
- **R / reference-grounded:** the representation/arithmetic can support a contextual task, but its interpretation needs authored/source-grounded quantities and Tutor clarification. R earns no D credit even when the arithmetic is deterministic.
- **U / uncovered:** no D, P or R mapping exists within the selected renderer set. A later-wave family may still support the node.
- Unique-ID set unions determine coverage. For exclusive reporting: D first; then R without D; then P without D/R; the complement is U. This ordering counts once and does not upgrade combined partial support.

[coverage_mapping.json](coverage_mapping.json) declares every concept ID, bridge/target kind, renderer registry, D/P/R lists, Core/batch sets, first-slice subsets and exclusions. The contextual nodes 15, 20, 23, 27 and 30 are R; node 8 is P because area representation does not cover its algorithm/fluency aim; node 2 is P for the incomplete pattern/plot combination; node 1 is P in the later expression family. Other D labels denote bounded mathematical representation support, never a complete educational assessment.

## Reproduction and calculated scorecard

From the repository root:

```sh
python3 research/curr-render-math-01/calculate_coverage.py --check
```

Python standard library only. The script reads the mapping and Markdown, emits the following report, and checks unique IDs, known references/renderer keys, first-slice subsets, Make-Ten exclusion, disjoint outcome sets, displayed totals and relative file links. It does not modify files. The calculation block below must exactly match its output; no overlapping per-renderer totals are summed.

<!-- CALCULATED:START -->
Universe: 36 = 34 Grade 5 targets + 2 prerequisite bridges.
Families: 11 proposed; 9 Core; 4 initial-batch families.

| Scope | Denominator | Direct union | Direct % | Partial only | Reference-grounded only | Uncovered |
|---|---:|---:|---:|---:|---:|---:|
| Core families / all nodes | 36 | 25 | 69.4% | 2 | 5 | 4 |
| Core families / Grade 5 targets | 34 | 23 | 67.6% | 2 | 5 | 4 |
| Batch families / all nodes | 36 | 17 | 47.2% | 1 | 2 | 16 |
| Batch families / Grade 5 targets | 34 | 16 | 47.1% | 1 | 2 | 15 |
| First slices / all nodes | 36 | 5 | 13.9% | 5 | 0 | 26 |
| First slices / Grade 5 targets | 34 | 4 | 11.8% | 5 | 0 | 25 |
| All planned families / all nodes | 36 | 28 | 77.8% | 3 | 5 | 0 |
| All planned families / Grade 5 targets | 34 | 26 | 76.5% | 3 | 5 | 0 |
| Implemented Grade 5 / all nodes | 36 | 0 | 0.0% | 0 | 0 | 36 |
| Implemented Grade 5 / Grade 5 targets | 34 | 0 | 0.0% | 0 | 0 | 34 |

| Renderer | Direct | Partial | Reference-grounded |
|---|---:|---:|---:|
| `number_line` | 5 | 2 | 0 |
| `place_value_workspace` | 5 | 2 | 0 |
| `area_array_model` | 4 | 2 | 1 |
| `fraction_model_workspace` | 8 | 0 | 2 |
| `division_workspace` | 3 | 0 | 0 |
| `measurement_conversion_workspace` | 1 | 0 | 1 |
| `line_plot_workspace` | 1 | 0 | 0 |
| `volume_composer` | 2 | 0 | 1 |
| `coordinate_geometry_plane` | 2 | 1 | 1 |
| `shape_property_explorer` | 3 | 0 | 0 |
| `expression_pattern` | 0 | 2 | 0 |

Historical reported coverage: 30/35 = 85.7%.
Historical catalog association union: 31/35 = 88.6% (associations, not verified direct support).

Core families — IDs (all nodes):
- direct: G5-G-COORDINATE-PLANE, G5-G-PLOT-INTERPRET, G5-MD-FRACTION-LINE-PLOTS, G5-MD-UNIT-RELATIONSHIPS, G5-MD-VOLUME-FORMULAS, G5-MD-VOLUME-UNIT-CUBES, G5-NBT-DECIMAL-ADD-SUBTRACT, G5-NBT-DECIMAL-COMPARE, G5-NBT-DECIMAL-DIVIDE-BY-WHOLE, G5-NBT-DECIMAL-MULTIPLY, G5-NBT-DECIMAL-READ-WRITE, G5-NBT-DECIMAL-ROUND, G5-NBT-DIVISION-ESTIMATE, G5-NBT-LONG-DIVISION, G5-NBT-MULTIPLICATION-ESTIMATE, G5-NBT-POWERS-OF-TEN, G5-NF-ADD-SUBTRACT-FRACTIONS, G5-NF-EQUIVALENCE-BRIDGE, G5-NF-FRACTION-AREA-MULTIPLY, G5-NF-FRACTION-AS-DIVISION, G5-NF-FRACTION-MULTIPLY-WHOLE, G5-NF-FRACTION-SCALING, G5-NF-UNIT-FRACTION-DIVISION, G5-PREREQ-AREA-ARRAY-STRUCTURE, G5-PREREQ-FRACTION-UNIT-WHOLE
- partial: G5-NBT-MULTIDIGIT-MULTIPLY, G5-OA-PATTERN-RULES
- reference_grounded: G5-G-COORDINATE-PROBLEMS, G5-MD-MEASUREMENT-PROBLEMS, G5-MD-VOLUME-ADDITIVE, G5-NF-FRACTION-MULTIPLY-PROBLEMS, G5-NF-FRACTION-WORD-PROBLEMS
- uncovered: G5-G-ANGLE-PROPERTIES, G5-G-CLASSIFY-2D, G5-G-SHAPE-HIERARCHY, G5-OA-NUMERICAL-EXPRESSIONS

Batch families — IDs (all nodes):
- direct: G5-NBT-DECIMAL-ADD-SUBTRACT, G5-NBT-DECIMAL-COMPARE, G5-NBT-DECIMAL-DIVIDE-BY-WHOLE, G5-NBT-DECIMAL-READ-WRITE, G5-NBT-DECIMAL-ROUND, G5-NBT-DIVISION-ESTIMATE, G5-NBT-LONG-DIVISION, G5-NBT-MULTIPLICATION-ESTIMATE, G5-NBT-POWERS-OF-TEN, G5-NF-ADD-SUBTRACT-FRACTIONS, G5-NF-EQUIVALENCE-BRIDGE, G5-NF-FRACTION-AREA-MULTIPLY, G5-NF-FRACTION-AS-DIVISION, G5-NF-FRACTION-MULTIPLY-WHOLE, G5-NF-FRACTION-SCALING, G5-NF-UNIT-FRACTION-DIVISION, G5-PREREQ-FRACTION-UNIT-WHOLE
- partial: G5-NBT-DECIMAL-MULTIPLY
- reference_grounded: G5-NF-FRACTION-MULTIPLY-PROBLEMS, G5-NF-FRACTION-WORD-PROBLEMS
- uncovered: G5-G-ANGLE-PROPERTIES, G5-G-CLASSIFY-2D, G5-G-COORDINATE-PLANE, G5-G-COORDINATE-PROBLEMS, G5-G-PLOT-INTERPRET, G5-G-SHAPE-HIERARCHY, G5-MD-FRACTION-LINE-PLOTS, G5-MD-MEASUREMENT-PROBLEMS, G5-MD-UNIT-RELATIONSHIPS, G5-MD-VOLUME-ADDITIVE, G5-MD-VOLUME-FORMULAS, G5-MD-VOLUME-UNIT-CUBES, G5-NBT-MULTIDIGIT-MULTIPLY, G5-OA-NUMERICAL-EXPRESSIONS, G5-OA-PATTERN-RULES, G5-PREREQ-AREA-ARRAY-STRUCTURE

First slices — IDs (all nodes):
- direct: G5-NBT-DECIMAL-ADD-SUBTRACT, G5-NBT-DECIMAL-COMPARE, G5-NBT-DECIMAL-ROUND, G5-NF-EQUIVALENCE-BRIDGE, G5-PREREQ-FRACTION-UNIT-WHOLE
- partial: G5-NBT-DECIMAL-READ-WRITE, G5-NBT-DIVISION-ESTIMATE, G5-NBT-LONG-DIVISION, G5-NBT-POWERS-OF-TEN, G5-NF-ADD-SUBTRACT-FRACTIONS
- reference_grounded: none
- uncovered: G5-G-ANGLE-PROPERTIES, G5-G-CLASSIFY-2D, G5-G-COORDINATE-PLANE, G5-G-COORDINATE-PROBLEMS, G5-G-PLOT-INTERPRET, G5-G-SHAPE-HIERARCHY, G5-MD-FRACTION-LINE-PLOTS, G5-MD-MEASUREMENT-PROBLEMS, G5-MD-UNIT-RELATIONSHIPS, G5-MD-VOLUME-ADDITIVE, G5-MD-VOLUME-FORMULAS, G5-MD-VOLUME-UNIT-CUBES, G5-NBT-DECIMAL-DIVIDE-BY-WHOLE, G5-NBT-DECIMAL-MULTIPLY, G5-NBT-MULTIDIGIT-MULTIPLY, G5-NBT-MULTIPLICATION-ESTIMATE, G5-NF-FRACTION-AREA-MULTIPLY, G5-NF-FRACTION-AS-DIVISION, G5-NF-FRACTION-MULTIPLY-PROBLEMS, G5-NF-FRACTION-MULTIPLY-WHOLE, G5-NF-FRACTION-SCALING, G5-NF-FRACTION-WORD-PROBLEMS, G5-NF-UNIT-FRACTION-DIVISION, G5-OA-NUMERICAL-EXPRESSIONS, G5-OA-PATTERN-RULES, G5-PREREQ-AREA-ARRAY-STRUCTURE

All planned families — IDs (all nodes):
- direct: G5-G-ANGLE-PROPERTIES, G5-G-CLASSIFY-2D, G5-G-COORDINATE-PLANE, G5-G-PLOT-INTERPRET, G5-G-SHAPE-HIERARCHY, G5-MD-FRACTION-LINE-PLOTS, G5-MD-UNIT-RELATIONSHIPS, G5-MD-VOLUME-FORMULAS, G5-MD-VOLUME-UNIT-CUBES, G5-NBT-DECIMAL-ADD-SUBTRACT, G5-NBT-DECIMAL-COMPARE, G5-NBT-DECIMAL-DIVIDE-BY-WHOLE, G5-NBT-DECIMAL-MULTIPLY, G5-NBT-DECIMAL-READ-WRITE, G5-NBT-DECIMAL-ROUND, G5-NBT-DIVISION-ESTIMATE, G5-NBT-LONG-DIVISION, G5-NBT-MULTIPLICATION-ESTIMATE, G5-NBT-POWERS-OF-TEN, G5-NF-ADD-SUBTRACT-FRACTIONS, G5-NF-EQUIVALENCE-BRIDGE, G5-NF-FRACTION-AREA-MULTIPLY, G5-NF-FRACTION-AS-DIVISION, G5-NF-FRACTION-MULTIPLY-WHOLE, G5-NF-FRACTION-SCALING, G5-NF-UNIT-FRACTION-DIVISION, G5-PREREQ-AREA-ARRAY-STRUCTURE, G5-PREREQ-FRACTION-UNIT-WHOLE
- partial: G5-NBT-MULTIDIGIT-MULTIPLY, G5-OA-NUMERICAL-EXPRESSIONS, G5-OA-PATTERN-RULES
- reference_grounded: G5-G-COORDINATE-PROBLEMS, G5-MD-MEASUREMENT-PROBLEMS, G5-MD-VOLUME-ADDITIVE, G5-NF-FRACTION-MULTIPLY-PROBLEMS, G5-NF-FRACTION-WORD-PROBLEMS
- uncovered: none
<!-- CALCULATED:END -->

Historical comparison: the old report stated a union of 30, excluding both OA nodes and three geometry nodes. The old catalog explicitly associated coordinate geometry with node 2 as well, yielding 31 literal associations. This discrepancy is preserved above as a historical audit, not repaired into false direct coverage. The corrected D definition separates contextual and partial associations, so lower percentages reflect both the added decimal node and more conservative qualification; they do not measure a decline in implemented capability.

## Recommended Grade 5 Math Renderer Foundation

Nine Core families remain proposed: the prior eight become nine because the measurement/data shell is split. Priorities remain design judgments about representation diversity and reuse, not evidence of relative learning gains.

| Family | Role retained / correction | Complexity | Photo reconstruction / cross-grade reuse |
|---|---|---|---|
| `fraction_model_workspace` | whole, equivalence, operations, sharing and scaling | medium | high / high |
| `place_value_workspace` | place chart and explicit decimal ADD/SUBTRACT conservation | medium | high / high |
| `area_array_model` | distributive and fractional area state; algorithm gap remains P | medium | high / high |
| `number_line` | magnitude, rounding, estimation and fraction relation | low–medium | medium / high |
| `division_workspace` | broader division strategies; mode-specific states | medium–high | very high / medium–high |
| `measurement_conversion_workspace` | quantities, units, exact same-system conversion | medium | medium / medium–high |
| `line_plot_workspace` | observation multiset, fractional scale and bounded aggregates | medium | medium / medium–high |
| `volume_composer` | occupancy/layers/formulas; contextual additive volume is R | medium–high | high / medium |
| `coordinate_geometry_plane` | axes and point states; pattern support only P | medium | medium / high |

### Recommended initial build batch

Retain `number_line`, `place_value_workspace`, `fraction_model_workspace`, and `division_workspace`. This matches the promoted recommendation; the research baseline's `long_division_workspace` becomes the broader family name. It is a proposal for four independently reviewable activities, not four fully implemented families. Core-family and batch-family totals above assume the full declared proposal; the first-slice totals count only the narrower activity descriptions below.

| Family / directly served full-family nodes | Smallest useful first activity and state | Bounded actions and validation | Alternatives, prerequisites and what waits |
|---|---|---|---|
| number_line / 5, 6, 7, 13, 18 | Compare two nonnegative decimals to thousandths and round to an authored place; exact scale, operands, points and interval endpoints. First-slice D: 5, 6. | Move/select exact snapped point; choose relation/rounding endpoint; explicit submit. Exact rational position, order and rounding checks; visual position alone is not correctness. | Place chart alternative; requires decimal-place/unit meaning. Powers of ten, product estimates and fraction modes wait. Tutor handles explanations. |
| place_value_workspace / 3, 4, 5, 6, 36 | Add/subtract nonnegative decimals to hundredths with fixed operands, typed place counts, equivalent exchanges and written result; subtraction has a ≥ b. First-slice D: 36; chart support for 3–6 is partial (5–6 also have D via the number line). | Align, exchange, combine/remove, enter bounded numeric result, submit. Integer-hundredths conservation and equation validation; preserve attempted model and original operands. | Written algorithm or number-line jumps; prerequisites are decimal place value and whole-number regrouping. Full read/write/number-name/exponent modes and decimal multiply/divide wait. |
| fraction_model_workspace / 13, 14, 16, 17, 18, 19, 21, 34 | Equivalence with one explicit fixed whole and two bars using equal partitions; declared bounded denominators. First-slice D: 13, 34; node 14 only P. | Partition/refine, select amount, compare equivalents, submit. Rational equality, common whole and equal-unit checks; accept multiple equivalent denominators, not one gesture path. | Number line and small-denominator circles; needs unit fraction/whole meaning. Operation construction, mixed-number arithmetic, area multiplication, scaling and sharing modes wait. |
| division_workspace / 10, 11, 12 | Two-digit whole dividend, positive one-digit divisor, quotient chunks and residual. First-slice P: 10, 11; no full-node D credit. | Choose bounded numeric chunk, subtract corresponding multiple, explicit submit. Conserve d = v × sum(chunks) + residual; final 0 ≤ residual < v; reject over-allocation. | Equal groups/area links and written algorithm are alternatives. Requires multiplication/subtraction/place value. Four-digit/two-digit range, other modes, decimal division and decimal-divisor policy wait. |

All actions are proposals for future exact-version Activity/Renderer contracts. Explorations are RECORD_ONLY; only a contract-declared explicit submission is Tutor-triggering. Server-owned semantic Events and Snapshot retain original submission and durable correctness. The accepted host/session/Runtime-03 supplies infrastructure; browser state is not authority. The sole Student-facing Tutor owns language/reasoning; no Canvas intelligence/Personal Facts writes.

The batch leaves expression interpretation and measurement/data activities for later, as the earlier recommendation did. Its diversity rationale is retained, while the calculation now exposes that it does not maximize coverage. Promoting expression, algorithms or measurement earlier would require a Product Owner priority decision, not a silent substitution.

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

`number_line`, `place_value_workspace`, `area_array_model`, `fraction_model_workspace`, `coordinate_geometry_plane`, `shape_property_explorer`, and `expression_pattern` are **HIGH** reuse. `division_workspace` and `measurement_conversion_workspace` and `line_plot_workspace` are **MEDIUM–HIGH**. `volume_composer` is **MEDIUM**. These are estimates from mathematical progression, not a research claim about later curricula.
