# Lina Full-System Historical Acceptance

## Execution status

- Historical real-Luna Segment Review and deterministic Session Finalization:
  `COMPLETED / CODEX-REPORTED`
- Real-Luna verification: `CODEX-REPORTED REAL-MODEL VERIFICATION`
- Database end-to-end verification: `CODEX-REPORTED ON ISOLATED DATABASE`
- Candidate-free strategy-outcome downstream correction replay:
  `COMPLETED / CODEX-REPORTED`
- SEG-EVID-01E reprocessing/authority compatibility replay:
  `COMPLETED / CODEX-REPORTED`
- Persisted-retention provenance correction:
  `FOCUSED POSTGRESQL VERIFIED / CODEX-REPORTED`
- Tutor personalization verification: `COMPLETED IN THE SEPARATE FULL-SYSTEM JOURNEY`
- Browser / Real-Lina verification: `NO`

The original isolated historical execution preserved the source raw-message
manifest (`145 / 73 / 72 / 38`) with zero source writes. It reconstructed eight
Segments through `openai / gpt-5.6-luna`, completed eight current-contract
Segment Reviews, and finalized the reviewed Session deterministically. The
runtime artifact records 49 staged Findings, 15 withheld Findings, one Session
authority, and 34 Event/Evidence rows. It is Codex-reported execution evidence,
not independently re-executed verification.

## Candidate-free strategy-outcome replay

After the downstream provenance correction, a distinct copy of the isolated
real-Luna acceptance database preserved the historical raw messages and all
completed Review artifacts. Only derived authority/projection rows for the
historical Session were reset in that copy; no Review or raw message was
rewritten and no model call was made. Deterministic finalization from the
persisted current-contract Reviews produced:

- `34` Events and `34` Evidence rows;
- `16` Current State rows, `11` Patterns, and `20` Decision Views;
- `8` Candidate-free, Review-grounded `strategy_outcome` Events;
- `6` strategy-effectiveness Patterns and `5` non-insufficient
  strategy-effectiveness Decision Views.

This verifies that a valid Candidate-free Finding now reaches downstream
strategy-effectiveness interpretation through exact Segment Review provenance.
Malformed provenance remains excluded; Candidate-free misconception Findings
still do not fabricate a recurrence identity. The replay is deterministic and
uses already-persisted real-Luna Reviews; it is not a new AI execution.

## SEG-EVID-01E reprocessing replay

On a further isolated copy of that acceptance database, the actual reprocess
worker reused the eight current-contract, provenance-valid Segment Reviews for
the historical Session. It staged a fresh deterministic run with `34` Events
and `34` Evidence rows before authority activation; only then did it swap the
Session authority and rebuild the authoritative Current State, Pattern, and
Decision projections. The activated run retained `8` Candidate-free,
Review-grounded `strategy_outcome` Events, `6` strategy-effectiveness Patterns,
and `5` non-insufficient strategy-effectiveness Decision Views (within `11`
Patterns and `20` Decision Views for that run).

The worker completed one reprocess Session and recorded a completed reprocess
run. The model-execution ledger changed by `0`: no new Segment Review was
required, so this is deterministic reuse of persisted real-Luna Review
artifacts, not a new real-model execution. The original acceptance database
and raw history were not written. This is Codex-reported copied-database
evidence, not independent re-execution or Real-Lina/browser verification.

## Persisted retention provenance correction

The follow-on correction separates two intentional retention boundaries. A new
Segment Review receives only currently authoritative historical Evidence. A
completed persisted Review validates only its exact recorded anchor IDs and may
use a later completed E-path activation audit to prove that a now-superseded
source Evidence run was authoritative when the Review completed. The proof
still requires the same Student, subject, prior closed Session, exact completed
run, demonstrated/strong Evidence, matching concept, and meaningful delay.
Completed-but-never-authoritative Evidence, malformed audit lineage, foreign
or wrong-run evidence, and insufficient delay are excluded fail-closed.

Codex-reported focused PostgreSQL coverage passed `117`; canonical Python
passed `689`, with `6` skipped. It covers E1 → E1′
authority replacement with E1 preserved, exact Finding resolution, later
Session E-path reprocessing, rejection of an arbitrary old Evidence row, and
fresh model input containing only E1′. No model call occurred. The retained
isolated acceptance database is not configured in this checkout, so no
copied-database replay was performed for this correction; the historical
real-Luna artifacts above remain the recorded original acceptance evidence.

## Verification taxonomy

- Focused E PostgreSQL reprocessing coverage: `14 passed`; relevant
  finalization/review/pattern/decision regression coverage: `109 passed`
  (Codex-reported).
- Canonical Python suite: `686 passed, 6 skipped` (Codex-reported).
- `git diff --check`: clean (Codex-reported).
- Real-Lina/browser validation: `NOT VERIFIED`.

The runtime artifact directory remains the only raw acceptance-artifact
destination. Its JSON and Markdown artifacts omit Student/Tutor raw content,
database credentials, provider secrets, and env contents.

## SEG-EVID-01F Math-only fresh-start execution

### CODE REVIEW / AUTOMATED

The F correction keeps the approved source-grounding, Candidate-free
provenance, and retention contracts strict. Focused PostgreSQL coverage passed
`93`; the canonical Python suite passed `688`, with `6` skipped. These are
Codex-reported executions, not independent re-execution.

### REAL LUNA VERIFIED

On a separately migrated copy of the local demo database, a fresh acceptance
Student completed `12` normal Math Sessions through the production Tutor,
Segment lifecycle, worker, and Model Gateway paths. The persisted ledger has
`19` successful Tutor and `15` successful Segment Review executions, all
`openai / gpt-5.6-luna`. Controlled Student inputs entered only through the
normal runtime; no Tutor output, Finding, Event, Evidence, State, Pattern,
Decision, or Card row was manually authored.

The original initial-learning journey distinguished confusion and a bare wrong
answer from grounded explicit wrong reasoning, preserved correction, and
produced a Candidate-free, server-grounded TeachingMethod `strategy_outcome`.
A changed Math application was conservatively reviewed as `transfer=not_tested`;
no transfer was fabricated. The retention Reviewer received only bounded prior
Session-authorized Evidence identity, exact concept, demonstration state,
observed time, elapsed time, and inclusion reason. A real output once rewrote
the anchored concept separator; strict validation failed closed. Prompt v5 now
requires exact copying, and the normal retry completed a grounded `retained`
Finding. No raw historic transcript, Card conclusion, or unrelated Evidence
entered retention input.

### DATABASE END-TO-END VERIFIED

Every controlled Session was normally closed and received one Session
Authority after deterministic finalization. An initial deliberately
single-Session E replay failed before activation because other authoritative
Sessions still used the superseded prompt identity; rollback preserved the live
authority. The subsequent complete-scope E reprocess reran or reused compatible
current-contract Reviews, staged deterministically, and activated atomically.
Candidate-free Event/Evidence provenance remained exact and auditable. This is
Codex-reported database evidence, not independent re-execution.

### MULTI-SESSION INTELLIGENCE VERIFIED

The `unit-fraction-comparison` support-need Pattern reached `RESOLVED` with
three support and two counter links. Its authorized Evidence lineage is:
supports `653e7095-b65a-4888-b66a-9d7a1f5e1338`,
`0340169c-041c-4d52-a230-4c2b1eda8b49`, and
`c662cd0e-6e9c-425c-ac96-87bd04d5d628`; counters
`a7579048-df51-4591-a7ab-7d1eea619ae4` and
`f747f6d6-6d5a-443e-84c0-7f408383a0cc`. The first independent correction
created a valid counter; the final independently grounded self-correction
completed the policy threshold. A separate misconception-recurrence Pattern
reached `WEAKENING`. `STABLE` was not manufactured because the real diversity
and time requirements were not met.

### TUTOR PERSONALIZATION VERIFIED

A later real Tutor turn selected six relevant Card sources: active Current
State and Pattern rows only. Its context debug recorded zero session-history,
older-continuity, and recent-exchange message IDs; the visible response stayed
natural and exposed no internal label or metadata. The current independent
Student demonstration resulted in a short next challenge rather than stale
remediation. A related Decision View remained available from the authoritative
projection; Decision Views are not separately injected by the Card contract.

### NEGATIVE-MEMORY EXCLUSION VERIFIED

A fresh later long-division Session selected `[]` Card intelligence sources and
zero historical-message IDs. Its visible Tutor reply contained neither fraction
history nor internal labels, and its Review created no Event/Evidence. Resolved
and unrelated fraction intelligence therefore did not enter this Math context.

### REAL-LINA VERIFIED

`NO` — this is controlled, isolated real-model acceptance, not Lina validation.

### BROWSER VERIFIED

`NOT VERIFIED`.
