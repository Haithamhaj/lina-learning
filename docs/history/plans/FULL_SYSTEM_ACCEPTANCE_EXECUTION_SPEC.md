# Full-System Learning Intelligence Acceptance — Execution Spec

**Status:** Approved execution specification

**Execution objective:** Prove one real stored conversation through real Segment
intelligence, authorized learning memory, and a real later Tutor personalization;
then prove the equivalent journey from a clean fresh start. This is an execution
specification only. It does not add product behavior beyond the approved
architecture and contracts below.

## Governing boundaries

- Work on `codex/ctx-03` and preserve unrelated changes. The original checkout
  may be read only for local configuration.
- Expected starting HEAD:
  `e5a12340c6ea8478bcaff10fdf0ed29281a9a3fc`.
- In the original checkout, never modify, stash, reset, or discard these
  protected files:
  - `scripts/verify_eureka_semantic_representation.py`
  - `services/content/semantics.py`
  - `tests/test_eureka_semantic_verifier.py`
  - `tests/test_semantic_batch_planning.py`
- The source database is test data and must remain untouched. Create and use a
  distinct isolated acceptance database; never use the source URL as a write
  target or reveal database credentials, API keys, or environment contents.
- Every AI-powered acceptance operation uses the configured real
  `openai / gpt-5.6-luna` route through the Model Gateway. `LocalTutorProvider`,
  mocked output, fabricated findings, fallback output, and hand-written Evidence
  are not acceptance evidence. If the real provider cannot execute, record the
  affected acceptance work as blocked.
- Deterministic production code performs Session Finalization, Current State,
  Pattern Engine, Decision Views, and Card work. These steps require no extra
  LLM call.
- Preserve raw messages and original student work as authority. Do not rewrite
  the historical Tutor responses or alter raw message text, roles, timestamps,
  or ordering.
- Do not expand Voice, Vision, UI/dashboard work, gamification, artifacts,
  REC-25, unrelated retrieval, or frozen capabilities. Do not redesign accepted
  SEG-EVID-01A/B/C unless execution demonstrates a concrete defect requiring
  the smallest architecture-consistent correction.

## Required evidence labels

Evidence must state only what was observed and distinguish these labels:

- `AUTOMATED TEST EXECUTION VERIFIED`
- `REAL LUNA VERIFIED` — only after a successful real-provider call with
  persisted execution evidence
- `DATABASE END-TO-END VERIFIED`
- `TUTOR PERSONALIZATION VERIFIED`
- `BROWSER VERIFIED` — only when actually executed
- `REAL-LINA VERIFIED = NO` unless Lina herself performs the validation

Configuration discovery alone is not Real Luna verification. Acceptance reports
must remain non-secret and include the relevant AI execution ledger IDs,
provider/model/task/status, database-isolation evidence, and source lineage.

## Acceptance journey and authority

The governed end-to-end path is:

```text
Conversation → Segments → Reviews → Evidence → Memory → Tutor personalization
```

`LearningEvent + LearningEvidence` are downstream authority. Candidate Event
and Segment Learning Review are provenance, not a second durable authority.
Candidate hints remain optional and provisional; Candidate-free authorized
Evidence must survive downstream processing. Normal Tutor context must not load
the complete historical transcript, and current student behavior continues to
outrank historical intelligence.

The canonical historical acceptance conversation is Session
`8b1b647c-91ec-427e-b455-0adbca831101`. Its source characteristics are 145
persisted raw messages (73 Student, 72 Tutor) and 38 historical Candidate
Events. Those counts, source-message identity/order, and raw source data must
be preserved on the copied acceptance database before reconstruction.

## Isolated acceptance database and historical reconstruction

The operator tooling must:

1. Create a uniquely named acceptance database only after proving that source
   and target identities differ.
2. Copy the source without source writes, migrate only the copy to current
   Alembic head, and record non-secret preservation-count and schema evidence.
3. Reconstruct historical `LearningSegment` boundaries only on the isolated
   copy through a dedicated real-Luna Model Gateway task. No manual boundary
   choice or keyword-based boundary classifier is permitted.
4. Submit the complete chronological 145-message list, validate that every
   source Message ID appears exactly once and in order, and retain an audit of
   reconstructed assignments, reasons, source Message IDs, and model/task
   lineage. The audit must state that these are acceptance reconstructions, not
   original live Segment decisions.
5. Persist only reconstructed Segments and safe acceptance-run/tool audit
   material; do not add unnecessary permanent product schema solely for this
   audit.

The historical acceptance report must show the actual Segment breakdown and
source-message lineage, not a predetermined conclusion.

## SEG-EVID-01D — Session Finalization and activation

SEG-EVID-01D/E/F are implementation and verification stages serving this
Full-System Acceptance objective; they are not separate product goals.

### Authority and provenance contract

- `IntelligenceSessionAuthority` remains the unified Session authority.
  `reprocess_run_id` is nullable for normal live finalization and selects a
  complete authoritative processing run. Legacy Sessions without explicit
  authority retain compatible legacy behavior.
- Add nullable `LearningEvent.segment_review_finding_index` as provenance only.
  Do not add `LearningEvent.semantic_context`.
- A new Session persists the explicit intelligence pipeline identity
  `segment-finalization-v1`. It never enqueues or runs legacy
  `SESSION_CONSOLIDATION`; historical Sessions keep legacy compatibility.

### Completeness, compatibility, and subject handling

Finalization is deterministic, atomic, and idempotent. It requires every
structurally-reviewable Segment in the closed Session to have a completed,
contract-compatible Review. It must reject activation when any required Review
is missing, pending, running, failed, or incompatible.

Compatibility is determined by schema, prompt, rubric, and review-policy
versions. Provider/model differences are execution provenance and do not alone
make Reviews incompatible.

After every required Review completes, activation-eligible `SAME_AS_SESSION`
findings may become authorized Evidence. `POSSIBLE_CROSS_SUBJECT` and
`UNCERTAIN` findings remain staged/withheld, are never silently attributed to
Math, and cannot erase valid safe same-session findings. A complete compatible
Review set with `findings=[]` finalizes successfully with zero new
learner-memory changes; it must not manufacture Evidence.

### Materialization and downstream compatibility

Finalization reads the strict persisted Review envelope, validates
Review/Session/Segment/Message/Candidate lineage, and makes no semantic Session
call. It materializes only eligible findings into `LearningEvent` and
`LearningEvidence`, establishes the authoritative run, and invokes the real
deterministic Current State, Pattern, Decision View, and Card production paths
inside the Session transaction boundary.

Downstream code must select the complete authoritative processing run rather
than require one Evidence per Candidate. When a deterministic projection safely
needs optional historical Candidate metadata, it may follow
`LearningEvent.segment_review_id` plus
`LearningEvent.segment_review_finding_index` to the original Review Finding.
If no safe equivalent exists, it must conservatively omit only that Pattern
inference; it must neither fabricate provenance nor duplicate Finding content.

### Orchestration

Implement the idempotent `SESSION_INTELLIGENCE_FINALIZE` path. Closure and the
settlement of the last outstanding required Segment Review converge on exactly
one finalization path without polling. A new `segment-finalization-v1` Session
does not double-interpret through legacy consolidation; a legacy Session still
uses its persisted legacy pipeline behavior.

## Historical real-Luna acceptance execution

On the isolated copied database only:

1. Preflight source non-write protection, source/copy distinction, Alembic
   head, schema, and preserved 145/73/72/38 source counts.
2. Perform real-Luna reconstruction and all required
   `SEGMENT_LEARNING_REVIEW` work. Persist and report real AI ledger evidence;
   validate every persisted Finding against cited raw Student Message IDs.
3. Close/reconcile the acceptance Session only in the copy, run the one
   deterministic finalization job, and inspect Event/Evidence/authority/state/
   pattern/decision/card rows. Distinguish durable outcomes from withheld and
   empty findings.
4. Start a new Math Session for the same acceptance Student using the actual
   Tutor runtime and real Luna. Capture context-debug selection IDs for Current
   State, Patterns, and Card/intelligence material; prove no full historical
   transcript was loaded; persist the actual Tutor response and its execution
   ledger evidence.
5. For the Math follow-up, prove that unrelated social, religion,
   pregnancy/fetal-development, Science, and school-interpersonal material is
   excluded unless a separately valid mechanism requires it. Also prove current
   behavior outranks history when they conflict.

The report must not predefine what Luna should conclude. It must state what
became durable learner memory, what remained staged, what produced no learning
intelligence, and source lineage for important conclusions.

## Fresh-start acceptance execution

Run a separate clean-student journey after the historical reconstruction case.
It must use the current live pipeline, not reconstructed history:

```text
Real Tutor + Real Luna
→ live Segment decisions
→ persisted Segments
→ optional Candidate hints
→ Segment closure
→ Real Luna Segment Reviews
→ Session Finalization
→ Evidence / Current State / Patterns / Decisions / Card
→ second real Tutor Session and real personalization
```

This fresh-start proof is mandatory because the released product begins with
clean data.

## Completion gates

Do not call Full-System Acceptance complete unless the evidence demonstrates:

- the original source is preserved and remains untouched, the isolated copy is
  distinct, and the current schema is applied;
- real-Luna reconstruction, persisted Segments, and all required real-Luna
  Reviews completed with auditable source grounding;
- deterministic Session Finalization completed; authorized Event/Evidence exist
  where warranted; and Candidate-free Evidence survives downstream processing;
- real production Current State, Pattern lifecycle, Decision Views, and Learner
  Intelligence Card work from the authorized output;
- a later real Luna Tutor call receives relevant selected memory without a full
  historical transcript, excludes irrelevant memory, and gives current behavior
  priority over history; and
- the clean fresh-start journey completes end to end.

Run focused RED/GREEN tests for each correction, relevant PostgreSQL integration
tests, the canonical Python suite, affected web/typecheck/build checks, Alembic
upgrade/check, `git diff --check`, and both real acceptance journeys. If any
gate fails, report it as unverified or blocked; do not claim full acceptance.
