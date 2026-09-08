PROCESS_CAPABILITY_PACK_V2

Execution-enabled only for PROCESS semantic proposals. The exact frozen pack
defines allowed motion intents: SEQUENCE permits REVEAL_IN_ORDER,
TRACE_SEQUENCE, TRANSITION_FOCUS, EMPHASIZE_RELATION; CYCLE permits
REVEAL_IN_ORDER, TRACE_CYCLE, TRANSITION_FOCUS, EMPHASIZE_RELATION. This pack
does not authorize a renderer, timing, persistence, callbacks, extra model
calls, Tutor dialogue, or any write outside the admitted Specialist proposal.

For CYCLE, stages are an ordered semantic cycle. For N stages, output exactly N
relations: each relation connects a stage to its next stage, and the final
relation connects the last stage to the first stage. Every relation must use
admitted semantic support. Do not invent a return relation unless the Frozen
Pack admits that cycle. Use `TRACE_CYCLE` only when it is allowed; never use
`TRACE_SEQUENCE` for CYCLE.

For SEQUENCE, output exactly N-1 forward relations for N stages, with no final
return relation.
