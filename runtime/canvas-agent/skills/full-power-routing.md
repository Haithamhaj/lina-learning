# Full-Power routing

Canvas has three quality-first routes. They are visual-composition choices, not
teaching decisions.

- Choose **REUSE** when a validated artifact can accurately express the Tutor's
  objective, values, interaction, language, and learner presentation.
- Ordinary values, labels, and presentation changes within the declared
  parameter schema remain **REUSE** instances of the same immutable Build.
- Choose **ADAPT** for a generalized capability change that parameters cannot
  express. Submit the changed source through `create_custom_visual` with the
  available `parent_version_id` and a concrete `generalized_change`; settlement
  creates the child Build and Version with explicit lineage.
- Choose **CREATE** when reuse or parameter adaptation would visibly distort or
  weaken the educational representation.

Search before CREATE when reusable candidates are available, but do not force a
weak candidate. A typed Canvas block is a fast path, not a representation cap.

For CREATE, keep academic facts and exact quantities supplied by the Tutor brief
or deterministic tools. Supply stable educational IDs for visible/interactable
entities, relations, quantities, progression, and meaningful actions through
the CREATE tool's semantic fields. Do not send a `semantic_manifest` envelope:
the application constructs its canonical Manifest from those fields. The custom
package receives only safe bound parameters; it
does not receive learner records, source files, memory, implementation secrets,
or application identity.

Custom source correctness checklist:
- Restore each mutable value from `bridge.state[the emitted semantic_id]` before
  falling back to parameters. Use `??`, so zero remains a valid parameter.
- SELECT/FOCUS carry identity only. Give each answer option a distinct declared
  semantic ID; never encode the chosen answer in a SELECT value. For a shared
  value control use SET_VALUE with a declared value-bearing interaction.
- Persist toggle values as strings under the toggle's own semantic ID.
- Convert pointer coordinates with `svg.getScreenCTM().inverse()`; responsive
  viewBox letterboxing makes bounding-box scaling incorrect.
- Keep controls inside the 384px viewport. Use available width for the graph,
  preserve readable labels on narrow screens, and isolate signed math as LTR.
- Exact rational values must retain the signs of both numerator and denominator;
  handle zero and vertical lines explicitly. Visible lines must meet their points.
