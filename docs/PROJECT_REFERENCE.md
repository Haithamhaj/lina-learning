# Lina Personal Learning System

## PROJECT_REFERENCE.md

**Status:** Approved project reference — living governing document; synchronized under `DOC-SYNC-01` pending Product Owner review  
**Audience:** Product owner, ChatGPT, Codex, AI agents, developers, reviewers  
**Primary use:** Governing source of truth for stable product intent, boundaries, architecture, learning behavior, and approved design decisions  
**Not a replacement for:** `LEARNING_PRODUCT_ROADMAP.md`, `LEARNING_INTELLIGENCE_SPEC.md`, `IMPLEMENTATION_PLAN.md`, `PROJECT_STATE.md`, implementation prompts, or task files

---

# 0. Document Authority and Truth Classification

This document owns **stable approved product truth**. It must not be used as a diary or as the current execution queue.

## 0.1 Document Authority Map

| Document | Authority |
|---|---|
| `AGENTS.md` | Rules for Codex/AI agents, protected areas, approval and verification discipline |
| `docs/PROJECT_REFERENCE.md` | **Stable approved product truth and durable product/architecture decisions** |
| `docs/LEARNING_INTELLIGENCE_SPEC.md` | Canonical Learning Intelligence semantics, rubrics, lifecycle, authority, and reprocessing contracts |
| `docs/LEARNING_PRODUCT_ROADMAP.md` | Approved product-evolution direction, capability sequencing, and gates; roadmap presence alone is not execution approval |
| `docs/IMPLEMENTATION_PLAN.md` | Implementation direction, technical boundaries, sequencing principles, and deferred complexity |
| `docs/CHILD_SAFETY_POLICY.md` | Child-safety baseline and Parent Learning Boundary semantics |
| `project-state/PROJECT_STATE.md` | **Current operational truth**: current goal, reality, decisions, risks, and next action |
| `TASKS.md` | Durable task history and executable/current task state |
| `project-state/SYSTEM_MAP.html` | Visual architecture plus current operational-readiness overlay |

Historical documents and task records remain valuable provenance. If historical wording conflicts with a newer governing decision, it remains historical context and must not silently resurrect superseded architecture.

## 0.2 Truth Classes Used by the Project

The project deliberately separates:

- **Stable Product Truth** — what the product is and the durable principles it must preserve.
- **Architecture Truth** — protected system boundaries and authority relationships.
- **Approved Deferred Direction** — intended capabilities whose implementation is gated by sequencing/evidence.
- **Current Operational State** — what is running, verified, blocked, or next now; this belongs primarily in `PROJECT_STATE.md`.
- **Historical Record** — prior phases, tests, fixes, and superseded approaches retained for provenance.

Do not turn temporary current task names or deployment choices into permanent product truth.

---

# 1. Project Identity

## 1.1 Name

**Lina Personal Learning System**

## 1.2 Product Definition

Lina Personal Learning System is a personal, evidence-grounded AI learning environment designed first around Lina, beginning with **Grade 5 Mathematics and Science**.

It aims to preserve the natural flexibility of a capable general AI tutor while adding the durable learning capability that a normal chat, Custom GPT, or Gem does not provide reliably over time: **evidence-grounded longitudinal understanding of how the individual learner is learning, and relevant personalization of future teaching based on that evidence.**

A general AI can already answer questions, read a PDF, transcribe speech, interpret an image, or explain a concept. Those are enabling capabilities, not the core differentiator of Lina Learning.

The differentiating product loop is:

```text
Natural learning interaction
        ↓
Preserved raw source history
        ↓
Completed-Segment semantic learning interpretation
        ↓
Session-authorized Evidence
        ↓
Current State / Patterns
        ↓
Learner Intelligence Card
        ↓
Relevant later personalization
        ↓
Better future teaching
```

The product is not intended to reproduce school digitally, act as a homework-answering chatbot, or operate as a conventional LMS. The current Student question drives the interaction. Books, school materials, trusted references, and captured pages are optional grounding sources that improve alignment and context; the Tutor remains usable without them.

The system combines, over its intended product evolution:

- a conversational AI Tutor,
- optional book/curriculum/reference grounding,
- multimodal Student input,
- visual and interactive learning representations,
- an event/evidence Learning Intelligence layer,
- compact longitudinal understanding of Lina's learning,
- relevant evidence-based personalization,
- and a Parent/Admin experience for oversight, safety boundaries, content management, evidence inspection, and system tuning.

The durable asset is not the Tutor model itself.

> **The durable product asset is the evolving, evidence-grounded, revisable understanding of Lina's learning and the system's ability to use it appropriately.**

Models, providers, books, UI components, representations, and extraction approaches may change. Raw learning history, source provenance, and the ability to reconstruct and improve derived intelligence must remain durable.

---

# 2. Core Product Objective

The system exists to help Lina **understand**, not merely finish tasks.

The primary objectives are:

1. Help Lina understand Grade-level Math and Science concepts using explanations appropriate to her current understanding.
2. Preserve the freedom to explore, ask outside the book, revisit old ideas, or move ahead when useful.
3. Support school learning without making the book's exact teaching method or current school position mandatory.
4. Build a persistent, evidence-grounded understanding of how Lina is learning over time.
5. Adapt support based first on what Lina demonstrates now, informed by relevant historical intelligence without becoming constrained by it.
6. Learn, from evidence, which teaching representations and support approaches appear useful in which contexts without assigning fixed learning-style labels.
7. Preserve raw learning history so future improvements to review, evidence rules, pattern logic, or models can re-analyze prior learning.
8. Keep the learner experience low-pressure, visually engaging, and natural for a child around ten years old.
9. Make important system conclusions explainable and inspectable by Parent/Admin.
10. Keep AI usage observable, replaceable, task-routed, and cost-aware.

The system should become more useful as Lina uses it, but should never require full historical conversation to be loaded into every future interaction.

---

# 3. Product Boundaries and Capability Status

## 3.1 Approved Product Scope

The intended product direction includes:

- Lina-first responsive web application.
- Grade 5 as the first active Grade environment.
- Mathematics and Science as the initial subject family.
- Conversational Tutor for learning, homework support, and open exploration.
- Arabic/English natural conversation, with later subject/language expansion possible.
- Question-driven optional grounding from books, school material, captured pages, trusted references, and model knowledge.
- Text input.
- Speech-to-text input.
- Student image/photo input.
- Handwritten work and drawings as potential learning evidence when the Vision path is authorized.
- Homework/page/diagram images.
- Vision-based interpretation of Student work while preserving the original.
- Annotation of the original image first when appropriate.
- Clean visual reconstruction when annotation is insufficient.
- Visual/interactive learning representations using typed, bounded renderers.
- Event capture and source provenance.
- Segment Learning Review and Session-authorized Evidence.
- Current Learning State.
- Temporal Learner Patterns.
- Compact Learner Intelligence Card.
- Derived mastery/confidence/retention decision views.
- Parent evidence/intelligence inspection.
- Parent-configurable learning boundaries for age/family-sensitive topics.
- Non-overridable child-safety baseline.
- Model routing and AI usage/cost logging.
- Reprocessing and rebuildability.
- Grade transition through Parent/Admin activation.

## 3.2 Current Capability Classification

The intended scope must not be confused with current implementation status.

| Capability | Product classification | Current implementation status |
|---|---|---|
| Text conversation | Approved core | Implemented |
| Math Tutor | Approved core / current proving ground | Implemented |
| Arabic/English continuity | Approved core | Implemented |
| Optional book/content grounding | Approved supporting capability | Implemented; Parent operational UX remains partial |
| Learning Intelligence core | Approved differentiator | Implemented / Full-System Acceptance completed |
| Relevant cross-session personalization | Approved differentiator | Implemented technically; recurring natural Lina validation remains pending |
| Science | **Approved core product direction** | Deferred by sequencing / frozen for production implementation |
| Voice → STT | **Approved core product direction** | Deferred by sequencing / frozen |
| Vision / homework photos | **Approved core product direction** | Deferred by sequencing / frozen |
| Handwriting/drawing interpretation and evidence | **Approved core product direction** | Deferred by sequencing / frozen |
| Annotate original / clean reconstruction | Approved core direction | Deferred with Vision |
| Visual/interactive learning artifacts | **Approved core product direction** | Deferred by sequencing / bounded Math readability is separate |
| Learning Canvas / broader Artifact Engine | Approved direction | Gated / frozen |
| Parent Evidence / Intelligence visibility | Approved first-product-loop capability | Partial / broader UI deferred |
| Parent Core Profile/onboarding | Approved future foundation | Deferred |
| Trusted Educational References | Approved future pilot | Deferred / evidence-gated |
| Grade progression | Approved direction | Production deferred |

A capability being deferred does **not** mean it is optional noise or rejected. Real Lina behavior should help order approved capabilities; it does not rediscover the product idea from scratch.

## 3.3 Explicitly Out of Scope Without a New Decision

Do not expand the current project into the following without later explicit approval:

- Native iOS/Android app.
- Offline mode.
- Teacher portal or classroom management.
- School SIS/LMS integration.
- Multi-family SaaS workflows.
- Billing/subscription platform.
- Organization/tenant administration.
- Leaderboards, competitive ranking, pressure streaks, or points economy.
- Exam Mode as a pressure-oriented feature.
- Countdown-based performance pressure.
- Social features.
- Multi-student classroom analytics.
- Universal cross-grade knowledge graph.
- Automatic cross-grade concept mapping as a core dependency.
- Generic autonomous agent framework for all actions.
- Chain-of-agents execution for every Tutor turn.
- Dedicated vector database unless PostgreSQL/pgvector becomes insufficient.
- Redis/Celery unless workload proves a need.
- Graph database as an MVP dependency.
- Advanced ML clustering as a current product requirement.
- Psychological diagnosis.
- Personality diagnosis.
- Intelligence labeling.
- Fixed learning-style labels such as "visual learner".

---

# 4. Real-Use Status

## 4.1 Verified Limited Real-Lina Use

**Limited real Lina use has occurred.** Lina herself participated in part of a real Tutor interaction. The same persisted interaction was then continued by the Product Owner and used as part of subsequent system testing and Tutor calibration.

This is stronger than synthetic model testing and must not be erased from project history.

## 4.2 What Limited Use Does Not Prove

The following remain separate verification horizons:

| Verification scope | Status |
|---|---|
| Lina herself interacted with the Tutor | **VERIFIED — LIMITED** |
| Basic real Student interaction | **PARTIALLY VERIFIED** |
| Persisted real interaction available for later testing/calibration | **VERIFIED** |
| Stable recurring/daily Lina use | **NOT VERIFIED** |
| Natural Lina `Session → Segment Review → Session Finalization → Evidence → Card → later Tutor` loop | **NOT VERIFIED end-to-end as recurring real use** |
| Longitudinal personalization across multiple natural Lina sessions over time | **NOT VERIFIED** |

Do not use the absolute shorthand `REAL-LINA = NOT VERIFIED` when it would deny the verified limited interaction. Likewise, do not upgrade limited use into daily or longitudinal validation.

---

# 5. Users and Roles

## 5.1 Lina — Student

Lina is the primary learner and main user of the learning experience. Her interface exposes learning actions, not learner analytics.

The intended experience supports, as capabilities are implemented and promoted:

- entering a learning experience naturally,
- asking questions,
- typing,
- speaking,
- showing a photo/page/work sample,
- photographing handwritten work or drawings,
- asking for hints, examples, easier explanations, or more challenge,
- interacting with visual/interactive representations,
- changing topic without managing internal Segments or chats.

Current implementation is Math/Text-first; deferred multimodal/Science capabilities above must not be presented as already live.

Lina should not see:

- mastery percentages,
- weakness labels,
- evidence counts,
- raw Learner Intelligence,
- Parent observations,
- model settings,
- AI costs,
- processing jobs,
- Grade archive controls.

## 5.2 Parent/Admin

Parent/Admin controls the learning environment and should be able, as the first product loop matures, to:

- manage authoritative child facts through Student Core Profile,
- manage books/references and Grade context,
- inspect processing status,
- view important Math/Science learning state,
- inspect Evidence behind important conclusions,
- inspect Patterns and meaningful changes,
- understand important Tutor adaptations,
- inspect AI usage/cost,
- configure Parent Learning Boundaries,
- challenge a conclusion or request re-validation,
- understand why the system reached an important conclusion.

Parent/Admin does not directly overwrite evidence-grounded learner conclusions. Parent input can create a hypothesis or review request; learning state remains evidence-governed.

## 5.3 Student Core Profile

Student Core Profile answers “who is this child?” It is Parent/Admin-owned factual state: child display/name identity, date of birth when supplied, and linkage to active Grade/Grade Period. Age is derived at runtime rather than maintained as a fixed learner label.

Student Core Profile is separate from Learner Intelligence, Evidence, conversation context, Segment State, Safety classification, and teaching decisions. Parent/Admin may not write weakness, mastery, learning-style, or support-preference labels into it.

## 5.4 UX Separation

```text
Lina UI   → Learning
Parent UI → Understanding + Control
```

Internal complexity must not leak into Lina's experience.

---

# 6. Learning Philosophy and Tutor Principles

## 6.1 Understanding Is the Objective

The Tutor prioritizes understanding over task completion. Withholding an answer is not itself an educational objective.

If Lina remains genuinely stuck after reasonable support, the Tutor should teach the solution clearly, explain why it works, and then check understanding with a new application.

## 6.2 Books and References Are Grounding, Not Teaching Authority

Books, school materials, trusted references, outlines, and captured pages can provide Grade scope, terminology, expected depth, examples, exercises, and contextual alignment.

They do not authorize, restrict, or own the teaching method. The Tutor may answer from model knowledge when no useful source exists and may choose alternative valid explanations, representations, examples, analogies, or micro-detours.

The product must not reduce RAG to “retrieve page and paraphrase it.”

## 6.3 Question-Driven Learning

Lina's current question or need is authoritative. School/book/reference context may improve alignment but does not decide what she is allowed or required to study now.

Relevant recent conversational context may help low-information continuations, but relevance outranks recency and the current question outranks both.

## 6.4 No Formal Diagnostic by Default

A new topic does not automatically begin with a formal diagnostic test. Prerequisites are investigated naturally if interaction evidence suggests a gap.

## 6.5 Current Behavior Outranks Historical Personalization

Historical intelligence is advisory.

> **Never personalize away demonstrated independence.**

If Lina previously needed a representation but now solves independently, current behavior wins.

## 6.6 Personalization Should Be Felt, Not Announced

Use useful representations/support naturally. Do not repeatedly announce labels such as “you are a visual learner.”

## 6.7 No Psychological or Personality Conclusions

The system may describe observed learning behavior in supported context: hint dependency, self-correction, transfer, persistence in a task, retention, or response to challenge.

It must not convert those observations into psychological diagnosis, personality classifications, intelligence labels, global motivation judgments, or fixed learning styles.

## 6.8 Low-Pressure Learning

Avoid countdowns, leaderboards, public scores, red failure pressure, exam-oriented pressure, and repetitive drill for its own sake. Light celebrations/badges may recognize meaningful learning without becoming a pressure economy.

## 6.9 Bilingual Interaction

Arabic questions should receive natural Arabic; English questions natural English; mixed language may receive a useful natural mix. Mathematical notation alone is not a language switch. Clear current-language intent overrides history while preserving relevant conversational context.

## 6.10 Child Safety and Parent Learning Boundaries

The product uses two layers:

1. **Non-overridable child-safety baseline** — mandatory product/runtime restrictions Parent settings cannot weaken.
2. **Parent-controlled learning boundaries** — age/family-sensitive categories using `ALLOW`, `AGE_APPROPRIATE_ONLY`, or `REDIRECT_TO_PARENT`.

Hard baseline safety is upstream. For normal Tutor turns, configurable Parent Boundary semantic applicability is determined within the same primary Tutor call; server-owned Parent settings remain final authority and the server enforces the visible result.

Safety/policy audit records are separate from Learner Intelligence.

Detailed rules belong to `CHILD_SAFETY_POLICY.md`.

---

# 7. Grade and Curriculum Model

## 7.1 Grade Activation

Grade transition is Parent/Admin-controlled; the system does not need to infer it automatically.

The longer-term product direction is to activate the next Grade explicitly and carry only compact useful transition intelligence while retaining prior Grade history for audit/reprocessing.

## 7.2 What Carries Forward

Only important, stable, or unresolved intelligence useful for future teaching should carry to the next Grade by default: significant foundational gaps, useful stable teaching patterns, unresolved misconceptions/loops, retention characteristics, and meaningful capabilities.

Full previous-Grade transcripts, every mastery view, and every lesson detail do not enter the next Grade runtime by default.

## 7.3 No Complex Cross-Grade Engine in MVP

If a later Grade exposes a missing foundation, the Tutor can detect it from current interaction, refresh it, and continue. A universal cross-grade prerequisite engine is not required.

---

# 8. Content and Book Understanding

## 8.1 Original Source Preservation

Original uploaded sources remain immutable source artifacts. Derived processing may be regenerated under new versions without requiring re-upload.

## 8.2 Docling Foundation

Docling is the baseline structural document-processing foundation. It can preserve hierarchy, reading order, headings, text, tables, pictures, formulas, page references, and provenance where available.

Docling is not itself the curriculum model.

## 8.3 Educational Semantics Are Optional Enrichment

Educational semantic extraction may add Unit/Lesson/Concept/Objectives/Examples/Exercises/Vocabulary/Figure metadata for navigation and analysis.

It is **not required** for Tutor availability, basic retrieval, Candidate metadata, Evidence, or Learner Intelligence.

Concept identity for Learning Intelligence belongs primarily to the interaction: current question, conversation, current image/page when available, relevant retrieved context, and model understanding.

## 8.4 Content Pipeline

```text
Learning Source
    ↓
Preserve original + provenance
    ↓
Structural extraction / normalization
    ↓
Retrieval-ready representation
    ↓
Hybrid search/index

Optional enrichment:
Structural representation
    ↓
Educational semantics
```

## 8.5 Student-Captured Pages

A future captured homework/page image is an interaction artifact by default. It may become an optional learning source when the Vision path is authorized and reliability is sufficient. A photographed page does not become learner Evidence merely because it exists.

## 8.6 Trusted References

Trusted references are an approved future pilot. They should enter through the existing Learning Source/Retrieval boundary rather than a parallel RAG subsystem. Their absence never blocks the Tutor.

---

# 9. Retrieval Architecture

Retrieval is optional grounding driven by the current question.

Preferred conceptual flow:

```text
Current Student question
    ↓
Grade / Broad Subject when known
    ↓
Metadata/structural candidates
    ↓
Lexical + vector retrieval
    ↓
Relevant source-linked context
```

Blind fixed-token-first chunking is not the primary strategy. Preserve structural hierarchy and split only where practical limits require it.

Recent conversational/topic context is advisory only. Current School Focus is not a learning-path authority and historical `current_school_focus` state must not re-enter runtime authority.

The accepted Hybrid Segment Context remains Current-Segment-scoped and relevance-first. It can include:

```text
Current Turn
+ Full Immediate Exchange
+ compact Structured Segment State
+ selected complete raw Exchanges from the Current Segment
+ relevant Learner Intelligence separately
+ question-driven RAG separately
+ effective Safety directive separately
```

Do not automatically inject full Session history, prior-session raw transcripts, all topic history, or an archive-memory service into normal Tutor context.

---

# 10. Tutor Runtime

## 10.1 Fixed Tutor Identity

Tutor identity is stable product policy. It should be warm, patient, clear, non-shaming, age-appropriate, bilingual, honest about uncertainty, and focused on understanding without baby-talk or unnecessary formalism.

## 10.2 Teaching Mode, Strategy, Method, and Prior Relation

TeachingMode, TeachingStrategy, and TeachingMethod are distinct. The same primary Tutor call may semantically select the instructional mode, support strategy, pedagogical representation, and relation to the immediately previous persisted TeachingMethod.

The small internal TeachingMethod registry owns canonical identities such as `CONCRETE_EXAMPLE`, `VISUAL_REPRESENTATION`, `WORKED_EXAMPLE`, `SOCRATIC_FOCUS`, `DECOMPOSITION`, `ANALOGY`, and `SYMBOLIC_EXPLANATION`.

Runtime validates canonical values, lineage, safety, and structural consistency. It must not replace semantic understanding with language keyword routing or add an extra normal-turn classifier call.

Selecting/using a method is **not Evidence that it worked**. Effectiveness requires observable Student outcome, later Segment Review interpretation, and Session-authorized Evidence.

## 10.3 Normal Runtime Path

```text
Current Student Turn
    ↓
Hard Safety baseline
    ↓
Conversation / Segment context
    ↓
Optional question-driven grounding
+
Relevant Learner Intelligence
+
server-owned Parent Boundary settings
    ↓
ONE primary Tutor model call
    ↓
Student-facing response
+ bounded semantic teaching/segment/subject metadata
+ optional provisional Candidate metadata
    ↓
Deterministic validation / persistence / final policy enforcement
```

The system avoids Tutor → Critic → Evaluator → Profile Agent chains for every turn.

## 10.4 Support Ladder

Support is adaptive, not rigid: independent attempt, focusing question, hint, stronger hint, changed representation, explicit teaching, guided application, independent follow-up. The Tutor may skip levels based on current behavior.

## 10.5 Homework Behavior

Give a meaningful opportunity to think; support/hint; change representation when useful; teach the solution clearly if continued hinting no longer helps; explain why; then check with a new application.

## 10.6 Repetition Control

Repeated independently reasoned success should reduce low-information near-identical practice and favor variation, deeper reasoning, transfer, useful progression, restored agency, or a natural close. Do not infer mastery from a fixed count.

---

# 11. Cross-Subject and School-Scope Policy

The accepted subject policy is:

- one technical Session may contain multiple Subjects through separate Segments;
- one Learning Segment owns one primary Broad Subject;
- a meaningful subject switch starts a new Segment;
- returning after an intervening Segment creates a new Segment;
- no extra Subject-classifier model call is approved;
- Segment Review is durable semantic Subject authority;
- Broad Subject and school relationship are separate axes;
- school relationship is `SCHOOL_ALIGNED`, `EXTENDED`, or `UNKNOWN`;
- absence of a school source means `UNKNOWN`, not automatically `EXTENDED`;
- current Student intent outranks stale prior Subject/source context;
- `LEARNING` and `NON_LEARNING / CASUAL` are distinct; casual conversation creates no academic Evidence.

`SCOPE-01` and `SUBJ-01` are accepted. Do not treat cross-subject attribution as an unresolved future architecture question.

---

# 12. Multimodal Learning — Approved Direction

## 12.1 Input Principle

The intended product is multimodal even though the current proving ground is Text/Math-first.

Approved future Student input includes:

- speech → transcript,
- current page/homework photo,
- handwritten work,
- drawing,
- diagram/image.

## 12.2 Voice

Approved current policy direction:

```text
Audio
  ↓
Speech-to-text
  ↓
Transcript
  ↓
Normal Tutor pipeline
```

Transcript is retained. Raw audio is not retained after successful transcription under the current approved direction unless a later speaking/pronunciation policy explicitly changes this.

## 12.3 Student Image Understanding

The original image remains source authority. Vision interpretation is derived and may be uncertain. If uncertainty can change the answer or Evidence meaning, the Tutor should clarify rather than guess.

## 12.4 Image Response Priority

```text
Understand original
    ↓
Clarify if needed
    ↓
Annotate original first when useful
    ↓
If insufficient
    ↓
Create clean derived reconstruction
```

AI annotation/reconstruction never replaces the original learner work as Evidence source.

---

# 13. Visual and Interactive Learning Artifacts — Approved Direction

The Tutor is not intended to remain text-only. When a visual or interactive representation materially improves understanding, the product should be able to show one.

Simple visuals may be inline; richer experiences may use a bounded Learning Canvas without starting a new learning session or losing conversation continuity.

Primary architecture:

> **Typed Artifact Specifications + reusable, tested renderers.**

The application owns rendering. Arbitrary unsandboxed AI JavaScript is rejected.

Approved renderer direction includes native React/SVG and, when promoted by evidence, bounded tools such as Motion, JSXGraph, React Konva, and MathLive. The exact renderer stack remains implementation-level and should be reevaluated when the capability is promoted.

Artifact failure must never block learning. Meaningful artifact interaction may contribute to Evidence only through the governed learning-intelligence path; raw clickstream is not learner intelligence.

---

# 14. Learning Intelligence — High-Level Contract

Detailed rubrics and lifecycle rules belong in `LEARNING_INTELLIGENCE_SPEC.md`.

The canonical architecture is **implemented and accepted**:

```text
Raw Interaction History
        ↓
Optional Provisional Candidate Hints
        ↓
Closed Structurally Reviewable Segment
        ↓
Segment Learning Review
        ↓
Staged Semantic Findings
        ↓
Session Intelligence Finalization
        ↓
Session-authorized Learning Events / Evidence
        ↓
Current Learning State + Learner Patterns
        ↓
Learner Intelligence Card
        ↓
Decision Views / relevant Tutor personalization / future Parent insights
```

## 14.1 Raw History

Raw interaction history is source material for future re-analysis: Student messages, Tutor responses, transcripts, future Student images/drawings/work, interaction assets, timestamps, Session/Segment refs, and model/request lineage where applicable.

Derived conversation metadata is rebuildable navigation/context metadata and cannot be the sole Evidence source.

## 14.2 Candidate Metadata

The same primary Tutor call may emit hidden Candidate metadata for observable potentially meaningful learning signals.

Candidate means “worth later review,” not “true learner memory.” It is optional, provisional, source-linked, and auditable. Segment Review may confirm, reject, reinterpret, combine, or find supported learning directly from raw Segment history when a Candidate was absent.

## 14.3 Segment Review and Session Finalization

Every closed Segment with valid lineage and at least one persisted raw Student interaction is structurally reviewable. Structural reviewability determines only whether semantic Review is safe to run; it does not decide whether learning occurred.

Segment Review receives complete relevant raw Segment history and produces staged findings. `findings=[]` is valid.

Session remains the durable activation authority. Session Finalization validates the required completed Review set, compatible versions, provenance, and lineage, then deterministically materializes authorized Events/Evidence and downstream State/Patterns/Decision Views. It makes no ordinary broad semantic Session model call by default and permits no partial activation.

Historical legacy Session Evidence remains preserved/auditable for compatibility/reprocessing, but it is **not** the current primary semantic architecture.

## 14.4 Meaningful Event Gate

Learning intelligence represents meaningful learning occurrences: attempts, understanding, misconception, self-correction, transfer, retention, support change, strategy outcome, or important state change. Greetings and ordinary conversation remain raw history but do not become academic intelligence merely because they occurred.

---

# 15. Learner Intelligence Card

The Card is not a transcript summary, complete mastery database, or new source of truth. It is an on-demand, compact runtime projection of what currently matters for a better interaction.

It is built from active Current State and relevant active/stable Patterns, source-linked to their authoritative rows.

CurrentFocus is not a learner-intelligence authority. Relevant current subject/conversation context may assist selection, but stale school-position state must not re-enter the Card.

The Card remains bounded by entry/character budgets and relevance rules. A substantive unmatched current question should not inherit stale intelligence merely because something was historically recent.

---

# 16. Mastery, Confidence, and Decision Views

Mastery, confidence, retention, independence, and strategy-effectiveness displays are **derived decision views**, not source learner truth.

Internal numeric calculations may support deterministic thresholds/ranking, but Parent-facing output should prefer interpretable categorical states rather than pseudo-scientific precision such as `83.47% mastery`.

Changing decision policy should permit recomputation without rewriting raw Events/Evidence.

---

# 17. Conversation Context: Sessions and Segments

## 17.1 Session Lifecycle

Sessions close automatically after configured inactivity plus grace. Session closure completes/reconciles the final open Segment, queues required Segment Reviews, and—when the complete compatible Review set exists—queues deterministic Session Intelligence Finalization.

The current implemented runtime no longer depends on legacy Session-wide semantic consolidation for new `segment-finalization-v1` Sessions.

A new Session begins conversationally fresh. Prior-session raw transcripts are not automatically injected. Relevant cross-session learning state flows through Session-authorized State/Patterns/Card, not through a replacement conversation-memory subsystem.

## 17.2 Learning Thread = Session-local Segment

A Learning Thread is the session-local contiguous Segment; there is no third conversation entity. A Segment contains coherent contiguous Turns while local intent/topic remains coherent. A meaningful transition starts a new Segment. Once another Segment intervenes, an earlier Segment is not reopened.

Optional Durable Conversation Topic may provide Grade-scoped navigation identity, but it is not Evidence, Learner Intelligence, curriculum authority, or Safety authority.

## 17.3 Structured Segment State and Hybrid Context

The technical CTX-03 Hybrid Segment Context runtime is implemented/verified technically. Structured Segment State is compact, source-linked, rebuildable conversational metadata—not Evidence or Learner Intelligence.

Normal recall is Current-Segment-only. Historical archive retrieval remains a separately gated on-demand future seam.

---

# 18. Parent Experience

The Parent interface should prioritize **insight before activity tracking**.

The first product loop ultimately needs enough Parent capability to understand important learning state, inspect Evidence behind material conclusions, manage useful content/Grade context, and inspect AI usage/cost without becoming a surveillance dashboard.

Desired areas include:

- Student Core Profile facts,
- overview and subject views,
- Learner Intelligence/Pattern/Evidence inspection,
- meaningful history and change,
- content/status/reprocessing,
- Grade controls,
- Learning Boundary settings,
- Recent Redirects / Policy Audit separate from Learner Intelligence,
- task/model route and AI usage/cost visibility where appropriate.

Parent UI implementation is intentionally broader than what is required for the current Math/Text proving ground.

---

# 19. AI and Model Architecture

## 19.1 Core Principle

> **Use AI for cognition; use deterministic system logic for state, weights, lifecycle, authority, and plumbing.**

## 19.2 Model Gateway

Application modules request AI by task rather than provider name.

Current/relevant task classes include:

- `tutor`
- `segment_evidence` — current implemented Segment Review route
- `session_evidence` — legacy/historical compatibility route where required
- `curriculum_semantics` — optional enrichment
- `embedding`
- future/gated `vision_student_work`
- future/gated `vision_content_enrichment`
- future/gated `speech_to_text`
- future/gated `grade_transition`
- optional future image generation / external verification

The current real provider implementation uses OpenAI for supported real routes. This is an operational implementation choice, not permanent product/provider lock-in.

## 19.3 Provider Independence

Tutor/Intelligence/Content domains must not call provider SDKs arbitrarily. Provider/model can change behind Model Gateway task routes without rewriting domain logic.

Use the fastest/lowest-cost model that meets task quality. Model selection should be benchmarked on Lina-specific scenarios rather than assumed from reputation.

---

# 20. Cost and Observability

Each AI execution should record enough information to audit task, provider, model, usage, latency, estimated cost, success/failure, fallback where applicable, and relevant processing/prompt/schema lineage.

Stored data is not automatically model context. Tutor context should remain bounded and relevance-selected.

Parent/Admin eventually needs compact cost/usage visibility, while engineering detail stays available for debugging without becoming the learner experience.

---

# 21. Rebuildability and Versioning

> **Original source remains; derived intelligence can be rebuilt.**

Content can be reprocessed from original sources. Learner intelligence can be reprocessed from retained raw interactions and completed Segment lineage under selected versions.

Reprocessing must preserve old generations for audit, stage new outputs safely, and activate coherent authority atomically for the selected scope.

Important derived paths record version/provenance such as provider/model, prompt/schema, Segment Review contract, evidence rubric, pattern/decision policy, processing run, and timestamps as appropriate.

Validation philosophy:

```text
Observe
→ Audit
→ Measure against governing rubrics
→ Correct prompt/rule/policy
→ Reprocess
→ Compare
```

The requirement is not “AI can never be wrong.” The requirement is that important learner conclusions remain traceable, revisable, and rebuildable.

---

# 22. Implementation Architecture Principles

## 22.1 Architecture Style

**Modular Monolith + Vertical Slice First.**

Do not begin with microservices. Keep internal boundaries clear while preserving operational simplicity.

Logical domains include Tutor, Intelligence, Content, Retrieval, Learning Artifacts, Model Gateway, Grade, and Platform.

## 22.2 API Layer

API routes stay thin. Prefer:

```text
API route
   ↓
Application/domain service
   ↓
Repository / provider / Model Gateway
```

Avoid enterprise abstraction for its own sake.

## 22.3 Background Work

Initial background architecture is:

```text
PostgreSQL jobs table + worker process
```

The Worker currently handles session lifecycle and registered content/intelligence jobs. Do not introduce Redis/Celery merely because background work exists.

Interactive Tutor responses remain synchronous/streaming rather than job-based.

---

# 23. Technology Direction

Approved current direction:

- **Frontend:** Next.js, TypeScript, responsive web, SSE.
- **Backend:** Python, FastAPI.
- **Database:** PostgreSQL + pgvector, JSONB where useful.
- **Object storage:** provider-neutral private storage; S3-compatible for persistent production-style deployments where assets are required.
- **Document processing:** Docling structural foundation.
- **Background jobs:** PostgreSQL jobs + separate Worker.
- **Model access:** task-routed Model Gateway.
- **Vector retrieval:** pgvector initially.
- **Artifacts when promoted:** typed React/SVG-oriented renderer architecture, with specialized libraries only where concrete learning need justifies them.

Replit configuration in the repository is an environment convenience, not a product architecture decision.

---

# 24. System Invariants

The following are protected unless Product Owner explicitly changes them:

1. Understanding is more important than answer withholding.
2. Current Student question/behavior outranks stale school context and historical personalization.
3. Books/references ground learning; they do not own teaching method or permission to learn.
4. Tutor remains usable with zero curriculum content.
5. Curriculum semantic extraction is optional enrichment, not a basic Tutor/RAG/intelligence prerequisite.
6. One primary Tutor model call is the normal Student-turn path.
7. Candidate metadata is provisional and never durable Evidence authority.
8. Completed Segment Review is semantic learning-analysis authority.
9. Session Finalization is deterministic durable intelligence authority; no partial activation.
10. Current State and Learner Patterns are distinct.
11. Current behavior can override/weaken historical personalization.
12. Never personalize away demonstrated independence.
13. TeachingMethod selection/use is not Evidence of effectiveness.
14. Meaningful learner intelligence is traceable to raw Student source interaction/work.
15. Mastery/confidence are derived views, not source truth.
16. Raw Student work is not replaced by AI interpretation.
17. AI annotation/reconstruction is derived, not what Lina originally produced.
18. No psychological/personality/intelligence/fixed learning-style diagnosis.
19. Normal Tutor input does not inject full historical transcripts.
20. Learning Thread means session-local contiguous Segment; intervened old Segments are not reopened.
21. Durable Conversation Topic is optional navigation metadata, not learner memory/authority.
22. Safety, conversation context, curriculum grounding, Student Core Profile, pedagogy metadata, and Learner Intelligence remain separate authorities.
23. Patterns begin narrow and broaden only with Evidence.
24. Pattern lifecycle/weighting is governed deterministically and versioned.
25. Original books/raw history remain preserved where policy allows so derived data can be rebuilt.
26. No unnecessary AI call without identifiable learning/system value.
27. Artifact failure must not block learning.
28. Student UX remains simpler than system internals.
29. Parent insight must not become surveillance-style activity tracking.
30. Grade transition is Parent/Admin-controlled and carries compact useful intelligence rather than full prior runtime.
31. Math + Science are intended initial subjects, but current production implementation may remain Math-first until Science is explicitly promoted.
32. No microservices, graph infrastructure, generic agent framework, second vector DB, Redis/Celery, or deployment redesign without demonstrated need/approval.
33. Child-safety baseline is non-overridable; Parent boundaries may restrict further but not weaken it.
34. Parent Boundary states are `ALLOW`, `AGE_APPROPRIATE_ONLY`, and `REDIRECT_TO_PARENT`.
35. Broad Subject and school relationship are separate; no school source means `UNKNOWN`, not automatically `EXTENDED`.
36. Current School Focus is not a learning-path authority.

---

# 25. Approved and Superseded Decisions

## 25.1 Key Approved Decisions

| Decision | Status |
|---|---|
| Lina-first personal learning system | Approved |
| Grade 5 first | Approved |
| Math + Science initial product family | Approved |
| Current question drives interaction | Approved |
| Tutor always available without book/content | Approved |
| Optional question-driven grounding | Approved |
| Structural/hybrid retrieval | Approved |
| Educational semantics optional/rebuildable | Approved |
| Learning Intelligence + personalization core differentiator | Approved |
| Segment-scoped semantic Review | Implemented / Approved |
| Session-scoped durable intelligence authority | Implemented / Approved |
| Candidate provisional only | Approved |
| Current behavior outranks history | Approved |
| One primary Tutor call | Approved |
| Multimodal Student input | Approved core direction / implementation gated |
| Handwriting/drawing may become Evidence through governed path | Approved core direction / gated |
| Annotate original first | Approved direction / gated |
| Clean reconstruction when useful | Approved direction / gated |
| Interactive typed learning artifacts | Approved core direction / gated |
| Parent evidence/intelligence visibility | Approved first-product-loop direction |
| Trusted Educational Reference pilot | Approved future pilot |
| Cross-subject Session/Segment policy | `SCOPE-01` accepted |
| Reviewed Broad Subject durable attribution | `SUBJ-01` accepted |
| Model Gateway provider replaceability | Approved |
| Modular Monolith | Approved |

## 25.2 Explicitly Superseded / Rejected — Do Not Resurrect

The following statements must not be used as current implementation requirements, even if preserved in historical records:

- **Current School Focus as learning-path authority — SUPERSEDED.**
- **A real book/content readiness required before Tutor use — SUPERSEDED.**
- **Mandatory educational semantic extraction before Tutor/basic RAG — SUPERSEDED.**
- **Curriculum Concept rows required before Learning Intelligence — SUPERSEDED.**
- **Session-level semantic LLM consolidation as the primary current review architecture — SUPERSEDED.**
- **Second normal-turn Candidate/Subject/Topic classifier call — REJECTED.**
- **Candidate metadata as Evidence or personalization authority — REJECTED.**
- **Adaptive mutable Persona as the main personalization mechanism — REJECTED.**
- **Exam-pressure/monitoring learning model — REJECTED.**
- **Fixed psychological/personality/intelligence/learning-style labels — REJECTED.**
- **Full prior-session transcript injection as normal memory — REJECTED.**
- **Arbitrary unsandboxed AI JavaScript artifacts — REJECTED.**
- **Replit as product architecture — NOT AN APPROVED PRODUCT DECISION.**
- **A specific permanent model/provider as product architecture — NOT APPROVED.**

---

# 26. Assumptions

Working assumptions, not immutable decisions:

1. Responsive web is sufficient for early Lina use.
2. Grade 5 Math/Science sources may be available digitally/scanned, but the Tutor cannot depend on them.
3. Docling is useful for structural extraction but quality must be measured.
4. A fast/cost-efficient model may handle normal Tutor work; quality must be tested on actual Lina scenarios.
5. Lina may naturally use text, speech, handwriting, drawings, and photos when those capabilities exist.
6. A bounded library of high-value representations may cover many early Math/Science needs better than a giant generic artifact platform.
7. PostgreSQL + pgvector is sufficient initially.
8. A DB-backed Worker is sufficient initially.
9. The system will improve by reviewing real sessions, Evidence, Patterns, Tutor behavior, cost, and errors.

---

# 27. Active Product Risks and Open Questions

Stable reference documents record durable unresolved product areas; current execution risks live in `PROJECT_STATE.md`.

Key open validation areas include:

- real book/structural extraction quality,
- Tutor model fit under natural Lina use,
- Evidence/rubric calibration from real interactions,
- the smallest high-value visual representation set,
- Vision reliability on child work when promoted,
- Voice friction/value when promoted,
- runtime cost/latency under recurring use,
- Parent inspectability needs,
- whether trusted external references materially improve grounding,
- longitudinal Pattern/Card usefulness over multiple natural sessions.

Do not over-design these before evidence appears.

---

# 28. Product Validation Horizons

Do not collapse the following into one gate:

## Horizon A — Daily-Use Lina Baseline

Turn the existing limited real interaction and implemented core into a reliable recurring private Lina experience. This concerns operational reliability and the minimum child-usable experience; it does not mean the full product is complete.

## Horizon B — First Product Loop Complete

The first intended product loop is broader than Student chat. It requires the differentiated learning loop to be credible in real use and enough Parent/content/operational inspectability to understand important learning state, evidence, system behavior, and cost.

## Horizon C — Intended Lina Product Expansion

After the core loop proves itself, deliberately promote approved deferred capabilities—Science, Voice, Vision, handwriting/drawing evidence, visual/interactive artifacts, richer Parent experience, and Grade progression—according to real evidence and product direction.

“Not required before the next Lina session” must never be interpreted as “unnecessary to the product.”

---

# 29. Real-Use Product Learning Loop

Early recurring Lina use should be observed lightly, as product learning rather than exam monitoring.

Useful questions include:

- Where does interaction friction appear?
- Does Lina naturally stay in text or prefer speech?
- Does she try/want to show pages/photos/work?
- Does Math representation limit explanation?
- Are suggested actions/guided checks useful or ignored?
- Does conversation continuity feel natural?
- Does prior intelligence improve later teaching?
- Does personalization ever fight current behavior?
- Does grounding add value when available?
- Does the system recover cleanly from errors?
- What does Parent actually need to inspect?
- What approved capability does Lina organically try to use before it exists?

Real behavior should **order approved capabilities**, not replace intentional product direction.

---

# 30. Relationship to Other Project Documents

This document defines **what the project is and the durable governing direction**.

- `LEARNING_PRODUCT_ROADMAP.md` owns approved product-evolution sequencing and future capability tracks. It does not itself make work executable.
- `LEARNING_INTELLIGENCE_SPEC.md` owns detailed Event/Evidence/State/Pattern/Card semantics, authority, and reprocessing rules.
- `CHILD_SAFETY_POLICY.md` owns hard child-safety and Parent Boundary semantics.
- `IMPLEMENTATION_PLAN.md` owns implementation direction and technical boundaries.
- `AGENTS.md` owns AI-agent operating/approval rules.
- `PROJECT_STATE.md` owns the short current operational snapshot and current next action.
- `TASKS.md` owns durable task/execution state.
- `SYSTEM_MAP.html` visualizes architecture plus current readiness; readiness overlays are not architecture themselves.

---

# 31. Governing Summary

Lina Learning should feel as natural to use as a capable general AI tutor while adding a durable, evidence-based learning system around that interaction.

The current Student question drives learning. Books and other sources optionally ground it. The Tutor teaches through one primary model call and can adapt support/representation based first on current behavior and then on relevant learner intelligence.

Raw interactions remain source authority. Completed Segments are semantically reviewed. Staged findings remain inactive until closed-Session finalization deterministically authorizes Evidence. Current State and Patterns evolve under explicit rules. The Learner Intelligence Card supplies only a compact relevant slice to future Tutor interactions.

The current core is Math-first and technically mature enough to have supported limited real Lina use. That does not prove stable daily use or longitudinal personalization. The next product stages must preserve the broader approved direction—Math + Science, multimodal input, visual learning, and Parent inspectability—while using real evidence to determine sequencing rather than overbuilding prematurely.

---

**End of PROJECT_REFERENCE.md**
