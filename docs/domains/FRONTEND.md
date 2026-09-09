# Daily Student frontend

The current proving ground is Lina, Grade 5, and the Daily Student UI. Long-term, Lina is one coherent primary-to-secondary product whose presentation may become age/grade-aware; this is not a commitment to separate apps or a design for that adaptive system.

The current approved direction is **Learning Chat + Adaptive Learning Workspace**: warm, intelligent, personal, and visually engaging—not preschool/cartoonish, corporate, or noisy. Deep ink is the reading foundation; lavender expresses the Student, mint/teal guides with the Tutor, and restrained apricot/gold marks learning accents. Use soft rounded surfaces and roomy message groups.

Tailwind plus current shadcn-style primitives is the functional baseline. Arabic, English, and mixed-direction interaction are first-class. External visual libraries are references or isolated capability choices, never application architecture.

Chat remains independently usable. A workspace appears only when visual or interactive representation materially improves learning, while preserving typed input, accessibility, reduced motion, narrow layouts, and original-source context. `UI-REFINE-01` must preserve current SSE, session, auth, Safety, and Studio contracts.

## Daily workspace presentation

Daily is a single student conversation, not a dashboard. With no active Studio Scene, it is a natural full-width chat with a reachable composer; an in-progress Canvas composition is expressed in the chat with simple learner-facing language and never by a blank or technical Workspace panel.

When the server Snapshot contains an active Scene, Daily presents a conditional Simple Dock: Chat stays on the physical left and Workspace stays on the physical right. The dock begins at the tablet layout (about 1024px) at roughly 47/53, then settles near 43/57 on wider desktop screens. The grid itself is direction-neutral so Arabic does not reverse the pane geometry; each pane retains its own content direction and independent scrolling. Free resize, a draggable divider, Focus mode, and a mobile redesign are outside this V1 scope.

Workspace visibility is a client-only presentation choice keyed by `scene_id`. Hiding a Scene makes chat full width without mutating Studio state. A later Snapshot for that same Scene stays hidden, a student may reopen it, a different Scene opens automatically, and no active Scene clears the stale local hide choice. Refresh may therefore show the active server Scene again. Workspace content is always the existing `StudioRendererHost` and its authoritative Snapshot, never recreated client content.
