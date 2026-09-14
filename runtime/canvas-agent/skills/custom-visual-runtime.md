# Custom visual authoring contract
Current product acceptance is desktop: design the complete experience for a 640px
Workspace pane and use extra space at 960px. Mobile is deferred. Use native HTML
text/control sizes or responsive SVG coordinates; never scale text below readable
screen size when adapting between desktop pane widths.
Only create_custom_visual accepts a complete JavaScript source. A defective immutable Manifest or parameter contract
may require one replacement CREATE with explicit replacement_reason and a new
block_id. Source-only defects use refinement; never change canonical meaning
through source edits. Superseded candidates cannot appear in the final plan.
refine_custom_visual accepts 1-8 exact before/after source edits. There are at most
four authoring attempts total, including failed calls, with no more than two CREATEs.
After one CREATE, an unused replacement slot can fund a third source correction;
after two CREATE attempts only two corrections remain. Repair all concrete findings together; each before must occur exactly once
in the current source. Preserve unaffected code and all canonical semantics.
Define window.mount(root, params, bridge) using ordinary DOM and native SVG.
No network, imports, storage, navigation, parent access or application writes.
Instance facts and labels come from params; do not hardcode the current example.
Use numeric parameter values for numeric facts and booleans for flags; strings are for labels/IDs.
Parameters are at most 32 named scalars; each string is at most 240 characters. Split long labels into separate parameters. Never truncate encoded JSON to fit a string limit; prefer separate scalar facts and labels. If an array/object is encoded as a JSON string, use
JSON.parse before indexing, mapping or iterating it. Do not treat a JSON string
as an array. Bind controls to real elements after creation; rebind recreated DOM.

Use bridge.control(element, semantic_id, action) for each actual interactive
element, with IDs/actions from your Manifest. It binds the diagnostic DOM
attributes and returns a handle:
- handle.read(initialValue) RETURNS the restored value using the fallback's type.
  Assign its result to your render state BEFORE computing geometry or labels.
  Reading after drawing does not update already-created shapes. Calling read
  and discarding its return does not restore any local variable or DOM control.
- handle.emit(newValue) serializes a mutation, updates sandbox-local state
  immediately, and sends its canonical event. Then render the updated state.
- handle.activate(callback) binds click and Enter/Space activation for non-native
  controls, and uses native keyboard behavior on native controls. Name the element
  accessibly. The callback owns emit/render, e.g. h.activate(()=>{h.emit();render()}).
  Rebinding replaces the previous helper callback. Do not add parallel onclick or
  keyboard handlers for the same activation. This optional helper does not alter
  historical controls that do not call it.
- handle.drag({move, end, dropTarget}) binds reliable mouse/touch dragging.
  move/end callbacks receive {clientX, clientY, target}; target is the element
  under the pointer. Update local geometry in move; return the final value from
  end to emit one canonical mutation. For sorting/reordering supply a meaningful
  alternate dropTarget DOM element (or its DOM id), so the browser can exercise
  the actual drop. It manages pointer capture even when inner DOM is redrawn.
  Add a keyboard/tap alternative as appropriate. Do not combine this helper
  with native HTML dragstart/drop handlers.
- For SELECT/FOCUS, call handle.emit() with no value. handle.selected supports
  immediate choice feedback. Selection is identity-only, not a persisted value;
  do not restore a choice through read or invent a value-bearing choice state.

Bootstrap restored state with bridge.read(semanticId, initialValue) BEFORE drawing.
Use the same named semanticId constant when later binding the actual control.
handle.read is also valid when the control exists before drawing dependent content.
A single state field has one semantic ID shared by all controls that change it;
do not create competing saved slots per button. Reset must emit the complete
changed state through those same field IDs, not merely reset local variables.
Persist the complete state required for reconstruction, including all coordinates
of a movable object. Local pointer movement may render continuously; emit the
final composite value on release. Parameters supply initial instance facts. Read those actual values; never advertise a parameter while hardcoding its initial value in source. Use nullish fallback for numbers so zero remains zero.
Choice feedback shows selection, never claims correctness or mastery.

The low-level bridge.read/emit API remains available for advanced bindings and
historical packages. It uses exact matching semantic IDs and string values.
Every declared interaction needs an operable binding. Use targets at least 24px
in both dimensions at the smaller desktop width, preferably larger for children, and native
controls or named, focusable elements with keyboard handlers. Use handle.drag for direct manipulation; it binds the gesture and drop-target
metadata automatically. Native HTML drag/drop alone does not work on touch.
The browser exercises these real controls at 960px and 640px desktop pane widths; annotations
are not substitutes for working event handlers. Never add hidden test controls.

Budget the entire root, including labels and controls, within 384px height at wide widths
and 512px height at widths <=520px. Preview and Studio use these same heights.
Read the actual root dimensions; representation plus headers/controls must fit. Use available
space responsively; do not merely scale a desktop composition down.

Keep local changes immediate, emit meaningful mutations on release/change, and
render from the same state on mount and updates. Derive coupled geometry and
labels together. Convert SVG pointer coordinates via getScreenCTM().inverse().
Avoid replacing a captured pointer target during dragging. Handle zero, bounds,
signed quantities and degenerate states explicitly; preserve exact relationships.
Review initial, post-action and replay screenshots plus event diagnostics. Refine
concrete defects within the remaining authoring budget; do not alter canonical meaning or retry
indefinitely. If refinement is exhausted, return the required plan referencing the current
candidate with a failed visual_review and its unresolved issues. This is a failure
report, not acceptance: the application rejects that candidate. Never omit the
required plan fields to express failure. Technical success alone is not visual acceptance.

Target text at 14 actual screen pixels or larger at both supported desktop workspace
widths. Treat 12px as an absolute acceptance floor, not a design target. When SVG
viewBox or responsive scaling is used, calculate the resulting screen size and preserve
enough margin so labels do not approach the 12px rejection threshold. Prefer larger
readable labels for child-facing educational content. SVG viewBox scaling scales fonts
and hit targets too: declared font-size is not final screen size.
Compute the screen scale from BOTH available width and height before sizing labels
and targets; changing plot proportions during repair requires recalculating them.
When equal geometric units carry meaning, use one pixels-per-unit scale for both
axes, fit the logical extent into the remaining plot area, and center spare space.
Do not stretch a meaningful grid to fill a rectangle.
Do not add interaction or reset controls unless they serve the brief.

Low-level bridge.emit has signature bridge.emit(action, semantic_id, {to_value: string});
bridge.emit(semantic_id, value) is invalid. Prefer the bound handle.emit(value).
Mutation values must fit the canonical 240-character event value bound; use compact IDs.

Preview checks restoration after EACH value-bearing action, not only after the final
reset. Every saved field must use the same semantic ID for read and emit. A handle
belongs to one concrete DOM element: if render replaces that element, create and
bind a new handle for its replacement, including after resize. Do not cache handles
across element replacement.
