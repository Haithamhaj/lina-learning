# Lina Personal Learning System — Project State

## Current goal

Hybrid Segment Context is the APPROVED Context v2 architecture. Parent-owned Student Core Profile is an APPROVED FUTURE FOUNDATION, not implemented, and belongs to future TASK-027A. REC-35.2 / LR-D04A remains in REVIEW behind the mandatory Lina Stabilization Gate. CTX-01, ACT-01, OBS-01, UI-01, CTX-02, and SAFE-01 are CLOSED. CTX-03 remains IN PROGRESS; CTX-03A Segment persistence and LearningMessage lineage are IMPLEMENTED / REVIEW only. LR-D04B remains deferred and REC-25 remains BLOCKED.

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
- CTX-03A is IMPLEMENTED / REVIEW: durable session-local Segment identity, deterministic within-Session sequence, and nullable LearningMessage lineage only. CTX-03B–E remain NOT IMPLEMENTED: same-call Segment relation/State, recent/raw semantic recall, capacity/observability, and real-Luna Gate-A verification remain separately scoped.
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
- New Sessions are conversationally fresh. Learner Intelligence / Current State / relevant Open Loops provide normal cross-session personalization, not prior raw transcripts.
- Historical archive lookup is on-demand and deferred until independently validated; no automatic semantic retrieval is approved.
- No separate normal-turn conversation classifier is approved; the executor remains replaceable and any extra model call requires measured need and Product Owner approval.
- CTX-03B–E remain deferred: Structured Segment State, automatic semantic turn relation, temporary semantic recall, final guardrail/observability, and real-Luna verification. Archive retrieval, automatic retro-linking, memory service, and extra classifier/summarizer model calls remain deferred.
- Stabilization order remains CTX-02 CLOSED → SAFE-01 CLOSED → CTX-03 NEXT → final targeted Gate-A manual verification, then B → C → D. SCOPE-01 remains a Product Owner decision gate before SUBJ-01.

## Protected areas

Event → Evidence → State/Pattern → Learner Intelligence Card; current behavior outranking history; Conversation Topic/Segment metadata never becoming learner conclusions; TeachingStrategy and TeachingMethod separation; method selection not being effectiveness Evidence; raw message/asset and student-original provenance; explicit child-safety and Parent Learning Boundaries; Safety before Tutor; one primary Tutor call; derived mastery/confidence; Model Gateway routing; question-driven RAG; semantic curriculum enrichment remaining optional; modular monolith; and frozen Vision, Voice, Science production, Learning Canvas, Artifact Engine, and Parent Dashboard expansion.

## Active risks

- CTX-03A must stay limited to schema/model/helper/test lineage foundation. CTX-03B–E, archive retrieval, memory service, extra classifier/model calls, and other frozen work remain outside its scope.
- ACT-02, CAND-01, SCOPE-01/SUBJ-01, DEC-01/DEC-02, REP-01, LANG-01, and CAND-02 remain open in the approved order.
- EVID-01 still has an unknown session-evidence HTTPError root cause; PERS-01 remains blocked until trustworthy Evidence exists.
- Historical semantic archive retrieval is unvalidated and must not be treated as a production capability.
- REC-25, LR-D04B, Track B, and other frozen future capabilities remain out of current execution scope.

## Next recommended action

Independently review CTX-03A, then begin CTX-03B only with separate authorization. Do not begin CTX-03C–E, ACT-02, REC-25, LR-D04B, archive retrieval, or frozen future capabilities. TASK-027A remains future/blocked.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
