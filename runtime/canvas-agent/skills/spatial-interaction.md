Use normalized logical coordinates inside a bounded viewport, never physical
pixels. Interaction resolves only to FOCUS, SELECT, MOVE, SET_VALUE, CONNECT,
or SUBMIT. Persist an element and semantic before/after state, never pointer
paths, hover, raw touch data, frames, or incomplete keystrokes. Encode legal
regions/values as constraints and expose affordance only when it has semantic
meaning.

Use direct manipulation only when moving, grouping, or connecting is the intended
learning action. Otherwise prefer a static semantic field. Shape and position may carry
meaning, so do not reduce every object to a rectangular card.
