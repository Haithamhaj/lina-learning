# STUDIO-ACT-SCI-01 — Implementation Record

**Status:** implementation decision record; not acceptance evidence.

## Bounded fixture

`sand_water_filtration` / `sand-water-filtration-fixture-v1` is a
Lina-authored controlled fixture. It models four ordinary filtration steps,
does not reproduce external source content, and has no external licensing or
live-content dependency.

| Stable stage ID | Learner-visible English label | Learner-visible Arabic label |
| --- | --- | --- |
| `prepare-filter-funnel` | Set the filter paper in the funnel | جهّز القمع وورق الترشيح |
| `pour-sand-water-mixture` | Pour the sand-and-water mixture | اسكب خليط الرمل والماء |
| `allow-water-to-filter` | Let the water pass through the filter | اترك الماء يمر عبر المرشح |
| `collect-filtered-water` | Collect the filtered water | اجمع الماء المُرشَّح |

The server-owned fixture map has one accepted order, exactly as shown. There
are no alternative valid orders in v1. Scene seed data contains only the
fixture identity, stable stage identities, labels, and a deliberately
non-complete starting order; it never contains the accepted answer order.

## Exact contracts

| Contract | Literal |
| --- | --- |
| Science profile | `subject-profile-v2` |
| Activity | `process_sequence_workspace` / `process-sequence-workspace-activity-v1` |
| Renderer | `process-sequence-workspace` / `process-sequence-workspace-renderer-v1` |
| Scene schema | `process-sequence-workspace-scene-v1` |
| Reorder Action | `REORDER_STAGE` / `process-sequence-workspace-reorder-v1` |
| Submit Action | `SUBMIT_CONFIGURATION` / `process-sequence-workspace-submit-v1` |
| Reorder Event | `science.process_sequence_workspace.stage_reordered` / `process-sequence-workspace-event-v1` |
| Submit Event | `science.process_sequence_workspace.configuration_submitted` / `process-sequence-workspace-event-v1` |
| Reducer | `process-sequence-workspace-reducer` / `process-sequence-workspace-reducer-v1` |
| Submit validator | `process-sequence-workspace-submit-validator` / `process-sequence-workspace-submit-validator-v1` |
| Tutor-triggering interaction | `SCIENCE_PROCESS_SEQUENCE_WORKSPACE_SUBMISSION` |

`REORDER_STAGE` accepts exactly `stage_id`, `from_index`, and `to_index`; it
is `RECORD_ONLY`. `SUBMIT_CONFIGURATION` accepts exactly `stage_ids`, a
one-to-one permutation of the known stage IDs. The reducer moves a stage only
when the declared source index matches the authoritative Snapshot. Submission
persists the submitted sequence as source truth and validates it against the
server fixture map. A structurally valid but scientifically wrong sequence is
persisted with a bounded invalid result, not rejected as a system error.

## Activation and renderer

Activation requires the persisted Student, LearningSession, StudioRuntime,
source Tutor message and Segment, a valid Workspace audit selecting the exact
Science profile/activity/renderer versions, and an exact matching accepted
Scene. It reuses that exact Scene idempotently; it never resolves by source
message alone or chooses a latest Scene. A compact application-owned dispatcher
may call the existing Make-Ten and this Science exact-activity adapter after
normal Tutor-message persistence, so `services/tutor/runtime.py` remains free
of Science-specific routing.

The production renderer uses local React DOM/SVG primitives only. Pointer,
touch, and keyboard/button paths emit the same `REORDER_STAGE` operation.
The mock-labelled isolated review mount is presentation-only; server Snapshot
and Event state remain the production authority.
