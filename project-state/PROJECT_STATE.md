# Lina Personal Learning System — Project State

## Current goal

Hybrid Segment Context is the APPROVED Context v2 architecture. Parent-owned Student Core Profile is an APPROVED FUTURE FOUNDATION, not implemented, and belongs to future TASK-027A. REC-35.2 / LR-D04A remains in REVIEW behind the mandatory Lina Stabilization Gate. CTX-01, ACT-01, OBS-01, UI-01, CTX-02, SAFE-01, and OUT-01 are CLOSED. CTX-03B is ACCEPTED after its long real-Luna replay; CTX-03C is NOT STARTED. SAFE-02 is IMPLEMENTED / REVIEW. LR-D04B remains deferred and REC-25 remains BLOCKED.

## Current reality

- Roadmap Track A architecture simplification is COMPLETE / ACCEPTED; REC-35.1 is DONE following Product Owner browser acceptance.
- The authenticated Student Tutor path works with zero content, persists messages, streams one primary Tutor response, and uses optional question-driven grounding.
- Structural-first content processing and PostgreSQL lexical + pgvector retrieval remain the approved grounding path; educational semantics remain optional enrichment.
- REC-35.2 is implemented but remains REVIEW until the ordered Stabilization Gate is completed.
- Closed stabilization items: CTX-01, ACT-01, OBS-01, UI-01. Open critical-path order remains A → B → C → D, with MATH-01 and ID-01 independent.
- Hybrid Segment Context is the approved governing architecture; its full production runtime is not yet implemented:
  - a logical Multimodal Turn may contain text, transcript, and original asset references;
  - Learning Thread = session-local contiguous Segment (`thread_id`), with no third Thread entity;
  - Segments are EPHEMERAL by default;
  - optional Durable Conversation Topics are Grade-scoped navigation metadata only;
  - returning to a topic after an intervening Segment creates a new Segment; normal raw Exchange recall never reopens or injects an earlier Segment merely because it shares a topic;
  - context is structural and relevance-first: Current Multimodal Turn + Full Immediate Exchange + compact Structured Segment State + recent complete Exchanges + 0..N semantically relevant older complete raw Exchanges from the current Segment only;
  - a new Session begins conversationally fresh; prior raw transcripts are not injected by default;
  - historical conversation lookup remains an on-demand future seam; automatic semantic archive retrieval/vector indexing is not approved.
- Conversation metadata is explicitly separate from personalization, Evidence, TeachingMode/TeachingStrategy/TeachingMethod, Safety / Parent Boundary classification, and curriculum/RAG semantics.
- Personalization remains governed only by Raw Interaction → Candidate Event → Validated Learning Event → Evidence → Current State/Patterns → Learner Intelligence Card; current Lina behavior outranks history.
- CTX-03A is ACCEPTED: durable session-local Segment identity, deterministic within-Session sequence, and nullable LearningMessage lineage. CTX-03B is ACCEPTED / LONG VERIFIED: the same primary Tutor call supplies a validated `CONTINUE` / `NEW_SEGMENT` / `UNCERTAIN` relation; completed Student→Tutor pairs share the resolved Segment; and a nullable, compact, typed, source-linked latest Structured Segment State is replaceable from raw messages. The approved 73-turn replay completed with the gold 8-Segment shape; invalid/missing relation remains conservative and failed streams leave the raw Student message unsegmented. CTX-03C–E remain NOT IMPLEMENTED.
- OUT-01 is CLOSED: server-only `TUTOR_MAX_OUTPUT_TOKENS` is positive-validated and defaults to 2000; it is an API completion ceiling, not a Student-facing response-length target. The configured ceiling completed the approved long replay without output-incomplete results.
- SAFE-02 is IMPLEMENTED / REVIEW. The hard child-safety baseline remains deterministic and upstream. For an otherwise open normal Tutor turn, compact effective server-owned Parent Boundary settings enter the one primary Luna call; Luna emits typed semantic category/applicability/proposed action, and the server resolves the effective action and enforces the final visible response. Redirects use only bounded Luna fragments or a deterministic fallback; ordinary model text and Candidate metadata are discarded. The streaming guard withholds text until an enforceable decision is available, while provider fallbacks buffer safely. This remains separate from Segment/State semantics, Evidence, and CTX-03C.
- CTX-02 is CLOSED after replacing the failed 1,200-character head+tail Immediate Bridge with Full Immediate Exchange while preserving exact Current Turn lineage. Focused/canonical automated verification and real-Luna beginning, middle, end, and faithful S3-style direct-continuity cases passed. Browser verification was unavailable in the isolated worktree but was not required to prove this faithful backend/context regression.
- Student Core Profile is an approved future Parent-owned factual foundation: identity, date of birth where supplied with runtime-derived age, and active Grade / GradePeriod linkage. It remains separate from Learner Intelligence, Evidence, Conversation Context, and Safety, and future TASK-027A owns implementation. Current approximately-10-year-old Tutor wording is a temporary Lina-first assumption; no runtime change is authorized now.
- SAFE-01 is CLOSED after independent review. The rejected deterministic physical-hazard-policy hypothesis remains rejected: hard Product Safety restrictions and Parent Boundaries remain upstream, while open-ended situational safety remains Luna/Tutor semantic behavior. One compact Tutor instruction makes immediate real-world Student safety outrank continuing ordinary teaching/activity when warranted; SafetyPolicyService semantics, one primary Tutor call, and zero added classifier/model calls remain unchanged. Focused/relevant/canonical automated verification, four real `gpt-5.6-luna` safety situations, four isolated benign controls without material overreaction, and a low-information Immediate-Exchange case passed.
- Candidate → Evidence → State/Pattern boundaries, raw-source provenance, Model Gateway routing, one primary Tutor call, and rebuildability remain protected.
- The local uncommitted Prompt-v5/Eureka semantic-enrichment files remain parked optional work and are not approved Context v2 scope.

## Active decisions

- Tutor is always available; grounding is optional and current-question-driven.
- Current Lina behavior outranks historical personalization; historical intelligence is advisory.
- Learning Thread means the session-local Conversation Segment.
- Durable Conversation Topic is optional Grade-scoped navigation metadata, not learner memory or Evidence authority.
- EPHEMERAL is the default; reuse an existing durable topic before creating a new one; ambiguity should not silently create durable memory.
- `UNCERTAIN` will create a new independent Ephemeral Segment without a topic, reassignment, merge, or backfill; CTX-03B owns that behavior, not CTX-03A.
- Normal raw Exchange recall is Current-Segment-only. CTX-03C will use a small direct recent-Exchange slice plus lazy state-reference/vector recall of older complete Exchanges; it will not retrieve an earlier Segment because of topic similarity.
- Conversation context, pedagogy classifications, Safety classification, curriculum concepts, and Learning Intelligence are separate authorities.
- Parent Boundary applicability is semantic same-primary-call metadata, never lexical Arabic/English topic routing. Default or ambiguous applicability is open. Effective Parent settings remain server-owned and override the model's proposed action; protected baseline safety remains non-overridable and upstream.
- New Sessions are conversationally fresh. Learner Intelligence / Current State / relevant Open Loops provide normal cross-session personalization, not prior raw transcripts.
- Historical archive lookup is on-demand and deferred until independently validated; no automatic semantic retrieval is approved.
- No separate normal-turn conversation classifier is approved; the executor remains replaceable and any extra model call requires measured need and Product Owner approval.
- CTX-03B is implemented but awaits independent review and a bounded real-Luna diagnostic when a secure route is available. CTX-03C–E remain deferred: temporary semantic/raw recall, final guardrail/observability, and real-Luna Gate-A verification. Archive retrieval, automatic retro-linking, memory service, and extra classifier/summarizer model calls remain deferred.
- Stabilization order remains CTX-02 CLOSED → SAFE-01 CLOSED → CTX-03 NEXT → final targeted Gate-A manual verification, then B → C → D. SCOPE-01 remains a Product Owner decision gate before SUBJ-01.

## Protected areas

Event → Evidence → State/Pattern → Learner Intelligence Card; current behavior outranking history; Conversation Topic/Segment metadata never becoming learner conclusions; TeachingStrategy and TeachingMethod separation; method selection not being effectiveness Evidence; raw message/asset and student-original provenance; explicit child-safety and Parent Learning Boundaries; Safety before Tutor; one primary Tutor call; derived mastery/confidence; Model Gateway routing; question-driven RAG; semantic curriculum enrichment remaining optional; modular monolith; and frozen Vision, Voice, Science production, Learning Canvas, Artifact Engine, and Parent Dashboard expansion.

## Active risks

- CTX-03B is accepted and must stay limited to same-primary-call relation, pair lineage, and compact source-linked State. CTX-03C–E, archive retrieval, memory service, extra classifier/model calls, and other frozen work remain outside its scope.
- SAFE-02 must keep hard-baseline enforcement upstream, one primary Tutor call, server-owned final Parent Boundary enforcement, and no visible/persisted ordinary model text on redirects.
- ACT-02, CAND-01, SCOPE-01/SUBJ-01, DEC-01/DEC-02, REP-01, LANG-01, and CAND-02 remain open in the approved order.
- EVID-01 still has an unknown session-evidence HTTPError root cause; PERS-01 remains blocked until trustworthy Evidence exists.
- Historical semantic archive retrieval is unvalidated and must not be treated as a production capability.
- REC-25, LR-D04B, Track B, and other frozen future capabilities remain out of current execution scope.

## Next recommended action

Review SAFE-02 after its focused and full automated verification, then run its bounded 10-case real-Luna diagnostic with `MODEL_PROVIDER=openai`, `MODEL_NAME=gpt-5.6-luna`, and `TUTOR_MAX_OUTPUT_TOKENS=2000`. CTX-03C remains NOT STARTED; do not begin CTX-03C–E, ACT-02, REC-25, LR-D04B, archive retrieval, or frozen future capabilities. TASK-027A remains future/blocked.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
