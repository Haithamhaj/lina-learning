# Tutor / Canvas A/B deferred evaluation cases

These synthetic, non-learner cases are prepared for AB-V02 only. They are not
authorization to call a provider or a release claim.

| Case | Expected observable behavior |
| --- | --- |
| Pending status inquiry | A question such as "Where is the visual?" retains the current Run and produces no new CanvasBrief. |
| Meaningful representation change | A request to replace a number line with a grouping representation may create one bounded successor Run. |
| Supported scene step | A STEP/reveal action continues the active Scene and does not enqueue composition. |
| Learn | The next move may be direct explanation, modeling, practice, comparison, or exploration; it is not explanation-first. |
| Practice | When an attempt is the purpose, the Student receives a real opportunity to attempt; it is not labeled QUIZ by default. |
| Explicit visual request | A mental image alone does not claim to fulfill an external visible representation request. |
| Profile calibration | Age/Grade calibrates presentation, never mastery or ability. |

## Local deterministic acceptance retained for V01

The following cases are covered locally and do not require a model-quality
claim:

| Case | Required invariant |
| --- | --- |
| Pending Run settles during inference | A late `REPLACE_PENDING` is rejected as `STALE_BASE`; the settled Scene is preserved and no Job or Run is added. |
| Successor Run appears | A decision bound to Run A cannot supersede newer Run B. |
| Scene identity/version changes | A stale `REPLACE_SCENE` creates no Run; an unchanged Scene admits exactly one replacement with exact base lineage. |
| Failed Run gains a successor | A stale `RETRY` is rejected; retry remains valid only for the exact current failed Run. |
| Empty state changes before CREATE | A visual appearing after Tutor selection makes the old `CREATE` stale. |
| Daily initial load/reload | `PENDING`/`RUNNING` opens Canvas immediately and elapsed time derives from server `run_created_at`. |
| Existing Scene plus in-flight update | The current Scene remains usable while localized update copy is shown. |
| Completion/failure/connectivity | `COMPLETED + scene_ready` reloads Snapshot; terminal failure stops waiting; status-read failure uses connectivity copy and preserves known state. |
| Chat availability | Tutor streaming disables the composer; background Canvas composition alone does not. |

AB-V02 must fix the model/settings, a maximum request count and cost ceiling,
run variants blind where practical, and use only isolated synthetic fixtures.
