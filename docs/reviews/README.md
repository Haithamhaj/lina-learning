# Documentation Reviews

This is the small navigation and delivery index for Product Owner review, not a governing specification. Delivery convention approved on 2026-09-07.

- Publish safe task documentation to GitHub when submitting it for review.
- Keep one canonical copy at its existing path; link to it rather than duplicating specifications.
- Index task, canonical path, review status, revision date and short purpose.
- New standalone sanitized review summaries may use `docs/reviews/<TASK-ID>/` when needed.
- For the active Canvas Specialist track, each CS task uses one `docs/reviews/<TASK-ID>/IMPLEMENTATION_RECORD.md` created before code and completed before review.
- Keep DRAFT / AWAITING REVIEW / READY / DONE / ACCEPTED distinct. Publication does not grant migration/dependency/runtime approval beyond the explicit task state.
- Documentation publication does not authorize committing unrelated source code.
- Return actual commit SHA and commit-pinned GitHub file links in delivery responses. This index uses relative canonical links.
- Private raw evidence/secrets remain local; publish only sanitized review summaries/screenshots.

| Task | Canonical document | Review status | Revision date | Purpose |
|---|---|---|---|---|
| STUDIO-VISUAL-01 | [docs/STUDIO_VISUAL_EXPLANATION_SPEC.md](../STUDIO_VISUAL_EXPLANATION_SPEC.md) | ACCEPTED AS IMPLEMENTATION DIRECTION (decision 36) | 2026-09-07 | Broader hybrid visual design source. Later bounded Canvas Specialist execution is governed by the dedicated accepted contract below where details differ. |
| STUDIO-VISUAL-PROCESS-01 | [Accepted closure and gallery](STUDIO-VISUAL-PROCESS-01/VISUAL_CHECKPOINT_2.md) | DONE / ACCEPTED (decision 38) | 2026-09-07 | V1 Process foundation and prepared-data visuals accepted; existing ProcessView is protected for the first natural-composition production slice. |
| CANVAS-SPECIALIST-EXECUTION | [Execution contract](../CANVAS_SPECIALIST_EXECUTION_CONTRACT.md) | ACCEPTED | 2026-09-07 | Governs Tutor↔Specialist↔Application authority, Semantic Alignment, Visual Learner Context, one-call policy, Toolbelt boundaries and first Process slice. |
| CANVAS-SPECIALIST-PLAN | [Implementation plan](../CANVAS_SPECIALIST_IMPLEMENTATION_PLAN.md) | APPROVED EXECUTION PLAN | 2026-09-07 | CS-01→CS-07 sequencing; CS-01→CS-04 are accepted and CS-05 is READY. |
| CANVAS-SPECIALIST-ACCEPTANCE | [Acceptance & verification spec](../CANVAS_SPECIALIST_ACCEPTANCE_SPEC.md) | GOVERNING VERIFICATION SPEC | 2026-09-07 | Quality→Speed→Cost gates, evidence taxonomy, per-task acceptance matrix and documentation lifecycle. |
| CS-01 | [Implementation record](CS-01/IMPLEMENTATION_RECORD.md) | DONE / ACCEPTED | 2026-09-07 | Runtime Visual Learning Composer Skill and per-run capability-boundary reconciliation accepted; no model/dependency/runtime execution enabled. |
| CS-02 | [Implementation record](CS-02/IMPLEMENTATION_RECORD.md) | DONE / ACCEPTED | 2026-09-07 | Complete visual Toolbelt installed/proven behind isolated adapters; no production routing or Specialist execution enabled. |
| CS-03 | [Implementation record](CS-03/IMPLEMENTATION_RECORD.md) | DONE / ACCEPTED | 2026-09-07 | Tutor v10 Visual Order, Semantic Alignment, bounded Visual Learner Context and Frozen Composition Pack accepted; no Specialist execution enabled. |
| CS-04 | [Implementation record](CS-04/IMPLEMENTATION_RECORD.md) | DONE / ACCEPTED | 2026-09-07 | Accepted at `8de9a752b00998f6d1f2a2b24102ba49cf5a1b2a`: one bounded Canvas Specialist Worker/Gateway proposal runtime with durable lineage and no Scene acceptance; live Luna remains unverified because configuration was unavailable. |
| CS-05 | [Implementation record](CS-05/IMPLEMENTATION_RECORD.md) | IMPLEMENTED / AWAITING PRODUCT OWNER REVIEW | 2026-09-08 | Additive Process Scene acceptance/activation, protected ProcessView host, record-only operations and same-Tutor Runtime-03 relation provenance; CS-06 remains blocked. |

Historical Process evidence: [Checkpoint 1 report and gallery](STUDIO-VISUAL-PROCESS-01/VISUAL_CHECKPOINT.md).

For later CS tasks, create their `docs/reviews/CS-XX/IMPLEMENTATION_RECORD.md` before code and add a row when the task becomes the active review artifact. Do not promote the next task from this index alone; current execution authority remains `project-state/PROJECT_STATE.md` plus `project-state/DAILY_USE_RELEASE_TASKS.md`.

Accompanying records: [Studio plan](../STUDIO_IMPLEMENTATION_PLAN.md), [decision register](../DAILY_USE_RELEASE_DECISIONS.md), [current task overlay](../../project-state/DAILY_USE_RELEASE_TASKS.md), and [Project State](../../project-state/PROJECT_STATE.md).
