# Lina Personal Learning System

## PROJECT_REFERENCE.md

**Status:** Approved project reference — living governing document  
**Audience:** Product owner, ChatGPT, Codex, AI agents, developers, reviewers  
**Primary use:** Governing source of truth for product intent, boundaries, architecture, learning behavior, and approved design decisions  
**Not a replacement for:** `LEARNING_PRODUCT_ROADMAP.md`, `LEARNING_INTELLIGENCE_SPEC.md`, `IMPLEMENTATION_PLAN.md`, implementation prompts, or task files

`docs/LEARNING_PRODUCT_ROADMAP.md` owns approved product-evolution sequencing,
future capability tracks, dependencies, and validation gates. This reference
continues to own durable product principles and protected boundaries.

---

# 1. Project Identity

## 1.1 Name

**Lina Personal Learning System**

## 1.2 Product Definition

Lina Personal Learning System is a personal, evidence-grounded learning environment designed first for Lina, beginning with **Grade 5 Mathematics and Science**.

It is not intended to reproduce school digitally, act as a homework-answering chatbot, or operate as a conventional LMS. The current Student question drives the interaction. Books, school materials, trusted references, and later captured pages are optional grounding sources that improve alignment and context; the Tutor remains usable without them.

The system combines:

- a conversational AI tutor,
- book and curriculum understanding,
- multimodal student input,
- interactive learning artifacts,
- an event/evidence intelligence layer,
- a compact longitudinal understanding of Lina,
- and a parent/admin view for oversight, content control, evidence inspection, and system tuning.

The durable asset is not the tutor model itself.

> **The durable product asset is the evolving, evidence-grounded understanding of Lina as a learner.**

Models, books, UI components, providers, and teaching representations may change. The learner history and the system's ability to reconstruct and improve its understanding must remain durable.

---

# 2. Core Product Objective

The system exists to help Lina **understand**, not merely finish tasks.

The primary objectives are:

1. Help Lina understand Grade-level Math and Science concepts using explanations appropriate to her current understanding.
2. Support school learning without making the book's exact teaching method mandatory.
3. Build a persistent, evidence-grounded understanding of how Lina is learning over time.
4. Adapt support based on what Lina is demonstrating now, informed by relevant historical patterns without becoming constrained by them.
5. Preserve raw learning history so that future improvements to extraction, evidence rules, or models can re-analyze prior learning.
6. Keep the learner experience low-pressure, visually engaging, and natural for a child around ten years old.
7. Make the system explainable and inspectable by the parent/admin.
8. Keep AI usage observable, replaceable, and cost-aware.

The system should become more useful as Lina uses it, but should never require full conversational history to be loaded into every future interaction.

---

# 3. Product Boundaries

## 3.1 In Scope

The initial product scope includes:

- Lina-first web application.
- Grade 5 as the first active Grade environment.
- Mathematics.
- Science.
- Parent/Admin control panel.
- School-book ingestion and structured understanding.
- Question-driven optional grounding from available learning sources.
- Conversational tutor.
- Homework assistance.
- Free exploration outside the curriculum.
- Optional quiz/review interactions.
- Text input.
- Speech-to-text input.
- Student image input.
- Handwritten work photographed and uploaded.
- Student drawings photographed and uploaded.
- Homework/page/diagram images.
- Vision-based understanding of student work.
- Annotation of the student's original image.
- Clean visual reconstruction when annotation is insufficient.
- Interactive learning artifacts using HTML/SVG/React-based renderers.
- Event capture.
- Evidence generation.
- Current learning state.
- Temporal learner patterns.
- Compact Learner Intelligence Card.
- Derived mastery/confidence views.
- Parent evidence inspection.
- Parent-configurable learning boundaries for age-sensitive/family-sensitive topics.
- Child-safety baseline guardrails that cannot be weakened from the Parent Dashboard.
- AI model routing.
- AI cost/usage logging.
- Reprocessing and rebuildability.
- Grade transition through parent/admin activation of the next Grade's books.

## 3.2 Explicitly Out of Scope for the Initial Product

Do not expand the initial implementation into the following without a later explicit decision:

- Native iOS or Android app.
- Offline mode.
- Teacher portal.
- Classroom management.
- School SIS/LMS integration.
- Multi-family SaaS workflows.
- Billing/subscription platform.
- Organization or tenant administration.
- Leaderboards.
- Competitive ranking.
- Exam Mode as a pressure-oriented feature.
- Countdown-based performance pressure.
- Heavy gamification or points economy.
- Social features.
- Multi-student classroom analytics.
- Universal cross-grade knowledge graph.
- Automatic cross-grade concept mapping as a core dependency.
- Generic agent framework for all actions.
- Chain-of-agents execution for every tutor turn.
- Dedicated vector database unless PostgreSQL/pgvector becomes insufficient.
- Redis/Celery unless job volume proves a need.
- Graphiti or a graph database as an MVP dependency.
- Advanced ML clustering.
- Psychological diagnosis.
- Personality diagnosis.
- Intelligence labeling.
- Learning-style labels such as "visual learner".

---

# 4. Users and Roles

## 4.1 Lina — Student

Lina is the primary learner and the main user of the learning experience.

Her interface should expose learning actions, not analytics.

Lina should be able to:

- enter Math or Science,
- ask a question naturally,
- type,
- speak,
- upload a photo,
- photograph handwritten work,
- photograph a drawing,
- upload homework or a textbook page,
- ask for another example,
- ask for a hint,
- say that she does not understand,
- ask for an easier explanation,
- ask to be challenged,
- interact with visual and interactive learning artifacts,
- continue the same learning session after opening an expanded learning canvas.

Lina should **not** see:

- mastery percentages,
- weakness labels,
- evidence counts,
- raw learner intelligence,
- parent observations,
- model settings,
- AI costs,
- processing jobs,
- Grade archive controls.

## 4.2 Parent/Admin

The Parent/Admin controls the learning environment and can inspect how the system is forming its understanding.

The Parent/Admin should be able to:

- create and manage the child's authoritative Student Core Profile,
- upload books,
- upload school plans and other reference material,
- assign books to a Grade,
- activate the next Grade by uploading/activating its books,
- inspect content processing status,
- reprocess a book,
- view Math and Science learning state,
- inspect important evidence,
- inspect patterns and recent changes,
- inspect tutor adaptations,
- review learning history,
- review AI usage and estimated cost,
- configure task-to-model routes,
- challenge a system conclusion or request re-validation,
- inspect why the system reached an important conclusion,
- configure learning boundaries for age-sensitive or family-sensitive topics.

The Parent/Admin does **not** directly overwrite evidence-grounded learner conclusions. Parent input can create a hypothesis or a review request, but the learner state remains evidence-governed.

## 4.3 Student Core Profile

The **Student Core Profile** answers “who is this child?” It is Parent/Admin-owned
factual state: child display/name identity, date of birth when supplied, and
linkage to the active Grade / Grade Period. Age is derived from date of birth at
runtime; it is not a manually maintained fixed value.

Parent authentication, email, and account data are Parent identity data: they
are neither child Learner Intelligence nor automatically Student Core Profile
data.

Student Core Profile is separate from Learner Intelligence, Evidence,
Conversation Context, Segment State, Safety classification, and Tutor teaching
decisions. Parent/Admin may not write learning claims such as weakness,
mastery, learning-style, or support-preference labels into it. The future Tutor
runtime consumes only a compact authoritative **Student Core Context**; it does
not infer or turn profile facts into learner conclusions.

## 4.4 UX Separation Principle

```text
Lina UI   -> Learning
Parent UI -> Understanding + Control
```

The system may be technically complex internally, but that complexity must not leak into Lina's experience.

---

# 5. Learning Philosophy and Tutor Principles

These are product-level invariants.

## 5.1 Understanding Is the Objective

The tutor should prioritize understanding over task completion.

Withholding an answer is **not** itself an educational objective.

If Lina remains genuinely stuck after a reasonable attempt, the tutor should teach the solution clearly, explain why it works, and then check understanding through a new application.

## 5.2 Books and References = Grounding Sources, Not Teaching Authority

An available book is a strong persistent curriculum anchor. Books, school
materials, trusted references, and later captured pages can provide:

- current Grade scope,
- topics,
- lesson structure,
- school terminology,
- expected depth,
- school examples,
- exercises Lina is likely to encounter.

No grounding source authorizes, restricts, or owns the teaching method. The
Tutor may answer from model knowledge when no useful source is available.

The tutor may use:

- alternative explanations,
- visual examples,
- concrete examples,
- analogies,
- different valid mathematical solution methods,
- interactive diagrams,
- micro-detours to prerequisites,
- examples outside the book,
- structured visual artifacts.

The tutor must not reduce RAG to "retrieve page and paraphrase it."

## 5.3 Question-Driven Learning, Reference-Grounded When Useful

Lina's current question or learning need is authoritative. School, book, and
reference context can improve terminology, scope alignment, examples, and
expected depth, but does not determine what Lina is allowed or required to
study now.

The Tutor may teach prerequisites or related ideas when useful and return to
the current question naturally. Relevant recent conversational/topic context
may help a low-information continuation, but relevance outranks recency and
history.

## 5.4 No Formal Diagnostic by Default

A new lesson should not automatically begin with a formal diagnostic test.

The tutor should enter the topic naturally. If signals of a missing prerequisite emerge during the interaction, the tutor may investigate and support that prerequisite in context.

## 5.5 Current Behavior Outranks Historical Personalization

Historical intelligence is advisory.

What Lina demonstrates in the current interaction has higher authority than historical patterns.

> **Never personalize away demonstrated independence.**

If Lina previously needed a visual representation but is now solving independently, the tutor should not force the older strategy.

## 5.6 Personalization Should Be Felt, Not Announced

The tutor may choose a strategy because history suggests it is useful, but it should not repeatedly tell Lina things such as:

> "Because you are a visual learner..."

The tutor should simply use the better representation when needed.

## 5.7 No Psychological or Personality Conclusions

The learner system may describe observed learning behavior in context, such as:

- hint dependency,
- self-correction,
- transfer,
- persistence during learning tasks,
- retention,
- response to challenge,
- successful teaching strategies,
- confidence/accuracy mismatch.

It must not convert those observations into:

- psychological diagnosis,
- ADHD-type conclusions,
- personality classifications,
- intelligence labels,
- global motivational judgments,
- fixed learning-style labels.

Claims should remain scoped to the contexts supported by evidence.

## 5.8 Low-Pressure Learning

The product should avoid:

- countdowns,
- leaderboards,
- red failure warnings,
- public scores,
- exam-oriented pressure,
- repetitive drill for its own sake.

Light celebrations or badges are acceptable when they recognize meaningful learning behavior rather than create a pressure economy.

## 5.9 Bilingual Interaction

Default behavior:

- English question -> English response.
- Arabic question -> Arabic response.
- Mixed language -> natural mixed response.

Educational terminology can preserve useful English terms even in Arabic explanation where appropriate.

Example:

> الكسر المكافئ اسمه **Equivalent Fraction**.

## 5.10 Child Safety and Parent-Controlled Learning Boundaries

The product serves a child around ten years old. Safety and age-appropriateness must therefore be enforced as product policy, not left only to a Tutor prompt.

The system uses two distinct layers:

### A. Non-Overridable Safety Baseline

These protections are mandatory and cannot be weakened by Parent/Admin settings. They cover categories such as:

- explicit sexual content or sexual exploitation,
- self-harm or dangerous self-injury guidance,
- practical instruction for weapons, dangerous substances, or hazardous activities,
- graphic or severely disturbing content inappropriate for a child,
- drug-related or other clearly dangerous behavior guidance,
- unsafe disclosure or handling of sensitive personal information,
- other content that violates system-level child-safety requirements.

This baseline is enforced by the product/runtime policy. Prompt instructions may reinforce it, but the prompt is not the sole enforcement mechanism.

### B. Parent-Controlled Learning Boundaries

Some topics are not inherently system-safety violations but may be age-sensitive, family-sensitive, or intentionally reserved for parent discussion. These are configurable from the Parent Dashboard.

Each configurable topic uses one of three states:

- **ALLOW** — the Tutor may discuss the topic normally within the general child-safety baseline.
- **AGE_APPROPRIATE_ONLY** — the Tutor may discuss the topic only in a simplified, age-appropriate manner suitable for Lina.
- **REDIRECT_TO_PARENT** — the Tutor should not elaborate and should briefly and naturally suggest discussing the topic with a parent.

Initial configurable categories may include, for example:

- religion,
- relationships,
- human reproduction / sex education,
- politics / current affairs,
- death / grief,
- money / family finances,
- other parent-defined age-sensitive categories added later.

The exact category catalog is configuration, not a hardcoded architectural limit.

### C. Runtime Order

Conceptually:

```text
Student input
    ↓
Safety & Learning Boundary Policy Engine
    ├── Non-overridable child-safety baseline
    ├── Parent learning-boundary policy
    └── Age-appropriateness directive
    ↓
Versioned policy decision
    ↓
Tutor behavior / safe redirect
```

The runtime policy decision is an explicit system contract; prompt instructions may reinforce it but cannot replace it.

Restricted-topic responses should remain calm and non-shaming. The Tutor should not make the restriction itself a dramatic event.

The detailed policy and enforcement rules are governed by `CHILD_SAFETY_POLICY.md`.

---

# 6. Grade and Curriculum Model

## 6.1 Grade Activation

The system does not infer Grade transition automatically.

Grade 5 remains the active environment while Grade 5 books are active.

When the Parent/Admin uploads and activates Grade 6 books, Grade 6 becomes the new active environment.

```text
Grade 5 books active
        ↓
Grade 5 learning environment
        ↓
Parent/Admin activates Grade 6 books
        ↓
Compact transition card created
        ↓
Grade 6 becomes active
```

## 6.2 What Carries Forward

The next Grade receives only a compact transition card containing important, stable, or unresolved learner intelligence that is still useful.

Examples:

- important stable teaching patterns,
- meaningful persistent foundational gaps,
- important unresolved misconceptions,
- useful strategy patterns,
- notable retention characteristics,
- stable learning behavior relevant to future teaching,
- important extended capabilities.

Detailed previous-Grade lesson mastery, all evidence, and full transcripts do not enter the new Grade runtime by default.

## 6.3 Previous Grade Archive

Previous Grade data remains preserved for audit, re-analysis, and optional historical lookup.

It is not loaded into every new Grade interaction.

If a similar issue appears later, historical records may be consulted to determine whether the system has seen something similar before. Historical similarity does not automatically reactivate an old pattern; fresh evidence remains required.

## 6.4 No Complex Cross-Grade Engine in MVP

Grade 6 naturally depends on prior knowledge. If Lina has forgotten a foundation, the tutor should detect that from the current interaction, re-explain it briefly, and continue the Grade 6 lesson.

The MVP does not require a universal cross-grade prerequisite engine.

---

# 7. Content and Book Understanding

## 7.1 Original Document Preservation

The original uploaded file remains preserved as the immutable source artifact.

Derived processing may be regenerated.

```text
original.pdf
   ↓
Docling processing v1
   ↓
Educational semantics v1

later:
original.pdf
   ↓
Docling processing v2
   ↓
Educational semantics v2
```

The Parent/Admin should not need to re-upload the original simply because extraction logic changed.

## 7.2 Document Understanding Foundation: Docling

Docling is the baseline document-processing foundation for books and relevant structured learning documents.

Its role is to provide a structured intermediate document representation preserving, where available:

- document hierarchy,
- reading order,
- headings,
- paragraphs,
- tables,
- pictures,
- formulas,
- page references,
- layout/provenance metadata.

Docling is not itself the curriculum model.

## 7.3 Educational Semantic Layer — Optional Enrichment

The project may add a rebuildable educational semantic layer over the
structured document representation. It is optional enrichment for navigation,
analysis, and source organization; it is not required for Tutor availability,
basic retrieval, Candidate Events, Evidence, or Learner Intelligence.

This layer identifies and normalizes concepts such as:

- Grade,
- Subject,
- Unit,
- Lesson,
- Topic/Concept,
- objective,
- prerequisite hints,
- explanation blocks,
- worked examples,
- exercises,
- vocabulary,
- figures,
- expected school scope.

Curriculum taxonomy can provide useful optional metadata. Concept identity for
Learning Intelligence primarily comes from the interaction: the question,
conversation, current page/image when available, retrieved references when
useful, and model understanding. A universal concept graph remains deferred.

## 7.4 Content Pipeline

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

Optional:
Structural representation
    ↓
Educational semantic enrichment
```

## 7.5 Figures, Images, and Formulas

Figures and formulas are first-class learning content.

The system should retain links between:

- figure/picture,
- page,
- caption,
- related lesson/concept,
- extracted description when generated,
- original document provenance.

Image description or other visual enrichment should be selective rather than automatically applied to every image if there is no educational value.

## 7.6 School Plans

School plans are supplementary references. They may reveal available
subjects, topics, material, dates, or homework references, but they do not
determine Lina's current learning position or steer the Tutor.

## 7.7 Student Uploads Are Not Automatically Curriculum Content

A student-uploaded homework page, drawing, or photographed notebook page is
an interaction artifact by default. Future captured-page handling may preserve
it as a learning source: a current page has the highest context priority for
that turn, and a historical page can be a learning-history reference. Vision
implementation remains separately frozen.

## 7.8 Learning Sources and Trusted References

Grounding priority is not teaching-method authority. Available sources may be
used in this order when useful: current captured page/image; exact uploaded
school material/book; historical student-captured pages; trusted aligned web
references; trusted general educational references; and model general
knowledge, which remains available.

The future Trusted Educational Reference Pack requires Grade and Subject, and
uses Country, School, Curriculum, Book, Publisher, and language when known.
Parents are not required to find the exact book or approve each trusted source.
The system may discover official/publisher sources first, then established
educational institutions, then reputable academic or school sources; anonymous
forums, low-trust blogs, SEO junk, and unclear-source content are excluded.
Sources are classified as `EXACT_CURRICULUM`, `ALIGNED_CURRICULUM`, or
`GENERAL_EDUCATION`. They may improve terminology, alignment, examples, and
representational diversity, but their absence never blocks the Tutor.

---

# 8. Retrieval Architecture

## 8.1 Retrieval Principle

Do not perform semantic search across every uploaded book for every question.

Retrieval is optional grounding driven by the current Student question. It
should narrow context before similarity search without requiring a curriculum
position.

Conceptual flow:

```text
Current Student question
    ↓
Grade / Subject when known
    ↓
Metadata filtering
   ↓
Lexical + vector retrieval
   ↓
Relevant content blocks / figures
```

## 8.2 Structural Chunking

Blind fixed-size token chunking is not the primary strategy.

The preferred baseline is:

1. preserve Docling's hierarchical document structure,
2. create structural/semantic retrieval units,
3. apply token-aware splitting only when a unit is too large,
4. merge small compatible peers only when context remains coherent.

Docling hierarchical/hybrid chunking is the baseline implementation candidate, not an immutable product dependency.

## 8.3 Hybrid Retrieval

Retrieval should combine as appropriate:

- metadata filters,
- exact/lexical search,
- vector similarity,
- relevant recent conversational/topic context as an advisory preference,
- optional concept/lesson/type metadata when available.

PostgreSQL + pgvector is sufficient for the initial architecture unless usage proves otherwise.

## 8.4 Recent Conversational Context

Recent conversational/topic context may help follow-up turns such as
"continue," "again," or "I don't understand." It is advisory only: a
substantive current question must outrank stale context. School plans and
curriculum position are references, not retrieval or teaching authority.

The approved current-session **Hybrid Segment Context** principle is structural,
relevance-first, and bounded only by final capacity guardrails:

```text
Current Multimodal Turn
+ Full Immediate Exchange
+ compact Structured Current Segment State
+ 0..N relevant complete raw Exchanges from the Current Segment
+ relevant Learner Intelligence / Open Loops separately
+ question-driven RAG / curriculum grounding separately
+ effective Safety policy decision separately
```

Do not automatically load all Session history, any earlier Segment merely
because it shares a Durable Conversation Topic, all Grade conversation history,
any whole Topic Registry, or prior-session raw transcripts. Returning to an
earlier idea after an intervening Segment creates a new Segment; normal context
recall remains limited to that Current Segment. Relevant context outranks raw
recency; the current Student Turn remains authoritative. Raw history remains
preserved outside normal Tutor input. Character slicing is not the
conversation-selection algorithm: if selected context must be reduced, prefer
dropping a lower-value complete selected Exchange rather than positionally
slicing critical raw conversation content. Exact token/capacity values are
calibrated from real usage. Structured Segment State is derived conversational
metadata, not learner truth, Evidence, or personalization.

The Full Immediate Exchange is the available immediately preceding raw
conversation in chronological order: previous Student Turn, then previous Tutor
Turn, followed by the Current Student Turn. When no preceding Student Turn
exists, preserve the available preceding Tutor Turn only; never invent missing
context or re-identify message lineage by text.

## 8.5 Retrieval Is Grounding, Not Teaching Style

Retrieval supplies authoritative and relevant content.

The tutor remains free to use a different valid explanation, representation, example, or interactive artifact to achieve understanding.

---

# 9. Tutor Runtime

## 9.1 Fixed Tutor Identity

Tutor identity is stable product policy, not an automatically rewritten persona.

The tutor should be:

- warm but not patronizing,
- clear,
- age-appropriate,
- patient without becoming repetitive,
- comfortable with Arabic, English, and mixed language,
- natural and conversational in Arabic rather than unnecessarily formal,
- natural and child-appropriate in English,
- responsive to Lina's reasonable level of formality,
- honest about uncertainty,
- focused on understanding,
- non-shaming,
- non-pressuring.

The Tutor should normally begin with a concrete, simple idea before unnecessary
formal terminology, then teach one manageable idea and interact rather than
deliver a full lecture.

The current approximately-10-year-old wording is a temporary Lina-first
implementation assumption, not the long-term identity architecture. When
TASK-027A is implemented, the Tutor will receive authoritative age and Grade
through Student Core Context and remove that hardcoded assumption.

## 9.2 Adaptive Teaching Strategy and Teaching Method

The system does **not** maintain a large mutable "Adaptive Persona" as the main personalization mechanism.

Instead, the normal primary Tutor call semantically chooses the turn-level teaching decisions from current behavior and relevant learner intelligence. **TeachingMode** describes the kind of learning interaction. **TeachingStrategy** describes the support/intervention flow (for example, `HINT_FIRST` or `EXPLAIN_THEN_CHECK`). **TeachingMethod** is a separate concept: the pedagogical representation used to teach the idea (for example, `CONCRETE_EXAMPLE` or `WORKED_EXAMPLE`). `prior_method_relation` records the semantic relationship of this turn to the immediately previous persisted Tutor method when relevant: `CONTINUATION`, `DID_NOT_HELP`, `HELPED`, `EXPLICIT_REPEAT_REQUEST`, or `NOT_RELEVANT`.

Teaching Methods are owned by a small internal, versioned registry inside the modular monolith, not by a giant static Tutor prompt or a new service. The initial active canonical identities are `CONCRETE_EXAMPLE`, `VISUAL_REPRESENTATION`, `WORKED_EXAMPLE`, `SOCRATIC_FOCUS`, `DECOMPOSITION`, `ANALOGY`, and `SYMBOLIC_EXPLANATION`. `INTERACTIVE_ARTIFACT` and `DRAWING_MODEL` remain future/frozen identities until their existing Artifact or Vision gates authorize those capabilities. With only seven active methods, the normal Tutor call may receive all compact active definitions; the registry validates canonical IDs and frozen status, not natural-language keyword rules.

Conceptual priority:

```text
1. What Lina is demonstrating right now
2. Current Learning State
3. Relevant recent intelligence
4. Relevant stable patterns
5. Curriculum context
6. Generic teaching policy
```

Historical patterns are priors, not commands. Relevant personalization informs Luna but does not control the decision, and current demonstrated behavior must not be personalized away.

Luna makes the joint semantic Mode + Strategy + Method + prior-method-relation decision inside the same primary Tutor call. Runtime code supplies the current message, relevant context/personalization, prior persisted method, and compact taxonomies; it validates values, null combinations, safety, lineage, and structural consistency after the call. It must not infer those meanings from Arabic/English keyword or phrase lists, and no additional classifier/model call is authorized. For greetings, thanks, casual conversation, and other genuinely non-instructional turns, all four turn decisions may be null. If Luna determines `DID_NOT_HELP`, a same-method selection is structurally inconsistent unless the relation is `EXPLICIT_REPEAT_REQUEST`; exact enforcement belongs to the REC-35.2 correction implementation.

Turn decisions are routing/audit metadata, not learner memory. Selecting or using a TeachingMethod, or marking `HELPED`/`DID_NOT_HELP`, is not Evidence that it worked or failed. Effectiveness is evaluable only after an observable Student outcome through optional provisional Candidate hints, completed Segment semantic review, and Session-authorized Evidence. Segment Review may interpret effectiveness only; it may not invent or rename the persisted, server-grounded TeachingMethod identity. Any later method history remains advisory, context-specific, and free of learning-style labels.

`NAVIGATION` and pure self-report action choices are not Evidence merely because they were selected. A bounded `ANSWER_CHOICE` may represent an observable guided attempt and may emit only the approved bounded Candidate Event types; it never becomes independent success or mastery merely from the click. The Tutor must not globally require hidden candidate metadata to be null for every button selection.

## 9.3 Normal Runtime Path

```text
Student question
    ↓
SafetyDecision
    ↓
Compact authoritative Student Core Context
    ↓
Optional question-driven grounding
    ↓
Relevant learner intelligence selection + prior persisted teaching decision + compact taxonomies / Method Registry
    ↓
ONE primary Tutor model call
    ↓
Semantic Mode + Strategy + Method + prior relation + student-facing response + hidden candidate-event metadata
    ↓
Deterministic validation / persistence
```

The MVP should avoid chains such as:

```text
Tutor → Critic → Evaluator → Profile Agent → Persona Agent
```

for every message.

## 9.4 Intervention Ladder

Support should be flexible rather than a rigid "three hints then answer" policy.

Possible intervention levels include:

1. observe / allow independent attempt,
2. focusing question,
3. light hint,
4. stronger hint,
5. change representation,
6. teach/explain solution,
7. guided application,
8. independent follow-up.

The tutor may skip levels according to what Lina is showing.

## 9.5 Homework Behavior

```text
Understand where Lina is
    ↓
Give opportunity to think
    ↓
Hint / focusing support
    ↓
Change representation if useful
    ↓
Still genuinely stuck?
    ↓
Teach the solution clearly
    ↓
Explain why
    ↓
New application
    ↓
Check understanding
```

A direct answer is not the first action, but teaching the answer is allowed when continued hinting would no longer help.

## 9.6 Frustration Signals

The tutor may respond to observable interaction signals such as:

- explicit "I don't understand",
- repeated failed attempts,
- repeated hint requests,
- explicit "too hard",
- abrupt disengagement.

The response may include:

- smaller step size,
- another representation,
- a concrete example,
- shorter response,
- lower cognitive load.

This is interaction adaptation, not psychological diagnosis.

## 9.7 Challenge Adaptation

If Lina demonstrates strong understanding quickly, the tutor should avoid repetitive same-format practice.

Prefer:

- lower scaffolding,
- explanation in her own words,
- error spotting,
- a new representation,
- transfer to a slightly different context,
- deeper understanding before unnecessary Grade acceleration.

---

# 10. Teaching Modes

The system may internally use a small number of teaching modes:

- **LEARN** — current school topic or concept teaching.
- **HOMEWORK** — support around a concrete assigned problem.
- **EXPLORE** — curiosity or learning outside the current school path.
- **QUIZ** — optional learner-requested checking.
- **REVIEW** — retention or revisit of previously learned material.

These modes need not be explicit buttons or labels visible to Lina unless useful. They are semantic turn decisions made by the primary Tutor call, not keyword classifications or learner labels; genuinely non-instructional turns may have no mode.

Free exploration can create Extended Learning evidence, but it does not automatically replace or redirect the current school path.

---

# 11. Multimodal Learning

## 11.1 Input Principle

The product is **multimodal-first**, not chat-text-first.

Lina may express understanding by:

- typing,
- speaking,
- writing on paper and photographing it,
- drawing on paper and photographing it,
- uploading homework,
- uploading a diagram,
- photographing a textbook or worksheet page.

## 11.2 Voice

Current policy:

```text
Audio
  ↓
Speech-to-text
  ↓
Transcript
  ↓
Normal tutor pipeline
```

The transcript is retained.

Raw audio is not retained in the current version after successful transcription.

If future speaking/pronunciation assessment is added, audio retention will require a separate policy.

## 11.3 Student Image Understanding

The system should understand, where practical:

- handwritten math,
- handwritten explanations,
- drawings,
- arrows and labels,
- diagrams,
- problem-solving steps,
- homework questions,
- photographed notebook work.

The vision layer is not assumed to be perfect.

If a critical part of the image is ambiguous, the tutor should ask Lina a simple clarification rather than convert uncertainty into strong evidence.

## 11.4 Image Response Priority

Default behavior for a student-uploaded drawing or handwritten solution:

```text
Understand original
    ↓
Clarify if needed
    ↓
Annotate the original image first
    ↓
If annotation is not enough
    ↓
Create a cleaner reconstructed explanation
```

## 11.5 Source vs Derived Artifacts

The student's original work remains the source learning artifact.

AI outputs such as:

- annotated copy,
- corrected copy,
- clean redraw,
- SVG reconstruction,
- HTML interactive reconstruction

are derived artifacts.

Evidence about Lina's original understanding must point to the original work, not to the AI-corrected reconstruction.

---

# 12. Interactive Learning Artifacts

## 12.1 Product Role

The tutor is not text-only.

When a visual or interactive representation would materially improve understanding, the system should be able to create or select an interactive learning artifact.

For a child around ten years old, visual clarity, color, motion, shape, and interaction are product requirements when they serve learning.

The intended style is:

> **playful + polished + intelligent**

not corporate, cluttered, or excessively childish.

## 12.2 UX Model

Simple visuals may appear inline in the conversation.

More complex interactions should open in an expandable **Learning Canvas** within the same session and page.

```text
Tutor conversation
    ↓
Inline visual/card
    ↓
"Try it" / "Open"
    ↓
Learning Canvas
    ↓
Interact
    ↓
Return to same tutor position/session
```

Opening an artifact must not create a separate learning session or lose conversational context.

## 12.3 Artifact Architecture

The primary architecture is **typed artifact specifications + reusable renderers**.

The AI determines the educational representation required.

The application determines how that representation is rendered.

Example:

```json
{
  "type": "fraction_equivalence",
  "goal": "show_why_equivalent",
  "values": ["1/2", "2/4"],
  "interaction": "drag_divisions",
  "difficulty": "grade_5"
}
```

This resolves through an Artifact Registry to a tested renderer.

## 12.4 Initial Artifact Stack

Initial recommended renderer/tool stack:

- Native React + SVG.
- Motion for animation and gestures.
- JSXGraph for interactive mathematics/geometry/graphs.
- React Konva for canvas-based drag/drop and spatial interaction.
- MathLive for mathematical input and editable math fields.

Optional later, based on real use:

- Rough.js for selective hand-drawn visual styling.
- Recharts for data charts.
- p5.js for richer simulations.
- React Flow for node/edge interaction when a concrete use case appears.

Mermaid and Sandpack are not core child-facing runtime dependencies.

## 12.5 Custom HTML/SVG

Custom AI-generated HTML/SVG may be supported as a fallback when no reusable artifact fits.

It must be sandboxed and must not have unrestricted access to application state, secrets, cookies, external network, or arbitrary APIs.

Artifact failure must never block learning; the tutor should fall back to another explanation.

## 12.6 Artifact Learning Value

An artifact should exist because it helps teach something, not because animation is available.

Each artifact should have a clear:

- learning goal,
- expected interaction,
- teaching purpose,
- success condition,
- follow-up behavior.

Meaningful artifact interactions can contribute to learning evidence. Raw clickstream analytics are not automatically learner intelligence.

---

# 13. Learning Intelligence — High-Level Contract

Detailed definitions, rubrics, event taxonomy, pattern rules, and weighting logic belong in:

> `LEARNING_INTELLIGENCE_SPEC.md`

This project reference governs only the architectural contract.

## 13.1 Intelligence Flow

```text
Raw Interaction History
        ↓
Optional Provisional Candidate Hints
        ↓
Completed Learning Segment
        ↓
Segment Learning Review
        ↓
Staged Semantic Findings
        ↓
Session Intelligence Finalization
        ↓
Validated Learning Events
        ↓
Evidence
        ↓
Current Learning State + Temporal Patterns
        ↓
Learner Intelligence Card
        ↓
Decision Views
        ↓
Tutor personalization / Parent insights
```

## 13.2 Raw History

Raw interaction history is the source material for future re-analysis.

It includes, as applicable:

- student messages,
- tutor responses,
- transcripts,
- student images,
- student drawings,
- uploaded work,
- interaction assets,
- timestamps,
- session and session-local Segment / Learning Thread references,
- model/request references.

Raw audio is excluded under the current voice policy.

The raw message, transcript, and original asset/reference remain the source
authority. Derived conversation metadata, including a Segment or Durable
Conversation Topic reference, is rebuildable navigation metadata and can never
be the sole source for Evidence.

## 13.3 Candidate Events

The primary tutor call may emit hidden candidate-event metadata as part of the same model execution.

A candidate event means:

> something in this interaction may be educationally meaningful and worth reviewing later.

Candidate Events are optional, provisional, source-linked, auditable semantic
hints. They are not Evidence, mandatory gates for every future Validated
Learning Event, Pattern or Current State authority, or personalization
authority. A Segment Review may confirm, reject, reinterpret, or combine
Candidates, and may identify a supported learning occurrence from raw Segment
history when the Tutor omitted a Candidate.

## 13.4 Segment Learning Review and Session Intelligence Finalization

Completed meaningful Segments are the semantic review unit. Background Segment
Learning Review receives the complete relevant raw Segment history, not merely
Candidate-local excerpts, and produces staged findings only.

Closed Sessions remain the durable activation authority. Session Intelligence
Finalization verifies required Segment Reviews, compatible versions,
provenance, and source lineage; it deterministically materializes Validated
Learning Events and Evidence, then activates downstream intelligence. No giant
semantic Session call is required after Segment Reviews by default.

The approved target is not yet implemented: current code uses legacy,
candidate-driven `SESSION_EVIDENCE` consolidation. Historical Session Evidence
remains valid, immutable, auditable, and rebuildable.

## 13.5 Meaningful Event Gate

Events enter Learner Intelligence only when they convey information that may change, confirm, challenge, or contextualize what the system knows about learning.

Examples:

- demonstrated understanding,
- misconception,
- independent attempt,
- hint requirement,
- self-correction,
- transfer,
- retention signal,
- teaching strategy success/failure,
- meaningful change in independence,
- important learning-state change.

Greetings, thanks, and ordinary conversation remain in raw history but do not become intelligence events merely because they occurred.

---

# 14. Learner Intelligence Card

## 14.1 Purpose

The Learner Intelligence Card is not a transcript summary and not a complete mastery database.

It is:

> **a compact temporal intelligence state describing what currently matters when interacting with Lina.**

It exists to make personalization useful without loading months or years of raw interaction history into the tutor context.

## 14.2 Card Contents

The card may contain compact representations of:

- current context,
- active learning states,
- current difficulties,
- active misconceptions,
- open learning loops,
- recent important changes,
- active/high-value patterns,
- successful recent teaching strategies,
- strategies whose usefulness appears to be weakening,
- retention-related signals,
- emerging capabilities.

It should not contain every concept, every event, every conversation, or every historical pattern.

## 14.3 Temporal Pattern Principles

Patterns evolve using explicit system rules based on factors such as:

- frequency,
- recency,
- evidence quality,
- context similarity,
- context diversity,
- supporting evidence,
- counter-evidence.

The AI may interpret or normalize semantic meaning, but the system owns weighting, lifecycle, and promotion rules.

## 14.4 Pattern Scope

Patterns begin at the narrowest scope supported by evidence.

Possible scope progression:

```text
Concept-specific
    ↓
Context-specific
    ↓
Subject-specific
    ↓
Cross-subject
    ↓
Global
```

A pattern must not become a general learner label simply because it appeared in one lesson.

## 14.5 Pattern Lifecycle

Conceptual lifecycle:

```text
candidate
   ↓
active
   ↓
stable
   ↓
weakening
   ↓
resolved / superseded
   ↓
removed from Current Card
```

Resolved patterns remain historically available but are not loaded into current runtime context by default.

If similar signals reappear later, the system may inspect the historical pattern, but fresh evidence is required before reactivation.

## 14.6 Current State vs Pattern

Current Learning State and Learner Patterns are separate concepts.

A single strong event may change Current Learning State.

A stable pattern requires repeated and appropriate evidence over time and context.

Current state may expire or resolve as new evidence appears.

---

# 15. Mastery and Confidence

Mastery and confidence are **Decision Views**, not the source of learner truth.

The source of truth is the underlying history, events, evidence, and intelligence state.

The system may internally calculate numeric values when useful for thresholds, scheduling, or ranking, but the Parent experience should prefer interpretable states such as:

- Needs support,
- Developing,
- Demonstrated,
- Strong,
- Needs revisit,
- Evidence confidence: Low / Medium / High.

Avoid false precision such as presenting `83.47% mastery` as if it were scientifically exact.

The calculation method may change later without losing historical learning data.

---

# 16. Conversation Context: Sessions, Segments, and Durable Topics

## 16.1 Session Lifecycle

Sessions close automatically after a configurable period of inactivity.

A grace window may allow a quick return to continue the same session.

Session closure completes the final Segment. In the approved target, required
completed-Segment Reviews finish in background work and deterministic Session
Intelligence Finalization activates Evidence and intelligence. Current code
still uses legacy candidate-driven Session Evidence consolidation.

A new Session begins conversationally fresh. It does not normally inject prior
raw transcripts, old Segments, or archived conversation history. Cross-session
personalization continues through the existing Learner Intelligence Card,
Current Learning State, relevant stable Patterns, relevant Open Learning Loops,
and Grade context—not through a replacement conversation-memory system.

## 16.2 Multimodal Turns

A logical Student **Multimodal Turn** may contain text, a speech transcript,
zero or more images/assets, raw asset references, and a derived Vision/OCR
interpretation when available. The whole Turn is the normal
conversation/segmentation unit. Original images/assets remain source authority;
Vision/OCR interpretation is derived and never replaces them.

For example, an image of handwritten work plus “حليت هيك صح؟” is one logical
Student Turn. A later “ليش هون؟” may depend on the relevant original asset,
derived interpretation when needed, and preceding Tutor explanation. This does
not authorize production Vision expansion.

## 16.3 Learning Thread = Session-local Segment

A **Learning Thread** is the session-local contiguous **Segment**; there is no
third conversation entity above or below Segment. Conceptually,
`thread_id = session-local Segment identity`.

A Segment belongs to one Session and holds contiguous relevant Turns while the
local intent/topic remains coherent. It may contain several questions,
explanations, checks, and exercises; it does not split for every Q/A pair. A
meaningful conversational transition starts a new Segment. Once another
Segment intervenes, the earlier Segment is never reopened.

Lina can move naturally without creating a chat manually. Returning to the
same idea after another Segment creates a **new** Segment, optionally with the
same `conversation_topic_ref`; it does not reopen the previous Segment.

Example:

```text
Session
├── Segment / Learning Thread 1 — Adding Fractions
├── Segment / Learning Thread 2 — Free Exploration
└── Segment / Learning Thread 3 — Adding Fractions (new Segment)
```

Thread separation is internal and supports correct evidence/context assignment.

For Hybrid Segment Context, a long active Segment may have a compact,
source-linked, rebuildable **Structured Segment State** describing only what is
conversationally necessary, such as an active goal, reference, unresolved point,
or relevant raw Exchange reference. It is not a free-form learner summary and
cannot create learner conclusions, Evidence, Current State, Patterns, Learner
Intelligence, personalization, curriculum authority, or Safety authority. This
is approved architecture; the technical CTX-03 runtime is verified, while
Real-Lina Context validation remains deferred.

## 16.4 Optional Durable Conversation Topics

A **Durable Conversation Topic** is optional, Grade/Grade-Period-scoped
conversation-navigation metadata with stable identity independent of its label.
It may be referenced by many Segments across Sessions in that Grade, for
example `math.long_division`. It is not Evidence, Learner Intelligence, a
learner characteristic, curriculum authority, or Safety authority.

Ephemeral is the default: casual or one-off conversation remains without a
`conversation_topic_ref` unless stable organizational value is clear. Before
creating a durable topic, reuse an existing identity when the idea is the same.
If uncertain, preserve Ephemeral state or let the Tutor ask naturally rather
than silently creating a duplicate. Aliases are grounded in observed phrasing;
do not generate speculative synonym lists. A semantic match does not by itself
persist a new alias. Optional curriculum linkage is enrichment only and cannot
be a prerequisite for conversation classification.

The conceptual classification contract is intentionally executor-independent:

```text
Segment: CONTINUE | NEW_SEGMENT | UNCERTAIN
New-Segment Topic: EPHEMERAL | REUSE_EXISTING_TOPIC |
                   CREATE_DURABLE_TOPIC | UNCERTAIN
```

`UNCERTAIN` creates a new independent Ephemeral Segment: it has no
`conversation_topic_ref`, does not attach the exchange to the prior active
Segment, and never triggers deferred reassignment, retroactive merge, or
backfill. A natural clarification is permitted when it matters. No separate
classifier/model call is a governing requirement; the preferred normal
architecture remains no extra model call unless measured evidence and Product
Owner approval justify one.

A prior Segment becomes complete whenever the governed CTX-03 transition
policy successfully persists a new LearningSegment, whether the model relation
was `NEW_SEGMENT` or `UNCERTAIN`. `CONTINUE` remains in the current Segment.

## 16.5 Historical Lookup Is On-Demand and Deferred

Historical conversation lookup is a future on-demand seam for a clear request,
such as remembering a prior image or explanation. Its conceptual outcomes are
`CLEAR_MATCH / USE`, `MULTIPLE_POSSIBILITIES / ASK`, and `NO_MATCH`; ambiguity
must ask Lina rather than guess. Automatic historical semantic retrieval,
archive vector indexing, and normal-turn prior-session injection are deferred:
the exploration did not validate them.

## 16.6 Open Learning Loops

If a session ends before understanding is sufficiently checked, the system may retain a compact open learning loop.

Example:

```text
Adding fractions:
concept explained; independent application not yet observed
```

Open loops should resolve or expire when no longer relevant.

---

# 17. Parent Experience

The Parent interface should prioritize **insight before activity tracking**.

Recommended areas:

## 17.1 Child Core Information

Parent-managed **Student Core Profile** facts: child identity, date of birth
when supplied, derived age, and active Grade / Grade Period linkage. This is
distinct from the evidence-derived Learner Profile / Learner Intelligence view.

## 17.2 Overview

- Relevant recent learning context when it helps the current question.
- What is going well.
- What currently needs attention.
- Important recent changes.
- Meaningful open learning loops.

## 17.3 Math

- Current topics/concepts.
- Interpretable learning state.
- Important misconceptions.
- Relevant evidence on demand.

## 17.4 Science

Same philosophy as Math, adapted to Science evidence.

## 17.5 Learner Profile / Learner Intelligence

Human-readable view of:

- active patterns,
- stable patterns,
- emerging patterns,
- recent changes,
- successful teaching strategies,
- resolved patterns/history on demand.

## 17.6 Learning History

- important sessions,
- session intelligence deltas,
- evidence trail,
- tutor adaptation events,
- original/derived learning artifacts.

## 17.7 Content and Settings

- books,
- Grade activation,
- school plans,
- content processing,
- reprocessing,
- AI model routes,
- AI usage/cost,
- Learning Boundaries (Allow / Age-appropriate only / Redirect to parent),
- Recent Redirects / Policy Audit for `REDIRECT_TO_PARENT` events, kept separate from Learner Profile intelligence.

## 17.8 Parent Insight Rule

> **Insights first; raw evidence on demand.**

The Parent interface should not become an activity-surveillance dashboard.

## 17.9 Separation of Conversation Context, Personalization, Pedagogy, Safety, and Curriculum Semantics

Conversation Segment and Durable Conversation Topic metadata describe what the
conversation is about. They must not directly update personalization. The only
protected personalization path remains:

```text
Raw Interaction
→ optional provisional Candidate hints
→ completed Segment semantic review
→ Session-authorized Validated Learning Events / Evidence
→ Current Learning State / Patterns
→ Learner Intelligence Card
→ Tutor personalization
```

For example, `conversation_topic = math.long_division` does not imply that
Lina struggles with long division, has a preference, has mastery, or found a
method effective. Current behavior continues to outrank historical
personalization, and demonstrated independence must never be personalized away.

Conversation context is also orthogonal to pedagogical routing:
`segment_relation`, `conversation_topic_relation`, and
`conversation_topic_ref` are not TeachingMode, TeachingStrategy,
TeachingMethod, or `prior_method_relation`. Selecting a method remains not
Evidence of effectiveness; an observable Lina outcome requires Segment Review
interpretation and Session-authorized Evidence.

Conversation Topic is distinct from a Safety / Parent Boundary category.
Safety remains upstream authority: the Current Student Turn is evaluated by the
Safety & Learning Boundary Policy Engine before Tutor/tools consume the
effective policy decision. Conversation metadata cannot authorize restricted
content, reinterpret `ALLOW`, `AGE_APPROPRIATE_ONLY`, or
`REDIRECT_TO_PARENT`, or weaken the non-overridable baseline.

Conversation Topic is also distinct from a Curriculum Concept, Evidence
subject/concept, and Safety category. They may link but none is automatic
authority for another. Conversation context cannot make curriculum semantics
mandatory, recreate Current School Focus authority, change question-driven
retrieval, change Book = Curriculum Anchor / not Teaching Authority, change
the current-question authority, or resolve SCOPE-01/SUBJ-01. Dialogue
continuity does not add a production Subject, change LearningSession.subject,
authorize Evidence attribution, or expand Math/Science scope.

---

# 18. AI and Model Architecture

## 18.1 Core Principle

> **Use AI for cognition; use deterministic system logic for state, weights, lifecycle, and plumbing.**

## 18.2 Model Gateway

Application modules should request AI by task rather than provider name.

Conceptual interface:

```text
ai.execute(task, payload, constraints)
```

Initial task classes include:

- `tutor`
- `segment_evidence` (approved future target)
- `session_evidence` (LEGACY / HISTORICAL EVIDENCE INTERPRETATION ROUTE until compatibility/reprocessing work completes)
- `curriculum_semantics`
- `vision_student_work`
- `vision_content_enrichment`
- `speech_to_text`
- `embedding`
- `grade_transition`
- optional future `image_generation`
- optional future `web_verification`

## 18.3 Provider Independence

The Tutor service must not directly call a provider-specific method such as `call_openai()`.

Model routing is configurable by task.

A route can define:

- primary provider/model,
- one fallback provider/model,
- timeout,
- output limit,
- task-specific settings,
- enabled/disabled state.

Long fallback chains are intentionally avoided.

## 18.4 Model Selection Philosophy

Use the fastest/lowest-cost model that meets the quality requirement for a task.

A fast GPT-5.6-class model such as Luna is an initial Tutor candidate to benchmark, not an architectural dependency.

Model quality must be evaluated on Lina-specific teaching scenarios rather than assumed from generic benchmark strength alone.

## 18.5 Cost Classes

Frequent/latency-sensitive:

- Tutor.
- STT.
- embeddings.

Background semantic:

- 0..N eligible Segment Learning Reviews per Session,
- semantic curriculum extraction,
- school-plan extraction.

Deterministic:

- Session Intelligence Finalization.

Legacy:

- `session_evidence` for historical compatibility/reprocessing where still required.

Rare/expensive:

- full-book reprocessing,
- historical re-analysis,
- Grade transition synthesis,
- optional image generation.

---

# 19. Cost and Observability

## 19.1 AI Execution Ledger

Each AI execution should record enough information to audit usage and quality, including:

- request ID,
- task,
- provider,
- model,
- input tokens,
- output tokens,
- vision usage when applicable,
- audio/STT usage when applicable,
- latency,
- estimated cost,
- success/failure,
- fallback usage,
- relevant processing/prompt/schema version.

## 19.2 Runtime Context Budget

Having data stored does not mean sending all of it to the model.

Tutor context should contain only the structurally selected, relevant slice of:

- current interaction,
- full Immediate Exchange and relevant complete current Segment / Learning
  Thread Exchanges,
- compact Structured Segment State when that future runtime is implemented,
- current learning state,
- relevant recent patterns,
- relevant stable patterns,
- relevant curriculum content,
- relevant open loops.

Explicit configurable budgets should limit:

- retrieved blocks,
- tutor output size,
- image size,
- historical lookback,
- Segment context,
- Segment review capacity / input budget,
- optional web/image-generation usage.

Exact values should be tuned from real usage rather than guessed prematurely.
They are final capacity/cost guardrails, not a positional conversation-selection
algorithm.

## 19.3 Cost Dashboard

Parent/Admin needs a compact view such as:

- Tutor,
- Vision,
- STT,
- Content processing,
- Evidence processing,
- Other,
- estimated monthly total.

Detailed technical logs remain available for debugging without turning the Parent interface into an engineering console.

---

# 20. Rebuildability and Versioning

## 20.1 Core Rule

> **Original source remains; derived intelligence can be rebuilt.**

This applies to both content and learner intelligence.

## 20.2 Content Rebuild

```text
Original Book
    ↓
Docling processing
    ↓
Educational semantics
    ↓
Index
```

A change in document-processing or semantic-extraction logic can rebuild downstream artifacts from the original book.

## 20.3 Learner Intelligence Rebuild

```text
Raw Interaction
        ↓
Completed Segments
        ↓
Segment Reviews / staged findings
        ↓
Session-authorized Events / Evidence
        ↓
Patterns / Current State
    ↓
Intelligence Card
```

A change in evidence rules, prompt, model, or pattern policy can reprocess raw history and rebuild downstream intelligence.

## 20.4 Version Metadata

Derived processing must be attributable to the logic used to produce it.

Version information may include:

- processing run,
- model,
- provider,
- prompt version,
- schema version,
- segment review schema/prompt/rubric/policy versions,
- session finalization policy version,
- evidence policy version,
- pattern policy version,
- document pipeline version.

This can be centralized through processing-run records rather than duplicating every field everywhere.

## 20.5 Validation Philosophy

The system is not expected to produce perfect evidence from day one.

The development model is:

```text
Observe
   ↓
Audit
   ↓
Measure against agreed rubrics
   ↓
Correct prompt/rule/policy
   ↓
Reprocess
   ↓
Measure again
```

The critical requirement is not "AI must never be wrong."

The critical requirement is:

> **No important AI-derived learner conclusion should be untraceable or impossible to recompute.**

The official measurement and review criteria are governed by `LEARNING_INTELLIGENCE_SPEC.md`.

---

# 21. Implementation Architecture Principles

## 21.1 Architecture Style

**Modular Monolith + Vertical Slice First.**

Do not begin with microservices.

The system should be modular internally while remaining simple to operate and modify.

## 21.2 Core Domains

Logical domains:

```text
Tutor
Intelligence
Content
Retrieval
Learning Artifacts
Model Gateway
Grade
Platform
```

Suggested responsibilities:

### Tutor
- runtime context,
- modes,
- teaching strategy,
- Multimodal Turn context and session-local Segment / Learning Thread resolution,
- optional Durable Conversation Topic resolution,
- tutor call,
- candidate events,
- open loops.

### Intelligence
- Segment semantic review and staged findings,
- Session Intelligence Finalization,
- validated events,
- evidence,
- current state,
- patterns,
- temporal lifecycle,
- intelligence card,
- derived decision views.

### Content
- uploaded books,
- source files,
- Docling processing,
- semantic curriculum extraction,
- school plans,
- figures,
- reprocessing.

### Retrieval
- metadata filtering,
- lexical search,
- vector search,
- ranking,
- context selection.

### Learning Artifacts
- artifact specification,
- registry,
- renderers,
- Learning Canvas,
- interaction events,
- image annotation/reconstruction integration.

### Model Gateway
- task routing,
- providers,
- fallbacks,
- usage logging.

### Grade
- active Grade,
- book assignment,
- activation of next Grade,
- compact transition card,
- previous-Grade archive linkage.

### Platform
- auth,
- roles,
- files,
- jobs,
- settings,
- AI usage,
- observability.

## 21.3 Extensibility Rule

Math and Science are the first subject modules.

Adding a future subject should not require rewriting the core Tutor architecture.

Avoid broad core logic such as:

```text
if subject == "math": ...
elif subject == "science": ...
```

spread across unrelated modules.

Subject-specific teaching guidance, evidence dimensions, artifact catalogs, and retrieval behavior should live behind clear subject extension points without requiring a generic plugin framework in the MVP.

## 21.4 API Layer Rule

API routes should be thin.

Avoid embedding AI calls, SQL, pattern updates, and business logic directly inside endpoint handlers.

Prefer:

```text
API route
   ↓
Application/domain service
   ↓
Repository / provider / model gateway
```

Do not over-engineer this into excessive enterprise layering.

## 21.5 Background Work

Initial background processing can use:

```text
jobs table + worker process
```

Appropriate jobs include:

- book processing,
- Docling conversion,
- semantic extraction,
- embeddings,
- Segment Learning Review,
- Session Intelligence Finalization,
- legacy Session Evidence reprocessing compatibility where required,
- intelligence rebuild,
- Grade transition processing.

Interactive tutor responses must remain synchronous/streaming rather than background jobs.

---

# 22. Technology Decisions

Initial approved technology direction:

## Frontend

- Next.js
- TypeScript
- responsive web app
- React-based component architecture
- SSE streaming

## Backend

- Python
- FastAPI

## Database

- PostgreSQL
- pgvector
- JSONB where schema flexibility is useful during early iteration

## Object Storage

- S3-compatible object storage

Used for:

- original books,
- student images,
- drawings,
- interaction assets,
- derived image annotations,
- generated/reconstructed visual artifacts when persistence is useful.

## Document Understanding

- Docling as baseline document-processing foundation.

Duckling may be used as a developer/admin content workbench or implementation reference, but is not a required runtime product dependency.

## Interactive Artifact Stack

Initial:

- React/SVG
- Motion
- JSXGraph
- React Konva
- MathLive

Optional later:

- Rough.js
- Recharts
- p5.js

## Background Jobs

- database-backed jobs table
- worker process

## Streaming

- Server-Sent Events (SSE)

## Vector Search

- pgvector in PostgreSQL initially

---

# 23. System Invariants

The following rules should be treated as protected design constraints unless the Product Owner explicitly changes them.

1. **Understanding is more important than answer withholding.**
2. **The book controls school scope, not teaching method.**
3. **Current behavior outranks historical personalization.**
4. **Strategy selection is not strategy-effectiveness Evidence; only observable Lina outcomes can support/challenge a strategy pattern.**
5. **Never personalize away demonstrated independence.**
6. **The Tutor does not directly create stable learner conclusions from one impression.**
7. **Meaningful learner intelligence must remain traceable to source interactions/evidence.**
8. **Mastery and confidence are derived decision views, not the source of truth.**
9. **Raw student work is never replaced by AI interpretation.**
10. **AI annotation/reconstruction is a derived artifact, not evidence of what Lina originally produced.**
11. **No psychological/personality/intelligence diagnosis from learning interactions.**
12. **No fixed learning-style labels.**
13. **Do not send full historical memory to the Tutor by default.**
14. **Normal new-session Tutor context does not inject prior-session raw transcripts, archived Segments, or automatic historical semantic retrieval.**
15. **Learning Thread / `thread_id` means the session-local Segment; returning after an intervening Segment creates a new Segment.**
16. **Durable Conversation Topic is optional Grade-scoped navigation metadata, not Learner Intelligence, Evidence, Safety, or curriculum authority.**
17. **Conversation classification does not substitute for TeachingMode, TeachingStrategy, TeachingMethod, Safety / Parent Boundary classification, or curriculum semantics.**
18. **The Intelligence Card must remain compact and temporally relevant.**
19. **Resolved patterns leave current runtime context but remain historically available.**
20. **Pattern weights/lifecycle are system-governed, not free LLM judgment.**
21. **AI is used for cognition; deterministic code is preferred for state, counts, lifecycle, and rules.**
22. **The normal Tutor path uses one primary Tutor model call.**
23. **Semantic learning interpretation is completed-Segment-scoped; durable Evidence/intelligence activation remains Session-scoped. No additional Evidence evaluator is added to each normal Tutor Turn.**
24. **Original books and raw learning history are preserved so derived state can be rebuilt.**
25. **Every important derived processing path is versionable and auditable.**
26. **No unnecessary AI call without identifiable product/learning value.**
27. **Artifact failure must never block learning.**
28. **Interactive visuals are used because they add learning value, not merely because animation is available.**
29. **Lina may change topics naturally; internal Segment separation must not burden her.**
30. **Student UX remains simpler than system internals.**
31. **Parent insight should not become surveillance-style activity tracking.**
32. **Grade transition is Parent/Admin controlled through new Grade book activation.**
33. **The next Grade receives a compact transition card, not the entire previous Grade runtime state.**
34. **Math and Science are first, but the core architecture must remain extensible to future subjects.**
35. **No microservices, graph infrastructure, or generic agent framework without demonstrated need.**
36. **All student-facing generation and tools must comply with the non-overridable child-safety baseline; prompt instructions alone are not considered enforcement.**
37. **Parent-configurable topic boundaries may restrict discussion further but may never weaken the system safety baseline.**
38. **Parent-controlled topic restrictions use only the approved states: Allow / Age-appropriate only / Redirect to parent.**
---

# 24. Approved Decisions

| Decision | Status |
|---|---|
| Lina-first, product-ready foundation | Approved |
| Multi-child/SaaS UX in MVP | Out of scope |
| Grade 5 first | Approved |
| Math + Science first | Approved |
| Book = Curriculum Anchor | Approved |
| Book teaching method is mandatory | Rejected |
| School-led path as product authority | Superseded — Roadmap Option A |
| Question-driven learning with useful prerequisite micro-detours | Approved |
| Formal prerequisite diagnostic on every new topic | Rejected |
| Current School Focus as authority | Superseded — Roadmap Option A |
| Relevant recent conversational/topic context | Approved — relevance first |
| Tutor always available without a book or ready content | Approved |
| Question-driven optional RAG | Approved |
| Semantic enrichment required before index/Tutor | Superseded — Roadmap Option A |
| Semantic enrichment as optional rebuildable layer | Approved |
| Interaction-derived concept identity for Learning Intelligence | Approved |
| Multi-source Learning Source model | Approved |
| Trusted Educational Reference pilot | Approved future capability |
| Universal cross-grade concept graph | Deferred / not required |
| Grade transition by Parent/Admin activation of next Grade books | Approved |
| Compact transition card to next Grade | Approved |
| Full prior Grade state in new runtime | Rejected |
| Learner profile updates are evidence-governed | Approved |
| Parent can challenge/revalidate but not directly rewrite profile | Approved |
| Psychological/personality/intelligence labels | Rejected |
| Tutor may teach the answer after reasonable support attempts | Approved |
| Rubric/categorical evidence over pseudo-precise scores | Approved |
| Numeric internal calculations allowed when useful | Approved |
| Event/evidence/card architecture is core | Approved |
| Mastery engine as source of truth | Rejected |
| Intelligence Card as compact temporal intelligence | Approved |
| Frequency + recency + counter-evidence affect patterns | Approved |
| Pattern weights determined by deterministic/configurable rules | Approved |
| Pattern scope starts narrow and may broaden with evidence | Approved |
| Patterns are advisory, not mandatory Tutor rules | Approved |
| Current behavior overrides history | Approved |
| Raw interaction history retained | Approved |
| Raw audio retained | Rejected for current version |
| Transcript retained | Approved |
| Detailed Session Learning Card for every trivial session | Rejected |
| Meaningful-session intelligence deltas/history | Approved |
| Multiple learning threads per session | Approved |
| Learning Thread = session-local contiguous Segment (`thread_id`) | Approved |
| Optional Grade-scoped Durable Conversation Topic navigation metadata | Approved |
| Durable Conversation Topic as Learner Intelligence, Evidence, Safety, or curriculum authority | Rejected |
| Automatic normal-turn prior-session transcript injection | Rejected |
| Archive vector / automatic historical semantic retrieval | Deferred — on-demand seam requires independent validation |
| Session auto-close after inactivity | Approved |
| Tutor emits candidate events in same Tutor call | Approved |
| Session-level semantic consolidation as primary semantic review unit | SUPERSEDED BY SEG-EVID-01 |
| Segment-scoped semantic Learning Review | Approved |
| Session-scoped durable intelligence authority | Approved |
| Staged Segment findings remain inactive until Session activation | Approved |
| Candidate Events are provisional semantic hints, not mandatory Evidence gates | Approved |
| Session Finalization deterministic by default; no semantic Session call after Segment Reviews by default | Approved |
| Existing Current State / Pattern / support-counter architecture preserved | Approved |
| Historical Session Evidence remains valid | Approved |
| EDU-ERR integrates into Segment Review later | Approved future |
| Cross-subject attribution | Deferred to SCOPE-01 / SUBJ-01 |
| Docling as document-understanding baseline | Approved |
| Duckling as runtime product dependency | Rejected |
| Duckling as content workbench/reference | Approved |
| Blind fixed-size chunking | Rejected |
| Structural/hierarchical + hybrid retrieval | Approved |
| Adaptive Persona as main personalization mechanism | Rejected |
| Adaptive Teaching Strategy | Approved |
| One primary Tutor call in normal turn | Approved |
| Multimodal student input | Core capability |
| Student handwriting/drawing can become evidence | Approved |
| Annotate original image first | Approved |
| Clean redraw/reconstruction when needed | Approved |
| Text-only Tutor | Rejected |
| Interactive HTML/SVG/React learning artifacts | Core capability |
| Typed artifact specs + reusable renderers | Approved |
| Arbitrary unsandboxed AI JavaScript | Rejected |
| Modular Monolith | Approved |
| Vertical Slice First | Approved |
| Learning Intelligence Rubric + Pattern Rules as official measurement reference | Approved |
| Full observability + reprocessing over excessive pre-emptive safeguards | Approved |
| Non-overridable child-safety baseline | Approved |
| Parent-configurable Learning Boundaries in Dashboard | Approved |
| Learning Boundary states: Allow / Age-appropriate only / Redirect to parent | Approved |
| Explicit Safety & Learning Boundary Policy Engine before Tutor behavior | Approved |
| REDIRECT_TO_PARENT events visible as Parent policy/audit records, not Learner Intelligence | Approved |
| Parent settings may weaken system safety baseline | Rejected |

---

# 25. Assumptions

These are working assumptions, not immutable product decisions.

1. A responsive web app is sufficient for Lina's initial use.
2. Grade 5 Math and Science books will be available in uploadable digital/scanned formats.
3. Docling will provide useful structural extraction on Lina's real books, but quality must be tested rather than assumed.
4. A fast, cost-efficient modern model may be sufficient for most Tutor interactions, but this must be benchmarked on actual teaching scenarios.
5. Parent/Admin is willing to upload/activate new Grade books once per Grade transition.
6. Lina will naturally use a mix of text, voice, handwriting, drawings, and photos.
7. A relatively small library of high-value interactive artifacts can cover many early Math/Science needs.
8. PostgreSQL + pgvector is sufficient for the initial scale.
9. A DB-backed worker is sufficient for initial batch processing.
10. The system will be iteratively improved by reviewing actual sessions, evidence, patterns, cost logs, and model behavior.

---

# 26. Risks and Open Questions

These are real unresolved areas that should be validated during implementation rather than over-designed in advance.

## 26.1 Real-Book Extraction Quality

Need to test Docling and the educational-semantic layer against Lina's actual Math and Science books.

Questions:

- Does page structure remain usable?
- Are formulas and figures extracted well enough?
- Are Units/Lessons recognized reliably?
- Are retrieval units meaningful?

## 26.2 Tutor Model Fit

Need benchmark scenarios covering:

- Grade-appropriate explanation,
- Arabic/English switching,
- hints,
- teaching after failure,
- visual/artifact selection,
- candidate-event metadata,
- correct behavior when uncertain.

The selected production Tutor model should be evidence-driven, not selected only by model reputation.

## 26.3 Evidence Rubric Quality

Exact evidence states, definitions, and pattern rules are intentionally moved to `LEARNING_INTELLIGENCE_SPEC.md`.

The main implementation risk is not that the model will never make an incorrect extraction. The important requirement is that extraction remains traceable and reprocessable against agreed rules.

## 26.4 Artifact Library Scope

The correct initial set of reusable Math/Science artifacts should be driven by real book content and real Lina interactions.

Do not create a large generic educational-widget library before those use cases appear.

## 26.5 Vision Reliability on Student Work

Handwriting and child drawings can be ambiguous. The interaction design must make clarification cheap and natural when required.

## 26.6 Runtime Cost

Exact costs are unknown until real usage exists. Cost should be measured by task/model and optimized from evidence rather than estimated through architecture complexity alone.

## 26.7 Learning-Boundary Classification

The initial topic catalog and routing behavior must be tested with realistic child questions. The implementation should distinguish clearly between:

- mandatory system-safety restrictions, and
- parent-configurable family/age boundaries.

Misclassification should be observable and correctable without changing the core Tutor architecture.

---

# 27. Validation and Decision Gate

The project should not attempt to complete every planned feature before Lina uses it.

The first meaningful decision gate is a real Math vertical slice. A real book
and trusted references are valuable grounding-validation inputs, not permission
for Lina to enter the Tutor.

## 27.1 Vertical Slice

```text
Lina asks/answers through the Tutor, with or without a source
        ↓
Safety applies
        ↓
Optional question-driven grounding improves the answer when available
        ↓
Tutor adapts explanation
        ↓
Optional Candidate hints are captured
        ↓
Meaningful Segment closes and background Segment Review stages findings
        ↓
Session closes
        ↓
Deterministic finalization activates Evidence
        ↓
Current state / patterns / card update
        ↓
Parent can inspect what happened
        ↓
Next session uses relevant intelligence
```

The validation loop must prove both `no book → Tutor still works` and
`content available → optional grounding improves the answer`. At least one
interactive artifact path should also be proven when it provides real learning
value.

## 27.2 Review Method

During early use, the Product Owner and AI assistant should review:

- raw transcript,
- source images when relevant,
- candidate events,
- evidence,
- pattern changes,
- intelligence card changes,
- Tutor decisions,
- retrieval references,
- AI model logs,
- token/cost logs.

The review compares system behavior against the approved Learning Intelligence Rubric and Pattern Rules.

If evidence extraction or pattern logic is wrong:

1. identify the systematic issue,
2. change the relevant prompt/rule/policy,
3. version the change,
4. reprocess the affected raw history,
5. compare the new result.

## 27.3 Decision Gate

Do not aggressively expand the product until the core loop proves useful with Lina.

Questions at the gate:

- Does Lina want to use it?
- Does the Tutor help her understand rather than merely answer?
- Does retrieval reliably ground school topics?
- Do interactive representations improve understanding when used?
- Do generated events/evidence broadly reflect what actually happened?
- Does the Intelligence Card remain compact and useful?
- Does personalization improve interactions without constraining Lina?
- Can the Parent understand why the system reached important conclusions?
- Is cost/latency acceptable?
- Can errors be traced and corrected through reprocessing?

If the answer is no in a core area, fix the core loop before adding breadth.

---

# 28. Relationship to Other Project Documents

This document defines **what the project is and the durable governing direction**.

The following documents refine execution. Approved product-evolution sequencing,
future capability tracks, dependencies, and validation gates are recorded in
`LEARNING_PRODUCT_ROADMAP.md`.

## `LEARNING_PRODUCT_ROADMAP.md`

Defines approved product-evolution decisions, capability tracks, dependencies,
and validation gates. A Roadmap item is not executable until it is promoted to
`TASKS.md` with a concrete scope.

## `CHILD_SAFETY_POLICY.md`

Defines:

- non-overridable child-safety baseline,
- age-appropriate response principles,
- Parent Learning Boundary categories,
- Allow / Age-appropriate only / Redirect-to-parent behavior,
- enforcement order across Tutor, vision, artifacts, web, and other student-facing tools,
- safe redirect behavior,
- audit/versioning expectations for boundary-policy changes.

## `LEARNING_INTELLIGENCE_SPEC.md`

Defines:

- meaningful event taxonomy,
- evidence dimensions,
- evidence rubrics,
- support levels,
- transfer rules,
- retention rules,
- self-correction rules,
- strategy-effectiveness rules,
- pattern identity,
- weighting inputs,
- recency/frequency logic,
- counter-evidence semantics,
- scope rules,
- lifecycle rules,
- card compaction rules,
- Segment Review, staged findings, and Session Finalization behavior,
- audit/reprocessing rules.

## `IMPLEMENTATION_PLAN.md`

Defines:

- concrete architecture,
- repository layout,
- database schema direction,
- phases,
- vertical slice sequencing,
- dependencies,
- technical integration order,
- implementation constraints,
- verification gates,
- what to delay.

## `AGENTS.md`

Defines how Codex/AI agents may operate inside the repository, including protected areas, approval rules, verification requirements, and state-update requirements.

## `PROJECT_STATE.md`

Maintains the short operational snapshot of the implementation state.

## `SYSTEM_MAP.html`

Provides the visual map of the operating architecture, data flows, boundaries, and readiness.

## `TASKS.md`

Contains ordered implementation tasks for Codex/AI agents.

---

# 29. Governing Summary

The project should remain simple in use and modular in construction.

The current Student question drives the interaction. Available books and other
trusted learning sources provide optional grounding; Docling structural
representation and hybrid retrieval preserve useful provenance, while
educational semantics remain optional enrichment. The Tutor teaches using a
stable identity and adaptive teaching strategy.

The system does not treat the Tutor model's impression as learner truth. Raw interactions are preserved; completed Segments are semantically reviewed and staged; closed Sessions deterministically authorize Evidence; temporal patterns evolve under explicit rules; and a compact Learner Intelligence Card provides relevant memory without loading years of history into each prompt.

Mastery and confidence are views over this evidence, not permanent source data.

The Parent/Admin controls content and Grade activation, sees important insights and evidence, and can audit how conclusions were formed. AI usage remains task-routed, observable, replaceable, and reprocessable.

The implementation starts with a modular monolith and a real Math vertical
slice. The core loop must work with zero content and improve with useful
grounding. The product expands only after Lina's real use demonstrates that it
is educationally useful, technically traceable, and operationally affordable.

---

**End of PROJECT_REFERENCE.md**
