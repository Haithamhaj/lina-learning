# Lina Personal Learning System — Project State

## Current goal

Hybrid Segment Context is the APPROVED Context v2 architecture. CAND-01 is FIX IMPLEMENTED / VERIFICATION, not CLOSED. Parent-owned Student Core Profile is an APPROVED FUTURE FOUNDATION, not implemented, and belongs to future TASK-027A. REC-35.2 / LR-D04A remains in REVIEW behind the mandatory Lina Stabilization Gate. CTX-01, ACT-01, ACT-02, OBS-01, UI-01, CTX-02, SAFE-01, SAFE-02, OUT-01, and DATA-01 are CLOSED. CTX-03B, CTX-03C, and CTX-03D are ACCEPTED; CTX-03 technical context runtime is VERIFIED and Real-Lina Context validation is DEFERRED. LR-D04B remains deferred and REC-25 remains BLOCKED.

## Current reality

- Roadmap Track A architecture simplification is COMPLETE / ACCEPTED; REC-35.1 is DONE following Product Owner browser acceptance.
- The authenticated Student Tutor path works with zero content, persists messages, streams one primary Tutor response, and uses optional question-driven grounding.
- Structural-first content processing and PostgreSQL lexical + pgvector retrieval remain the approved grounding path; educational semantics remain optional enrichment.
- REC-35.2 is implemented but remains REVIEW until the ordered Stabilization Gate is completed.
- Closed stabilization items: CTX-01, ACT-01, ACT-02, OBS-01, UI-01. ACT-02 is ACCEPTED / CLOSED: generic Suggested Action and legacy `ANSWER_CHOICE` clicks are non-evidentiary; only a validated latest persisted Guided Learning Check answer with exact choice membership can enter bounded Candidate processing. Forged, stale, cross-session, and non-member responses are rejected, with runtime retaining final authority validation. Configured production build/browser verification was not run because this isolated worktree has no valid Clerk publishable key; this is non-blocking for ACT-02 closure. Critical-path order remains A → B → C → D, with MATH-01 and ID-01 independent.
- CAND-01 is FIX IMPLEMENTED / VERIFICATION: `misconception_signal` needs `misconception-evidence-v1` with a Luna-proposed incorrect model, exact normalized Student reasoning span, and the current raw Student message ID. Runtime proves only source identity, role, interaction kind, and exact normalized grounding; it filters unsupported misconception Candidates while preserving unrelated valid Candidates. It does not classify educational correctness, alter Evidence/State/Pattern processing, or add a migration. Focused and disposable-PostgreSQL automated verification passed; Real Luna was not configured.
- Hybrid Segment Context's current text-based runtime is implemented and technically verified; future Multimodal Turn inputs such as Voice, Vision, and original assets remain frozen future capability and do not reopen CTX-03:
  - a logical Multimodal Turn may eventually contain text, transcript, and original asset references;
  - Learning Thread = session-local contiguous Segment (`thread_id`), with no third Thread entity;
  - Segments are EPHEMERAL by default;
  - optional Durable Conversation Topics are Grade-scoped navigation metadata only;
  - returning to a topic after an intervening Segment creates a new Segment; normal raw Exchange recall never reopens or injects an earlier Segment merely because it shares a topic;
  - context is structural and relevance-first: Current Multimodal Turn + Full Immediate Exchange + compact Structured Segment State + recent complete Exchanges + 0..N semantically relevant older complete raw Exchanges from the current Segment only;
  - a new Session begins conversationally fresh; prior raw transcripts are not injected by default;
  - historical conversation lookup remains an on-demand future seam; automatic semantic archive retrieval/vector indexing is not approved.
- Conversation metadata is explicitly separate from personalization, Evidence, TeachingMode/TeachingStrategy/TeachingMethod, Safety / Parent Boundary classification, and curriculum/RAG semantics.
- Personalization remains governed only by Raw Interaction → Candidate Event → Validated Learning Event → Evidence → Current State/Patterns → Learner Intelligence Card; current Lina behavior outranks history.
- CTX-03A is ACCEPTED: durable session-local Segment identity, deterministic within-Session sequence, and nullable LearningMessage lineage. CTX-03B is ACCEPTED / LONG-CONVERSATION REAL-LUNA VERIFIED: the same primary Tutor call supplies a validated `CONTINUE` / `NEW_SEGMENT` / `UNCERTAIN` relation; the 73/73 historical replay reached the expected eight-Segment shape with exact major Human Gold boundaries, no fallback/output-availability failure, and safe invalid-State degradation. Structured Segment State lineage reliability remains STATE-01 OPEN / NON-BLOCKING at 64 valid of 68 attempted (94.1%); invalid State is safely rejected. CTX-03C and CTX-03D are ACCEPTED. CTX-03D measures the final serialized Tutor request, removes only complete optional context units in a deterministic layer order, and records private operational lineage; protected-only overflow fails before Luna. CTX-03E-A TECHNICAL CONTEXT RUNTIME VERIFIED using real Luna and real embeddings; Real-Lina validation is deferred.
- OUT-01 is CLOSED: server-only `TUTOR_MAX_OUTPUT_TOKENS` is positive-validated and defaults to 2000; it is an API completion ceiling, not a Student-facing response-length target. The configured ceiling completed the approved long replay without output-incomplete results.
- DATA-01 is CLOSED / CURRENT DEFECT FIX ACCEPTED: the historical missing Tutor row is high-confidence failed-stream behavior, while the exact provider trigger remains unknown. A Student-facing Tutor response is final only after terminal `event: turn`; reader errors and EOF without that event discard only the current provisional Tutor bubble, retain the Student message, and preserve the backend failed-turn audit contract. Browser verification was unavailable without Clerk configuration; automated terminal-protocol verification passed.
- SAFE-02 is ACCEPTED / CLOSED. The hard child-safety baseline remains deterministic and upstream. For an otherwise open normal Tutor turn, same-primary-call Luna metadata supplies semantic category/applicability/proposed action while the server-owned Parent setting resolves final enforcement; ambiguity is open/ALLOW, Biology/reproduction education is age-appropriate ALLOW, and sexual content/behavior is separately restricted as `SEXUAL_CONTENT`. Redirects use only constrained Luna fragments or a deterministic fallback; ordinary model text and Candidate metadata are discarded. Parent Boundary metadata remains audit metadata only, never Evidence or Learner Intelligence; historical `HUMAN_REPRODUCTION` rows are not reinterpreted as `SEXUAL_CONTENT` settings.
- CTX-02 is CLOSED after replacing the failed 1,200-character head+tail Immediate Bridge with Full Immediate Exchange while preserving exact Current Turn lineage. Focused/canonical automated verification and real-Luna beginning, middle, end, and faithful S3-style direct-continuity cases passed. Browser verification was unavailable in the isolated worktree but was not required to prove this faithful backend/context regression.
- Student Core Profile is an approved future Parent-owned factual foundation: identity, date of birth where supplied with runtime-derived age, and active Grade / GradePeriod linkage. It remains separate from Learner Intelligence, Evidence, Conversation Context, and Safety, and future TASK-027A owns implementation. Current approximately-10-year-old Tutor wording is a temporary Lina-first assumption; no runtime change is authorized now.
- SAFE-01 is CLOSED after independent review. The rejected deterministic physical-hazard-policy hypothesis remains rejected: hard Product Safety restrictions remain upstream, while open-ended situational safety remains Luna/Tutor semantic behavior. One compact Tutor instruction makes immediate real-world Student safety outrank continuing ordinary teaching/activity when warranted; SafetyPolicyService semantics, one primary Tutor call, and zero added classifier/model calls remain unchanged. Focused/relevant/canonical automated verification, four real `gpt-5.6-luna` safety situations, four isolated benign controls without material overreaction, and a low-information Immediate-Exchange case passed. Parent Boundary architecture is governed by SAFE-02.
- Candidate → Evidence → State/Pattern boundaries, raw-source provenance, Model Gateway routing, one primary Tutor call, and rebuildability remain protected.
- The local uncommitted Prompt-v5/Eureka semantic-enrichment files remain parked optional work and are not approved Context v2 scope.

## Active decisions

- Tutor is always available; grounding is optional and current-question-driven.
- Current Lina behavior outranks historical personalization; historical intelligence is advisory.
- Learning Thread means the session-local Conversation Segment.
- Durable Conversation Topic is optional Grade-scoped navigation metadata, not learner memory or Evidence authority.
- EPHEMERAL is the default; reuse an existing durable topic before creating a new one; ambiguity should not silently create durable memory.
- `UNCERTAIN` will create a new independent Ephemeral Segment without a topic, reassignment, merge, or backfill; CTX-03B owns that behavior, not CTX-03A.
- CTX-03C is ACCEPTED: one primary Tutor call receives the Current Turn, Full Immediate Exchange, a small complete-Exchange Recent Raw window, Compact Structured Segment State, and current-Segment-only semantic recall of older relevant complete Exchanges. Exchange vectors are temporary, session-owned PostgreSQL/pgvector rows; the current-question vector is batched once with missing eligible Exchanges and supplied to Curriculum Retrieval without a second query embedding. Calibration uses cosine similarity >= 0.65 from controlled identical/orthogonal fixtures; zero semantic matches remains valid. CTX-03D is ACCEPTED as the final deterministic capacity guardrail only: it does not re-rank CTX-03C relevance, never slices protected/raw units, and records IDs/refs/sizes rather than hidden prompt text. Current Turn remains unassigned before Luna returns its Segment relation; no prior Segment/session/archive retrieval, second classifier/summarizer call, or external vector database is approved. CTX-03E-A TECHNICAL CONTEXT RUNTIME VERIFIED with real Luna and real embeddings; Real-Lina validation is deferred.
- Conversation context, pedagogy classifications, Safety classification, curriculum concepts, and Learning Intelligence are separate authorities.
- Parent Boundary applicability is semantic same-primary-call metadata, never lexical Arabic/English topic routing. Default or ambiguous applicability is open. Effective Parent settings remain server-owned and override the model's proposed action; protected baseline safety remains non-overridable and upstream.
- New Sessions are conversationally fresh. Learner Intelligence / Current State / relevant Open Loops provide normal cross-session personalization, not prior raw transcripts.
- Historical archive lookup is on-demand and deferred until independently validated; no automatic semantic retrieval is approved.
- No separate normal-turn conversation classifier is approved; the executor remains replaceable and any extra model call requires measured need and Product Owner approval.
- CTX-03C reuses PostgreSQL, pgvector, `ModelTask.EMBEDDING`, the OpenAI embedding provider, `text-embedding-3-small` at 1536 dimensions, the model execution ledger, and embedding batching; conversation-memory indexing remains Tutor/session-owned rather than Curriculum RetrievalService authority. The precomputed query-vector seam is implemented. Archive retrieval, automatic retro-linking, memory service, extra classifier/summarizer model calls, and an external vector database remain deferred.

## Protected areas

Event → Evidence → State/Pattern → Learner Intelligence Card; current behavior outranking history; Conversation Topic/Segment metadata never becoming learner conclusions; TeachingStrategy and TeachingMethod separation; method selection not being effectiveness Evidence; raw message/asset and student-original provenance; explicit child-safety and Parent Learning Boundaries; Safety before Tutor; one primary Tutor call; derived mastery/confidence; Model Gateway routing; question-driven RAG; semantic curriculum enrichment remaining optional; modular monolith; and frozen Vision, Voice, Science production, Learning Canvas, Artifact Engine, and Parent Dashboard expansion.

## Active risks

- STATE-01 remains OPEN / NON-BLOCKING: invalid Structured Segment State is safely rejected and must not stop CTX-03C. CTX-03C must remain current-Segment-only and preserve the already accepted CTX-03B relation, pair lineage, and compact source-linked State boundaries.
- SAFE-02 must keep hard-baseline enforcement upstream, one primary Tutor call, server-owned final Parent Boundary enforcement, and no visible/persisted ordinary model text on redirects.
- CAND-01 remains FIX IMPLEMENTED / VERIFICATION; EDU-ERR-01 is APPROVED / NOT STARTED and must follow CAND-01 review before SCOPE-01/SUBJ-01. DEC-01/DEC-02, REP-01, LANG-01, and CAND-02 remain open in the approved order.
- EVID-01 still has an unknown session-evidence HTTPError root cause; PERS-01 remains blocked until trustworthy Evidence exists.
- Historical semantic archive retrieval is unvalidated and must not be treated as a production capability.
- REC-25, LR-D04B, Track B, and other frozen future capabilities remain out of current execution scope.

## Next recommended action

Review CAND-01 verification. EDU-ERR-01 is approved but must not start until CAND-01 is accepted; then follow the recorded EDU-ERR-01 → SCOPE-01 Product Owner decision → SUBJ-01 order. Real-Lina validation remains deferred and is required before any final CORE LEARNING RUNTIME STABILIZED declaration. Do not begin REC-25, LR-D04B, archive retrieval, or frozen future capabilities. TASK-027A remains future/blocked.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
