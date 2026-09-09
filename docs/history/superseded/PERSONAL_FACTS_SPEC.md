# Personal Facts Specification

**Status:** Accepted Release-1 contract  
**Scope:** Governing Personal Facts contract for PF-02/PF-03 implementation.

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

`fact_key` is a stable semantic topic and `value` is the explicit asserted state. Example:

```text
category          = PREFERENCE
fact_key          = preference:drawing
value             = LIKE
display_statement = Likes drawing
```

Facts may expose `support_count`, `first_observed_at`, and `last_observed_at` as deterministic rollups of their Observations.

## Observations and Current Value

Every explicit repetition of the same semantic Fact creates an immutable, source-linked Observation. Differently worded or cross-language statements may support the same Fact when the extraction model semantically resolves them to the same known Fact identity.

Example:

```text
“I like drawing.”
“I really love drawing.”
“أنا أحب الرسم.”
```

may all support:

```text
preference:drawing = LIKE
```

Observation history is source authority. `support_count` must be rebuildable from Observations; a stored count is only a deterministic cache. Do not store confidence percentages.

A different explicit value for the same `fact_key` is another historical Fact, not an overwrite:

```text
preference:drawing = LIKE
preference:drawing = DISLIKE
```

At read time, the Fact with the latest explicit Observation for a Student and `fact_key` is current. Timestamp ties use deterministic ordering. Historical count never overrides a newer contrary assertion; older Facts and their Observations remain history.

If a Student later returns to an older value, the new statement should support that existing historical Fact rather than create a duplicate Fact. Example: LIKE → DISLIKE → later LIKE again adds a new Observation to the original LIKE Fact, making LIKE current again by recency.

## Categories and Qualification

The Release-1 controlled taxonomy is:

- `PREFERENCE`
- `FAVORITE`
- `ACTIVITY`
- `PET`
- `RELATIONSHIP`
- `SAFE_PERSONAL_CONTEXT`

Store only explicit, safe, durable Student assertions about the Student or her ordinary world. Examples include “I like drawing,” “My favorite color is purple,” “I play basketball every Thursday,” “My cat is called Luna,” and “Sara is my best friend.” Repeated discussion without an explicit assertion does not create a preference or trait.

Future plans, agenda/calendar events, and temporary states remain Conversation Context. `TEMPORAL_EVENT` is not a category.

Never store personality labels, psychological interpretation, diagnosis, intelligence labels, learning styles, inferred talent, mastery, misconceptions, academic strengths/weaknesses, Tutor strategy conclusions, transcript summaries, or Core Profile competitors such as authoritative age or Grade.

## Child Privacy

Do not duplicate passwords/credentials, precise home address or live location, contact details, financial/account information, highly sensitive medical/private information, sexual/private sensitive information, or safety-risk secrets into Personal Facts. Raw-history and Safety policies remain separate authorities.

## Data Contract

`PersonalFact`:

- `id`, `student_id`, `category`, `fact_key`, `value`, `display_statement`
- `support_count`, `first_observed_at`, `last_observed_at`

`PersonalFactObservation`:

- `id`, `personal_fact_id`, `student_id`, `source_message_id`
- `source_session_id` when useful, `observed_at`, `normalized_assertion` when useful

Do not duplicate complete transcripts. The source `LearningMessage` remains authoritative.

## Personal Memory Document

Each Student has one logical **Personal Memory Document**: a deterministic, rebuildable projection of current Personal Facts, grouped into useful categories such as Preferences, Activities, Favorites, Pets, Relationships, and Other Safe Personal Context.

It is not another authority and need not include the full historical evidence chain. Historical contrary Facts and Observations remain in Fact/Observation data. Do not physically shard the document in Release 1. No LLM is needed to regenerate it after every Session.

## PF-02 Extraction and Existing-Fact Reuse Contract

PF-02 is separate from the normal Tutor call and Segment Learning Review:

```text
Tutor Call              = teaching only
Segment Learning Review = Learning Intelligence only
Personal Facts          = dedicated asynchronous Session-level extraction
```

For each completed Learning Session, PF-02 runs one dedicated background Model Gateway call. Every accepted semantic decision must cite Student-authored `source_message_id` values; Tutor statements may provide conversational context but never support a Fact. The backend verifies source ownership and Student role.

The same PF model call must also receive a compact Student-scoped catalog of **existing Personal Fact identities**, including historical contrary values. The catalog should contain only what is needed for semantic identity reuse, for example:

```text
fact_id
category
fact_key
value
display_statement
```

It does not need prior Observation bodies, support counts, or timestamps for this purpose.

The model's semantic job is to decide whether the new explicit Student assertion:

1. **supports an existing Fact identity**, or
2. **proposes a genuinely new canonical Fact**.

This prevents the server from trying to infer semantic sameness with keywords and prevents differently phrased statements from creating duplicate Fact slots.

A suitable strict model output distinguishes:

- `SUPPORT_EXISTING`: references one supplied `existing_fact_id` plus grounded Student assertions.
- `ADD_NEW`: supplies a new canonical `category + fact_key + value + display_statement` plus grounded Student assertions.

No explicit output is required for `NOOP`; ineligible content may simply produce no accepted candidate.

The server remains authoritative for:

- existing Fact ID ownership and Student scope;
- source-message grounding and Student role;
- safety/privacy exclusions;
- category/key/value canonical validation;
- duplicate-source idempotency;
- Observation creation and deterministic rollups.

If the model proposes `ADD_NEW` for an exact Fact identity that already exists, the server must not create a duplicate; it may safely reconcile that exact identity to support/idempotent no-op.

There is **no second reconciliation model call** and no `UPDATE`, `SUPERSEDE`, or `INVALIDATE` state machine in Release 1.

The existing Session-capacity guard must account for both the completed Session input and the compact existing-Fact catalog. Do not silently truncate facts or source messages.

PF extraction is not a semantic Session Learning Intelligence summarizer and may not write Learning Events, Evidence, Current State, or Patterns. Its failure must not block Segment Review, and Segment Review failure must not block it.

## PF-03 Direction

PF-03 remains separately governed. Personal Facts are optional advisory Tutor context and never a teaching dependency.

The previously discussed simple lexical matcher is **not an accepted semantic-relevance solution**. PF-03 must be separately approved before implementation. Release 1 still protects these constraints:

- no extra normal Tutor-turn model call;
- no Personal Facts mixed into curriculum RAG by default;
- no unnecessary vector-memory platform;
- current raw Student conversation outranks stored Personal Facts;
- Student Core Profile remains authoritative for Core fields.

## Parent Inspection and Isolation

A linked Parent may later inspect statement, category, support count, first/last-observed times, and historical values for a `fact_key` when useful. Inspection does not make the Parent a Personal Fact source.

Every Fact, Observation, extraction run, semantic reuse decision, reconciliation action, document projection, Parent inspection, and future Tutor use is Student-scoped. A source message and any referenced existing Fact must belong to the same Student. Student A facts must never reconcile against, appear in the document/context of, or be visible to Student B or an unrelated Parent.
