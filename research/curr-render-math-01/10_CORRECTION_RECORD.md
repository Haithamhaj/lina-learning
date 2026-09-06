# CURR-RENDER-MATH-01A — Correction Record

**Date:** 2026-09-06. **Status:** Product Owner accepted planning pack;
this closure commit records the acceptance. **Baseline:**
`f62b6ff593485e411a39b0ea91039bfc348e53ca`, `codex/ctx-03` in
`/Users/haitham/development/lina-learning-ctx03` (fetched parity 0/0).

## Seven-correction disposition and traceability

The original ten-file organization is retained. The Git baseline is the old
pack; there is no second planning pack. Source facts below cite the accessible
[official CCSS-M](https://corestandards.org/wp-content/uploads/2023/09/Math_Standards1.pdf)
with exact printed pages/standards. The same A–D wording was corroborated in
the CDE publication listed in [07_SOURCE_LICENSE_MANIFEST.md](07_SOURCE_LICENSE_MANIFEST.md).
Source facts describe education; every proposed key, UI or coverage decision
is a Lina design judgment.

| Correction | Original claim / mapping | SOURCE FACT or repository fact | LINA DESIGN RECOMMENDATION / impact | Disposition |
|---|---|---|---|---|
| A — decimal operations | No addition/subtraction node; decimal display/bridge implicitly stood in for arithmetic | CCSS-M p.35, 5.NBT.B.7 includes decimal addition/subtraction to hundredths with modeled strategies linked to written reasoning | Add node 36, `G5-NBT-DECIMAL-ADD-SUBTRACT`; place-value operation mode, exact unit exchanges, combine/remove actions, decimal-operation validator; add one universe member | Corrected in 01–06; explicit state/invariants in 05 |
| B — expressions | Node 1 assigned writing/interpretation to 5.OA.A.1 alone | CCSS-M p.35: .1 concerns grouping/evaluation; .2 writing calculations and interpretation without evaluation | Retain node 1 key; distinguish evaluation from assembly/structural interpretation; equality alone earns only partial coverage | Corrected in 01–06; no forced split or extra denominator count |
| C — division | `long_division_workspace` as family identity; algorithm implied as organizing method | CCSS-M p.35, 5.NBT.B.6 is strategy-based; standard-algorithm division fluency occurs at 6.NS.B.2 (p.42) | Family becomes `division_workspace`, with five declared planning modes; first activity only small whole-number partial quotients; node 11 key retained; node 12 still decimal-by-whole | Corrected planning references; no runtime/persisted identity changes |
| D — measurement/data | One shell combined conversion and line-plot states without resolving its boundary | CCSS-M p.37: 5.MD.A.1 concerns within-system conversions and contextual problems; .B.2 fractional measurement plots and fraction operations | Split to `measurement_conversion_workspace` and `line_plot_workspace`; distinct state/action/validator/restore boundaries; one extra Core family, no added concept | Comparison and tradeoff in 03; consistent 02–06 references |
| E — Make-Ten | Accepted foundation missing from planning coverage distinction | Governing Studio plan §14.3 and task overlay STUDIO-ACT-MATH-01 record accepted `ten_frame_group_transfer` | Accepted cross-grade activity is explicitly outside both numerator and denominator; it implements none of the proposed Grade 5 families | Recorded in 00, 03–04, 06, 09 and machine-readable exclusion |
| F — coverage | 35 nodes, eight Core families, reported 30/35; catalog also associated node 2 with coordinate plane | Repository baseline and deterministic extraction show the historical catalog/report disagreement | Keep bridges; add decimal node; classify partial and contextual support separately; union unique IDs; distinguish full-family from first-slice proposals | Reproducible calculation in 06 and support files |
| G — rights/provenance | Existing manifest distinguishes source versions, restricted uses and unknown McGraw edition | Original manifest remains the rights baseline; current targeted standard checks establish no new reuse permission | Preserve every prior restriction/date; add narrow CDE reference provenance only; leave 08 untouched | No collection, redistribution, rights upgrade or exact-curriculum claim |

## Coverage result and counting impact

The following are **design classifications of proposed support**, not new
educational requirements. Old associations come from baseline 02/03/06; exact
old and new ID sets are in `coverage_mapping.json`. Unlisted node/family
relationships retain their bounded representation purpose.

| Affected association | Old → corrected treatment | Source / section and reason for coverage effect |
|---|---|---|
| Number line, node 3; fraction operations, node 14 | Undifferentiated association → P; matrix-only fraction-operation association made explicit as P | Baseline 02/03; CCSS-M p.35, 5.NBT.A.1–2, and p.36, 5.NF.A.1. The declared point/range validator lacks full place/exponent or operation-construction state. |
| Place value, nodes 9 and 12; new 36 | Operation bridge → P for multiplication/division; explicit modeled ADD/SUBTRACT → D for 36 | A above, CCSS-M p.35, 5.NBT.B.7; numeric display/assignment alone does not supply operation-state validation. |
| Area/array, nodes 7 and 8 | Matrix estimate association → P; multi-digit multiplication → P | Baseline 02 plus CCSS-M p.35, 5.NBT.B.5. Partial-product state is useful but the proposed algorithm path is missing; estimation remains an auxiliary association. |
| Contextual nodes 15, 20, 23, 27, 30 | Previously included in reported direct union → R, excluded from D | Existing concept map and `contextual_answer_validator`; references 5.NF.A.2 / 5.NF.B.6 (p.36), 5.MD.A.1 / 5.MD.C.5c (p.37), 5.G.A.2 (p.38). The renderer verifies quantities, not source interpretation. |
| Pattern node 2 in coordinate/expression families | Catalog association conflicted with exclusion from reported direct union → P in both | CCSS-M p.35, 5.OA.B.3; the current plotting or rule-table proposal does not specify the whole combined activity. |
| Expression node 1 | Equality/assembly treated generically → P | B above; the corrected two-part mapping still needs an explicit writing/interpretation fixture contract for D. |
| First-slice coverage | No independent slice sets → narrower D/P sets in 06 | LINA DESIGN RECOMMENDATION against the full-family node declarations; limited numeric range or missing operation modes cannot inherit full-family D credit. |

Exact counts, percentages, D/P/R/U ID sets and per-renderer scorecards are in
the script-checked block in [06_COVERAGE_AND_PRIORITY.md](06_COVERAGE_AND_PRIORITY.md).
This record deliberately links those numbers rather than maintaining a second
manual scorecard. The baseline report counted contextual tasks with direct
coverage and had inconsistent pattern associations; the correction is a more
conservative planning measurement, not a measured change in learner benefit.

Universe membership keeps every historical key and both bridges. Node 1 is
expanded to accurately distinguish its two requirements, not duplicated. Node
11's method-specific key is kept for planning traceability; its broader meaning
does not require any accepted runtime migration. Node 12 remains a subset of
its cited standard. Full-family support is not credit for all aspects of a
standard; first slices have their own smaller mapped sets. Make-Ten never
enters these sets.

Reproduction command, from repository root:

```sh
python3 research/curr-render-math-01/calculate_coverage.py --check
```

Input: [coverage_mapping.json](coverage_mapping.json), concept-map/catalog
rows and the rendered totals in 06. Output: unique-union totals, exclusive
D/P/R/U IDs and a PASS line for consistency/link checks. Standard library
only; no writes, application imports, tests, package installation or DB access.
Arithmetic reproducibility verifies the recorded classification, not the
educational judgment behind every D/P/R assignment.

## Bounded batch and unresolved assumptions

Retain the promoted four-family recommendation: number line, place value,
fraction model and broader division workspace. It preserves diversity in
mathematical state. The small first activities in 06 cover comparison/rounding,
decimal addition/subtraction, fixed-whole equivalence and small-number partial
quotients. They are proposals only. Other division modes, wider ranges,
fraction operations and full-family capabilities wait for separate review.

The measurement split prioritizes independent mathematical state and testing
over a single shell name; its tradeoff is separate fixture/activity entries.
Source standards do not mandate that design or the batch priority. Existing
Studio contracts remain constraints: one Tutor; exact Activity/Renderer
versions; server-owned Events/Snapshot/correctness; bounded controls;
Activity-declared RECORD_ONLY/submission triggering; no direct intelligence or
Personal Facts writes.

UNRESOLVED ASSUMPTIONS: no verified McGraw edition/year/ISBN/sequence; no
asset-level permission to ingest a school book; no evidence that the proposed
batch optimizes Lina's learning; decimal divisors/recurring quotient policy
remain outside the bounded first activity. Full expression interpretation is
not proved by numeric equality. The exact partial/reference-grounded gaps are
shown by the calculation, not hidden by the headline percentage.

Separately discovered historical citation issues outside A–G are listed in
[09_OPEN_QUESTIONS.md](09_OPEN_QUESTIONS.md): fractional-area node 19 and
classification node 31. Their rows are retained for direction. This run does
not certify every unchanged citation or introduce new release blockers.

## Verification and independent review

Main-agent `python3 research/curr-render-math-01/calculate_coverage.py --check`:
PASS (mapping integrity, calculated scorecard, concept/catalog consistency and
relative links). Tracked `git diff --check` and individual added-file whitespace
checks: PASS. No application tests or acceptance runs were performed.

Fresh independent READ-ONLY review completed: **0 Critical / 0 Important /
0 new Minor findings**. The reviewer read the entire corrected pack and baseline
diff, verified the named standards against official CCSS and CDE corroboration,
reran `--check` successfully, and independently reproduced every D/P/R/U total
with a separate per-concept calculation. The review included the association
traceability table and final concept/matrix table formatting. Historical node
19/31 citation questions above remain disclosed and outside this correction.

At the final reviewed-pack freeze, the scope inventory was nine modified
research documents and three new research support files; all 282 pre-existing
untracked paths were retained, staging was empty, and HEAD was unchanged at
the baseline. No application changes were made.

**CORRECTION COMPLETE — READY FOR PRODUCT OWNER REVIEW.**

## Product Owner acceptance closure

The Product Owner accepted this bounded seven-correction planning pack on
2026-09-06. Acceptance covers the corrected planning basis only: the four
recommended families remain proposed, smallest first activities remain smaller
than full-family scope, and implemented Grade 5 renderer capability coverage
remains 0/36. It does not promote `MATH-RENDER-BATCH-01`, create a renderer,
or resolve the McGraw, rights, learning-benefit, node 19 or node 31 questions.
The independent-review result remains 0 Critical / 0 Important / 0 new Minor.

## Complete file inventory

Modified existing files (all under `research/curr-render-math-01/`):

- `00_RESEARCH_BRIEF.md`
- `01_GRADE5_CONCEPT_MAP.md`
- `02_CONCEPT_REPRESENTATION_MATRIX.md`
- `03_RENDERER_CATALOG.md`
- `04_INTERACTION_PATTERNS.md`
- `05_VALIDATOR_MAP.md`
- `06_COVERAGE_AND_PRIORITY.md`
- `07_SOURCE_LICENSE_MANIFEST.md`
- `09_OPEN_QUESTIONS.md`

New: `10_CORRECTION_RECORD.md`, `coverage_mapping.json`,
`calculate_coverage.py`. Read and unchanged: `08_MCGRAW_ALIGNMENT_PLACEHOLDER.md`.
Governance acceptance metadata is included only in the four authorized
governance files. Application/test/schema/environment files and all prior local
reports/evidence remain unchanged.
