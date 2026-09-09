# STUDIO-ACT-AR-01 completion checklist

| Requirement | Current implementation | Evidence |
| --- | --- | --- |
| Exact Arabic v2 profile, safe seed, validator and reducer | Implemented | focused unit tests |
| Exact activation and Daily Renderer Host dispatch | Implemented | host tests; actual adapter reuse after progress/reload; active schema negative test |
| Strict fixed-fixture reader | Implemented | duplicate/changed-label plus repeated-ID and undeclared-field RED-to-GREEN tests; permutations remain readable |
| Pointer, touch, and button reorder paths | Implemented | authenticated trusted mouse/touch, cancellation/outside/retry, Enter controls; focus boundary corrected and rechecked |
| PostgreSQL activation, ownership, stale, rebuild and idempotency | Implemented and tested | real service/API tests; cross-Student and unknown denial; replay/malformed/stale/state-mismatch no mutation |
| Runtime-03 source/current distinction and provenance | Implemented and tested | actual configured mock Gateway, provider observation, historical source separate from later state; no direct intelligence writes |
| Authenticated `/student/daily` matrix | Executed | fresh real Clerk/CDP observations, durable Events/readback, wrong/correct/alternative submissions, same-session reload |
| Full suite, Alembic and independent final review | Checks and review passed | final full suite 953 passed/7 skipped/exit0; web34/typecheck/build/Alembic pass; fresh read-only review: 0 Critical / 0 Important / 0 Minor |

**Status:** DONE / ACCEPTED — Product Owner acceptance closure on 2026-09-06.
This checklist preserves the implementation/review evidence and its limits; it
does not promote `STUDIO-ACCEPT-01` or authorize deployment.

## Starting gaps and final evidence categories

A. Implementation correctness: preserved prior implementation, then corrected
remaining strict-catalog uniqueness/field checks, boundary focus restoration,
malformed token type validation, exact active-schema reuse and VOS alternative.
B. Missing API/Runtime coverage: added real-route isolation/source-current and
actual mock construction checks; source manifests and JUnit retained.
C. Browser environment: diagnosed missing Next hydration chunks (404); identified
web restart restored200 and the existing Clerk/Daily flow. No auth code changed.
D. Full-suite capture: prior truncated output not reused; this run has durable
stdout/stderr, JUnit and subprocess exit status. Earlier runs are retained as
superseded after subsequent tested corrections, not added to final counts.
E. Final acceptance review: fresh independent read-only review of the complete
Arabic diff against `0ab0286f8073135d3ed43c3575c2cbcb827eacbf` returned
0 Critical / 0 Important / 0 Minor. Product Owner acceptance is recorded in the
governing files. Review inspected recorded browser observations and
durable data, not an independent replay of gestures. Prepared-Scene integration
and browser-emulated touch are evidenced; natural model selection, paid-provider
output, physical-device behavior and real-Lina use are not claimed.

Evidence: `output/playwright/arabic-acceptance-20260906/acceptance-evidence.md`.
