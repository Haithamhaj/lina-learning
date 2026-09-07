# Documentation Reviews

This is the small navigation and delivery index for Product Owner review, not
a governing specification. Delivery convention approved on 2026-09-07.

- Publish safe task documentation to GitHub when submitting it for review.
- Keep one canonical copy at its existing path; link to it rather than duplicating specifications.
- Index task, canonical path, review status, revision date and short purpose.
- New standalone sanitized review summaries may use `docs/reviews/<TASK-ID>/` when needed.
- Keep DRAFT / AWAITING REVIEW distinct from ACCEPTED. Publication does not grant design, migration, dependency or implementation approval.
- Documentation publication does not authorize committing unrelated source code.
- Return the actual commit SHA and commit-pinned GitHub file links in the delivery response. This index uses relative canonical links, not a self-referential commit SHA.
- Private raw evidence remains local; publish only sanitized review summaries.

| Task | Canonical document | Review status | Revision date | Purpose |
|---|---|---|---|---|
| STUDIO-VISUAL-01 | [docs/STUDIO_VISUAL_EXPLANATION_SPEC.md](../STUDIO_VISUAL_EXPLANATION_SPEC.md) | ACCEPTED AS IMPLEMENTATION DIRECTION (decision 36) | 2026-09-07 | Reviewed revision at 20b87f0 retained; only the separate early process visual checkpoint is authorized. No specialist enabled. |
| STUDIO-VISUAL-PROCESS-01 | [Checkpoint 2 report and gallery](STUDIO-VISUAL-PROCESS-01/VISUAL_CHECKPOINT_2.md) | VISUAL CHECKPOINT 2 / PRODUCT OWNER REVIEW | 2026-09-07 | Semantic radial SVG, focus/reveal/trace and narrow return; 11 actual previews. Six source files remain unstaged/uncommitted; not DONE or ACCEPTED. |

Historical process evidence: [Checkpoint 1 report and gallery](STUDIO-VISUAL-PROCESS-01/VISUAL_CHECKPOINT.md).

Accompanying records: [scoped Studio plan](../STUDIO_IMPLEMENTATION_PLAN.md), [decision register](../DAILY_USE_RELEASE_DECISIONS.md),
[current task overlay](../../project-state/DAILY_USE_RELEASE_TASKS.md), and
[Project State](../../project-state/PROJECT_STATE.md).
