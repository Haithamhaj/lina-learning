# MATH-RENDER-NUMBER-LINE-01 — Acceptance Closure

**Status:** DONE / ACCEPTED on 2026-09-07. This is one bounded child of
`MATH-RENDER-BATCH-01`; the umbrella remains **NOT ACCEPTED**. It does not
complete the `number_line` family, change the research coverage count, make
`STUDIO-ACCEPT-01` ready, or promote any later work.

## Accepted bounded contract

- MATH `subject-profile-v3` retains the historical v1/v2 registrations.
  `decimal_number_line` uses activity
  `decimal-number-line-activity-v1`, renderer
  `decimal-number-line-renderer-v1`, seed
  `decimal-number-line-scene-v1`, catalogue
  `decimal-number-line-catalog-v1`, reducer
  `decimal-number-line-reducer-v1`, and state
  `decimal-number-line-state-v1`.
- The two supported modes are `COMPARE` and `ROUND`. Values are exact integer
  thousandths in the inclusive range 0–10000 (0–10); authored display precision
  may retain trailing zeroes, so 0.5 and 0.500 are equal values. There is no
  floating-point or pixel-distance correctness tolerance.
- Rounding is to ones, tenths, or hundredths (steps 1000, 100, 10) with explicit
  nonnegative half-up: a midpoint selects the upper multiple; an exact multiple
  remains unchanged. The bounded catalogue includes less/equal/greater cases,
  below/midpoint/above rounding, carry, zero, exact-multiple, tenths, and ones
  configurations. It is not an arbitrary problem generator.
- `PLACE_POINT` and `SELECT_ANSWER` are RECORD_ONLY; only
  `SUBMIT_CONFIGURATION` is Tutor-triggering. Immutable server configuration is
  separate from mutable Student attempt state. Distinct point identities remain
  distinct when equal values coincide.

## Authority, durability, and interaction

The existing Workspace source-reference seam carries one versioned,
activity-owned `decimal-line:v1:<key>` reference. The server validates that
reference against the issued MATH catalogue, retains it in the Workspace audit,
and the activation adapter verifies lineage, capability, and exact source before
persisting/reusing a Scene. Missing, ambiguous, or unsupported linkage safely
declines activation. The browser receives instructional values and permitted
controls, never an explicit answer key.

The accepted implementation reuses Studio Event/Snapshot/rebuild, the Daily
Renderer Host, the controller/feed reconciliation path, and Runtime-03. Wrong
but in-grid attempts persist bounded feedback; malformed, stale, unknown-point,
cross-Student, and Snapshot-mismatched requests reject without mutation.
Submitted source state remains distinct from a later current Snapshot. Historical
Make-Ten v2 remains available through exact supported host rows rather than a
latest-profile fallback.

The number line is mathematically LTR inside Arabic surrounding UI. Pointer,
trusted browser-emulated touch, and keyboard/button controls resolve to exact
grid values; fine adjustment avoids subpixel selection. Cancel/outside/lost
capture produces no durable operation, while one completed move produces one
semantic RECORD_ONLY operation. Explicit submit remains separate from exploration.

## Verification and evidence disposition

- New closure preflight: six tests passed. The authenticated Daily matrix reused
  the previously verified four prepared authored configurations and seven
  continuations in the intended environment; it includes ordering/equality,
  midpoint rounding, wrong-then-corrected work, input equivalence, cancellation,
  stale rejection/reconciliation, reload, Arabic/English, narrow layout, focus,
  and reduced motion.
- New guarded equality and actual process/database provenance were verified.
  The initial accidental no-ID visit used a worktree environment pointing at a
  demo database and provisioned an empty local Studio runtime. Those retained
  records are **INVALIDATED**, excluded from acceptance, and remain only in
  private local evidence. The intended-environment browser evidence is
  **REUSED**; exact identifiers are intentionally not committed.
- 40 web tests passed; web typecheck and production build passed; whitespace
  checks passed. The previously completed isolated Python suite remains
  applicable because backend/runtime code was unchanged: 984 passed, 7 skipped.
  It was not rerun during closure. Results overlap and are not additive.
- The independent environment addendum reported 0 Critical and 0 Important
  findings. External Clerk state remains **UNVERIFIED**. Browser recovery was
  not forced by injecting/corrupting state; malformed-state recovery is supported
  by focused automated coverage only. Touch proof is trusted browser emulation,
  not physical-device evidence. No paid provider, natural-model selection,
  Canvas Specialist, or real-Lina history run occurred.

Private raw reports, exact local identifiers, logs, screenshots, and machine
outputs remain untracked by design. This committed record is the sanitized
acceptance/disposition summary.
