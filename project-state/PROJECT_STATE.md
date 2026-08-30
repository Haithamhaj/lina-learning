# Lina Personal Learning System — Project State

## Current goal

Full-System Acceptance is DONE / ACCEPTED: the governed
path from raw conversation through real Segment Review, Session-authorized
learning memory, and real later Tutor personalization was exercised on an
isolated acceptance database and from a clean fresh start. CTX-03 remains the
approved, technically verified Context v2 direction.
SEG-EVID-01 is the approved Learning Intelligence semantic architecture.
CAND-01 is ACCEPTED / CLOSED. SEG-EVID-01A/B/C are DONE / ACCEPTED;
SEG-EVID-01D is DONE / CODE REVIEW VERIFIED / ACCEPTED;
SEG-EVID-01E is DONE / CODE REVIEW VERIFIED / ACCEPTED; SEG-EVID-01F is DONE /
CODE REVIEW VERIFIED / ACCEPTED. EDU-ERR-01 remains approved with its prior F
blocker cleared, but it is deferred behind the next approved SCOPE-01 → SUBJ-01
product-boundary sequence.

## Current reality

- SEG-EVID-01A is independently CODE REVIEW VERIFIED: Segment Review creation
  requires a durably closed Segment; Event-linked Segment and Segment Review
  provenance uses `RESTRICT`; Candidate remains provisional with nullable
  `SET NULL` lineage; and the migration, legacy backfill, and Candidate-free
  downgrade-refusal design were reviewed. It includes no Segment Review runtime,
  job, model call, Session Finalization, or Evidence activation; Session remains
  the durable Evidence authority.
- SEG-EVID-01B is independently CODE REVIEW VERIFIED. `CONTINUE` leaves its
  Segment open with no Review; `NEW_SEGMENT`, `UNCERTAIN`, and the accepted
  fallback close the prior Segment before creating the next. Session close
  reconciles only that Session's lineage: superseded open Segments become
  `NEXT_SEGMENT_CREATED`, and the final open Segment becomes `SESSION_CLOSED`.
- Structural reviewability requires only durable closure, valid
  Session/Segment/Student lineage, and one persisted raw Student
  `LearningMessage` assigned to the Segment. It does not determine educational
  meaning or inspect Candidate, Guided Check, TeachingMethod, Tutor-response,
  Exchange-count, concept, keyword, or other semantic prerequisites.
- Each eligible closure idempotently queues the unhandled
  `SEGMENT_LEARNING_REVIEW` request at `segment-review-request-v1`, identified
  by Segment/request-version only. The current strict-grounding correction
  preserves v1/v2 audit rows and executes the immutable v3 request/prompt pair:
  `segment-review-request-v3` / `segment-learning-review-prompt-v3`. B creates no `SegmentLearningReview` row,
  ModelTask, model call, or handler; `SESSION_CONSOLIDATION` remains
  operational. Codex-reported, not independently re-executed: focused
  B/runtime/lifecycle PostgreSQL coverage (45 passed) and canonical Python
  coverage (552 passed, 5 skipped). No GitHub CI status is available.
- SEG-EVID-01C is independently **CODE REVIEW VERIFIED / ACCEPTED**:
  `SEGMENT_EVIDENCE` performs one strict,
  versioned semantic review of a durably closed Segment through the Model
  Gateway. AI determines educational meaning from complete ordered raw Segment
  input plus optional validated Candidate hints and available validated
  Guided Check/TeachingMethod provenance; `findings=[]` is valid. Capacity
  failure refuses the complete request rather than truncating it. Review
  output is staged only, source-grounded in its own raw Student messages, and
  safely persists failure before a Job retry; completed Review identity is
  idempotent. C was accepted at `segment-learning-review-v1`,
  `segment-learning-review-prompt-v1`, `evidence-rubric-v1`, and
  `segment-review-policy-v1`; the actual `SEGMENT_LEARNING_REVIEW` worker
  handler persists safe FAILED state before retry and never enqueues Session
  Finalization.
- Segment Review v2 admits bounded authoritative historical anchors only for
  delayed retention: prior Session-authorized Evidence ID, exact concept ref,
  prior demonstration state, observed time, elapsed time, and inclusion reason.
  It never receives a full Card, Pattern conclusion, transcript, or profile.
  Without an exact supplied anchor, retention remains `not_tested`; cross-subject
  findings remain staged/fail-closed. Invalid, stale, unsupported, or
  ungrounded Candidate hints are excluded before AI input while raw Segment
  Review continues. It creates no
  LearningEvent, LearningEvidence, Current State, Pattern, Decision View,
  Card, Session Finalization, or personalization activation.
- Codex-reported verification: focused C/structured-provider 24 passed;
  Candidate/CAND-01/TeachingMethod/worker/structured-output/legacy Session
  Evidence 87 passed; canonical Python 577 passed, 6 skipped. Controlled
  synthetic real `openai / gpt-5.6-luna` testing completed six strict-schema
  representative Segment cases: casual 0 Findings, Candidate-free learning
  explanation, bare-answer incorrect attempt without misconception,
  misconception plus self-correction, grounded `CONCRETE_EXAMPLE` strategy
  outcome, and `POSSIBLE_CROSS_SUBJECT`. `REAL LUNA SEGMENT REVIEW TRANSPORT
  VERIFIED` and representative scenarios are CODEX-REPORTED, not independently
  re-executed or Real-Lina validation. Correction RED was 6 failed, 17 passed;
  clean `git diff --check` is Codex-reported. No GitHub CI status is available.
- Candidate Events are provisional hints. Staged Segment findings do not update
  current-session personalization; Pattern counters/lifecycle are unchanged.
- SEG-EVID-01D deterministically finalizes a complete, current-contract Review
  set into Event/Evidence and derived State/Pattern/Decision projections; no
  semantic Session call is made. For Segment-review-backed Evidence, downstream
  candidate-free `strategy_outcome` handling resolves and verifies the exact
  Finding through Review ID/index, contract version, raw lineage, and materialized
  Event/Evidence provenance. A valid grounded TeachingMethod can therefore
  reach strategy-effectiveness Patterns and Decision Views without a Candidate.
  Malformed provenance is excluded, legacy Candidate-backed behavior remains,
  and Candidate-free misconception recurrence remains conservative with no
  fabricated identity. `SESSION_EVIDENCE` remains the operational legacy path
  for legacy sessions; historical Evidence remains valid, auditable, and
  rebuildable.
- Codex-reported D verification: focused PostgreSQL finalization/pattern/decision
  coverage `74 passed`; canonical Python `682 passed, 6 skipped`; clean
  `git diff --check`. A deterministic replay on a copied isolated acceptance
  database, using persisted real-Luna Review artifacts without a new model call,
  produced 34 Event/Evidence rows, 16 Current State rows, 11 Patterns, 20
  Decision Views, 6 strategy-effectiveness Patterns, and 5 non-insufficient
  strategy-effectiveness Decision Views from 8 Candidate-free strategy outcomes.
  This is Codex-reported acceptance evidence, not independent acceptance or
  Real-Lina/browser verification.
- SEG-EVID-01D is independently **CODE REVIEW VERIFIED / ACCEPTED**:
  deterministic Session Finalization, one unified Session Authority,
  Candidate-free Event/Evidence downstream authority, exact Segment Review
  Finding provenance, cross-subject withholding, atomic rollback/no partial
  activation, legacy/new pipeline separation, and Candidate-free grounded
  TeachingMethod strategy outcomes are accepted. Codex-run automated tests and
  real-model/copied-database acceptance evidence remain Codex-reported and were
  not independently re-executed.
- SEG-EVID-01E is independently **CODE REVIEW VERIFIED / ACCEPTED**.
  Reprocessing remains externally
  Session/date-scoped while dispatching per persisted pipeline: legacy Sessions
  retain versioned `SESSION_EVIDENCE`; new Sessions reuse valid current Segment
  Reviews or rerun unavailable ones through the Segment gateway, then stage
  deterministic Event/Evidence with no live authority. Only a complete selected
  scope may atomically swap Session authorities and rebuild projections;
  staged run ownership, Session/pipeline, and contract identity are checked
  before that swap. Rollback protection, Candidate-free Event/Evidence and exact
  Review Finding provenance, and legacy audit compatibility remain intact.
- Codex-reported E verification: focused PostgreSQL `14 passed`; relevant
  finalization/review/pattern/decision PostgreSQL `109 passed`; canonical Python
  `686 passed, 6 skipped`. A further isolated copy of the real-Luna historical
  database reused eight valid Reviews, made zero new model executions, staged
  and activated 34 Event/Evidence rows, and retained eight Candidate-free
  strategy outcomes, six strategy-effectiveness Patterns, and five
  non-insufficient strategy-effectiveness Decision Views. It is database
  evidence reported by Codex, not independently re-executed. Real-Lina/browser
  remain NOT VERIFIED.
- Full-System Acceptance is governed by
  `docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md`. It requires a copied,
  isolated acceptance database with the source database untouched; actual
  `openai / gpt-5.6-luna` Model Gateway evidence for AI-powered operations;
  and separate historical-reconstruction and clean fresh-start journeys.
  SEG-EVID-01D/E/F serve this one acceptance objective and do not reopen the
  accepted A/B/C decisions.
- SEG-EVID-01F is independently **CODE REVIEW VERIFIED / ACCEPTED**:
  Codex-reported
  isolated Math acceptance completed 12 normal Sessions, 19 successful real
  Luna Tutor calls, 15 successful real Luna Segment Reviews, deterministic
  Session authorities, Candidate-free TeachingMethod outcome, bounded retained
  anchor, complete-scope E reprocessing, and rollback/no-partial-activation.
  A strict anchor-concept separator mismatch failed closed and was corrected by
  prompt v5 exact-copy guidance. Real authorized Evidence exercised Pattern
  support/counter, WEAKENING, and RESOLVED states. A later Card selected only
  relevant State/Pattern sources with no historical transcript injection; an
  unrelated long-division turn selected none. Changed-context transfer stayed
  `not_tested` rather than being invented. Focused PostgreSQL `93 passed` and
  canonical Python `688 passed, 6 skipped` are Codex-reported, not independently
  re-executed. Real-Lina/browser remain NOT VERIFIED.
- Follow-on retention-provenance correction: fresh Segment Reviews still receive
  only current Session-authorized historical anchors. A completed persisted
  Review can instead revalidate its exact stored anchor only when the same
  Student/subject/prior Session/Evidence run remains qualifying and is current
  authority or is proven by a later completed E-path authority activation audit.
  Arbitrary old Evidence, wrong/foreign run lineage, malformed audit data, and
  insufficient delay remain fail-closed. Codex-reported focused PostgreSQL
  coverage passed (`117 passed`); canonical Python passed (`689 passed, 6
  skipped`); no new model call occurred. The retained
  isolated acceptance database is not configured in this checkout, so this
  correction was not replayed there. PostgreSQL/Python execution results and
  real-Luna execution counts remain Codex-reported, not independently
  re-executed. Real-Lina/browser remain NOT VERIFIED.
- Full-System Learning Intelligence Acceptance is independently accepted. The
  accepted result includes the real Math multi-Session path; real Tutor and
  Segment Review executions; Session-authorized Event/Evidence activation;
  Current State lifecycle; Pattern support/counter/weakening/resolution;
  Candidate-free provenance; grounded TeachingMethod outcome; bounded
  authoritative retention anchors and persisted provenance across authority
  replacement; current behavior outranking historical intelligence; relevant
  later personalization; negative-memory exclusion; Session-scoped reprocessing
  with atomic authority activation; and auditable old Evidence generations.
  Implementation/code review is independently accepted; all PostgreSQL/Python
  and real-Luna execution evidence remains Codex-reported. `REAL-LINA = NO`;
  browser remains NOT VERIFIED.
- Track A is COMPLETE / ACCEPTED; the authenticated Tutor works with zero
  content, uses optional question-driven grounding, and remains safety-first.
- CTX-03 preserves current-Segment-only context. `CONTINUE` stays in the
  current Segment; `NEW_SEGMENT` and `UNCERTAIN` persist a new Segment and
  complete the prior one. Session close completes the final Segment.
- One primary Tutor call, safety-first policy enforcement, question-driven RAG,
  and separation of Safety, context, RAG, Student Core Profile, and learner
  intelligence remain protected.
- CAND-01 is ACCEPTED / CLOSED after independent engineering review: the strict
  Structured Output correction and source-grounded misconception protection are
  accepted. Codex-reported focused/relevant and canonical Python execution is
  544 passed, 5 skipped. Codex-reported controlled real `gpt-5.6-luna`
  Tutor/Model-Gateway verification was successful, not independently
  re-executed: confusion, bare wrong answer, and arithmetic slip did not become
  misconception signals; explicit wrong reasoning produced grounded
  `misconception-evidence-v1`. Turn-level Candidate remains provisional and
  Segment Review is the future durable semantic authority; this does not claim
  perfect turn-level Luna classification. Real-Lina validation remains deferred
  and is not part of CAND-01 closure. For future real-model checks, existing
  local project env configuration may be loaded read-only when the isolated
  worktree has no env file. EVID-01 remains an open legacy HTTPError defect but
  is off the new critical path. PERS-01 is absorbed into SEG-EVID-01F.

## Active decisions

- Segment interprets. Session commits. Segment = semantic review unit; Session
  = durable intelligence activation authority.
- Segment review is asynchronous/background; Session Finalization is
  deterministic by default with no semantic Session call after Reviews.
- Raw interaction outranks Candidate metadata; Candidate is provisional.
- No partial Session activation; Card updates only after Session authority.
- Current behavior outranks history; TeachingMethod identity is server-grounded;
  no learner-style/psychological labels or second learner-memory/counter system.
- Bounded authoritative historical anchors are allowed only when a rubric
  requires them. Cross-subject findings fail closed pending SCOPE-01/SUBJ-01.
- The next product boundary is SCOPE-01 → SUBJ-01: one technical Session may
  contain multiple session-local Segments / Learning Threads with potentially
  different Subjects. Lina must not need a separate chat to move among Math,
  Science, or future academic Subjects. SCOPE-01 clarifies/reconciles policy;
  SUBJ-01 later implements Subject Attribution at Segment/Finding/Event
  boundaries. The current Math-first vertical slice remains intact until then.
- Full-System Acceptance evidence labels distinguish automated tests, real Luna,
  database end-to-end behavior, Tutor personalization, and browser execution
  when performed; `REAL-LINA VERIFIED = NO` until Lina validates it herself.

## Protected areas

```text
Raw interaction provenance
→ completed Segment semantic interpretation
→ Session-authorized Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ personalization
```

Atomic reprocessing authority remains required. Safety, conversation context,
and RAG/curriculum remain separate authorities.

## Active risks

- **SEG-EVID-R1 — Segment Boundary Fidelity — 5**
- **SEG-EVID-R2 — Partial Session Activation — 5**
- **SEG-EVID-R3 — Cross-Subject Attribution — 5**
- **SEG-EVID-R4 — Legacy/New Authority Coexistence — 5**
- **SEG-EVID-R5 — Semantic Review Cost — 3**
- **FSA-R1 — Source Database Isolation — 5**
- **FSA-R2 — Real-Luna Evidence Integrity — 5**
- **STATE-01 — Structured Segment State lineage reliability — OPEN / NON-BLOCKING**

## Next recommended action

Begin SCOPE-01 — Cross-Subject Conversation & Subject Policy Reconciliation.

CAND-01 is ACCEPTED / CLOSED. SEG-EVID-01A–C are DONE / ACCEPTED;
SEG-EVID-01D is DONE / CODE REVIEW VERIFIED / ACCEPTED;
SEG-EVID-01E and SEG-EVID-01F are DONE / CODE REVIEW VERIFIED / ACCEPTED;
Full-System Acceptance is DONE / ACCEPTED. EDU-ERR-01 is approved with its
prior F blocker cleared but deferred; SUBJ-01 remains blocked by SCOPE-01;
REC-25, LR-D04B, archive retrieval, and frozen future capabilities remain
deferred. Real-Lina validation remains deferred; browser remains NOT VERIFIED.

## Critical references

`AGENTS.md`; `docs/PROJECT_REFERENCE.md`; `docs/LEARNING_PRODUCT_ROADMAP.md`;
`docs/LEARNING_INTELLIGENCE_SPEC.md`; `docs/IMPLEMENTATION_PLAN.md`; `TASKS.md`.
