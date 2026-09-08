# CS-05M — Semantic Motion Intelligence

**Parent task:** CS-05 — Process Production Integration  
**Reason:** AUD-03 Product Owner audit finding  
**Status:** IMPLEMENTED / AWAITING PRODUCT OWNER REVIEW  
**Dependencies:** AUD-01 and AUD-02 closed  

CS-05M is a bounded corrective implementation subtask inside CS-05. It enables
application-owned Process semantic motion selection while preserving historical
V1 execution and awareness contracts. It does not constitute CS-05 acceptance.

## Actual implementation

- Added `canvas-specialist-process-proposal-v2` and `process-capability-pack-v2`.
  New admitted packs durably include topology-derived `allowed_motion_intents`.
  Historical V1 packs/runs retain their original identity and remain readable.
- The Worker resolves its proposal schema, validator, Skill, and capability pack
  from each persisted Run. It retains one generation and `max_attempts=1`.
- Production Process seeds carry only approved motion identifiers. Replay state
  remains the existing semantic state; playback/progress is never persisted.
- ProcessView maps all five identifiers application-side, has no timer/loop or
  focus mutation, and disables motion while retaining visible semantic state
  under reduced motion.

## Changed paths

`services/studio/canvas_specialist.py`, `services/studio/visual_order.py`,
`workers/studio_handlers.py`, `services/studio/process_production_acceptance.py`,
`services/studio/subjects/process_production.py`, runtime V2 Skill/pack,
ProcessView/model tests, and current governance state.

## Verification

- Python focused contracts: 14 passed.
- Admission/execution/production/awareness regression selection: 28 passed,
  48 skipped where PostgreSQL integration environment was not selected.
- ProcessView renderer: 14 passed; web typecheck and production build passed.
- Independent read-only CS-05M/AUD-03 review: Critical 0, Important 0 after
  correction and focused rerun.

CS-05 remains IMPLEMENTED / UNDER PRODUCT OWNER AUDIT. CS-06 and CS-07 remain
BLOCKED. No browser-host acceptance, provider-live evidence, or Product Owner
acceptance is claimed by this implementation record.
