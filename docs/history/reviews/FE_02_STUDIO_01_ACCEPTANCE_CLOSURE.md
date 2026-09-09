# FE-02-STUDIO-01 — Acceptance Closure

**Status:** DONE / ACCEPTED on 2026-09-06.

## Accepted scope

The real authenticated Daily Student App is the greenfield `/student/daily`
route, separate from protected legacy `/student` and `StudentMathSession`.
It uses one exact Student-owned LearningSession for Chat and Studio. The route
retains that resource in `?session=`; a supplied eligible owned ID resumes only
that session, unknown/cross-Student IDs fail closed, non-resumable sessions use
the implemented bounded response, and only an explicit no-ID request creates a
new Daily session.

The technical Daily session does not determine academic subject. There is no
`DAILY` subject discriminator; `LiveSubjectContext` and reviewed Segment
authority remain independent. Daily Chat keeps the existing Tutor/Safety/auth
authority and its admission/message-identity behavior: pre-admission failure
removes temporary presentation, admitted failure preserves the durable Student
turn and removes only provisional Tutor presentation.

The Workspace is governed only by the server-projected ACTIVE Scene contract
and safe seed. The application-owned Renderer Host accepts exact persisted
Math Make-Ten, Science Process Sequence, and English Sentence Ordering
Activity/Renderer versions. It does not derive a renderer from Tutor prose,
use review fixtures as product truth, or implement an arbitrary artifact
executor. The existing Studio controller, Snapshot, typed operations, and
resumable feed remain the sole Workspace protocol/state authority; browser
state is presentation/optimistic state only.

The accepted corrections cover consistent Event/Scene/Snapshot versions and
rebuild, feed frames materialized within their consistent read transaction,
authoritative operation/reload/reconnect reconciliation, and configured
Gateway/local-provider composition. Runtime-03 remains the only Canvas-origin
Tutor continuation path: a triggering submit creates one continuation with
provenance, while record-only actions create neither a Tutor execution nor fake
Student message. Canvas has no direct Candidate, Evidence, Personal Facts, or
Learning Intelligence write path.

## Evidence record

The final authenticated matrix is **37 PASS / 0 FAIL / 0 NOT VERIFIED**:
**1 NEW** controlled Chromium/CDP-emulated touch case and **36 REUSED**
applicable cases. This is not a claim that 37 cases were freshly run together.

The new touch trace proves a trusted browser-emulated drag of stable item
`ones-group-06`, one accepted `TRANSFER_ITEM`, 9+6 becoming 10+5, Scene and
Snapshot version advancement from 2 to 3, no accidental Submit or extra Tutor
execution, and successful reload of the same OPEN LearningSession. It is not
physical-device certification.

Reviewed verification evidence from 2026-09-06 records one isolated full
Python run of **941 passed / 7 skipped**, **28 web tests passed**, focused
backend/web groups, and prior applicable typecheck, production build, and
Alembic no-model-diff evidence. Counts overlap and are not added. The seven
skips are not passes; they are the documented opt-in external S3/real-Luna
checks. Final source/evidence reviews recorded no Critical, Important, or
Minor findings within their respective review scopes; they did not independently
rerun every test or visual observation.

The raw local reports, screenshots, traces, browser state, and acceptance
artifacts are intentionally retained locally rather than versioned here. They
contain operational/session references or generated output. The committed
verification helpers are limited to the passive touch observer and the
read-only touch-evidence assertion runner; neither contains credentials or
browser-auth state.

## Open observations and limits

Two earlier recovered HTTP 401 episodes remain **OPEN OBSERVATIONS**. Their
root cause is unknown; this closure does not infer token expiry, harmlessness,
or a permanent fix. The prior session-expiry HTTP 409 is a separate historical
lifecycle observation. No new 401 or 409 occurred in the final controlled
touch opening, operation, or same-session reload.

This acceptance does not establish live-model pedagogical quality,
physical-device coverage, deployment, unrestricted daily-use readiness, or a
clean Real-Lina longitudinal-history baseline.

`STUDIO-ACT-AR-01` remains **DEFERRED — POST-FE-02 PRODUCT OWNER
RE-EVALUATION**, neither accepted nor cancelled. `STUDIO-ACCEPT-01` remains
**BLOCKED**; Arabic remains part of final Studio acceptance unless the Product
Owner later implements it, explicitly approves an alternative proof, or
revises the final acceptance matrix. No later Studio task was promoted or
started.

## Closure checks

Before staging, all 248 source/test entries in the final reviewed manifest
matched the worktree; all 38 changed or newly added production/test files were
present in that manifest. `git diff --check` passed. Closure changes only add
this sanitized acceptance record and update the four governing status files;
they do not alter the reviewed production or test source.
