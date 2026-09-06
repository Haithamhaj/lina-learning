# CURR-RENDER-MATH-01 — Proposed Renderer Catalog

**Status:** Conceptual catalog only. Names and payloads are planning vocabulary, not approved API/schema names. All proposed actions must use the accepted application-owned Studio event envelope and exact-version subject-capability validation when separately implemented. A renderer never becomes Tutor, safety, persistence, or Learning Intelligence authority.

| Renderer key | Purpose and covered concepts | Modes / configuration concept | Student actions and semantic events | Validator / state | A11y, locale, mobile, fallback | Technology / priority |
|---|---|---|---|---|---|---|
| `number_line` | Decimal comparison/rounding, powers-of-ten shifts, fraction equivalence/scaling, estimates; 3, 5–7, 13, 18 | display, guided, construct; domain, scale, marks, intervals, labels, assistance | place/move point; choose interval; commit (`POINT_PLACED`, `INTERVAL_SELECTED`, `REASON_SUBMITTED`) | numeric coordinate/range; selected interval; no free pixel truth | keyboard increment/decrement; text endpoints/table; math LTR, prose `dir=auto`; responsive vertical alternative; static labelled line | React/SVG; **Core** |
| `place_value_workspace` | Direct bounded support: 3–6, 36; partial operation bridge only: 9, 12 | chart, decomposition, powers-of-ten/exponent link, shift, decimal add/subtract; typed places, operands, operator, exact values, target form, locale | assign digit; compose expansion; exchange equivalent units; combine/remove; compare; submit (`DIGIT_ASSIGNED`, `DECOMPOSITION_SUBMITTED`; new operation names remain proposals) | digit/place equality and exact decimal-operation conservation; explicit place columns; exchanges never change operand value | header/cell relationship announced; LTR columns; on mobile one place strip plus summary; accessible table fallback | React DOM/SVG; **Core** |
| `area_array_model` | Whole/decimal multiplication, fraction × whole, fraction area, area prerequisites; 8–9, 17, 19–20, 35 | display, partition, partial-products; factors, partitions, units, fractions | partition; fill product; shade region; submit (`PARTITION_CREATED`, `PARTIAL_PRODUCT_ENTERED`, `REGION_SELECTED`) | factor/partition/product constraints; allow equivalent decompositions | row/column table and equation alternative; buttons for each action; mobile vertical layers; static equation/diagram fallback | React/SVG; **Core** |
| `fraction_model_workspace` | Equivalence, fraction operations, sharing, scaling; 13–21, 34 | bars, equal groups, area grid, small-denominator circle; whole, denominator, operation, target | partition; shade; distribute; compare; submit (`WHOLE_DECLARED`, `PARTITION_SET`, `FRACTION_COMMITTED`) | equal partition, common-whole, equivalence, operation result | screen-reader fraction grammar and list form; no color-only meaning; mobile bars; plain fraction/equation fallback | React/SVG; **Core** |
| `division_workspace` | Direct family proposal: estimate and whole/decimal-by-whole division, 10–12; mode-specific support below | equal groups; area model; partial quotients; standard algorithm/long division; decimal division domain | allocate typed quantities, partition rectangle, choose quotient chunk, submit step/configuration; bring-down only in algorithm mode | mode-specific conservation plus exact quotient/residual; alternative valid chunks; decimal scaling tracked | group/area table or ordered step transcript; keyboard controls; single current step on mobile | React DOM/SVG; **Core**; first slice is partial quotients only |
| `measurement_conversion_workspace` | Direct: 22; reference-grounded: 23 | same-system unit table/scale; typed dimension, exact conversion factors, source quantity, target unit | choose allowlisted unit; enter equivalent quantity; submit table | unit dimension and exact conversion equality; contextual interpretation remains Tutor-owned | announced source/factor/destination sentence; keyboard numeric entry; compact LTR value rows | React/SVG; **Core**, later than Batch 1 |
| `line_plot_workspace` | Direct bounded mathematical support: 24 | observation IDs, rational values, unit, axis increment, multiplicities, authored aggregate question | plot/remove observation, select interval, submit rational aggregate | exact observation multiset, frequency, fraction arithmetic; not marks alone | frequency-table fallback; tap palette/buttons and keyboard placement; scroll-safe axes | React/SVG; **Core**, later than Batch 1 |
| `volume_composer` | cube filling, formulas, composite-prism additivity; 25–27 | display, build, split; dimensions, allowed decompositions, unit cube | add/remove layer; split prism; enter formula; submit (`LAYER_COMMITTED`, `PRISM_SPLIT`, `VOLUME_SUBMITTED`) | grid occupancy; rectangular prism dimensions; additive volume; no overlap/gaps | layer list / 2D grid alternative; buttons and steppers; mobile starts 2D; narrated static layers | React/SVG; optional Konva only if constrained spatial editing proves necessary; **Core** |
| `coordinate_geometry_plane` | axes, plotting/interpreting, coordinate problems; 2, 28–30 | display, plot, read; axis ranges, scale, point set, context labels | select/plot/move point; label; submit (`POINT_PLACED`, `POINT_LABELED`, `COORDINATE_SUBMITTED`) | snapped coordinate state; point set and labels | point-list/table alternative; keyboard coordinate entry; pan/zoom controls, not gesture-only; static graph fallback | React/SVG; JSXGraph only after proof of a material geometry benefit; **Core** |
| `shape_property_explorer` | shape attributes and category hierarchy; 31–33 | inspect, sort, construct; shape set, properties, category graph | label property; sort; assert relation (`PROPERTY_LABELED`, `SHAPE_CLASSIFIED`, `RELATION_SUBMITTED`) | geometry property graph and hierarchy constraints | property table, labelled diagrams, tap-to-sort; mobile one category at a time; static classification fallback | React/SVG; **Second wave** |
| `expression_pattern` | numerical expressions/pattern rules; 1–2 | display, assemble, rule-table; tokens, precedence, sequence rule | group/reorder/enter; submit (`EXPRESSION_GROUPED`, `RULE_ENTERED`, `PATTERN_TERM_SUBMITTED`) | parser/equality/pattern rule; multiple equivalent forms allowed | linearized expression and table; keyboard-first; compact stacked view; plain text fallback | React DOM + MathLive only if structured entry proves needed; **Second wave** |

## Corrected family decisions — LINA DESIGN RECOMMENDATIONS

### Division modes and scope

The family is broader than any one first activity. 5.NBT.B.6 supports strategy-based whole-number division; standard-algorithm fluency is stated in 6.NS.B.2, not mandated here as Grade 5's sole method. See source trace C in [10_CORRECTION_RECORD.md](10_CORRECTION_RECORD.md).

| Approved planning mode | Mathematical state / invariant | Operations / validator | Boundary |
|---|---|---|---|
| Equal groups | conserved quantity, number of groups or size of each group, unallocated residual | allocate/reallocate; check equal completed groups and conservation | distinguish sharing from measuring; small quantities first; not thousands of draggable items |
| Area model | dividend as area, divisor as one side, accumulated other-side widths and residual area | partition/add rectangle; exact area and width sum | relates division to multiplication; not a generic geometry surface |
| Partial quotients | immutable dividend/divisor, chosen quotient chunks, exact residual | choose chunk k; residual decreases by divisor × k; quotient is sum of chunks | accept any admissible chunk order; no forced pre-authored path |
| Standard algorithm / long division | place-indexed partial dividends, quotient digits, subtraction and next-place transition | submit digit/row/bring-down; validate place-weighted value and final result | optional later method; each row remainder must be interpreted in its place, not as an unscaled final remainder |
| Decimal division | exact decimal operands, declared precision, optional common scaling, same quotient | exchange fractional units or scale both operands equally; validate exact equality | number domain that can accompany several methods; node 12 covers decimal-by-whole only; decimal divisors and recurring results wait for a separate bounded slice |

For nonnegative whole-number division: d = v × q_acc + r, v > 0, r ≥ 0; final integer quotient requires 0 ≤ r < v. Exact terminating decimal results require r = 0 in common units. No binary-floating tolerance grants arithmetic correctness. First activity: small whole-number partial quotients, not all five modes; coverage credit for the full node 11 remains partial at that first-slice boundary.

### Measurement/data: bounded comparison and recommendation

| Concern | One measurement_data_workspace shell + explicit sub-renderers | Separate measurement_conversion_workspace and line_plot_workspace |
|---|---|---|
| State | discriminated conversion/plot variants under a shell | one conversion table; one observation multiset/axis |
| Semantic operations | shell routes incompatible conversion and plot operations | unit/value actions stay distinct from observation-placement/aggregate actions |
| Validators | still two validators; shell must dispatch and reject cross-mode payloads | independent dimension/factor checks and multiset/fraction checks |
| UI | common header plus mode-specific table or axis; mode switch needs recovery semantics | compact form/table versus axis/palette; each has its own accessible fallback |
| Actual reuse | labels, rational arithmetic, buttons; little mathematical state reuse | same modest primitives can be reused without sharing lifecycle/state |
| Testing | two suites plus shell dispatch, mode-switch, stale-event and restore cases | two exact-version activity suites through accepted Studio dispatch; no cross-mode transitions |
| Complexity | fewer top-level names but extra union/routing/mode-switch contract | more catalog entries, simpler independent state/recovery boundaries |

Recommend the **separate capabilities**. Conversion and line-plot data have distinct source truth and invalid states; the accepted Studio host already supplies common presentation/lifecycle dispatch. Tradeoff: one additional Core family and separate fixtures; no generic visualization framework or new shared runtime is justified. 5.MD.A.1 and 5.MD.B.2 motivate different mathematical requirements, not this software naming decision. The former shell name is historical planning vocabulary only.

### Coverage qualifications

The catalog's numeric lists describe candidate associations; [coverage_mapping.json](coverage_mapping.json) is the exact D/P/R allocation. Decimal display alone earns no operation credit. Area/array multiplication (8) is partial because the existing proposal does not cover the standard-algorithm/fluency component. Expression (1) remains partial even after its mapping correction: evaluation and bounded assembly can be checked, but equality alone does not verify interpretation/writing. Coordinate pattern support (2) supplies plotting, not a complete pattern-generation/relationship activity. Contextual nodes 15, 20, 23, 27, 30 are R, excluded from D counts. These are limitations of proposed coverage, not additional release blockers.

### Accepted cross-grade foundation

`ten_frame_group_transfer` is DONE / ACCEPTED in the governing records: exact-version Make-Ten, conserved total in `9 + 6 → 10 + 5`, `TRANSFER_ITEM` record-only, submit-only Runtime-03 continuation, server Event/Snapshot authority. It sits outside this catalog's Grade 5 Core and Batch sets and outside both numerators and denominators. Its implementation proves reusable architecture, not implementation of `place_value_workspace` or any other Grade 5 family.

## Required common behavior

- **Display-only is valid.** Interactivity must be chosen for a learning purpose, not because the capability exists.
- **Failure is non-blocking.** Render a concise explanation, notation, and retry/report control; leave Tutor conversation usable.
- **Photo-work compatibility:** every renderer declares whether it can later support `SOURCE_VIEW`, `ANNOTATION`, `RECONSTRUCTION`, and `SIDE_BY_SIDE`. `division_workspace`, `place_value_workspace`, `fraction_model_workspace`, `area_array_model`, `measurement_conversion_workspace`, `line_plot_workspace`, and `volume_composer` are strong reconstruction candidates. All can be shown beside the original; none replaces it.
- **Animation:** Motion may orient (digit shift, layer reveal, partition transition) or acknowledge a valid committed action. It must have reduced-motion behavior and must not communicate correctness by motion alone.
- **Accessibility:** all meaningful state has text; every drag action has a keyboard/button alternative; color is redundant; focus and error text are programmatically exposed.

## Specialist gap map

| Gap | Classification | Why not prebuild now |
|---|---|---|
| Novel multi-representation scene that composes several known renderers around a Tutor objective | Canvas Specialist candidate | Only after an eligible deterministic gap, safe typed plan, and non-blocking application scheduling |
| Handwritten or photographed page markup | source-specific annotation | Needs separately approved Vision/asset pipeline; original remains source authority |
| Perspective/physical simulation or rich 3D manipulation | future simulation | Must show learning value, device/a11y fallback, and performance evidence |
| Rare publisher-specific diagram | rare variant | Better map to concept/renderer configuration after McGraw evidence arrives |
| Decorative illustration | generated-image candidate only | Not a correctness/interaction surface and not a substitute for a renderer |
| Straight arithmetic explanation with no representation need | unnecessary Canvas case | Tutor text/notation is simpler and lower risk |
