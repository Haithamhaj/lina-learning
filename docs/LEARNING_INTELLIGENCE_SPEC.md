# Lina Personal Learning System

## LEARNING_INTELLIGENCE_SPEC.md

**Status:** Complete specification — awaiting approval  
**Authority:** Governing specification for the Learning Intelligence subsystem  
**Audience:** Product owner, ChatGPT, Codex, AI agents, developers, reviewers  
**Depends on:** `PROJECT_REFERENCE.md`  
**Does not define:** Tutor UI, detailed database implementation, document ingestion implementation, implementation phases, or model-vendor selection

---

# 1. Purpose & Authority

This document defines how the Lina Personal Learning System converts real learning interactions into structured, explainable, revisable learner intelligence.

It is the governing contract for:

- meaningful learning events,
- evidence extraction,
- evidence rubrics,
- current learning state,
- learner patterns,
- temporal weighting,
- pattern scope and lifecycle,
- session consolidation,
- the Learner Intelligence Card,
- derived mastery/confidence views,
- grade transition intelligence,
- multimodal evidence handling,
- traceability,
- versioning,
- reprocessing,
- observability and human audit.

The system must not treat an AI-generated impression as learner truth.

The durable source is the original interaction history. All higher-level intelligence is derived and must remain traceable and rebuildable.

> **Learning Intelligence is an evidence-grounded interpretation of Lina's learning history, not a permanent label about Lina.**

The detailed implementation may evolve, but it must preserve the contracts and invariants in this specification unless the project owner explicitly changes them.

---

# 2. Core Intelligence Model

The canonical pipeline is:

```text
Raw Interaction
      ↓
Candidate Event
      ↓
Validated Learning Event
      ↓
Evidence
      ↓
┌───────────────────────┐
│ Current Learning State│
│ Learner Patterns      │
└───────────┬───────────┘
            ↓
Learner Intelligence Card
            ↓
Decision Views
            ↓
Tutor Personalization / Parent Insights
```

The system separates **what happened**, **what it suggests**, **what has become a repeated pattern**, and **what decision should be made now**.

## 2.1 Raw Interaction

The original interaction record. Examples:

- Lina's text message,
- tutor response,
- speech transcript,
- uploaded homework image,
- photographed handwriting,
- photographed drawing,
- artifact interaction result,
- associated session/thread/context metadata.

Raw interaction is the historical source from which downstream intelligence can be rebuilt.

Here `thread_id` has one governing meaning: the identity of the session-local
contiguous **Learning Thread / Segment**. It is context linkage, not an
independent third Thread entity or a replacement for raw source references.
Messages, transcripts, and original asset/source references remain authoritative
for all downstream lineage.

## 2.2 Candidate Event

A lightweight signal emitted during the interaction indicating that something potentially meaningful happened.

A Candidate Event is **not** evidence and must not directly update a stable learner pattern.

## 2.3 Validated Learning Event

A structured description of a meaningful learning occurrence after end-of-session consolidation.

It describes **what happened in that context**, not a general conclusion about Lina.

## 2.4 Evidence

A rubric-based interpretation of what a validated event demonstrates in one or more learning dimensions.

Evidence remains attached to its event and source context.

## 2.5 Current Learning State

Short-lived intelligence about what matters **now**, for example:

- an active difficulty,
- an active misconception,
- an unresolved learning loop,
- a recently successful strategy,
- a current retention concern.

A strong event may update Current Learning State immediately after consolidation.

## 2.6 Learner Pattern

A repeated, evidence-supported observation that has persisted sufficiently across time and/or contexts to be useful for personalization.

A Learner Pattern must never be created from one ordinary interaction.

## 2.7 Learner Intelligence Card

A compact, current, runtime-oriented representation of the most relevant learning intelligence about Lina.

It is **not** a transcript summary and is **not** a complete archive.

## 2.8 Decision View

A computed interpretation used by the Tutor or Parent Dashboard, for example:

- `Developing`,
- `Strong`,
- `Needs Revisit`,
- `Evidence Confidence: High`.

Decision Views are derived, versioned, and replaceable. They are not source-of-truth learner memory.

---

# 3. Governing Separation of Responsibilities

The subsystem must preserve the following separation:

```text
AI models
→ understand semantic meaning
→ classify or extract events/evidence
→ synthesize human-readable descriptions when needed

Deterministic system logic
→ count frequency
→ calculate recency
→ apply evidence weights
→ track counter-evidence
→ manage lifecycle
→ apply scope rules
→ maintain card size
→ compute decision views
```

The AI may suggest that an event supports a pattern. It must not independently decide the final importance, weight, lifecycle state, or persistence of that pattern.

> **AI interprets meaning. The system governs memory.**

---

# 4. Meaningful Event Rules

## 4.1 Meaningful Event Principle

An interaction becomes a Candidate Event only when it can reasonably:

1. add information about Lina's understanding or learning behavior,
2. confirm existing intelligence,
3. challenge existing intelligence,
4. update current learning state,
5. reveal a teaching strategy outcome,
6. create or resolve an important learning loop.

Normal conversational activity is not intelligence merely because it occurred.

## 4.2 Examples That Usually Qualify

- Lina attempts a problem independently.
- Lina requires a hint to continue.
- Lina corrects her own mistake.
- A specific misconception appears.
- A teaching representation fails.
- A different teaching representation succeeds.
- Lina explains a concept in her own words.
- Lina transfers a concept to an unfamiliar context.
- Lina fails to recall something previously demonstrated after meaningful elapsed time.
- Lina quickly regains previously learned understanding after a short review.
- Lina demonstrates substantially more independence than before.
- Lina demonstrates substantially less support need than before.
- Lina creates a drawing/model that reveals concept understanding or a misconception.
- Lina successfully interacts with a learning artifact in a way that demonstrates understanding.
- A current learning loop is resolved.

## 4.3 Examples That Do Not Qualify by Themselves

- greeting the tutor,
- saying thank you,
- casual conversation with no learning signal,
- opening a page,
- clicking a button with no educational meaning,
- viewing an artifact without meaningful interaction,
- the tutor choosing an explanation strategy without observing an outcome,
- a single vague impression such as "Lina seemed distracted."

These remain available in raw history but do not enter Learner Intelligence unless a later meaningful event gives them educational relevance.

---

# 5. Event Taxonomy

The taxonomy is intentionally compact. New event types may be added without changing the core architecture if they preserve the same evidence-first contract.

| Event Type | Meaning | Typical Source |
|---|---|---|
| `learning_attempt` | Lina attempts a question/task | Tutor interaction, artifact |
| `independent_success` | Successful task completion without instructional support | Tutor, quiz, artifact |
| `guided_success` | Successful completion with support | Tutor, homework |
| `incorrect_attempt` | Attempt contains an important error | Tutor, image, artifact |
| `misconception_signal` | Error suggests a specific conceptual misunderstanding | Tutor, drawing, handwriting |
| `self_correction` | Lina identifies and corrects her own error | Tutor, artifact |
| `explanation_attempt` | Lina explains reasoning/concept in her own words | Text, voice, drawing |
| `transfer_attempt` | Concept is applied in a meaningfully different context | Tutor, quiz, exploration |
| `retention_check` | Previously learned concept is encountered after meaningful elapsed time | Review, natural curriculum use |
| `strategy_applied` | Tutor uses a teaching strategy worth tracking | Tutor runtime |
| `strategy_outcome` | Observable outcome follows a teaching strategy | Tutor, artifact |
| `support_change` | Required support materially increases or decreases | Session consolidation |
| `open_loop_created` | Important understanding remains unresolved | Session end |
| `open_loop_resolved` | Previously open learning loop is resolved | Tutor/session |
| `extended_learning_event` | Meaningful learning outside the current school scope | Explore mode |
| `artifact_interaction` | Interactive artifact action has educational meaning | Learning Artifact Engine |

Event type alone never determines mastery or a learner pattern.

> **Historical compatibility:** older persisted `current_focus_signal` rows
> remain readable for audit and bounded reprocessing. New Tutor Candidate Event
> output must not emit them: school position is not learner-intelligence
> authority.

---

# 6. Validated Learning Event Contract

A validated event should contain enough structure for downstream processing without attempting to summarize the entire conversation.

Conceptual shape:

```json
{
  "event_id": "...",
  "student_id": "...",
  "grade_period_id": "...",
  "session_id": "...",
  "thread_id": "...",
  "subject": "math",
  "concept_ref": "equivalent_fractions",
  "event_type": "self_correction",
  "event_summary": "Lina initially compared denominators incorrectly, then corrected the comparison without being told the answer.",
  "school_or_extended": "school",
  "source_refs": ["message:...", "message:..."],
  "occurred_at": "...",
  "processing_run_id": "..."
}
```

The event summary must describe the interaction contextually. It must not contain unsupported labels such as:

- "Lina is careless",
- "Lina is a visual learner",
- "Lina has poor attention",
- "Lina is highly intelligent".

---

# 7. Evidence Model

Evidence is rubric-based rather than pseudo-precise numeric judgment.

One validated event may create evidence across multiple dimensions.

Example:

```json
{
  "understanding": "demonstrated",
  "independence": "light_support",
  "reasoning_demonstration": "coherent",
  "transfer": "partial",
  "self_correction": "self_initiated",
  "retention": "not_tested"
}
```

Numeric values may be used internally for deterministic weighting, but the AI does not invent values such as `reasoning = 0.83` as learner truth.

---

# 8. Evidence Dimensions & Rubrics

The following rubrics are the initial approved semantic contract. Their names and definitions are more important than any later internal numeric mapping.

## 8.1 Concept Understanding

Measures what the interaction demonstrates about understanding **of the relevant concept in this task**.

| State | Definition |
|---|---|
| `not_observed` | Interaction does not meaningfully test understanding. |
| `not_demonstrated` | Evidence does not show the required concept understanding. |
| `partial` | Some correct understanding is visible, but an important conceptual gap remains. |
| `demonstrated` | Lina shows adequate conceptual understanding for the task/context. |
| `strong_demonstration` | Lina demonstrates understanding with explanation, flexibility, or depth beyond simple successful execution. |

### Does not count as strong understanding by itself

- copying a demonstrated procedure,
- choosing the correct answer by chance,
- reaching the answer after full teaching without independent follow-up,
- repeating tutor wording without showing application.

---

## 8.2 Independence / Support Requirement

Describes the instructional support required for the observed success.

| State | Definition |
|---|---|
| `independent` | Lina proceeds without instructional help relevant to the solution. |
| `light_support` | Small prompt/focusing hint; core reasoning remains Lina's. |
| `moderate_support` | Meaningful scaffolding is needed, but Lina completes important reasoning herself. |
| `substantial_support` | Tutor supplies major parts of the reasoning or structure. |
| `full_teaching` | Tutor effectively teaches or demonstrates the solution before Lina can proceed. |
| `not_applicable` | The event is not a learning attempt for which support level is meaningful. |

The number of hints may be stored as metadata, but `2 hints` is not automatically equivalent to a specific support category.

---

## 8.3 Reasoning Demonstration

Describes the quality of reasoning demonstrated **within the task**, not Lina's general intelligence.

| State | Definition |
|---|---|
| `not_observed` | No meaningful reasoning was expressed or required. |
| `fragmented` | Reasoning is incomplete, internally inconsistent, or depends heavily on prompting. |
| `coherent` | Reasoning connects the relevant steps or causes in a logically useful way. |
| `well_supported` | Reasoning is coherent and supported with explanation, relationships, or justification. |

A reasoning state must remain scoped to the context in which it was observed.

---

## 8.4 Transfer

Tests whether understanding survives a meaningful change in representation, context, wording, or application.

| State | Definition |
|---|---|
| `not_tested` | No meaningful transfer opportunity occurred. |
| `unsuccessful` | Lina cannot apply the concept in the changed context. |
| `partial` | Some transfer occurs, but support or conceptual gaps remain. |
| `demonstrated` | Lina applies the concept successfully in a meaningfully different context. |

A near-identical practice item is not automatically transfer.

---

## 8.5 Self-Correction

| State | Definition |
|---|---|
| `not_observed` | No relevant correction event occurred. |
| `externally_corrected` | Error was corrected only after the tutor directly identified or supplied the correction. |
| `prompted` | Lina corrected the error after a general prompt to reconsider/check. |
| `self_initiated` | Lina independently noticed and corrected the error. |

This rubric distinguishes "the final answer became correct" from "Lina detected her own mistake."

---

## 8.6 Retention

Retention is evaluated only when sufficient time or natural curriculum distance makes the event meaningfully different from immediate practice.

| State | Definition |
|---|---|
| `not_tested` | Event does not meaningfully evaluate retention. |
| `retrieval_failed` | Previously demonstrated knowledge cannot currently be retrieved/applied. |
| `partial_retrieval` | Some retained understanding is present but requires support or refresh. |
| `retained` | Previously demonstrated understanding is retrieved and applied adequately. |
| `rapid_recovery` | Initial recall is weak, but prior understanding returns quickly with a small refresh. |

A retention failure does **not** automatically contradict that the concept was learned previously.

It may instead indicate:

> learned previously + retention currently weak.

---

## 8.7 Strategy Effectiveness

This dimension evaluates the **teaching strategy**, not Lina.

| State | Definition |
|---|---|
| `not_evaluable` | No meaningful outcome can be linked to the strategy. |
| `ineffective` | Strategy did not improve the relevant learning state in that interaction. |
| `unclear` | Outcome is ambiguous or mixed. |
| `helped` | Observable improvement followed the strategy. |
| `enabled_independent_success` | Strategy was followed by meaningful independent understanding/application. |

Examples of strategy identity:

- concrete example,
- visual fraction representation,
- decomposition of a word problem,
- Socratic focusing question,
- worked example,
- interactive artifact,
- drawing/model request,
- change from symbolic to visual representation.

For teaching-representation effectiveness, **TeachingMethod** is the canonical method identity. It is distinct from TeachingStrategy, which governs the support/intervention flow. The existing `strategy_applied` and `strategy_outcome` taxonomy remains compatible: the existing `strategy_key` lineage may carry the canonical TeachingMethod identifier where the established pattern contract requires it.

Mode, Strategy, Method, and prior-method-relation are turn-level semantic routing/audit metadata from the same primary Tutor call, not Candidate Events, Evidence, or learner memory. Runtime validates their canonical values and persisted source lineage but does not infer their natural-language meaning. That method identity must be source-grounded in persisted project-owned Tutor-turn metadata, together with the bounded prior-turn/source lineage needed to connect the method to the later observable Student outcome. Session Evidence consolidation must not invent a method identity. An immediate same-session method change after current confusion is contextual adaptation; repeated method outcomes are the separate, evidence-dependent basis for any stable `strategy_effectiveness` pattern.

---

## 8.8 Persistence in Learning Interaction

This dimension describes observed behavior **within the learning interaction only** and must never become a personality diagnosis.

| State | Definition |
|---|---|
| `not_observed` | No meaningful persistence signal. |
| `stopped` | Lina chose not to continue the task. |
| `continued_with_support` | Lina continued after support or representation change. |
| `continued_independently` | Lina continued through difficulty without requiring instructional intervention. |

Do not convert this into labels such as "persistent child" or "low motivation."

---

## 8.9 Confidence Calibration

Use only when Lina expresses confidence explicitly or the interaction provides a clear confidence signal.

| State | Definition |
|---|---|
| `not_observed` | No meaningful confidence signal. |
| `under_confident` | Expressed confidence is materially lower than demonstrated performance. |
| `calibrated` | Expressed confidence broadly matches demonstrated performance. |
| `over_confident` | Expressed confidence is materially higher than demonstrated performance. |

This is contextual evidence, not a permanent trait.

---

# 9. Evidence Quality Metadata

Evidence quality is influenced by structured metadata. The AI may classify semantic properties; the system computes any weighting.

Recommended metadata includes:

```text
support_level
attempt_count
hints_used
task_novelty
task_context
curriculum_level
relative_challenge
representation_type
school_or_extended
source_modality
elapsed_since_related_evidence
same_session_or_delayed
concept_scope
artifact_used
strategy_used
```

## 9.1 Task Novelty

Suggested states:

```text
routine
similar
meaningfully_varied
novel
```

## 9.2 Relative Challenge

Suggested states:

```text
below_expected
expected
above_expected
unknown
```

This is relative to the current learning context, not a judgment of Lina's ability.

## 9.3 Source Modality

Examples:

```text
text
voice_transcript
handwritten_image
drawing_image
homework_image
interactive_artifact
quiz
```

The modality may affect interpretation but must not produce learning-style labels.

---

# 10. Evidence Relationship to Existing Intelligence

When new evidence is processed against an existing pattern or state, it should be classified conceptually as one of:

```text
supports
contradicts
improvement
retention_failure
scope_exception
insufficient
unrelated
```

## 10.1 `supports`

Evidence is consistent with and adds support to the existing interpretation.

## 10.2 `contradicts`

Evidence directly challenges the interpretation itself.

Example:

> Pattern claims Lina requires substantial support in a context, while multiple genuinely comparable recent events demonstrate independent success.

## 10.3 `improvement`

Evidence indicates growth beyond a previous difficulty. It may weaken or resolve an old pattern without implying that the old evidence was wrong at the time.

## 10.4 `retention_failure`

Lina previously demonstrated understanding but does not currently retrieve it after meaningful elapsed time.

This updates retention-related intelligence rather than erasing prior learning.

## 10.5 `scope_exception`

A pattern remains useful in some contexts but does not generalize to the current context.

## 10.6 `insufficient`

The evidence is too ambiguous or weak to affect the relevant pattern materially.

---

# 11. Current Learning State

Current Learning State is intentionally more responsive than Learner Patterns.

A single strong meaningful event may create or update a Current State item.

## 11.1 Current State Types

Initial types include:

```text
active_difficulty
active_misconception
open_learning_loop
recent_strategy_success
recent_strategy_failure
current_retention_concern
important_recent_change
```

## 11.2 Recent Learning Context

Recent Learning Context is conversational context, not Evidence-derived Current
Learning State. It may use relevant recent messages or topic metadata to help
an ambiguous continuation such as “Continue.”

It does not represent where Lina is supposed to be in the curriculum, what she
is required to study now, or what questions she is allowed to ask. The current
question remains highest authority; relevance comes before recency.

Historical `current_school_focus` Current State rows remain preserved for audit
but are excluded from runtime Learner Intelligence Card selection.

Optional Durable Conversation Topic metadata may assist bounded conversation
navigation or audit, but it is neither Evidence nor Learner Intelligence and
cannot create a learner conclusion. It does not directly update Current State,
Patterns, the Intelligence Card, or personalization.

## 11.3 Current State Lifecycle

Conceptual lifecycle:

```text
detected
   ↓
active
   ↓
resolving
   ↓
resolved
```

Some short-lived states may expire automatically when they are no longer relevant.

## 11.4 Resolution Principle

Old current-state information must not remain in runtime merely because it was once true.

Resolution can occur through:

- direct counter-evidence,
- successful independent application,
- explicit loop closure,
- deterministic expiry policy for short-lived state,
- replacement by a newer state.

Resolved state remains available historically but is removed from active runtime intelligence.

---

# 12. Learner Pattern Model

A Learner Pattern is a repeated evidence-supported observation useful for future teaching decisions.

Patterns describe **observable learning behavior in scope**, not personality.

## 12.1 Pattern Contract

Conceptual shape:

```json
{
  "pattern_id": "...",
  "pattern_key": "strategy_effectiveness:decompose_long_math_word_problem",
  "description": "Decomposition has repeatedly helped when long math word problems become difficult.",
  "pattern_type": "strategy_effectiveness",
  "scope_type": "context",
  "scope_ref": "math_word_problems",
  "evidence_count": 8,
  "counter_evidence_count": 2,
  "first_detected_at": "...",
  "last_supported_at": "...",
  "last_challenged_at": "...",
  "status": "active",
  "policy_version": "..."
}
```

The counts and timestamps are system-computed.

## 12.2 Pattern Identity

Semantically equivalent descriptions must map to the same normalized pattern where possible.

These should not become separate patterns:

```text
"benefits from breaking long word problems into steps"
"decomposition helps on lengthy math word problems"
```

A stable `pattern_key` or normalized pattern taxonomy should be preferred over free-form text identity.

The human-readable description may evolve without changing pattern identity.

---

# 13. Pattern Scope

Every pattern starts at the **narrowest scope supported by evidence**.

Supported conceptual scope levels:

```text
concept-specific
context-specific
subject-specific
cross-subject
global
```

Example progression:

```text
Equivalent Fractions
    ↓ repeated in other fraction tasks
Math representation context
    ↓ repeated across multiple Math concepts
Math subject pattern
    ↓ repeated meaningfully in Science and other contexts
Cross-subject / Global candidate
```

Generalization is never automatic merely because the wording sounds general.

> **Scope follows evidence. Evidence does not follow the desired scope.**

A pattern may also shrink in scope if later evidence shows that the original generalization was too broad.

---

# 14. Pattern Lifecycle

Canonical lifecycle:

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
```

## 14.1 Candidate

An emerging repeated signal that is not yet trusted enough for meaningful historical personalization.

## 14.2 Active

Enough relevant evidence exists for the pattern to be useful as a contextual teaching prior.

## 14.3 Stable

The pattern has remained meaningfully supported across sufficient time/context diversity to be treated as established learner intelligence.

Stable does not mean permanent.

## 14.4 Weakening

Recent, relevant counter-evidence or improvement reduces the pattern's current usefulness.

## 14.5 Resolved

The pattern no longer describes Lina's current learning state sufficiently to remain in Current Intelligence.

It is removed from the runtime card but remains historically available.

## 14.6 Superseded

A newer pattern more accurately explains the same area.

Example:

```text
Old:
Requires decomposition for long Math word problems.

New:
Generally handles long Math word problems independently; decomposition remains useful only when multiple irrelevant details are present.
```

---

# 15. Pattern Weighting Rules

Pattern strength/relevance is determined by deterministic policy, not free AI judgment.

The initial policy must consider:

```text
frequency
recency
evidence quality
independence/support
context similarity
context diversity
counter-evidence
pattern scope
```

Conceptually:

```text
Pattern relevance = f(
    frequency,
    recency,
    evidence quality,
    context similarity,
    context diversity,
    counter-evidence
)
```

The exact mathematical function and coefficients are calibration parameters, not fixed truth in this document.

## 15.1 Recency

New evidence generally carries more relevance for current personalization than old evidence.

Old evidence remains historically valid but may have low current weight.

## 15.2 Frequency

Repeated evidence strengthens a pattern, but raw counts alone must never govern promotion.

## 15.3 Context Diversity

Repeated evidence across independent contexts is stronger than repeated evidence from near-identical tasks in one lesson.

Example:

```text
3 signals in the same exercise set
<
3 comparable signals across different concepts/sessions
```

## 15.4 Counter-Evidence

Recent strong counter-evidence may outweigh larger quantities of older evidence.

Do not use simplistic arithmetic such as:

```text
5 old negative events - 4 new positive events = still negative
```

Time and quality matter.

## 15.5 Evidence Quality

Independent transfer should normally contribute more than heavily guided repetition, but the final mapping is deterministic and versioned.

---

# 16. Pattern Recurrence

Resolved patterns are absent from current runtime intelligence.

If a new event resembles a resolved historical pattern:

```text
New meaningful signal
       ↓
Historical similarity trigger
       ↓
Relevant resolved pattern lookup
       ↓
Possible recurrence context
       ↓
Collect new evidence
```

A single new signal does not automatically reactivate the old pattern.

Historical context informs interpretation; current evidence decides whether the pattern should return.

---

# 17. Session & Thread Intelligence

## 17.1 Session Lifecycle

A session closes automatically after configurable inactivity.

A short configurable grace window may allow Lina to return and continue the same session.

The exact inactivity duration is an implementation calibration parameter.

## 17.2 Learning Thread = Session-local Segment

A Learning Thread is the session-local contiguous Segment; `thread_id` is that
Segment identity. It is not a third entity. A Session may contain several
Segments as Lina changes topics or intent naturally.

Example:

```text
Session
├── Math / Adding Fractions
├── Science / Why is the sky blue?
└── Math / Homework continuation
```

Thread/Segment resolution is internal. Lina is not required to create a new
chat manually when she changes topic. A return to the same topic after an
intervening Segment creates a new Segment; it may reuse the same optional
`conversation_topic_ref`.

Events and evidence are associated with the relevant thread/context.

A Durable Conversation Topic is optional Grade-scoped conversation-navigation
metadata. It may help audit/context, but cannot be Evidence authority,
personalization, a learner characteristic, curriculum authority, or Safety
authority. Segment summaries, topic references, and aliases can never be the
sole source for Evidence; raw `source_refs` (message IDs and asset/source refs
where applicable) preserve lineage.

## 17.3 Candidate Event Capture

The primary Tutor call may emit hidden Candidate Event metadata alongside the student-facing response.

Example:

```json
{
  "meaningful_event": true,
  "candidates": [
    {
      "type": "learning_attempt",
      "concept_ref": "equivalent_fractions",
      "signal": "needed_light_hint"
    }
  ]
}
```

This avoids an additional event-extractor LLM call after every message.

## 17.4 End-of-Session Consolidation

At session close:

```text
Candidate Events
      +
Relevant Interaction Excerpts
      +
Thread Context
      ↓
Session Consolidation
      ↓
Validated Learning Events
      ↓
Evidence
      ↓
Current State + Pattern Engine
      ↓
Intelligence Card Refresh
```

The consolidation step should receive only the relevant excerpts needed to interpret Candidate Events accurately, not automatically the entire historical transcript.

Normal new-session context does not automatically load prior raw transcripts or
archived Segments. Historical conversation lookup and semantic archive retrieval
remain deferred on-demand work, not part of normal Tutor context.

## 17.5 Sessions Without Meaningful Learning

Every session remains stored.

If no meaningful learning/evidence/state change occurred:

- keep the normal session record,
- do not create unnecessary intelligence objects,
- do not create a full learning card.

If meaningful learning occurred, create an Intelligence Delta for that session.

---

# 18. Session Intelligence Delta

Do not store a duplicate full Learner Intelligence Card after every meaningful session.

Store a compact delta such as:

```json
{
  "session_id": "...",
  "added_states": [],
  "resolved_states": [],
  "patterns_created": [],
  "patterns_strengthened": [],
  "patterns_weakened": [],
  "patterns_resolved": [],
  "important_learning_changes": []
}
```

This creates a useful historical intelligence sequence without duplicating the entire current state.

Periodic full snapshots may be created for:

- important checkpoints,
- debugging/reprocessing boundaries,
- end of Grade,
- explicitly configured periodic analysis.

---

# 19. Learner Intelligence Card

## 19.1 Definition

The card represents:

> **What currently matters about Lina's learning for a better interaction now?**

It is a compact materialized state derived from events, evidence, current states, and patterns.

It is not:

- raw history,
- a complete Grade record,
- a transcript summary,
- a list of every concept,
- a permanent personality profile,
- a collection of arbitrary AI scores.

## 19.2 Recommended Card Sections

```text
CURRENT CONTEXT
- active Grade
- current school focus
- active thread context when relevant

CURRENT LEARNING STATE
- active difficulty
- active misconception
- open learning loops
- current retention concern

RELEVANT PATTERNS
- active/stable high-value patterns
- recent useful strategy patterns

RECENT CHANGES
- growing independence
- weakening old pattern
- recently resolved state

TEACHING INTELLIGENCE
- strategies that have recently helped
- strategies with weak recent value
```

The card need not expose these sections literally to Lina or the Parent UI; they define internal intelligence organization.

## 19.3 Card Compaction

The Current Intelligence Card must have a configurable size/token budget.

When over budget, the system prioritizes:

1. current active state,
2. current subject/context relevance,
3. recent high-value patterns,
4. stable relevant patterns,
5. important recent changes.

The system drops or excludes from runtime:

- resolved patterns,
- obsolete state,
- unrelated subject details,
- low-relevance historical entries,
- redundant descriptions.

Historical records remain elsewhere.

## 19.4 Card Update

The card is refreshed after meaningful end-of-session consolidation, not after every message.

---

# 20. Runtime Intelligence Selection

Even the Current Intelligence Card is not automatically injected in full into every Tutor turn.

The runtime flow is:

```text
Learner Intelligence Card
        ↓
Context Selector
        ↓
Relevant Intelligence Slice
        ↓
Tutor
```

A Math fraction question should not receive unrelated Science-specific patterns unless a pattern is genuinely cross-subject/global and relevant.

This is both an accuracy and cost requirement.

---

# 21. Tutor Consumption Rules

The Tutor uses learner intelligence as contextual guidance, not mandatory behavior.

Priority order:

```text
1. What Lina is demonstrating right now
2. Current Learning State
3. Relevant recent patterns
4. Relevant stable historical patterns
5. Curriculum context
6. Generic teaching strategy
```

## 21.1 Current Behavior Overrides History

> **Never personalize away demonstrated independence.**

If a historical pattern says Lina often needs decomposition, but she is currently solving the problem independently, the Tutor must not intervene merely because the pattern exists.

## 21.2 Patterns Are Priors, Not Rules

A pattern may make one strategy more likely to be useful. It does not force that strategy.

## 21.3 Personalization Should Be Felt, Not Announced

The Tutor should not routinely say:

> "Because you usually need visual explanations..."

It should simply adapt naturally:

> "Let's try looking at it another way."

Parent/Admin may inspect why the adaptation occurred.

---

# 22. Teaching Strategy and Method Intelligence

Teaching strategies are tracked as contextual interventions.

Example strategy record:

```text
strategy: concrete_fraction_representation
scope: equivalent_fractions
used_after: two unsuccessful conceptual attempts
outcome: enabled independent follow-up
```

Repeated outcomes may create patterns such as:

> Concrete representation has often helped when equivalent fractions are initially unclear.

Do not convert this into:

> Lina is a visual learner.

Strategy intelligence may weaken or resolve over time as Lina develops.

TeachingMethod records the pedagogical representation used by that intervention; it is not a synonym for TeachingStrategy. The primary Tutor call's semantic method choice or prior-method relation is not outcome Evidence. Repeated source-grounded outcomes may create `strategy_effectiveness` patterns, but they must stay scoped to the supported concept/context, such as “Concrete representation has often helped when equivalent fractions were initially unclear.” They must never become a fixed learning-style label. Historical method influence on later ranking is a later evidence-dependent capability, not an inference from a single current interaction.

---

# 23. Mastery, Confidence & Other Decision Views

## 23.1 Governing Principle

> **Mastery is a decision view over evidence, not learner memory.**

The same applies to evidence confidence and retention views.

The system may change its decision algorithm later without losing historical truth.

## 23.2 Parent-Facing Mastery States

Initial recommended vocabulary:

```text
Needs Support
Developing
Demonstrated
Strong
```

Exact mapping from evidence to these states belongs to a versioned decision policy.

Avoid displaying false precision such as:

```text
Mastery = 83.47%
```

## 23.3 Evidence Confidence

Recommended parent-facing states:

```text
Low
Medium
High
```

Confidence should be computed from factors such as:

- amount of meaningful evidence,
- recency,
- evidence quality,
- context diversity,
- independence,
- consistency/counter-evidence.

It does not describe Lina's confidence. It describes the system's confidence in the decision view.

## 23.4 Retention View

Recommended states may include:

```text
Not Enough Evidence
Needs Revisit
Developing Stability
Stable
```

Again, the mapping is derived and versioned.

## 23.5 Historical Understanding vs Current Recall

The system must be able to represent:

```text
Previously demonstrated understanding: yes
Current recall: needs refresh
Retention: needs strengthening
```

rather than rewriting history as if the original understanding never occurred.

---

# 24. Parent Challenges & Re-Validation

The Parent/Admin may challenge an intelligence conclusion but does not manually overwrite it.

Flow:

```text
Parent challenge/hypothesis
        ↓
Review request
        ↓
Relevant evidence inspection
        ↓
Optional future targeted learning opportunity
        ↓
New evidence
        ↓
Pattern/state updated normally
```

Example:

> Parent: "I think this reasoning pattern may only be true in fractions."

The system may mark the interpretation for scope re-validation rather than directly changing the learner profile to the parent's opinion.

---

# 25. Grade Transition Intelligence

Grade transition is simple and parent/admin controlled.

## 25.1 Trigger

A new Grade becomes active when the Parent/Admin uploads/activates the new Grade's books/content.

The system does not need to infer that Lina moved to a new Grade.

## 25.2 Transition Card

When moving from Grade 5 to Grade 6, carry a **compact transition card**, not the complete Grade 5 learner state.

It may include:

```text
stable important learning patterns
important unresolved foundational gaps
stable successful teaching strategies
important retention characteristics
important extended-learning capabilities
important unresolved observations
```

It should not contain:

- every Grade 5 concept,
- every mastery view,
- every session,
- every resolved temporary difficulty,
- the full Intelligence Card history.

Grade 6 is governed primarily by Grade 6 books and Grade 6 interactions.

If a Grade 6 lesson exposes an old foundational gap, the Tutor explains/refreshed it naturally and continues the Grade 6 lesson.

No complex cross-grade prerequisite engine is required in the initial architecture.

---

# 26. Historical Intelligence & Archive

The system keeps historical data for analysis, traceability, and possible future reprocessing.

The history may contain:

- raw sessions,
- messages,
- voice transcripts,
- original student images,
- events,
- evidence,
- session intelligence deltas,
- pattern history,
- resolved patterns,
- periodic snapshots,
- tutor adaptation events,
- Grade transition cards.

Historical information is **not runtime context by default**.

It can be queried later for:

- longitudinal analysis,
- auditing a conclusion,
- reprocessing with improved rubrics,
- investigating possible recurrence of a resolved pattern.

---

# 27. Multimodal Evidence Rules

Multimodal work is a first-class evidence source.

## 27.1 Text

Original Lina text is raw source.

A logical Multimodal Turn may combine text, speech transcript, image/assets,
raw asset references, and derived interpretation. The whole Turn may provide
conversation context, while original raw records remain source authority.

## 27.2 Voice

Current policy:

```text
Audio
→ STT
→ Transcript stored
→ Raw audio not retained
```

The transcript becomes the stored source record for current voice interactions.

No speaking/pronunciation assessment is assumed.

## 27.3 Handwritten Work

The original uploaded image is the evidence source.

Vision interpretation is derived.

If the important content is materially ambiguous, the Tutor should clarify before treating the ambiguous interpretation as strong evidence.

## 27.4 Drawings

Drawings may demonstrate:

- conceptual relationships,
- causal understanding,
- missing components,
- misconceptions,
- model/diagram understanding.

The system evaluates learning content, not artistic quality.

## 27.5 Annotated Original

Default visual response priority:

```text
Understand original
→ annotate original image first
→ continue teaching
```

The annotated image is a derived teaching artifact.

It must never overwrite or replace the original student work as evidence.

## 27.6 Clean Reconstruction

If annotation is insufficient, the system may produce:

- clean SVG,
- HTML visual,
- interactive learning artifact,
- simplified reconstructed diagram.

The reconstruction is a derived teaching artifact and cannot be treated as if Lina created it.

---

# 28. Interactive Artifact Evidence

Learning artifacts may produce meaningful events when Lina's interaction has educational significance.

Examples:

- correctly aligning equivalent fractions,
- placing an item correctly on a number line,
- assembling a science process in the correct sequence,
- adjusting a variable and explaining the observed effect,
- correcting a visual model after feedback.

Do not record meaningless interaction telemetry as learner intelligence.

Examples that normally do not become evidence by themselves:

- hovering,
- random clicking,
- opening the canvas,
- dragging without an educational outcome.

Each artifact should expose meaningful semantic interaction events rather than raw UI noise.

---

# 29. Traceability

Every important intelligence conclusion must be traceable downstream to evidence and upstream to original interaction sources.

Conceptually:

```text
Pattern
  ↓
Evidence refs
  ↓
Learning Event
  ↓
Session / Message / Student Image / Artifact Interaction
```

The Parent/Admin inspection path should be able to answer:

> **Why does the system believe this?**

without requiring a developer to manually search the database.

---

# 30. Processing Versioning

Derived intelligence must record how it was produced.

At minimum, processing lineage must support:

```text
processing_run_id
model/provider
prompt_version
schema_version
evidence_rubric_version
pattern_policy_version
decision_policy_version
timestamp
```

The implementation may normalize these through shared processing-run records rather than duplicating every field on every table.

The requirement is lineage, not a specific schema.

---

# 31. Reprocessing & Rebuildability

The architecture must support rebuilding intelligence from historical source data.

Canonical rebuild path:

```text
Raw Interactions
      ↓
Event Extraction vN
      ↓
Evidence Rubric vN
      ↓
Pattern Policy vN
      ↓
Current State / Patterns
      ↓
Learner Intelligence Card
      ↓
Decision Views
```

Use cases:

- evidence rubric improved,
- pattern rules improved,
- model changed,
- extraction prompt improved,
- a systematic classification error is discovered,
- a historical period needs re-analysis.

The system should support bounded reprocessing by date/Grade/session range where practical rather than requiring full-history rebuild every time.

Reprocessing creates versioned derived outputs and preserves the original raw source.

---

# 32. Observability & Human Audit

The system is expected to improve through real use and review.

The product owner and development process should be able to inspect:

- raw transcript/source interaction,
- Candidate Events,
- validated events,
- evidence outputs,
- pattern changes,
- current card changes,
- Tutor strategy used,
- Tutor model call,
- prompt/model version,
- input/output tokens,
- latency,
- estimated API cost,
- processing errors,
- reprocessing history.

The governing development loop is:

```text
Real usage
   ↓
Observe
   ↓
Audit against agreed rubric
   ↓
Identify systematic error
   ↓
Adjust rubric/prompt/policy
   ↓
Reprocess relevant history
   ↓
Compare result
```

The goal is not to guarantee that AI never produces an incorrect event or evidence item.

The goal is:

> **No important intelligence should be untraceable, irreparable, or impossible to rebuild.**

---

# 33. Human Audit Standard

When reviewing a sample of generated intelligence, evaluators should compare the system against this specification rather than personal intuition alone.

For each reviewed event/evidence item, ask:

1. Did a meaningful learning event actually occur?
2. Did the event description stay contextual rather than generalize about Lina?
3. Does each evidence dimension match the approved rubric definition?
4. Was support/independence interpreted correctly?
5. Was transfer truly tested or merely repeated practice?
6. Was self-correction genuinely self-initiated or prompted?
7. Is a retention event genuinely delayed enough to represent retention under current policy?
8. Did the event create/update a Current State appropriately?
9. Did the Pattern Engine apply deterministic policy correctly?
10. Is the resulting personalization useful without becoming a rigid label?

Audit disagreements should lead to rubric/policy refinement when they reveal systematic ambiguity.

---

# 34. Intelligence Invariants

These rules are non-negotiable unless explicitly changed by the project owner.

1. **Raw learner work remains the historical source.**
2. **Derived intelligence must be traceable and rebuildable.**
3. **A Candidate Event is not Evidence.**
4. **A single ordinary event does not create a stable learner pattern.**
5. **Current Learning State and Learner Patterns are different constructs.**
6. **Current behavior outranks historical personalization.**
7. **Patterns are teaching priors, not mandatory rules.**
8. **Patterns begin at the narrowest scope supported by evidence.**
9. **Pattern generalization requires evidence across wider contexts.**
10. **Old patterns may weaken, resolve, and disappear from Current Intelligence.**
11. **Resolved patterns remain historical and may be inspected if similar signals recur.**
12. **Retention failure does not erase previous demonstrated learning.**
13. **Mastery and confidence are derived Decision Views, not source truth.**
14. **Do not store arbitrary AI-generated percentages as learner facts.**
15. **Do not create psychological, personality, intelligence, or learning-style labels.**
16. **Teaching-strategy effectiveness is context-specific until evidence supports broader scope.**
17. **The Tutor may emit Candidate Events but does not directly declare stable patterns.**
18. **Frequency, recency, weighting, lifecycle, and scope promotion are governed by deterministic policy.**
19. **Normal conversation remains raw history and does not automatically enter Intelligence.**
20. **Multimodal AI reconstructions never replace Lina's original work as evidence.**
21. **Only meaningful artifact interactions become learning evidence.**
22. **The Current Intelligence Card must remain compact and relevance-driven.**
23. **Full historical intelligence is not injected into normal Tutor context.**
24. **Grade transition carries a compact intelligence card, not the previous Grade's full state.**
25. **No irreversible AI judgment is allowed in the Learning Intelligence architecture.**
26. **TeachingMethod selection/use is not evidence of effectiveness; an observable Student outcome and persisted project-owned method lineage are required.**
27. **A Learning Thread / `thread_id` is the session-local Segment identity; its metadata does not replace raw message or asset lineage.**
28. **Durable Conversation Topic and Segment metadata are navigation context only and create no learner conclusion, Evidence, personalization, Safety, or curriculum authority.**
29. **Normal Tutor context does not inject prior-session raw history or automatic historical semantic archive retrieval.**

---

# 35. Open Calibration Parameters

The following are intentionally **not fixed** until real Lina usage provides data.

They must be configurable/versioned rather than hardcoded across business logic.

## 35.1 Pattern Parameters

- minimum support before `candidate → active`,
- requirements for `active → stable`,
- evidence diversity threshold,
- recency decay curve,
- counter-evidence strength,
- weakening threshold,
- resolution threshold,
- recurrence lookup threshold,
- scope-promotion requirements.

## 35.2 Current State Parameters

- expiry by state type,
- resolution rules,
- recent-strategy usefulness window,
- open-loop persistence rules.

## 35.3 Session Parameters

- inactivity timeout,
- grace window,
- maximum consolidation excerpt size,
- maximum candidate-event count per session.

## 35.4 Intelligence Card Parameters

- target token/size budget,
- maximum active pattern count,
- maximum recent changes,
- ranking/compaction policy.

## 35.5 Decision View Parameters

- evidence-to-mastery mapping,
- evidence-confidence derivation,
- retention-view mapping,
- treatment of incomplete evidence.

## 35.6 Evidence Quality Parameters

- relative weight of independent vs guided performance,
- relative value of transfer,
- delayed evidence weighting,
- evidence-quality mapping from support/novelty/challenge.

These parameters are expected to evolve through observability, audit, and real use.

---

# 36. Initial Validation Scenarios

The implementation should support a compact set of scenario tests against this specification.

## Scenario A — Repeated Misconception

Lina makes a similar conceptual error across multiple relevant interactions.

Expected:

```text
meaningful events created
→ current misconception may become active
→ repeated evidence may create candidate pattern
→ Tutor adapts
→ later correction/resolution updates state and pattern normally
```

## Scenario B — Fast Understanding

Lina demonstrates understanding quickly and independently.

Expected:

```text
strong current evidence
→ no unnecessary repetition
→ optional deeper/transfer task
→ independence evidence captured
```

## Scenario C — Text Fails, Visual Helps

Text explanation is unsuccessful. Interactive/visual representation helps and Lina later applies the concept independently.

Expected:

```text
strategy outcome evidence
→ possible narrow strategy-effectiveness pattern
→ no "visual learner" label
```

## Scenario D — Old Difficulty Resolves

An old active pattern is followed by repeated strong recent independent successes.

Expected:

```text
old pattern weakens
→ resolves/supersedes when policy threshold is met
→ leaves Current Intelligence Card
→ remains historical
```

## Scenario E — Retention Failure

Lina previously demonstrated a concept and later cannot recall it after meaningful elapsed time.

Expected:

```text
prior understanding remains historical truth
+ retention_failure evidence
+ current revisit need
```

Not:

```text
old mastery erased
```

## Scenario F — Drawing/Handwriting Evidence

Lina submits original handwritten/drawn work.

Expected:

```text
original stored
→ vision interpretation derived
→ evidence linked to original
→ annotation/reconstruction stored separately
```

## Scenario G — Multi-Thread Session

One session contains Math, Science exploration, then Math again.

Expected:

```text
one technical session
→ multiple learning threads
→ events attached to correct thread/subject
→ no cross-topic evidence contamination
```

## Scenario H — Grade Transition

Parent/Admin activates Grade 6 books.

Expected:

```text
Grade 6 becomes active
→ Grade 5 remains archive
→ compact transition intelligence available
→ Grade 6 learning is driven by Grade 6 books/context
```

---

# 37. Definition of Done for the Learning Intelligence Core

The Learning Intelligence core is ready for real Lina use when all of the following are true:

1. Raw interaction sources are retained according to project policy.
2. The Tutor can emit Candidate Events without a separate extractor call per message.
3. Sessions consolidate automatically after inactivity.
4. Consolidation can produce structured validated events and evidence.
5. Evidence follows the approved categorical rubrics.
6. Current Learning State is distinct from long-term Patterns.
7. Pattern frequency, recency, counter-evidence, scope, and lifecycle are deterministic and versioned.
8. Patterns can weaken and resolve rather than accumulate permanently.
9. The Current Intelligence Card remains compact.
10. Tutor context receives only relevant intelligence.
11. Parent/Admin can inspect why an important conclusion exists.
12. Mastery/confidence views can be recalculated without rewriting historical evidence.
13. Historical raw interactions can be reprocessed with a newer rubric/policy.
14. AI processing lineage and token/API usage are observable.
15. Multimodal original work remains distinct from AI annotations/reconstructions.
16. The first Math vertical slice demonstrates that intelligence from one meaningful session can improve a later Tutor interaction without loading the full old transcript.

---

# 38. Relationship to Other Project Documents

## `PROJECT_REFERENCE.md`

Defines:

- product intent,
- user roles,
- learning philosophy,
- Tutor architecture,
- Content/Docling/RAG direction,
- multimodal interaction,
- interactive learning artifacts,
- Grade behavior,
- child safety and parent boundaries,
- overall architecture.

This document must remain consistent with it.

## `IMPLEMENTATION_PLAN.md`

Will define:

- implementation phases,
- concrete service/module boundaries,
- schema implementation choices,
- dependencies,
- build order,
- testing strategy,
- decision gate,
- what to build now vs later.

## `CHILD_SAFETY_POLICY.md`

Will define:

- non-overridable child-safety baseline,
- age-appropriate handling requirements,
- enforcement of Parent Learning Boundaries.

Learning Intelligence must not create or preserve prohibited psychological/personality inference merely because such information could theoretically be extracted.

---

# 39. Final Governing Principle

The subsystem should be judged by this question:

> **Can we explain what the system currently believes about Lina's learning, show the evidence that led there, observe how that belief changes over time, and rebuild it when our analysis improves?**

If yes, the Learning Intelligence architecture is working as intended.

If the system produces conclusions that cannot be traced, reviewed, recalculated, or corrected from the learning history, the implementation has violated this specification.
