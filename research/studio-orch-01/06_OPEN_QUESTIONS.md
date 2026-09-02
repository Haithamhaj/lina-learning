# STUDIO-ORCH-01 — Open Questions Register (Reclassified)

**Status:** Research only. This is a decision/proof agenda, not an architecture
decision or implementation authorization.

## Facts

The Product Owner has clarified that Canvas-specialist calls may be evaluated
and later approved when quality justifies latency/cost; separate Tutor and
Canvas models/providers are allowed in principle; Canvas is first-class Student
input; Tutor requires complete meaningful Canvas observability; structured
practice/quiz interaction may occur on Canvas; and Studio is learning-first,
not pressure Exam Mode.

Those are no longer binary permission questions. The unresolved work is to
define the bounded eligibility, state, persistence, evaluation, and adoption
contracts that preserve those decisions.

## Assumptions

No current Studio-shell visual proves learning value, provider quality, Canvas
safety, or multi-agent benefit. No external framework/package is approved by
this register.

## Risks

If questions below are silently resolved in UI or prototype code, Lina can
accidentally acquire an unversioned Studio protocol, hidden agent authority, or
unreconstructable learner history.

## Contradictions

The system must keep complete meaningful Canvas history available to Tutor while
not replaying the complete history in every model prompt. It must permit
specialist quality where warranted while protecting routine first-token latency
and the existing normal Tutor path.

## Options

Synthesis may recommend a bounded proof, a state/protocol design spike, a
package evaluation, or retention of deterministic renderer baseline. It may not
treat the permission clarifications as approval for a specific runtime.

## Blocking before Synthesis

1. **First proof use case:** which exact learning task, learner outcome, and
   comparison measure establish Canvas value? Candidate examples are make-ten,
   fraction comparison, Canvas-first geometry, or structured practice.
2. **Specialist eligibility rule:** what observable conditions make a visual
   request complex enough for a Canvas model rather than typed renderer?
3. **Latency/cost envelope:** what added first-token, Canvas-ready, rich-ready,
   and per-turn cost thresholds are acceptable for the proof?
4. **State/event contract:** what minimal event families, scene snapshot,
   source-turn lineage, version/idempotency/cancellation rules, and
   observation-watermark behavior are needed?
5. **Persistence depth:** what is durable versus derived; how long is semantic
   Studio history retained; how does the full-history query boundary authorize
   and redact older events?

## Nonblocking

1. Which first renderer visual primitives, tokens, and interaction affordances
   form the Studio design system?
2. What narrow-screen representation preserves a desktop-first Studio without
   treating mobile as the primary constraint?
3. Which Arabic/English/mixed-direction fixture set verifies each renderer?
4. Which operational dashboards are needed for job latency, stale rejection,
   renderer failure, and content-free lifecycle tracing?
5. What read-only history/navigation can be safely shown to learners later?

## Requires Product Owner Decision

1. The first proof use case and success criterion.
2. The initial specialist eligibility, time, and cost thresholds.
3. The initial persistence/retention boundary for semantic Studio events and
   snapshots.
4. Whether the first protocol proof may expose a dedicated Studio feed, use a
   small terminal extension, or remain server-internal/read-model only.
5. Whether to promote a specific package evaluation (A2UI, AG-UI, OpenMAIC DSL
   or renderer, tldraw) after Synthesis.

## Requires Proof Spike

1. The application can reconstruct full meaningful history while Tutor receives
   current snapshot plus all events since its observation watermark and can query
   older history when needed.
2. A typed renderer improves a concrete learner task without inventing Tutor
   content or creating learning evidence from visual clicks.
3. A specialist ScenePlan, if eligible, improves that same task enough to earn
   latency/cost against the typed control.
4. Source-turn/revision/idempotency/cancel rules survive delta, terminal,
   reload, specialist failure, and a new Student turn.
5. Keyboard/focus/screen-reader and Arabic/English/mixed direction remain usable
   in the first Canvas renderer and structured practice.

## Requires Real-Use Evidence

1. Learners use the Canvas to understand or act, not only to admire a visual.
2. Tutor/Canvas coordination reduces confusion or improves observable guided
   success without increasing learner dependence.
3. Parents understand that Studio state is not stable assessment, Evidence, or
   Safety authority.
4. The experience remains calm, comprehensible, and robust on realistic devices,
   networks, and learner language patterns.

## Recommendations

### Maintain a threshold-based synthesis agenda

- **Recommendation:** Use this register to make the Synthesis choose thresholds,
  a proof use case, and a bounded contract rather than reconsidering already
  clarified permission principles.
- **Reason:** It converts broad approval into testable architecture decisions.
- **Expected impact:** A small, measurable next step without accidental runtime
  expansion.
- **Mandatory / Optional:** Mandatory process guardrail.
- **Priority:** P0.
- **Direct view:** Do not promote any item to implementation before Synthesis
  and explicit task promotion.
- **Risk of ignoring:** Permission becomes mistaken for architecture approval.
- **Confidence:** High.
