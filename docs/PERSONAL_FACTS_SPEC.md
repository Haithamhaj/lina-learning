# Personal Facts Specification

**Status:** Accepted Release-1 contract
**Scope:** Contract only. PF-02 and PF-03 are not implemented by this document.

## Authority

```text
Student Core Profile = Parent/System-authoritative facts
Personal Facts       = explicit safe durable Student-asserted personal context
Learner Intelligence = evidence-backed learning-derived state
Conversation Context = raw/current conversational continuity
Safety               = safety authority
RAG                  = curriculum/reference grounding
```

These are separate authorities. Personal Facts never become Learning Evidence merely because they exist.

## Core Memory Model

Release 1 uses **Personal Fact + Personal Fact Observation History**. A Fact is one explicit, safe, durable Student assertion, identified by:

```text
student_id + category + fact_key + value
```

`fact_key` is a stable semantic topic and `value` is the explicit asserted state. For example:

```text
category          = PREFERENCE
fact_key          = preference:drawing
value             = LIKE
display_statement = Likes drawing
```

Facts may additionally expose `support_count`, `first_observed_at`, and `last_observed_at`.

## Observations and Current Value

Every explicit repetition of the same Fact creates an immutable, source-linked Observation. “I like drawing,” “I really like drawing,” and “I still love drawing” all support `preference:drawing = LIKE`; the resulting Fact has `support_count = 3`, its original first-observed time, and its latest last-observed time.

Observation history is source authority. `support_count` must be rebuildable from Observations; a later stored count is only a deterministic cache. Do not store confidence percentages.

A different explicit value for the same `fact_key` is another historical Fact, not an overwrite:

```text
preference:drawing = LIKE
preference:drawing = DISLIKE
```

At read time, the Fact with the latest explicit Observation for a Student and `fact_key` is current. Timestamp ties use deterministic ordering. Historical count never overrides a newer contrary assertion; older Facts and their Observations remain history.

## Categories and Qualification

The Release-1 controlled taxonomy is:

- `PREFERENCE`
- `FAVORITE`
- `ACTIVITY`
- `PET`
- `RELATIONSHIP`
- `SAFE_PERSONAL_CONTEXT`

Store only explicit, safe, durable Student assertions about the Student or her ordinary world. Examples include “I like drawing,” “My favorite color is purple,” “I play basketball every Thursday,” “My cat is called Luna,” and “Sara is my best friend.” Repeated football discussion without an explicit assertion does not create `preference:football = LIKE`.

Future plans, agenda/calendar events, and temporary states remain Conversation Context: “I’m going to Jeddah next weekend,” “I have an exam tomorrow,” “I’m going to the club Thursday,” and “I’m tired today” are not Personal Facts. `TEMPORAL_EVENT` is not a category.

Never store personality labels, psychological interpretation, diagnosis, intelligence labels, learning styles, inferred talent, mastery, misconceptions, academic strengths/weaknesses, Tutor strategy conclusions, transcript summaries, or Core Profile competitors such as authoritative age or Grade. “I’m shy” is conversation-only. “I’m bad at math” is conversation-only; Learning Intelligence requires independent learning Evidence. A conflicting claimed age or Grade does not create a competing Personal Fact authority.

## Child Privacy

Do not duplicate passwords/credentials, precise home address or live location, contact details, financial/account information, highly sensitive medical/private information, sexual/private sensitive information, or safety-risk secrets into Personal Facts. Raw-history and Safety policies remain separate authorities.

## Proposed Data Contract

`PersonalFact`:

- `id`, `student_id`, `category`, `fact_key`, `value`, `display_statement`
- `support_count`, `first_observed_at`, `last_observed_at`

`PersonalFactObservation`:

- `id`, `personal_fact_id`, `student_id`, `source_message_id`
- `source_session_id` when useful, `observed_at`, `normalized_assertion` when useful

Do not duplicate complete transcripts. The source `LearningMessage` remains authoritative.

## Personal Memory Document

Each Student has one logical **Personal Memory Document**: a deterministic, rebuildable projection of Personal Facts and Observations, grouped into useful current categories such as Preferences, Activities, Favorites, Pets, Relationships, and Other Safe Personal Context.

It is not another authority and need not include the full historical evidence chain. Historical contrary Facts and Observations remain in Fact/Observation data. Do not physically shard the document in Release 1. PF-02 may choose on-demand construction or a cache using the simplest existing seam; it must not use an LLM after every Session.

## PF-02 Extraction and Reconciliation Contract

PF-02 is separate from the normal Tutor call and Segment Learning Review:

```text
Tutor Call             = teaching only
Segment Learning Review = Learning Intelligence only
Personal Facts          = dedicated asynchronous Session-level extraction
```

For each completed Learning Session, PF-02 will run one dedicated background Model Gateway call over the completed Session conversation. Every accepted candidate must cite Student-authored `source_message_id` values; Tutor statements never become Personal Facts. The backend verifies source ownership and Student role.

PF extraction is not a semantic Session Learning Intelligence summarizer and may not write Learning Events, Evidence, Current State, or Patterns. It must not run per Tutor turn, per Segment, or inside Segment Review. Its failure must not block Segment Review, and Segment Review failure must not block it.

Reconciliation is deterministic and has only:

- `ADD`: new `(student_id, fact_key, value)` creates a Fact and first Observation.
- `SUPPORT`: an exact Fact creates another Observation, refreshes `last_observed_at`, and derives/increments `support_count`.
- `NOOP`: transient, inferred, sensitive/prohibited, Core-Profile-conflicting, ungrounded, or otherwise ineligible candidate.

A different explicit value for an existing `fact_key` is another `ADD`. There is no reconciliation LLM call and no `UPDATE`, `SUPERSEDE`, or `INVALIDATE` state machine in Release 1. After reconciliation, the Personal Memory Document refresh is deterministic.

## PF-03 Retrieval Direction

PF-03 remains later. Personal Facts are optional, advisory Tutor context, never a teaching dependency. The approved direction is:

```text
Student-scoped PostgreSQL lookup
→ current Fact per fact_key
→ deterministic lexical/key/statement relevance
→ relevance, then recency, then support_count
→ small fact and character budgets
→ zero Facts when nothing is clearly relevant
```

Do not use a vector Personal Facts index, Fact embeddings, curriculum-RAG integration, or an extra Tutor-turn model call.

## Parent Inspection and Isolation

A linked Parent may later inspect statement, category, support count, first/last-observed times, and historical values for a `fact_key` when useful. Inspection does not make the Parent a Personal Fact source.

Every Fact, Observation, extraction run, reconciliation action, document projection, Parent inspection, and future Tutor selection is Student-scoped. A source message must belong to the same Student. Student A facts must never reconcile against, appear in the document/context of, or be visible to Student B or an unrelated Parent.
