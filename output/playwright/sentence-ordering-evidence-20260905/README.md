# STUDIO-ACT-EN-01 browser evidence

This directory contains an actual Chromium browser matrix against the isolated
`/studio/sentence-ordering-review` mock mount. It is not a Student route,
does not persist Studio state, and makes no live-model or Real Lina claim.

`matrix.cjs` drives native mouse, Chromium-emulated touch, and keyboard input
through the real local React renderer. Its sixteen named cases also check
retry after touch cancellation/outside release, rejected-operation
reconciliation, one explicit submit, English and Arabic direction boundaries,
mixed labels, narrow layout, Arabic keyboard focus traversal, mounted-payload
answer-key absence, keyboard naming/focus/live status, and reduced motion. Each
successful reorder must emit the same identity-based operation:

```json
{
  "action_key": "REORDER_TOKEN",
  "payload": {
    "token_id": "tok-c820",
    "from_index": 1,
    "to_index": 0
  }
}
```

Run it from the worktree while the review server is on port 5001:

```sh
SENTENCE_ORDERING_PLAYWRIGHT=/Users/haitham/.npm/_npx/31e32ef8478fbf80/node_modules/playwright \
  node output/playwright/sentence-ordering-evidence-20260905/matrix.cjs
```
