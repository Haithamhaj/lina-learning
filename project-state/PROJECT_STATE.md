# Project state

## Current goal

Close the independently accepted Tutor pedagogy patch in one authorized local commit. Implementation and structural review are complete (`ACCEPT_PATCH_FOR_COMMIT`); comparative teaching quality is NOT YET EVALUATED and longitudinal learning benefit is NOT ESTABLISHED. Push, merge, deployment and the next Canvas production-use phase remain separately gated.

## Current reality

TUTOR-PEDAGOGY-REFINE-01 changes only the approved shared teaching block and one duplicate pedagogical sentence, with existing contract-test updates and an unchanged authoring-reference copy. Independent review reran 151 tests and inspected the 153 passing PostgreSQL results from implementation; it did not rerun those PostgreSQL tests. The existing instruction-provenance limitation is non-blocking; later evaluation must associate execution/message IDs, code version and actual instruction hash in the existing evaluation record. Request measurements show no additional context removal. See TASKS.md for exact scope, reference mapping, commands and evidence limits.

Lina remains a modular monolith. Primary Tutor owns teaching; the implemented Full-Power Hybrid Canvas composes typed, REUSE, ADAPT and CREATE representations and returns bounded Semantic Manifest/Studio state to the same Tutor. Immutable Build/ObjectStorage references remain authoritative; generated custom code runs only in the approved sandbox.

Selective CREATE, promotion, true REUSE and true ADAPT have desktop production-equivalent browser evidence. Selective REUSE demonstrated materially lower observed Luna time/cost than CREATE (7.189s/$0.006012 versus 55.588s/$0.032735 for the documented exact pair). These are engineering observations, not a general performance guarantee.

Canvas Development Review is an internal on-demand path: it lists experiences, captures a bounded independent review record, runs one advisory AI analysis, and preserves prior reports for comparison. It does not write Learning Intelligence, learner profile/personalization or Tutor memory. The first real report missed the known unequal grid-proportion defect, so AI review is not a correctness or release gate. See `docs/proposals/CANVAS-DEVELOPMENT-REVIEW.md`.

## Active decisions

- Primary Tutor owns teaching; Canvas composes and verifies representation only.
- GPT-5.6 Luna remains the runtime Canvas model. Independent verification and Development Review have no teaching, source-change or release authority.
- The current Canvas authoring budget is at most four total attempts: at most two CREATE attempts and at most three source-only refinements, with a shared 16-turn composition ceiling and one final-plan-only repair. Exhaustion does not reopen authoring.
- Parameters-only changes are REUSE; new capability requires ADAPT lineage. Promotion remains selective and owner-scoped.
- Immutable Build/ObjectStorage source and digest verification remain authoritative; Scenes hold bounded references/state.

## Protected areas

Primary Tutor authority; child safety and Parent Boundaries; owner/privacy isolation; Learning Intelligence/Evidence semantics; Model Gateway; original source/provenance; canonical Manifest and Studio event/replay authority; sandbox isolation.

## Active risks

Broad unrestricted production CREATE reliability is not accepted. Authenticated Daily use, deployment, traffic reliability and real learner learning benefit are not established by disposable-owner proofs. Runtime CREATE latency/cost remain material considerations. Existing promoted Versions are not retroactively certified by AI review or later checks.

## Next recommended action

Retain the accepted pedagogy patch locally; any comparative teaching evaluation requires separate authorization. Comparative teaching evaluation must retain clear, manageable, child-appropriate explanations and useful application of correction when appropriate, without forced retries. Paid/live evaluation requires separate authorization; structural checks do not establish learning improvement.

Begin a separately authorized controlled real-use / production-use phase only when the Product Owner requests it. It must reassess correctness/replay defects, authenticated Daily use, reliability and learning benefit without treating AI review as a correctness gate. Mobile was explicitly deferred and is not the current release gate; no model change is authorized.

## Critical references

- `docs/FULL-POWER-CANVAS-HARDENING.md`
- `docs/FULL-POWER-CANVAS-HARDENING_METRICS.json`
- `docs/FULL-POWER-CANVAS-01_ARCHITECTURE_IMPLEMENTATION_SPEC.md`
- `docs/proposals/CANVAS-DEVELOPMENT-REVIEW.md`
- `docs/PROJECT_REFERENCE.md`
- `TASKS.md`
