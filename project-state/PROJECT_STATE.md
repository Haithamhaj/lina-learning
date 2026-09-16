# Project state

## Current goal

Tutor/Canvas A+B local repair is complete and approved as a local evaluation candidate on `codex/tutor-canvas-ab-01`. The baseline remains `b909e2d8c0878453604d5213cb349dd71651d8db`; a package-only local commit is authorized, while push, merge, deployment, production data access, and paid/live model evaluation remain unauthorized.

## Current reality

The A/B branch now has the versioned Canvas composition view, reload/reconnect recovery, durable `run_created_at` ordering, localized Daily waiting/update/failure states, and a server-owned v12 decision base for Chat and Studio-interaction Canvas changes. Admission revalidates the exact Run and Scene identity/version under the existing Runtime lock and rejects stale CREATE/REPLACE/RETRY decisions as `STALE_BASE` without enqueueing or superseding newer work. Historical v11 records retain their prior reader/admission behavior.

Local verification on 2026-09-16 produced `1483 passed, 4 failed, 12 skipped`; the four failures are the same baseline-known failures in DB inventory, migration-head preflight, scheduled Grade, and Personal Facts reconciliation. TypeScript typecheck, 21 focused frontend tests, the synthetic-Clerk production build, repository-truth check, and diff check pass. These results establish deterministic contract/behavior closure only; they do not establish real-Luna teaching quality.

Lina remains a modular monolith. Primary Tutor owns teaching; the implemented Full-Power Hybrid Canvas composes typed, REUSE, ADAPT and CREATE representations and returns bounded Semantic Manifest/Studio state to the same Tutor. Immutable Build/ObjectStorage references remain authoritative; generated custom code runs only in the approved sandbox.

Selective CREATE, promotion, true REUSE and true ADAPT have desktop production-equivalent browser evidence. Selective REUSE demonstrated materially lower observed Luna time/cost than CREATE (7.189s/$0.006012 versus 55.588s/$0.032735 for the documented exact pair). These are engineering observations, not a general performance guarantee.

Canvas Development Review is an internal on-demand path: it lists experiences, captures a bounded independent review record, runs one advisory AI analysis, and preserves prior reports for comparison. It does not write Learning Intelligence, learner profile/personalization or Tutor memory. The first real report missed the known unequal grid-proportion defect, so AI review is not a correctness or release gate. See `docs/proposals/CANVAS-DEVELOPMENT-REVIEW.md`.

## Active decisions

- Primary Tutor owns teaching; Canvas composes and verifies representation only.
- GPT-5.6 Luna remains the runtime Canvas model. Independent verification and Development Review have no teaching, source-change or release authority.
- The current Canvas authoring budget is at most four total attempts: at most two CREATE attempts and at most three source-only refinements, with a shared 16-turn composition ceiling and one final-plan-only repair. Exhaustion does not reopen authoring.
- Parameters-only changes are REUSE; new capability requires ADAPT lineage. Promotion remains selective and owner-scoped.
- Immutable Build/ObjectStorage source and digest verification remain authoritative; Scenes hold bounded references/state.
- Canvas change intent remains model-semantic, while Run/Scene identity and stale-decision authority remain server-owned internal metadata.
- Daily uses the Studio feed as the primary Snapshot path; two-second composition polling supports recovery/wait state, and the elapsed display is derived from server `run_created_at` without percentages or ETA.

## Protected areas

Primary Tutor authority; child safety and Parent Boundaries; owner/privacy isolation; Learning Intelligence/Evidence semantics; Model Gateway; original source/provenance; canonical Manifest and Studio event/replay authority; sandbox isolation.

## Active risks

Broad unrestricted production CREATE reliability is not accepted. Deployment, traffic reliability and real learner learning benefit are not established by disposable tests or a synthetic-key build. Runtime CREATE latency/cost remain material considerations. AB-V02 real-Luna pedagogy evaluation is still blocked and not run. Existing promoted Versions are not retroactively certified by AI review or later checks.

## Next recommended action

Preserve the A/B branch and worktree for the separately authorized AB-V02 real-Luna evaluation and authenticated browser acceptance. No local deterministic result establishes teaching quality or production readiness.

## Prior baseline next action

Use only the verified published origin/main baseline for a separately authorized deployment task. `ui/refine-01c`: PARTIALLY_PORTED_FOR_PILOT; layout/Canvas hide-reopen deferred. FE-02: PROTOTYPE_OR_HISTORICAL. Both branches remain preserved. Authenticated visual verification is not established. See `TASKS.md` for exact scope and fresh evidence. Any comparative teaching evaluation requires separate authorization. Comparative teaching evaluation must retain clear, manageable, child-appropriate explanations and useful application of correction when appropriate, without forced retries. Paid/live evaluation requires separate authorization; structural checks do not establish learning improvement.

Begin a separately authorized controlled real-use / production-use phase only when the Product Owner requests it. It must reassess correctness/replay defects, authenticated Daily use, reliability and learning benefit without treating AI review as a correctness gate. Mobile was explicitly deferred and is not the current release gate; no model change is authorized.

## Critical references

- `docs/FULL-POWER-CANVAS-HARDENING.md`
- `docs/FULL-POWER-CANVAS-HARDENING_METRICS.json`
- `docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md`
- `docs/proposals/CANVAS-DEVELOPMENT-REVIEW.md`
- `docs/PROJECT_REFERENCE.md`
- `TASKS.md`
- `docs/TUTOR_CANVAS_AB_EVALUATION_CASES.md`
