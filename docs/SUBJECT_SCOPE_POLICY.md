# Lina Personal Learning System

## SUBJECT_SCOPE_POLICY.md

**Status:** APPROVED — governing SCOPE-01 policy  
**Owns:** Cross-Subject Conversation & Subject Policy  
**Implementation successor:** `SUBJ-01 — Subject Attribution at Segment/Finding/Event Boundaries`  
**Authority:** This document is the approved governing addendum for subject scope, school-context alignment, and cross-subject conversation. For these topics it supersedes conflicting older wording in `PROJECT_REFERENCE.md`, `LEARNING_INTELLIGENCE_SPEC.md`, `IMPLEMENTATION_PLAN.md`, `TASKS.md`, or project-state snapshots until those larger documents are naturally consolidated.

---

# 1. Governing Decision

The product uses:

> **one technical Session that may contain multiple session-local Segments / Learning Threads, with one primary Broad Subject per Learning Segment.**

Lina does **not** need to create a separate chat when she moves from Math to Science, Language Arts, Social Studies, or another supported learning domain.

A meaningful topic/subject switch creates a new Segment inside the same technical Session.

```text
Technical Session
├── Segment 1 → LEARNING → MATH
├── Segment 2 → NON_LEARNING / CASUAL
├── Segment 3 → LEARNING → SCIENCE
└── Segment 4 → LEARNING → MATH
```

`thread_id` continues to mean the session-local Segment / Learning Thread identity. There is no third independent Thread entity.

---

# 2. Current Input Is Authoritative

The current Student question or learning need outranks stale conversation, old images, old retrieval context, prior Subject assumptions, and historical personalization.

If Lina changes the subject, the system must follow the new question and create a new Segment when appropriate.

Example:

```text
Segment A
SCIENCE → stars
source: photographed Science page

Lina then asks:
"How do I divide 735 by 5?"

Segment B
MATH → long division
```

The previous Science page remains source context for Segment A. It does not force Segment B to remain Science unless Lina explicitly refers back to it.

> **Current behavior and current intent outrank stale context.**

---

# 3. Learning vs Non-Learning Segments

A Segment first has a semantic kind:

- `LEARNING`
- `NON_LEARNING / CASUAL`

A Learning Segment is eligible for subject attribution and later Learning Intelligence.

A Non-Learning/Casual Segment has no academic Broad Subject and does not create learning Evidence merely because conversation occurred.

Examples:

```text
"How are you today?"
→ NON_LEARNING / CASUAL
→ no learning Evidence

"Why is the sky blue?"
→ LEARNING
→ SCIENCE
→ concept/topic: light / atmosphere
```

`GENERAL_KNOWLEDGE` is **not** the fallback for casual chat. It is reserved for genuine learning questions that do not fit a more appropriate Broad Subject.

---

# 4. Controlled Broad Subject Registry

Broad Subjects come from a controlled, versioned, extensible registry. The model may select from the registry but must not invent a new top-level Broad Subject during semantic review.

The initial base registry is intentionally small and editable:

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

This registry is a stable analytical classification layer, **not** a claim about Lina's official school timetable.

The registry can be changed/versioned later without redesigning Learning Intelligence.

## 4.1 Science

`SCIENCE` remains the stable Broad Subject. Physics, Chemistry, Biology, Astronomy, Earth Science, and similar areas may appear lower in the semantic hierarchy or as independent school subjects in later Grades.

For example, in a later Grade:

```text
school_subject_ref = Physics
broad_subject = SCIENCE
```

A school may split Science into Physics/Chemistry/Biology without requiring a new intelligence architecture.

## 4.2 Language Arts

Approved top-level organization:

```text
LANGUAGE_ARTS
├── English
├── Arabic
├── French
└── future languages
```

Language-specific structure may continue through a flexible Domain Path, for example:

```text
LANGUAGE_ARTS
→ Arabic
→ Grammar
→ concept/topic: nominal sentence
```

or:

```text
LANGUAGE_ARTS
→ English
→ Reading
→ concept/topic: main idea
```

Cross-language generalization is never automatic. Evidence from English does not by itself establish the same Pattern in Arabic or French.

## 4.3 Social Studies

Approved top-level organization:

```text
SOCIAL_STUDIES
├── History
├── Geography
├── Civics
├── Economics
├── Sociology
└── Saudi Culture
```

## 4.4 Religious Studies

Approved top-level organization:

```text
RELIGIOUS_STUDIES
├── Quran
├── Islamic Studies
├── Fiqh
├── Tawheed
├── Hadith
├── Seerah
└── other relevant domains
```

The hierarchy is not required to have the same depth in every subject.

---

# 5. Flexible Domain Path and Concept/Topic

The system does **not** require one fixed `Broad Subject → Subdomain → Topic` depth for all subjects.

The governing model is:

```text
Broad Subject                 ← controlled registry
    ↓
Flexible semantic Domain Path ← zero or more levels
    ↓
Concept / Topic               ← specific learning focus
```

Examples:

```text
SCIENCE
→ Astronomy
→ concept/topic: stars
```

```text
LANGUAGE_ARTS
→ Arabic
→ Grammar
→ concept/topic: nominal sentence
```

```text
RELIGIOUS_STUDIES
→ Islamic Studies
→ Fiqh
→ concept/topic: pillars of prayer
```

The semantic `concept/topic` may be inferred from the conversation even when no school outline or book exists.

A school-specific Domain Path must not be invented when the project has no school source supporting it.

---

# 6. School Context Is Optional Enrichment

School/curriculum structure is useful context, but it is not a prerequisite for teaching and it is not the source of learner truth.

The Core Tutor and Learning Intelligence must continue to work with **zero**:

- books,
- outlines,
- timetables,
- weekly plans,
- curriculum maps,
- photographed pages.

Conceptually:

```text
Learning Segment
├── broad_subject       ← semantic classification
├── concept/topic       ← semantic learning focus
│
└── optional school context
    ├── school_subject_ref
    ├── domain_path
    ├── unit
    ├── lesson
    ├── page
    └── source_refs
```

School data improves alignment, retrieval, reporting, and curriculum-position understanding. Its absence must never block the Tutor from teaching.

---

# 7. Lina's Actual School Subjects

A controlled Broad Subject Registry and Lina's actual school-subject list are different authorities.

Actual school subjects may come from trusted Parent/Admin or school sources such as:

- timetable,
- official outline / table of contents,
- weekly plan,
- book metadata,
- other trusted school material.

When available, these sources can create/configure Grade-specific school subject identities and mappings.

Example:

```text
School subject: Science
Broad Subject: SCIENCE
Source: Grade 5 timetable / weekly plan / outline
```

Without such a source, the system may still classify a learning question as `SCIENCE`, but it must not invent that `Science` is an active official school subject for Lina.

---

# 8. School Relationship

School/curriculum relationship has three conceptual states:

- `SCHOOL_ALIGNED`
- `EXTENDED`
- `UNKNOWN`

`UNKNOWN` means only that the relationship to the current school curriculum is unknown. It does **not** mean that the academic subject is unknown.

Example with no school material:

```text
question: "Why do stars shine?"
broad_subject = SCIENCE
concept/topic = stars
school_subject_ref = null
school_relation = UNKNOWN
```

Absence of school material must **not** be interpreted automatically as `EXTENDED`.

`EXTENDED` requires affirmative reason to conclude that the learning is outside the relevant current school scope.

---

# 9. Grounding Source Priority

Useful context follows relevance and source authority, not a rigid permission chain.

Conceptually:

```text
Current Student question / current learning need
        ↓
Current photographed page/work, when relevant
        ↓
Exact school source / book / outline, when available
        ↓
Weekly plan / timetable, when relevant
        ↓
Trusted reference, when useful
        ↓
Model knowledge
```

The Tutor remains allowed to teach when higher-ranked sources are absent.

The outline/book improves school alignment. It does not own the teaching method and does not confine Lina to book wording.

---

# 10. Future Vision / Student Image Grounding

Vision is not required for the current Subject policy implementation, but the architecture must preserve the following future direction.

A photographed book/page may provide grounded context such as:

- book identity,
- Broad Subject / school subject,
- Unit / Chapter,
- Lesson title,
- page number,
- exercise/question,
- diagram/table/figure.

A photographed Student solution may later contribute observable learning signals after the approved Vision interpretation and Evidence gates.

Important separation:

```text
Photo of textbook/page
→ learning/school context
→ NOT Evidence about Lina by itself

Photo of Lina's own solution
→ learning context
→ may support Evidence only through normal governed review
```

The original image remains the source artifact. Derived Vision interpretation never replaces it.

---

# 11. Live Tutor Call Contract

SCOPE-01 must **not** introduce additional normal-turn AI calls.

Protected runtime rule:

> **One primary Tutor model call per normal Student turn.**

Do not add a separate:

- Subject classifier call,
- Topic classifier call,
- evidence extractor call,
- summarizer call,
- learner-memory call.

The existing primary Tutor execution may emit the minimum hidden metadata required by the current conversation architecture, including Segment relation such as:

- `CONTINUE`
- `NEW_SEGMENT`
- `UNCERTAIN`

No new model execution is justified merely to classify the Subject during the live turn.

---

# 12. Authoritative Semantic Classification

The authoritative semantic classification belongs to **Segment Learning Review**, after the Segment is durably closed and structurally reviewable.

For each completed Segment, semantic review may determine:

```text
segment_kind
→ LEARNING or NON_LEARNING/CASUAL

if LEARNING:
→ broad_subject
→ concept/topic
→ flexible domain path when supportable
→ optional school subject mapping
→ school relationship
→ normal learning findings/evidence dimensions
```

The Segment Review is the semantic-analysis unit.

The Session remains the durable intelligence authority.

Canonical architecture:

> **Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority**

```text
Live conversation
→ ONE primary Tutor call per turn
→ Segment boundary metadata inside that call

Closed Segment
→ background Segment Learning Review
→ staged findings only

Session finalization
→ deterministic completeness/authority checks
→ Event / Evidence activation
→ Current State / Patterns / Decision Views / Card
```

There is no normal semantic Session-level LLM call after Segment Reviews.

---

# 13. Subject Attribution and Evidence Authority

For the new Segment Review pipeline:

- a Learning Event must inherit Subject attribution from its authoritative Segment Review Finding, not blindly from a Session-level default Subject;
- a Session-level `subject` field may remain for legacy/current-entry compatibility but must not be the durable cross-subject intelligence authority;
- Evidence must remain attached to the correct Segment/Finding/Event provenance;
- incorrect or unresolved Subject attribution must fail closed rather than silently contaminate a different Subject;
- Non-Learning/Casual Segments must not create academic learning Evidence;
- cross-subject Pattern generalization remains evidence-governed and must never occur merely because multiple Subjects share one technical Session.

One Learning Segment has one primary Broad Subject for Evidence authority. Secondary-domain metadata is not required for the current implementation.

---

# 14. Future Parent-Selected Learning Policy

This is an **approved future direction**, not current implementation scope.

Future Parent/Admin onboarding may allow a learning-policy choice such as:

## A. Adaptive / Open Learning

This is the current product direction.

- current Student question drives learning;
- school sources are optional;
- Tutor may teach through explanations different from the book;
- learning outside curriculum is allowed;
- school alignment is useful context, not a teaching prison.

## B. School-Focused / Book-Led Learning

A future Parent may prefer the Tutor primarily as a school/book assistant.

This mode may require or strongly encourage:

- active school subjects,
- books,
- outlines,
- curriculum mappings,
- stronger Unit/Lesson alignment,
- stronger curriculum coverage/progress metrics,
- tighter Tutor grounding to the school's material and terminology.

The two modes must use the **same Learning Intelligence Core**:

```text
Raw Interaction
→ Segment Review
→ Event
→ Evidence
→ Current State
→ Patterns
→ Card / Decision Views
```

Do **not** create a second learner-memory or Evidence architecture for School-Focused mode.

The difference belongs in Tutor policy, grounding policy, and school-alignment/coverage decision views.

---

# 15. SCOPE-01 Acceptance

SCOPE-01 is **DONE / APPROVED** when this policy is adopted as the governing cross-subject product contract.

Approved decisions include:

1. one technical Session may contain multiple Subjects through multiple session-local Segments;
2. one Learning Segment has one primary Broad Subject;
3. current Student intent outranks stale Subject/source context;
4. Learning and Non-Learning/Casual Segments are distinct;
5. Broad Subjects come from a controlled, versioned, extensible registry;
6. `GENERAL_KNOWLEDGE` is for genuine learning, not casual chat;
7. semantic Domain Path is flexible in depth;
8. Concept/Topic may be inferred without school data;
9. school structure is optional enrichment and must not block learning;
10. actual school subjects require trusted Grade/school provenance when represented as official school subjects;
11. school relationship is `SCHOOL_ALIGNED`, `EXTENDED`, or `UNKNOWN`;
12. no school source does not imply `EXTENDED`;
13. Language Arts, Social Studies, and Religious Studies use the approved broad groupings in this document;
14. future photographed pages/work may strengthen grounding without becoming learner Evidence by identity alone;
15. no additional normal-turn Subject/classifier model call is introduced;
16. Segment Review owns authoritative semantic classification;
17. Session Finalization remains deterministic and Session-scoped authority;
18. future Adaptive/Open and School-Focused modes share the same Learning Intelligence Core.

---

# 16. Next Implementation Boundary

The next task is:

> **SUBJ-01 — Subject Attribution at Segment/Finding/Event Boundaries**

SUBJ-01 must implement the approved policy without expanding into a separate Science product, a second live-turn classifier, a second intelligence pipeline, or the future Parent-selected School-Focused mode.
