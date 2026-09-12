# Full-Power routing

Canvas has three quality-first routes. They are visual-composition choices, not
teaching decisions.

- Choose **REUSE** when a validated artifact can accurately express the Tutor's
  objective, values, interaction, language, and learner presentation.
- Choose **ADAPT** when the same structure remains strong but its declared
  parameters can change values, labels, locale, density, palette, or optional
  illustration without changing the artifact's educational purpose.
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
