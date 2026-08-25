# Lina Personal Learning System — Project State

## Current goal

Hybrid Segment Context is the APPROVED Context v2 architecture. REC-35.2 / LR-D04A remains in REVIEW behind the mandatory Lina Stabilization Gate. CTX-01, ACT-01, OBS-01, and UI-01 are CLOSED. CTX-02 is in VERIFICATION / FAILED and requires its direct-continuity correction; SAFE-01 follows CTX-02, and CTX-03 is architecture-approved but not implemented. LR-D04B remains deferred and REC-25 remains BLOCKED.

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
  - returning to a topic after an intervening Segment creates a new Segment that may reuse the same `conversation_topic_ref`;
  - context is structural and relevance-first: Current Multimodal Turn + Full Immediate Exchange + compact Structured Segment State + 0..N relevant complete raw Exchanges from the current Segment, with the latest prior same-topic Segment eligible only for within-session resume;
  - a new Session begins conversationally fresh; prior raw transcripts are not injected by default;
  - historical conversation lookup remains an on-demand future seam; automatic semantic archive retrieval/vector indexing is not approved.
- Conversation metadata is explicitly separate from personalization, Evidence, TeachingMode/TeachingStrategy/TeachingMethod, Safety / Parent Boundary classification, and curriculum/RAG semantics.
- Personalization remains governed only by Raw Interaction → Candidate Event → Validated Learning Event → Evidence → Current State/Patterns → Learner Intelligence Card; current Lina behavior outranks history.
- CTX-03 is the future implementation task for Segment runtime, Structured Segment State, relevance-selected complete current-Segment Exchanges, and a final capacity guardrail. No Context v2 DB tables, separate classifier, archive vector index, retro-link job, memory service, agent chain, or extra normal-turn model call has been authorized or implemented.
- CTX-02 Real-Luna verification discovered a genuine middle-context failure: the 1,200-character head+tail Immediate Bridge omitted the only follow-up-critical middle fact. CTX-02 remains in VERIFICATION and requires a direct-continuity correction: exact Current Turn lineage + complete raw Immediate Exchange; it does not implement CTX-03.
- Safety remains upstream and policy-engine governed. The real reproduction/religion conversation still demonstrates SAFE-01/policy-consistency concerns that are not closed by the Context v2 documentation work.
- Candidate → Evidence → State/Pattern boundaries, raw-source provenance, Model Gateway routing, one primary Tutor call, and rebuildability remain protected.
- The local uncommitted Prompt-v5/Eureka semantic-enrichment files remain parked optional work and are not approved Context v2 scope.

## Active decisions

- Tutor is always available; grounding is optional and current-question-driven.
- Current Lina behavior outranks historical personalization; historical intelligence is advisory.
- Learning Thread means the session-local Conversation Segment.
- Durable Conversation Topic is optional Grade-scoped navigation metadata, not learner memory or Evidence authority.
- EPHEMERAL is the default; reuse an existing durable topic before creating a new one; ambiguity should not silently create durable memory.
- Conversation context, pedagogy classifications, Safety classification, curriculum concepts, and Learning Intelligence are separate authorities.
- New Sessions are conversationally fresh. Learner Intelligence / Current State / relevant Open Loops provide normal cross-session personalization, not prior raw transcripts.
- Historical archive lookup is on-demand and deferred until independently validated; no automatic semantic retrieval is approved.
- No separate normal-turn conversation classifier is approved; the executor remains replaceable and any extra model call requires measured need and Product Owner approval.
- Structured Segment State/runtime retrieval, automatic retro-linking, archive retrieval, memory service, and extra classifier/summarizer model calls remain deferred until CTX-03 is separately implemented and real usage demonstrates value.
- Stabilization order remains CTX-02 → SAFE-01 → CTX-03 → final targeted Gate-A manual verification, then B → C → D. SCOPE-01 remains a Product Owner decision gate before SUBJ-01.

## Protected areas

Event → Evidence → State/Pattern → Learner Intelligence Card; current behavior outranking history; Conversation Topic/Segment metadata never becoming learner conclusions; TeachingStrategy and TeachingMethod separation; method selection not being effectiveness Evidence; raw message/asset and student-original provenance; explicit child-safety and Parent Learning Boundaries; Safety before Tutor; one primary Tutor call; derived mastery/confidence; Model Gateway routing; question-driven RAG; semantic curriculum enrichment remaining optional; modular monolith; and frozen Vision, Voice, Science production, Learning Canvas, Artifact Engine, and Parent Dashboard expansion.

## Active risks

- CTX-02 remains Criticality 5 and is in VERIFICATION / FAILED: the direct-continuity correction must replace positional Immediate Bridge slicing without extending into CTX-03. CTX-03 remains architecture-approved but unimplemented.
- SAFE-01 remains Criticality 5 and follows CTX-02; physical-safety and parent-boundary behavior must not depend on fragile conversational memory.
- ACT-02, CAND-01, SCOPE-01/SUBJ-01, DEC-01/DEC-02, REP-01, LANG-01, and CAND-02 remain open in the approved order.
- EVID-01 still has an unknown session-evidence HTTPError root cause; PERS-01 remains blocked until trustworthy Evidence exists.
- Historical semantic archive retrieval is unvalidated and must not be treated as a production capability.
- REC-25, LR-D04B, Track B, and other frozen future capabilities remain out of current execution scope.

## Next recommended action

Complete the approved CTX-02 direct-continuity correction through automated and real-Luna/browser verification, then leave CTX-02 at VERIFICATION for independent review. Do not begin SAFE-01, CTX-03, ACT-02, REC-25, LR-D04B, archive retrieval, or frozen future capabilities.

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_PRODUCT_ROADMAP.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
