# STUDIO-ACT-EN-01 — Implementation Record

**Status:** implementation decision record; not acceptance evidence.

## Bounded fixture

`english_sentence_ordering_fixture_slate` /
`english-sentence-ordering-fixture-slate-v1` is a
Lina-authored controlled fixture. It is a short, ordinary English sentence
written for this bounded architecture check, has no external source or rights
dependency, and makes no English-curriculum or Grade-coverage claim.

| Stable token ID | Learner-visible label | Accepted position |
| --- | --- | --- |
| `tok-c820` | `Birds` | 1 |
| `tok-43bd` | `fly` | 2 |
| `tok-7f2c` | `over` | 3 |
| `tok-a91e` | `clouds` | 4 |

The only accepted order is `tok-c820` → `tok-43bd` → `tok-7f2c` →
`tok-a91e`; no alternative valid order exists in v1. The identifiers are fixed,
fixture-owned opaque values: they do not encode labels, canonical position, or
serialization order. The browser-visible Scene seed uses the opaque fixture
`english_sentence_ordering_fixture_slate` / `english-sentence-ordering-fixture-slate-v1`,
catalogue order `tok-7f2c` → `tok-a91e` → `tok-43bd` → `tok-c820`, and initial
current order `tok-a91e` → `tok-c820` → `tok-7f2c` → `tok-43bd`. Neither order,
nor lexical ID sorting, equals the server-owned accepted order.

The production sentence has no natural duplicate visible word. A focused
contract test therefore uses two independently identified tokens with the same
visible label, `the`, and proves they remain separate semantic objects. No
durable identity is based on token text, array position, or DOM content.

## Exact contracts

| Contract | Literal |
| --- | --- |
| English profile | `subject-profile-v2` |
| Activity | `sentence_ordering_workspace` / `sentence-ordering-workspace-activity-v1` |
| Renderer | `sentence-ordering-workspace` / `sentence-ordering-workspace-renderer-v1` |
| Scene schema | `sentence-ordering-workspace-scene-v1` |
| Token schema | `sentence-ordering-token-v1` |
| Fixture | `english_sentence_ordering_fixture_slate` / `english-sentence-ordering-fixture-slate-v1` |
| Reorder Action | `REORDER_TOKEN` / `sentence-ordering-workspace-reorder-v1` |
| Submit Action | `SUBMIT_CONFIGURATION` / `sentence-ordering-workspace-submit-v1` |
| Reorder Event | `english.sentence_ordering_workspace.token_reordered` / `sentence-ordering-workspace-event-v1` |
| Submit Event | `english.sentence_ordering_workspace.configuration_submitted` / `sentence-ordering-workspace-event-v1` |
| Reducer | `sentence-ordering-workspace-reducer` / `sentence-ordering-workspace-reducer-v1` |
| Submit validator | `sentence-ordering-workspace-submit-validator` / `sentence-ordering-workspace-submit-validator-v1` |
| Tutor-triggering interaction | `ENGLISH_SENTENCE_ORDERING_WORKSPACE_SUBMISSION` |

`REORDER_TOKEN` accepts exactly `token_id`, `from_index`, and `to_index`; it
is `RECORD_ONLY`. `SUBMIT_CONFIGURATION` accepts exactly `token_ids`, a
one-to-one permutation of the declared stable IDs, and is
`TUTOR_TRIGGERING`. The reducer independently requires an authoritative source
index and an exact submitted/current-Snapshot match. A structurally valid but
wrong order remains durable with bounded invalid feedback rather than becoming
a malformed request.

## Activation and renderer rule

Activation requires the persisted Student, LearningSession, StudioRuntime,
source Tutor message and Segment, a valid Workspace audit selecting these exact
English profile/activity/renderer identities, and an exact accepted Scene.
Repeated exact activation reuses that Scene without resetting progressed state.
The existing exact-activity dispatcher is extended in place; it is not
replaced by a generic activation framework.

Academic English tokens always render in an LTR token row. The outer
instruction/status surface may be English LTR or Arabic RTL, but it must not
reverse token sequence, stable identity, or focus order. The renderer uses
local React/DOM primitives with bounded pointer/touch and named-button
operations; it has no free-form input, `contenteditable`, or textarea.
