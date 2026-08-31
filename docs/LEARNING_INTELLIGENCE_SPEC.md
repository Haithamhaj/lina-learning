# Lina Personal Learning System

## LEARNING_INTELLIGENCE_SPEC.md

**Status:** Approved governing specification; **implemented / Full-System Acceptance completed / limited Real-Lina use observed / longitudinal real-use validation pending**  
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
- Segment semantic review,
- staged Segment findings,
- Session Intelligence Finalization / Session authority,
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

The detailed implementation may evolve, but it must preserve the contracts and invariants in this specification unless the Product Owner explicitly changes them.

## 1.1 Real-Use Verification Scope

Limited real Lina use has occurred: Lina herself participated in part of a real Tutor interaction, and the persisted interaction was subsequently continued and used during testing/calibration. This does not establish stable daily Lina use, a complete recurring Lina cross-session intelligence loop, or longitudinal personalization across multiple natural Lina sessions. Those remain separate validation horizons.

---

# 2. Core Intelligence Model

The canonical pipeline is:

```text
Raw Interaction
      ↓
Optional Provisional Candidate Hint
      ↓
Completed Learning Segment
      ↓
Segment Learning Review
      ↓
Staged Segment Findings
      ↓
Session Intelligence Finalization
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

The current accepted implementation follows the same authority model: Segment Review interprets completed learning episodes; Session Finalization is the deterministic durable activation boundary. Historical legacy Session Evidence generations remain auditable and compatible where required, but they are not the primary current semantic architecture.

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

A lightweight, optional, source-linked, auditable hint emitted during the
interaction indicating that something potentially meaningful may have happened.

A Candidate Event is **not** Evidence, is not a mandatory gate, and must not
directly update Current State, a stable Pattern, or personalization. Segment
Review may produce supported staged findings with zero Candidate IDs.

## 2.3 Validated Learning Event

A Session-authorized structured learning occurrence derived from one completed
Segment semantic review. Its conceptual lineage includes `session_id`,
`segment_id`, `segment_review_id`, optional `candidate_event_ids[]`, potentially
multiple `source_refs[]`, and `processing_run_id`.

The accepted implementation supports this Segment/Finding/Event/Evidence lineage for the current Segment-finalization path. Historical legacy rows remain separately auditable.

A Validated Learning Event describes **what happened in that context**, not a general conclusion about Lina.

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

A strong Session-authorized event may update Current Learning State only after
successful Session Intelligence Finalization.

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

An interaction or completed Segment contains a meaningful learning occurrence only when it can reasonably:

1. add information about Lina's understanding or learning behavior,
2. confirm existing intelligence,
3. challenge existing intelligence,
4. update current learning state,
5. reveal a teaching strategy outcome,
6. create or resolve an important learning loop.

Normal conversational activity is not intelligence merely because it occurred.
These Meaningful Event Rules govern semantic Segment Review and later
intelligence interpretation; they are not deterministic pre-review eligibility
criteria.

For misconception semantics: confusion alone, a bare wrong answer alone, and
an arithmetic slip alone do not establish a misconception. Explicit incorrect
reasoning may establish one. Segment Review may interpret reasoning distributed
across multiple turns; a later correction in the same Segment becomes
counter/corrective Evidence rather than erasing the original observation.
Turn-level `misconception_signal` remains provisional only.

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
| `support_change` | Required support materially increases or decreases | Segment Review / Session Finalization |
| `open_loop_created` | Important understanding remains unresolved | Segment Review / Session Finalization |
| `open_loop_resolved` | Previously open learning loop is resolved | Segment Review / Session Finalization |
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

This dimension evaluates the **teaching strategy/method outcome**, not Lina as a person.

| State | Definition |
|---|---|
| `not_evaluable` | No meaningful outcome can be linked to the strategy/method. |
| `ineffective` | The intervention did not improve the relevant learning state in that interaction. |
| `unclear` | Outcome is ambiguous or mixed. |
| `helped` | Observable improvement followed the intervention. |
| `enabled_independent_success` | The intervention was followed by meaningful independent understanding/application. |

Examples of representation/method identity include:

- concrete example,
- visual fraction representation,
- decomposition of a word problem,
- Socratic focusing question,
- worked example,
- interactive artifact,
- drawing/model request,
- change from symbolic to visual representation.

For teaching-representation effectiveness, **TeachingMethod** is the canonical method identity. It is distinct from TeachingStrategy, which governs the support/intervention flow. The existing `strategy_applied` and `strategy_outcome` taxonomy remains compatible: the existing `strategy_key` lineage may carry the canonical TeachingMethod identifier where the established pattern contract requires it.

Mode, Strategy, Method, and prior-method-relation are turn-level semantic routing/audit metadata from the same primary Tutor call, not Candidate Events, Evidence, or learner memory. Runtime validates their canonical values and persisted source lineage but does not infer their natural-language meaning. That method identity must be source-grounded in persisted project-owned Tutor-turn metadata, together with the bounded prior-turn/source lineage needed to connect the method to the later observable Student outcome. Segment Review interprets outcome only and must not invent a method identity. An immediate same-session method change after current confusion is contextual adaptation; repeated method outcomes are the separate, evidence-dependent basis for any stable `strategy_effectiveness` pattern.

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
school_relationship
source_modality
elapsed_since_related_evidence
same_session_or_delayed
concept_scope
artifact_used
teaching_method_used
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

Initial/current types include concepts such as:

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

Recent Learning Context is conversational context, not Evidence-derived Current Learning State. It may use relevant recent messages or topic metadata to help an ambiguous continuation such as “Continue.”

It does not represent where Lina is supposed to be in the curriculum, what she is required to study now, or what questions she is allowed to ask. The current question remains highest authority; relevance comes before recency.

Historical `current_school_focus` Current State rows remain preserved for audit but are excluded from runtime Learner Intelligence Card selection. **Current School Focus is not an active product authority.**

Optional Durable Conversation Topic metadata may assist bounded conversation navigation or audit, but it is neither Evidence nor Learner Intelligence and cannot create a learner conclusion. It does not directly update Current State, Patterns, the Intelligence Card, or personalization.

Likewise, Structured Segment State and conversation retrieval metadata are compact, session-local, source-linked, and rebuildable conversational context. They may reference raw messages or complete Exchanges, but are not Candidate Evidence, Learning Evidence, Current Learning State, Learner Pattern, or Learner Intelligence. They cannot create learner conclusions or bypass the protected Raw Interaction → completed Segment semantic review → Session-authorized Validated Learning Event / Evidence path. Candidate metadata may assist this path but is not required.

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

Resolution can occur through direct counter-evidence, successful independent application, explicit loop closure, deterministic expiry policy, or replacement by newer state.

Resolved state remains historically available but is removed from active runtime intelligence.

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

Semantically equivalent descriptions must map to the same normalized pattern where possible. A stable `pattern_key` or normalized taxonomy is preferred over free-form identity. Human-readable wording may evolve without changing identity.

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

Generalization is never automatic because wording sounds general.

> **Scope follows evidence. Evidence does not follow the desired scope.**

A pattern may shrink if later evidence shows the original scope was too broad.

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

- **Candidate:** emerging repeated signal not yet trusted for historical personalization.
- **Active:** enough relevant evidence to be a useful contextual prior.
- **Stable:** supported across sufficient time/context diversity; still not permanent.
- **Weakening:** recent relevant counter-evidence/improvement reduces usefulness.
- **Resolved:** no longer current enough for runtime Card; retained historically.
- **Superseded:** a newer scoped pattern explains the area more accurately.

---

# 15. Pattern Weighting Rules

Pattern strength/relevance is determined by deterministic policy, not free AI judgment.

The policy considers:

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

Exact coefficients are calibration parameters rather than fixed truth in this specification.

Recent strong counter-evidence may outweigh larger quantities of older evidence. Repeated near-identical evidence in one exercise set is weaker generalization support than comparable evidence across independent contexts.

---

# 16. Pattern Recurrence

Resolved patterns are absent from current runtime intelligence.

If a new event resembles a resolved historical pattern, historical context may be inspected, but a single new signal does not automatically reactivate the old pattern. Fresh evidence decides whether it returns.

---

# 17. Session & Thread Intelligence

## 17.1 Session Lifecycle

A session closes automatically after configurable inactivity plus grace. Exact timing is an implementation calibration parameter.

## 17.2 Learning Thread = Session-local Segment

A Learning Thread is the session-local contiguous Segment; `thread_id` is that Segment identity. It is not a third entity. A technical Session may contain several Segments as Lina changes topic or subject naturally.

A return to the same topic after an intervening Segment creates a new Segment. Optional Durable Conversation Topic may link navigation across Segments but is not Evidence, personalization, curriculum, or Safety authority.

## 17.3 Segment Completion and Candidate Capture

A prior Segment becomes complete whenever the governed transition successfully persists a new LearningSegment; Session closure completes the final Segment.

The primary Tutor call may emit Candidate Event metadata alongside the Student-facing response. This avoids an extra event-extractor call after every message. The hints remain provisional and are never the only route to intelligence.

## 17.4 Segment Learning Review and Session Intelligence Finalization

Structural reviewability is the deterministic pre-review gate. A Segment is reviewable when it is durably closed, has valid Session/Segment ownership lineage, and contains at least one persisted raw Student interaction assigned to that Segment.

This gate must not determine whether learning meaning occurred or require Candidate, Guided Check, TeachingMethod, Tutor response, concept, keyword, message length, or minimum Exchange count.

```text
Closed structurally reviewable Segment
      ↓
asynchronous Segment Learning Review of complete raw Segment history
      ↓
Staged findings (zero is valid; no personalization update)
      ↓
Session CLOSED + every structurally reviewable Segment accounted for
      ↓
compatible Review versions + provenance validation
      ↓
deterministic Session Intelligence Finalization
      ↓
Validated Learning Events / Evidence / downstream activation
```

Segment Review is semantic authority for the completed learning episode. Session Finalization is durable activation authority: deterministic by default, no broad semantic Session call after Segment Reviews by default, and no partial activation.

When a rubric logically requires authoritative historical comparison such as retention, Segment Review may receive bounded structured anchors. It does not receive a full prior transcript, broad learner profile, or arbitrary historical memory dump.

## 17.5 Sessions Without Meaningful Learning

Every Session remains stored. A structurally reviewable Segment may validly return `findings=[]`; that result creates no unnecessary intelligence.

---

# 18. Session Intelligence Delta

The architecture need not persist a duplicate full Learner Intelligence Card after every Session. Historical change may instead be represented through compact deltas/processing lineage and authoritative State/Pattern generations.

Any delta/snapshot mechanism remains derived and must preserve source authority and rebuildability.

---

# 19. Learner Intelligence Card

## 19.1 Definition

The Card answers:

> **What currently matters about Lina's learning for a better interaction now?**

It is a compact runtime projection derived from authorized Current State and Patterns. It is not raw history, a complete Grade record, transcript summary, permanent profile, or arbitrary AI scoring table.

## 19.2 Recommended Runtime Organization

Conceptually the Card may surface compact entries such as:

```text
RELEVANT CURRENT LEARNING STATE
- active difficulty / misconception / open loop when relevant

RELEVANT PATTERNS
- active/stable evidence-supported patterns matching the current question/context

RECENT MEANINGFUL CHANGES
- growing independence / weakening or resolved prior state when relevant

TEACHING INTELLIGENCE
- evidence-supported contextual method/strategy outcomes when relevant
```

**Current School Focus is not a Card authority.** Relevant current subject, current question, or conversational context may guide selection, but stale school-position metadata must not control the Card or Tutor.

## 19.3 Card Compaction

Card size is bounded. Prioritize current active state, direct current-question relevance, recent high-value patterns, stable relevant patterns, and important changes. Exclude resolved, obsolete, unrelated, or redundant entries from runtime while preserving history elsewhere.

## 19.4 Card Update

The Card is built/selected from Session-authorized intelligence only. Staged Segment findings do not enter it before Session finalization.

---

# 20. Runtime Intelligence Selection

Even the Card is not injected in full into every Tutor turn.

```text
Authorized Current State / Patterns
        ↓
Learner Intelligence Card projection
        ↓
Question/context relevance selection
        ↓
Relevant Intelligence Slice
        ↓
Tutor
```

A substantive unmatched current question should not inherit stale intelligence merely because it is recent. Current demonstrated behavior remains higher authority than historical personalization.

---

# 21. Tutor Consumption Rules

Priority order:

```text
1. What Lina demonstrates now
2. Current Learning State
3. Relevant recent intelligence
4. Relevant stable Patterns
5. Curriculum/reference context
6. Generic teaching policy
```

> **Never personalize away demonstrated independence.**

Patterns are priors, not mandatory Tutor rules. Personalization should be felt through useful support/representation rather than announced as a learner label.

---

# 22. Teaching Strategy and Method Intelligence

Teaching strategies are contextual interventions. TeachingMethod records the pedagogical representation used by that intervention and is distinct from support strategy.

The primary Tutor call's method choice or prior-method relation is not outcome Evidence. Repeated source-grounded Student outcomes may create `strategy_effectiveness` Patterns, but these must remain scoped to supported concept/context and never become fixed learning-style labels.

Historical method influence on later ranking is an evidence-dependent capability; do not infer stable preferences from a single interaction.

---

# 23. Mastery, Confidence & Other Decision Views

Mastery, evidence confidence, retention, independence, and strategy-effectiveness views are derived and versioned.

Parent-facing states may use interpretable categories such as `Needs Support`, `Developing`, `Demonstrated`, `Strong`, and evidence-confidence `Low / Medium / High`.

Avoid pseudo-precision such as `83.47% mastery` as if scientifically exact.

The system must be able to represent:

```text
Previously demonstrated understanding: yes
Current recall: needs refresh
Retention: needs strengthening
```

rather than rewriting history as if prior learning never occurred.

---

# 24. Parent Challenges & Re-Validation

Parent/Admin may challenge an intelligence conclusion but does not manually overwrite it.

A challenge may trigger Evidence inspection, scope review, or a future targeted learning opportunity. New Evidence updates state through the normal governed path.

---

# 25. Grade Transition Intelligence

Grade transition is Parent/Admin-controlled. When a new Grade is activated, carry a compact transition view of important stable/unresolved intelligence rather than the complete previous Grade runtime/history.

The next Grade is primarily governed by its own current interaction and Grade context. Missing prior foundations can be refreshed naturally without requiring a universal cross-grade prerequisite engine.

---

# 26. Historical Intelligence & Archive

Historical data remains available for traceability, longitudinal analysis, reprocessing, and investigating recurrence. It is **not normal runtime context by default**.

Normal new-session Tutor context does not inject prior-session raw transcripts or archived Segments. Historical lookup/archive semantic retrieval remains a separately gated seam.

---

# 27. Multimodal Evidence Rules

Multimodal work is an approved first-class Evidence source when the capability is implemented and authorized.

- **Text:** original Lina text is raw source.
- **Voice:** transcript is retained; raw audio is not retained under current approved direction after successful STT.
- **Handwriting/drawing/photo:** original image remains source; Vision interpretation is derived.
- **Ambiguity:** if uncertain interpretation can change Evidence meaning, clarify rather than guess.
- **Annotation/reconstruction:** derived teaching artifacts never replace original Student work.

Current multimodal production capability remains sequencing-gated; these rules govern it when promoted.

---

# 28. Interactive Artifact Evidence

Meaningful artifact interaction may become a learning occurrence when it demonstrates understanding, correction, transfer, or other approved learning meaning.

Opening, hovering, random clicking, or raw drag telemetry is not Evidence by itself. Artifact systems should emit semantic interaction events rather than treating UI noise as learner intelligence.

---

# 29. Traceability

Every important intelligence conclusion must be traceable downstream to Evidence and upstream to original interaction sources.

```text
Pattern / Current State / Decision View
  ↓
Evidence refs
  ↓
Learning Event
  ↓
Segment Review Finding / processing lineage
  ↓
Raw Student interaction / original asset
```

Parent/Admin inspection should eventually answer:

> **Why does the system believe this?**

without requiring a developer to manually reconstruct lineage.

---

# 30. Processing Versioning

Derived intelligence records how it was produced. Lineage supports, as relevant:

```text
processing_run_id
provider/model
prompt_version
schema_version
segment_review_schema_version
segment_review_prompt_version
segment_review_rubric_version
segment_review_policy_version
session_finalization_pipeline/policy
evidence_rubric_version
pattern_policy_version
decision_policy_version
timestamp
```

The requirement is complete lineage, not a specific duplication strategy.

---

# 31. Reprocessing & Rebuildability

Canonical rebuild path:

```text
Raw Interactions
      ↓
enumerate completed/reviewable Segments
      ↓
re-run/reuse Segment Reviews under selected versions
      ↓
stage complete Session generation
      ↓
atomic Session authority activation
      ↓
Current State / Patterns / Decision Views
      ↓
on-demand Learner Intelligence Card
```

Reprocessing may be bounded by date/Grade/Session scope. Prior generations remain auditable. Partial selected-scope failure must not replace a coherent previous authority.

---

# 32. Observability & Human Audit

The system improves through real use and review. Product/development audit should be able to inspect:

- raw transcript/source interaction,
- Candidate metadata,
- Segment and Segment Review lineage,
- staged findings and Review failures,
- Session authority/finalization generation,
- Events/Evidence,
- Current State/Pattern changes,
- Card selection,
- Tutor teaching decisions,
- AI execution/provider/model/usage/cost,
- reprocessing history.

Development loop:

```text
Real usage
   ↓
Observe
   ↓
Audit against governing rubric
   ↓
Identify systematic error
   ↓
Adjust rubric/prompt/policy
   ↓
Reprocess relevant history
   ↓
Compare result
```

> **No important intelligence should be untraceable, irreparable, or impossible to rebuild.**

---

# 33. Human Audit Standard

For reviewed Event/Evidence items, ask:

1. Did meaningful learning actually occur?
2. Did description remain contextual rather than generalize about Lina?
3. Does each Evidence dimension match the approved rubric?
4. Was support/independence interpreted correctly?
5. Was transfer truly tested?
6. Was self-correction self-initiated or prompted?
7. Is retention genuinely delayed/authorized by historical lineage?
8. Did Current State update appropriately?
9. Did deterministic Pattern policy apply correctly?
10. Is resulting personalization useful without becoming rigid?

Systematic audit disagreements should refine rubric/policy rather than create ad-hoc exceptions.

---

# 34. Intelligence Invariants

These rules are non-negotiable unless Product Owner explicitly changes them:

1. Raw learner work remains historical source authority.
2. Derived intelligence is traceable and rebuildable.
3. Candidate Event is not Evidence.
4. A single ordinary event does not create a stable Pattern.
5. Current State and Learner Patterns are distinct.
6. Current behavior outranks historical personalization.
7. Patterns are teaching priors, not mandatory rules.
8. Patterns begin at narrowest evidence-supported scope.
9. Pattern generalization requires wider-context Evidence.
10. Patterns may weaken/resolve and leave runtime while remaining historical.
11. Retention failure does not erase prior demonstrated learning.
12. Mastery/confidence are derived Decision Views, not source truth.
13. Do not store arbitrary AI percentages as learner facts.
14. No psychological/personality/intelligence/fixed learning-style labels.
15. TeachingMethod selection/use is not effectiveness Evidence.
16. Tutor may emit Candidate metadata but does not directly declare stable Patterns.
17. Frequency, recency, weighting, lifecycle, and scope promotion are deterministic/versioned.
18. Normal conversation remains raw history and does not automatically become Intelligence.
19. Multimodal AI reconstruction never replaces Lina's original work.
20. Only meaningful artifact interactions become Evidence.
21. Card stays compact and relevance-driven.
22. Full historical intelligence/transcripts are not injected into normal Tutor context.
23. Learning Thread / `thread_id` is session-local Segment identity.
24. Durable Conversation Topic and Segment metadata are navigation/context only, not learner/Safety/curriculum authority.
25. Segment Review is semantic authority for completed learning episodes.
26. Session Finalization is durable activation authority; no partial activation.
27. Candidate metadata is optional provisional context; no second learner-memory system is authorized.
28. Current School Focus is not an active learning-path or Card authority.
29. School relationship and Broad Subject are separate; absent school source is `UNKNOWN`, not automatically `EXTENDED`.
30. No second normal-turn classifier/summarizer/evidence call is introduced without explicit Product Owner approval and measured need.

---

# 35. Open Calibration Parameters

The following remain configurable/versioned and should evolve from real usage rather than be guessed permanently:

- Pattern support/promotion/diversity/recency/counter-evidence thresholds.
- Current State expiry/resolution windows.
- Session inactivity/grace and operational review capacity.
- Card entry/character budgets and relevance policy.
- Decision-view mappings.
- Evidence-quality weighting.
- Retention elapsed-time rules and authoritative-anchor requirements.

These are calibration parameters, not hidden learner truth.

---

# 36. Initial / Regression Validation Scenarios

The subsystem should preserve scenario coverage for:

- repeated misconception with later correction/counter-evidence,
- fast independent understanding,
- text fails / another representation helps without creating a learning-style label,
- old difficulty weakens/resolves,
- retention failure without rewriting prior learning,
- future drawing/handwriting Evidence preserving original source,
- multi-Subject/Segment Session without Evidence contamination,
- Grade transition using compact intelligence,
- Candidate-free raw-Segment-supported learning findings,
- irrelevant historical intelligence exclusion,
- current behavior overriding prior personalization,
- reprocessing with atomic authority replacement.

---

# 37. Implemented Core Status and Remaining Real-Use Validation

The Learning Intelligence core has passed Full-System Acceptance at the code/technical system level under the project's recorded evidence labels. The accepted implementation includes:

1. retained raw interaction sources according to project policy;
2. optional same-primary-call Candidate metadata;
3. structurally reviewable completed Segments;
4. asynchronous Segment Learning Review;
5. strict source/provenance validation;
6. staged findings that are inactive before Session authorization;
7. deterministic Session Finalization;
8. Session-authorized Events/Evidence;
9. Current State and deterministic Pattern lifecycle;
10. compact relevant Card projection;
11. later Tutor consumption of relevant intelligence in technical acceptance paths;
12. versioned reprocessing and authority replacement;
13. AI execution lineage and usage observability.

This acceptance must not be overstated. **Stable recurring Lina use, the complete naturally recurring cross-session Lina loop, and longitudinal personalization across multiple real Lina sessions remain validation work.** Limited real Lina interaction has occurred, but it is not equivalent to longitudinal validation.

Parent inspectability and deferred multimodal/product expansion are separate product-loop/capability horizons; their incompleteness does not mean the Learning Intelligence architecture itself is “implementation pending.”

---

# 38. Relationship to Other Project Documents

## `PROJECT_REFERENCE.md`

Defines stable product intent, user roles, learning philosophy, Tutor architecture, content/RAG direction, multimodal/artifact principles, Grade behavior, safety principles, product capability classification, and protected overall architecture.

This specification must remain consistent with it.

## `IMPLEMENTATION_PLAN.md`

Defines implementation direction, concrete service/module boundaries, dependencies, sequencing principles, testing strategy, and deferred complexity. Current execution state belongs in `PROJECT_STATE.md` / `TASKS.md`, not in this specification.

## `CHILD_SAFETY_POLICY.md`

Defines non-overridable child-safety baseline, age-appropriate handling, and Parent Learning Boundary semantics/enforcement.

Learning Intelligence must not create or preserve prohibited psychological/personality inference merely because such information could theoretically be extracted.

## `LEARNING_PRODUCT_ROADMAP.md`

Defines approved product-evolution sequencing and capability gates. A roadmap item does not become executable until explicitly promoted.

---

# 39. Final Governing Principle

The subsystem should be judged by this question:

> **Can we explain what the system currently believes about Lina's learning, show the Evidence that led there, observe how that belief changes over time, and rebuild it when our analysis improves?**

If yes, the Learning Intelligence architecture is working as intended.

If the system produces conclusions that cannot be traced, reviewed, recalculated, or corrected from learning history, the implementation has violated this specification.
