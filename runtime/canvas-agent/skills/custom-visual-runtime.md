# Custom visual runtime

Custom source is allowed only through `create_custom_visual` and only when it
materially improves the representation. It is not lesson prose and never has
application authority.

Use a small `window.mount(root, params, bridge)` implementation. Render with
native SVG and ordinary DOM/SVG APIs. Receive facts solely through `params`.
When a meaningful declared learner action happens, use
`bridge.emit(action, semantic_id, { from_value, to_value })`.

Never use network requests, imports, dynamic package loading, cookies, storage,
parent-window access, browser navigation, popups, filesystem APIs, or direct
Studio writes. Do not invent exact values, coordinates, units, or scientific
relationships. If exact values are absent, obtain them through the appropriate
deterministic tool or select a representation that does not claim them.

Prefer a clear focal idea, connected geometry, and useful direct manipulation
over decorative motion. Make labels legible at the learner's calibrated density
and make directionality explicit for Arabic/RTL presentation.
