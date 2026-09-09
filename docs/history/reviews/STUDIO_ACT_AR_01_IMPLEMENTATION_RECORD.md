# STUDIO-ACT-AR-01 — Implementation Record

**Status:** DONE / ACCEPTED — Product Owner acceptance closure on 2026-09-06.
The evidence limits recorded below remain part of this acceptance; it is not a
deployment, natural live-model selection, physical-device, or real-Lina claim.

## Bounded design

One project-authored, rights-safe architectural fixture is implemented; it makes
no Grade or curriculum-coverage claim. The learner-visible instruction is:

> رتّب الكلمات لتكوين الجملة التي تبدأ بالفعل وتصف أن الطالبة تكتب الدرس.

The tokens are `تكتبُ` (`tok-6d3a`), `الطالبةُ` (`tok-f18c`), and `الدرسَ`
(`tok-2b7e`). The noncanonical initial order is `tok-f18c → tok-2b7e →
tok-6d3a`. The accepted configurations are `tok-6d3a → tok-f18c →
tok-2b7e` (VSO) and `tok-6d3a → tok-2b7e → tok-f18c` (VOS). The unchanged
instruction constrains a verb-initial sentence, not the relative subject/object
order. The supplied nominative/accusative endings preserve those roles in VOS.
The earlier single-answer claim in this unaccepted draft was incorrect and was
corrected with a failing behavioral test. No historical accepted ARABIC v1
profile was changed. Other arrangements are not labelled generally ungrammatical.
IDs are opaque and independent of words,
order, and grammatical role; duplicate visible labels would remain distinct
objects under the contract, although this fixture has none.

## Exact contracts

| Layer | Version/key |
| --- | --- |
| Profile | `ARABIC / subject-profile-v2` (v1 unchanged) |
| Activity / renderer | `arabic_sentence_ordering_workspace / arabic-sentence-ordering-workspace-activity-v1`; `arabic-sentence-ordering-workspace / arabic-sentence-ordering-workspace-renderer-v1` |
| Seed / tokens | `arabic-sentence-ordering-workspace-scene-v1`; `arabic-sentence-ordering-token-v1` |
| Fixture | `arabic_sentence_ordering_fixture_orchid / arabic-sentence-ordering-fixture-orchid-v1` |
| Actions | `REORDER_TOKEN` record-only; `SUBMIT_CONFIGURATION` Tutor-triggering |
| Reducer / validator | `arabic-sentence-ordering-workspace-reducer-v1`; `arabic-sentence-ordering-workspace-submit-validator-v1` |

The server owns the accepted orders. The browser seed carries only fixture
identity, token catalogue, and deterministic noncanonical current order—never
an answer field or canonical-order metadata.

## Integration and direction

`services/studio/arabic_sentence_ordering_activation.py` is an exact,
source-lineage/idempotency-preserving adapter registered in the existing
activation loop. The accepted Daily `StudioRendererHost` adds one exact Arabic
contract and consumes only the server-projected active Scene/seed plus Snapshot
state. Arabic reading order is RTL; named controls operate on the current
semantic token array, and free-form language remains Chat-only. This satisfies
Section 22.7 by exercising Arabic academic content, Arabic token identity, RTL
presentation, and unchanged Studio state/transport/orchestration boundaries.

## Corrections and current evidence

The fixed-fixture client reader now requires the exact three-entry catalogue,
including each ID-to-visible-text association, plus a complete unique current
order. It remains deliberately independent of the server-only accepted order.
The Arabic workspace now uses the established pointer-capture lifecycle:
pointer/touch pickup from the visible token, geometry-based destination lookup,
cancel/lost-capture cleanup, and the same typed reorder operation as its named
keyboard buttons. It declares `lang="ar"` and restores a focused button after
server reconciliation.

Current verification and browser evidence are recorded in
`output/playwright/arabic-acceptance-20260906/`. See `acceptance-evidence.md` and
the completion checklist for final disposition. No prior English or FE-02
artifact is presented as fresh Arabic evidence.

## Scope limits

No grammar engine, curriculum, generic text/drag system, new Router/feed/client
reducer/session type, Canvas Specialist, extra model call, or answer-key browser
metadata is introduced. Runtime-03 remains the sole submission continuation;
record-only reorders do not create a Tutor execution.
