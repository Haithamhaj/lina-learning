# CS-07: bounded visual capabilities

Import application capabilities from `index.tsx`, and include `toolbelt.css`.
The coordinate board also uses the local `/visual-toolbelt/jsxgraph.css` asset.
All four entry points load only on the client. The existing review route is the
integration example; it has no persistence or Student/Tutor runtime ownership.

| Capability | Controlled input → result | Disposition |
| --- | --- | --- |
| Relation focus | source/target → source/target | KEEP: finite interruptible Motion transition, immediate reduced-motion equivalent |
| Spatial placement | A outside/in B → `{objectId: "object-a", targetId: "target-b" or null}` | KEEP: bounded pointer/touch placement and equivalent keyboard buttons |
| Coordinate construction | integer P, each axis −4…4 → exact integer P | KEEP: grid snapping, pointer/touch/native arrows and labeled numeric controls |
| Math expression | application LaTeX → emitted LaTeX; explicit submit → `{format: "latex", value}` | KEEP: stable controlled field, keyboard/touch input, local fonts, no sounds |

These are deliberately small reusable primitives/examples, not an activity
framework. The application owns configuration, value acceptance and submission.
No technology name, renderer ID or engine option enters the Specialist schema.
Pixels from spatial dragging stay private. Coordinates are mathematical content
in the coordinate construction and are quantized before handoff. Math submission
checks only presence and length (1–200 characters); it is not mathematical syntax
validation or grading. MathLive's emitted LaTeX is preserved without numerical
evaluation. Future activities supply their own meaning and validation.

## Inspection and engineering result

CS-02 already installed Motion, react-konva/Konva, JSXGraph and MathLive and supplied
local proof adapters, browser boundaries, local fonts and JSXGraph `freeBoard`.
Those adapters were reused. The previous source-text lifecycle check was replaced
by actual engine behavior tests; the package guard remains.

- Motion's infinite decorative loop became a controlled 350 ms focus transition.
  The native ProcessView is unchanged: native CSS/SVG remains simpler for its
  accepted Process semantics. Motion is available when richer transformations help.
- Konva gained stable object/target IDs, a controlled value, equivalent keyboard
  controls and ResizeObserver sizing. The label travels with its draggable group. React-Konva destroys the Stage on unmount;
  the wrapper disconnects its observer. A drop proposes a result, then renders
  the application's accepted state, including when the application rejects it.
- JSXGraph's static number-line proof became a bounded integer coordinate plane;
  the accepted SVG decimal number line is unchanged. The wrapper frees boards,
  removes pointer/key listeners and disconnects its observer. Browser testing
  found and fixed a CSS/content-box resize feedback loop (300 → 228 px in 600 ms)
  and native arrow-key movement that initially bypassed the semantic callback.
- MathLive no longer owns the durable value or remounts on callback identity
  changes. Input and external changes reconcile against the parent value; removal
  detaches the input listener and field. A failed inner import retains a plain
  LaTeX input alternative; JSXGraph retains its numeric alternative on failure.
- All wrappers share spacing, colors, rounded surfaces, readable Arabic/English
  prose, mathematical LTR direction, visible focus and usable narrow layouts.

## Verification

Run from the repository root:

```sh
node --test apps/web/tests/cs02-visual-toolbelt-contract.mjs apps/web/tests/toolbelt/semantics.test.cjs
node apps/web/tests/toolbelt/build-harness.cjs
python3 -m http.server 5077 --bind 127.0.0.1 --directory /tmp/lina-cs07-harness
# In another terminal, with an installed Playwright runtime available:
node apps/web/tests/toolbelt/browser.cjs
npm run typecheck
npm run build
git diff --check
```

`NODE_PATH` may point to an existing Playwright installation. The harness uses
installed Next webpack and Sucrase without adding dependencies; it mounts the
actual capability entry points in React StrictMode. `CS07_HARNESS` and `CS07_URL`
override its output directory and URL. Browser outputs go to
`/tmp/lina-cs07-evidence/` (results and wide/narrow/touch images).

The browser matrix covers finite/interrupted/reduced Motion, Konva mouse/touch/
keyboard, JSXGraph exact mouse/touch/native keyboard/number controls, stable
resizing, controlled-value rejection, MathLive physical and virtual keyboards,
explicit submission, empty-input handling, repeated unmount/remount, observer
cleanup, detached input listeners, delayed import cancellation and narrow/wide
layout. Local font/asset requests and browser exceptions are checked.

Authenticated Daily is not included: the web environment has no Clerk secret.
AUTHENTICATED DAILY BROWSER NOT RUN — CLERK CONFIGURATION UNAVAILABLE

Evidence is isolated Chrome engine proof, including emulated touch, not physical
mobile-device or assistive-technology certification. No backend or provider path
changed; no Python tests are required. A future production activity still needs
its own activity-specific accessibility, semantics and end-to-end verification.

Final verification: 18 Chrome browser cases and 12 focused/package/renderer checks
passed; web typecheck, production build and diff whitespace checks passed.
Saved browser evidence: `output/playwright/cs07-toolbelt/` at the repository root.
