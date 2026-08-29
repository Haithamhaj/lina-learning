# Lina Personal Learning System — Project State

## Current goal

CTX-03 remains the approved, technically verified Context v2 direction.
SEG-EVID-01 is the approved Learning Intelligence semantic architecture; its
first two slices are complete in code, while current durable intelligence still
uses legacy Session Evidence. CAND-01 is ACCEPTED / CLOSED. SEG-EVID-01A is
DONE and independently accepted; SEG-EVID-01B is implemented and awaiting
independent review. EDU-ERR-01 remains blocked by SEG-EVID-01F.

## Current reality

- SEG-EVID-01A is independently CODE REVIEW VERIFIED: Segment Review creation
  requires a durably closed Segment; Event-linked Segment and Segment Review
  provenance uses `RESTRICT`; Candidate remains provisional with nullable
  `SET NULL` lineage; and the migration, legacy backfill, and Candidate-free
  downgrade-refusal design were reviewed. It includes no Segment Review runtime,
  job, model call, Session Finalization, or Evidence activation; Session remains
  the durable Evidence authority.
- SEG-EVID-01B completes Segments and creates only structural Review requests:
  a closed Segment must belong to the supplied Session, its Session to a valid
  Student, and contain at least one persisted raw Student `LearningMessage`
  assigned to it. It does not inspect content, Candidate metadata, Guided
  Learning Checks, TeachingMethod, semantic output, or derived intelligence.
  `CONTINUE` does not schedule a Review; `NEW_SEGMENT`, `UNCERTAIN`, and the
  conservative fallback close the prior Segment before creating the next.
  Session close reconciles only that Session's legacy-open Segments and keeps
  the existing `SESSION_CONSOLIDATION` job.
- Each reviewable closure idempotently queues the unhandled
  `SEGMENT_LEARNING_REVIEW` job with `segment-review-request-v1`; no Segment
  Review row, ModelTask, model call, handler, Session Finalization, or Evidence
  activation exists in B. SEG-EVID-01C's future AI Reviewer determines 0..N
  supported findings, including valid empty findings.
- Candidate Events are provisional hints. Staged Segment findings do not update
  current-session personalization; Pattern counters/lifecycle are unchanged.
- Existing Session Evidence remains the current/legacy implementation until
  SEG-EVID-01D. Historical Evidence remains valid, auditable, and rebuildable.
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

- Segment = semantic review unit; Session = durable intelligence authority.
- Segment review is asynchronous/background; Session Finalization is
  deterministic by default with no semantic Session call after Reviews.
- Raw interaction outranks Candidate metadata; Candidate is provisional.
- No partial Session activation; Card updates only after Session authority.
- Current behavior outranks history; TeachingMethod identity is server-grounded;
  no learner-style/psychological labels or second learner-memory/counter system.
- Bounded authoritative historical anchors are allowed only when a rubric
  requires them. Cross-subject findings fail closed pending SCOPE-01/SUBJ-01.

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
- **STATE-01 — Structured Segment State lineage reliability — OPEN / NON-BLOCKING**

## Next recommended action

Independently review SEG-EVID-01B — Segment Completion & Review Jobs.

CAND-01 is ACCEPTED / CLOSED. SEG-EVID-01B remains REVIEW; SEG-EVID-01C–F
remain BLOCKED; EDU-ERR-01 remains blocked by SEG-EVID-01F; SCOPE-01,
SUBJ-01, REC-25, LR-D04B, archive retrieval, and frozen future capabilities
remain deferred. Real-Lina validation remains deferred.

## Critical references

`AGENTS.md`; `docs/PROJECT_REFERENCE.md`; `docs/LEARNING_PRODUCT_ROADMAP.md`;
`docs/LEARNING_INTELLIGENCE_SPEC.md`; `docs/IMPLEMENTATION_PLAN.md`; `TASKS.md`.
