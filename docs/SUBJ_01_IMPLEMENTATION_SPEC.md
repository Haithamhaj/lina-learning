# Lina Personal Learning System

## SUBJ_01_IMPLEMENTATION_SPEC.md

**Status:** READY — approved implementation contract  
**Task:** `SUBJ-01 — Subject Attribution at Segment/Finding/Event Boundaries`  
**Depends on:** `docs/SUBJECT_SCOPE_POLICY.md` — SCOPE-01 DONE / APPROVED  
**Governing architecture:** Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority

This specification turns the approved cross-subject product policy into the next bounded implementation task. It does **not** authorize a Science product build, a second normal-turn classifier, a new learner-memory system, Vision implementation, or the future School-Focused mode.

---

# 1. Objective

Make Subject attribution truthful and durable when one technical Session contains multiple Segments that may belong to different academic Subjects or may be non-learning/casual.

The implementation must guarantee:

```text
one technical Session
→ multiple Segments
→ each Learning Segment has one authoritative primary Broad Subject
→ each materialized Event/Evidence inherits that reviewed Subject
→ no Event/Evidence is stamped from a stale Session-level Subject default
```

A wrong or unresolved Subject must fail closed rather than contaminate another Subject's Evidence, Current State, Patterns, Decision Views, Card, retention logic, or personalization.

---

# 2. Protected Runtime Invariants

SUBJ-01 must preserve all of the following:

1. **One primary Tutor model call per normal Student turn.**
2. No separate normal-turn Subject classifier.
3. No separate normal-turn Topic classifier.
4. No second evidence/summarizer/learner-memory call.
5. Current Student intent outranks stale prior Subject/source context.
6. Segment Review is asynchronous/background and is the semantic-analysis unit.
7. Session Finalization is deterministic and is the durable intelligence authority.
8. Candidate Events remain provisional hints only.
9. Raw interaction remains the source authority.
10. No partial Session intelligence activation.
11. Existing Evidence generations remain auditable/reprocessable.
12. Current behavior continues to outrank historical personalization.

---

# 3. Live Conversation Behavior

The live Tutor path does **not** need final Subject authority before answering.

The existing primary Tutor call may continue to provide the minimal session-local Segment relation used by CTX-03:

- `CONTINUE`
- `NEW_SEGMENT`
- `UNCERTAIN`

A meaningful change in current learning intent/Subject should create a new Segment through the existing conversation-boundary behavior.

No new model call is introduced to decide Subject before the Tutor response.

A provisional Subject hint may exist internally only if it naturally comes from an already-approved structured Tutor payload; it is optional and must never become durable Evidence authority.

---

# 4. Segment Review Becomes Subject Authority

A completed structurally reviewable Segment is interpreted once by Segment Learning Review under the existing background-review architecture.

The next versioned Segment Review contract must be able to represent, conceptually:

```text
segment_kind:
  LEARNING | NON_LEARNING

if LEARNING:
  primary_broad_subject
  concept/topic
  optional school_context
  findings[]
```

Exact field names may vary if the same contract is preserved.

## 4.1 Review-Level Classification

Subject classification belongs at the reviewed Segment level because SCOPE-01 defines one primary Broad Subject per Learning Segment.

A Review should preserve enough structured state to answer:

- Is this Segment learning or non-learning/casual?
- If learning, which controlled Broad Subject owns it?
- What concept/topic is the Segment about?
- Is there source-grounded school context?
- What learning findings, if any, are supported by the raw Segment?

A Learning Segment may legitimately produce `findings=[]`. Subject/topic classification remains useful even when the interaction contains no meaningful learner Evidence.

A Non-Learning Segment should not materialize academic learning findings merely to populate the schema.

---

# 5. Broad Subject Registry

Broad Subject validation must use the controlled, versioned registry governed by `SUBJECT_SCOPE_POLICY.md`.

Initial registry:

```text
MATH
SCIENCE
LANGUAGE_ARTS
SOCIAL_STUDIES
COMPUTING
RELIGIOUS_STUDIES
ARTS
PHYSICAL_EDUCATION
GENERAL_KNOWLEDGE
OTHER
```

Implementation requirement:

> Adding or renaming a Broad Subject should not require redesigning Learning Intelligence or scattering Subject conditionals through Tutor/Intelligence code.

Prefer a centralized versioned registry/configuration contract rather than a database-enum design that forces a schema migration for every registry extension.

The Review model may choose only from the supplied registry keys.

---

# 6. Concept/Topic Contract

A Learning Segment must support a semantic concept/topic even when there is no school content.

Examples:

```text
SCIENCE → stars / star light
MATH → equivalent fractions
LANGUAGE_ARTS → Arabic grammar — nominal sentence
SOCIAL_STUDIES → Sociology — migration
```

The existing Finding-level `concept_ref` remains the exact concept provenance used by Event/Evidence when a finding is materialized.

The Review may also preserve a Segment-level topic summary/classification for analysis and future Parent views. It must not invent a curriculum Unit/Lesson merely to supply structure.

---

# 7. Optional School Context

School context is nullable and source-grounded.

Conceptual shape:

```text
school_context:
  school_relation
  school_subject_ref?
  school_domain_path?
  unit_ref?
  lesson_ref?
  page_refs[]?
  source_refs[]?
```

`school_relation` uses:

- `SCHOOL_ALIGNED`
- `EXTENDED`
- `UNKNOWN`

Rules:

- no school source → `UNKNOWN`, not automatically `EXTENDED`;
- `school_subject_ref` represents an actual configured/trusted school Subject, not a model invention;
- `school_domain_path`, Unit, Lesson, Page, or similar curriculum-position metadata requires source provenance;
- school context may improve reporting/retrieval but does not create learner Evidence by itself.

SUBJ-01 does not need to build the final Parent school-subject management UI or full outline ingestion workflow. Nullable contracts and correct authority boundaries are sufficient for this task.

---

# 8. Replace Relative Session-Subject Semantics

The current Math-first Review contract contains relative semantics such as `subject_alignment = SAME_AS_SESSION / POSSIBLE_CROSS_SUBJECT / UNCERTAIN` and a binary `school_or_extended` field.

Those are insufficient for the approved product model.

The next Review contract must represent the **actual reviewed Broad Subject** rather than only whether a finding matches a Session default.

Compatibility rule:

- historical Review/Event/Evidence rows remain immutable/auditable under their original contract version;
- legacy relative fields remain readable for history/reprocessing compatibility;
- new Review rows use the new subject/school-relation contract;
- reprocessing may regenerate new-version Reviews/Events without rewriting prior historical generations.

Do not destructively reinterpret old rows in place.

---

# 9. Finding-Level Subject Safety

All materializable findings from a correctly bounded Learning Segment normally inherit the Review's primary Broad Subject.

If semantic review detects that a candidate Finding clearly belongs to another Broad Subject than the reviewed Segment, treat this as a boundary/attribution conflict rather than silently creating cross-subject Evidence.

Required behavior:

```text
reviewed Segment = MATH
finding clearly = SCIENCE

→ do not stamp SCIENCE finding as MATH
→ do not silently materialize it under another Subject
→ withhold/fail closed for durable Evidence
→ retain auditable review/provenance signal for investigation/reprocessing
```

The exact conflict-status field is implementation-owned, but the fail-closed behavior is mandatory.

Secondary-domain Evidence duplication is not part of SUBJ-01.

---

# 10. Event and Evidence Materialization

For the new Segment Review pipeline, a materialized Learning Event must derive Subject authority from the reviewed Segment/Finding lineage.

Conceptually:

```text
LearningEvent
├── session_id
├── segment_id
├── segment_review_id
├── finding_index / exact Finding provenance
├── broad_subject        ← reviewed authority
├── concept_ref          ← reviewed Finding authority
├── school_relation      ← reviewed/source-grounded
├── optional school refs
└── exact raw/source provenance
```

Do **not** assign the Event's Subject from `LearningSession.subject` simply because the Session was opened through the current Math-first entry flow.

Evidence inherits the Event's authoritative Subject/provenance.

Session authority still governs whether the complete Event/Evidence generation becomes active.

---

# 11. Session-Level Subject Field

The current `LearningSession.subject` may remain for backward compatibility and current entry/runtime hints.

For new Segment-review-backed intelligence it is **not** the durable Subject authority.

SUBJ-01 should make this explicit in code contracts and tests.

Do not require a destructive rename/removal if that creates unnecessary migration risk. A compatibility interpretation such as `entry/default subject hint` is acceptable as long as downstream new-path Event/Evidence authority no longer depends on it.

---

# 12. Session Finalization

Session Finalization remains one deterministic authority boundary even when the Session contains several Subjects.

Example:

```text
Session
├── Segment 1 → MATH Review complete
├── Segment 2 → NON_LEARNING Review complete
├── Segment 3 → SCIENCE Review complete
└── Segment 4 → MATH Review complete

complete coherent Review set
        ↓
Session Finalization
        ↓
activate correctly attributed Events/Evidence atomically
```

Do not create one intelligence authority run per Subject merely because the Session is cross-subject.

No semantic Session-level LLM call is added.

---

# 13. Downstream Intelligence

The new authoritative Event Subject must be used consistently by downstream logic.

Review/update at minimum:

- Event/Evidence subject filters;
- Current State identity/scope where Subject is relevant;
- Pattern subject scope and support/counter selection;
- Decision Views;
- Learner Intelligence Card relevance selection;
- later Tutor personalization selection;
- retention-anchor same-Subject validation;
- reprocessing/rebuild selection and compatibility checks.

For the new pipeline, same-Subject checks must use authoritative reviewed/materialized Subject lineage rather than a stale Session default.

Legacy sessions retain their existing compatibility behavior.

---

# 14. Retrieval / Tutor Context Boundary

SUBJ-01 must not solve live Subject routing by adding a pre-Tutor classifier.

Question-driven retrieval remains allowed to operate from the current query plus trustworthy current context.

When Subject is not yet authoritative for the current new turn:

- do not force a stale prior Session/Segment Subject filter;
- prefer relevance-based Grade-scoped retrieval or a trustworthy current-context hint;
- if no relevant school source exists, the Tutor may answer from model knowledge under the approved grounding policy.

Math remains the first production-verified content slice; this does not make Math the permanent architectural authority for every Segment.

---

# 15. Tutor Identity / Cross-Subject Architecture

The core conversational architecture must not require a separate Tutor chat per Subject.

SUBJ-01 may remove or isolate Math-only assumptions where they incorrectly act as core Subject authority.

It does **not** require building complete Science ingestion, Science dashboards, Science-specific artifacts, or all future Subject modules.

Subject-specific teaching/content configuration remains modular and may expand later.

---

# 16. Reprocessing and Historical Audit

Reprocessing preserves the existing Session-scoped external authority model.

Requirements:

- old subject-contract generations remain auditable;
- new policy/contract versions are explicit;
- reprocessing can regenerate Segment Reviews with the new subject contract;
- complete-scope activation remains atomic;
- exact Segment Review/Finding/Event/Evidence provenance remains intact;
- authority replacement must not make valid historical retention provenance unverifiable;
- no in-place rewriting of historical evidence generations.

---

# 17. Acceptance Scenarios

SUBJ-01 is not complete until focused tests cover at least the following.

## A. Math → Science → Math in one technical Session

Expected:

```text
Segment 1 → MATH
Segment 2 → SCIENCE
Segment 3 → MATH
```

Materialized Events/Evidence use the correct Segment Subjects. No Science Evidence is stamped Math and no Math Evidence is stamped Science.

## B. Casual middle Segment

```text
Math learning
→ casual conversation
→ Science learning
```

Casual Segment creates no academic learning Evidence.

## C. No school data

Question about stars:

```text
broad_subject = SCIENCE
concept/topic = stars
school_relation = UNKNOWN
school_subject_ref = null
```

Tutor and Learning Intelligence continue normally.

## D. Trusted outline/book available

The Review may attach the correct sourced school Subject/Domain Path/Unit/Lesson without changing Broad Subject authority.

## E. Stale page followed by Subject switch

A photographed Science page followed by a Math question must not force the Math Segment to remain Science.

## F. Language Arts

Arabic/English/French learning is classified under `LANGUAGE_ARTS` without automatically generalizing Evidence across languages.

## G. Social Studies

History/Geography/Civics/Economics/Sociology/Saudi Culture map under `SOCIAL_STUDIES` as appropriate.

## H. Religious Studies

Quran/Islamic Studies/Fiqh/Tawheed/Hadith/Seerah map under `RELIGIOUS_STUDIES` as appropriate.

## I. Boundary conflict

A Finding whose semantic Subject conflicts with its reviewed Segment must fail closed for durable Evidence rather than being silently stamped with the Session/Segment default.

## J. No extra live model call

Normal-turn execution count remains one primary Tutor model call. Subject authority is produced by the later Segment Review, not a live classifier.

## K. Deterministic Session authority

Multi-subject Session Finalization makes no semantic model call and atomically activates only a complete coherent Review set.

## L. Reprocessing

A new subject-contract reprocessing generation can replace authority atomically while prior Event/Evidence generations remain auditable.

---

# 18. Out of Scope

Do not include in SUBJ-01 unless separately approved:

- full Science production rollout;
- new Science book ingestion UX;
- final Parent school-subject management UI;
- automatic outline/weekly-plan ingestion expansion;
- Vision/photo understanding implementation;
- future School-Focused / Book-Led Parent mode;
- a second Learning Intelligence pipeline;
- cross-subject Pattern generalization redesign;
- secondary-domain duplicate Evidence;
- new archive retrieval/memory service;
- additional normal-turn classifier/summarizer calls;
- EDU-ERR-01;
- REC-25;
- LR-D04B.

---

# 19. Verification Required

Before claiming SUBJ-01 complete, report verification separately as applicable:

- `CODE REVIEW VERIFIED`
- `AUTOMATED TEST EXECUTION VERIFIED` or clearly `CODEX-REPORTED TEST EXECUTION`
- `REAL MODEL VERIFIED` only if actually executed
- `BROWSER VERIFIED` only if actually executed
- `REAL-LINA VERIFIED` only after Lina herself exercises the behavior

At minimum, implementation acceptance requires code review plus focused automated cross-subject/authority tests and the canonical regression suite.

A real-model synthetic Math → Science → Math Segment Review path is strongly recommended before closure because the task changes the semantic Review contract.

---

# 20. Task Transition

With `docs/SUBJECT_SCOPE_POLICY.md` approved:

```text
SCOPE-01 = DONE / APPROVED
SUBJ-01  = READY
```

`EDU-ERR-01` remains approved/deferred. Other deferred or frozen feature tracks remain unchanged.
