# MATH-RENDER-PLACE-VALUE-01 — Acceptance closure

**Status:** DONE / ACCEPTED on 2026-09-07. This accepts only the bounded
`G5-NBT-DECIMAL-ADD-SUBTRACT` child; `MATH-RENDER-BATCH-01` remains
**UMBRELLA / NOT ACCEPTED** and no coverage calculation changes.

## Accepted contract

The activity has 12 authored, server-owned configurations, not an unrestricted
generator. ADD and SUBTRACT use integer hundredths: operands are 0–99.99, ADD
results are 0–199.98, and subtraction requires `a >= b`. The fixed columns are
hundreds, tens, ones, tenths, and hundredths (weights 10000, 1000, 100, 10,
and 1). Immutable source configuration/operands remain separate from mutable
pools and the attempted written result.

ADD conserves `V(a) + V(b) + V(result) = a + b`; SUBTRACT conserves remaining
plus removed against the original minuend and limits removed value to the
subtrahend. Exchanges preserve value, valid nonnormalized counts and alternate
legal exchanges are accepted, and over-removal/fabricated state rejects without
mutation. The contract covers carry, zero/boundary cases, zero-column
decomposition, and separate model-completeness versus written-answer feedback.

The accepted exact versions are MATH `subject-profile-v4`, activity and
renderer `decimal-place-value-activity-v1` / `decimal-place-value-renderer-v1`,
and the matching `decimal-place-value-<kind>-v1` scene, catalog, state,
action, reducer, and validator contracts. Exact authored source reference and
safe Scene identity are persisted through the existing activation path.

The existing `/student/daily` Renderer Host supports RECORD_ONLY exploration
and result editing; explicit submission alone creates one source-linked
Runtime-03 interaction/Tutor continuation. Original submitted state remains
distinct from later current Workspace state. Persistence, ownership, rejection,
idempotent replay, reload, rebuild, localized recovery, accessible controls,
and Arabic/RTL surrounding UI are within the accepted path. There is no
fabricated Student message or direct Canvas Evidence, Personal Facts, or
Learning Intelligence write. Historical profiles, Number-Line, and Make-Ten
compatibility remain preserved.

## Reviewed verification and evidence limits

The retained reviewed evidence records: focused Python **104 passed**; full
isolated Python **1,049 passed, 7 gated skips** (two opt-in real-Luna and five
opt-in S3/cloud-write tests); web regressions **48 passed**; typecheck,
production build, Alembic, and whitespace checks passed; and independent
read-only review **0 Critical / 0 Important / 0 Minor**. These are reviewed
results, not tests rerun for this descriptive closure.

Authenticated `/student/daily` evidence covered four configurations, mouse,
trusted browser-emulated touch, keyboard, cancellation/outside release, real
422/409 reconciliation, wrong-answer correction, explicit configured mock
Tutor continuation, same-session reload, Arabic/narrow layout, and reduced
motion. The reported final scenario observed Event 69, Scene version 14, five
mock continuations, and zero fabricated Student messages. Prepared
configuration selection is not natural model selection; configured mock
continuations are not live teaching-quality evidence; emulated touch is not
physical-device proof. No real-Lina or deployment claim is made.

Production-mode serving remained blocked in this environment by the reported
missing Clerk secret. The production build and authenticated browser acceptance
passed. This is an OPEN later production-serving/deployment readiness item; it
does not assert that Clerk is globally unconfigured or that the issue is fixed.

## Boundaries and retained records

Read/write/number-name and exponent modes, decimal multiplication/division,
fraction/division work, Voice/Vision, image annotation, NotebookLM, Replit,
deployment, real-Lina baseline, `STUDIO-ACCEPT-01`, and all other renderer
tasks remain unpromoted. The raw implementation record, review, screenshots,
traces, logs, browser state, and exact local identities remain preserved
locally and are intentionally not committed because they contain private local
identifiers or raw evidence.

## Authorized EOF-only exception

The Product Owner authorized one post-review source exception solely to remove
the redundant final blank line in `services/studio/decimal_place_value_activation.py`.
The retained pre-change local copy hashes to
`f3332fc97930c3691676628160930834563bd0a1a43f76773bb73889fa9e5b4f`; the
final one-newline version hashes to
`3637a88a269a0e3af5557f3d2cb8f71dc9582887c971b6e0925cf659142673e3`.
The exact diff removes only that blank line; both versions parse successfully
and their `ast.dump(ast.parse(...), include_attributes=False)` values are
identical. Every other reviewed production, test, and runner source remains
byte-identical to the final reviewed manifest. The original manifest is
retained as the pre-exception review record and is not asserted to match this
one final file.
