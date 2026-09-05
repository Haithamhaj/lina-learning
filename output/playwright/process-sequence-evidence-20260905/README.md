# STUDIO-ACT-SCI-01 browser evidence

This directory contains an actual Chromium browser matrix against the isolated
`/studio/process-sequence-review` mock mount. It does not claim a Student route,
real persistence, a live model, or Real Lina evidence.

The runner used installed Google Chrome through the pre-existing cached
Playwright package and writes screenshots plus `results.json`. It verified all
12 required cases on 2026-09-05: mouse center/edge, touch center/edge, keyboard
move, touch cancellation recovery, capture-loss recovery, mouse/touch outside
recovery, rejected operation, Arabic RTL narrow touch, and reduced motion.

Every successful reorder emits exactly:

```json
{
  "action_key": "REORDER_STAGE",
  "payload": {
    "stage_id": "prepare-filter-funnel",
    "from_index": 1,
    "to_index": 0
  }
}
```

The review mount is visibly labelled as mock-only. Its saved trace and rendered
state are assertions about the real browser component, not server persistence.

Run from the worktree while a review server is on port 5001:

```sh
PROCESS_SEQUENCE_PLAYWRIGHT=/Users/haitham/.npm/_npx/31e32ef8478fbf80/node_modules/playwright \
  node output/playwright/process-sequence-evidence-20260905/matrix.cjs
```
