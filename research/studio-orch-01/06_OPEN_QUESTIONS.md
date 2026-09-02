# STUDIO-ORCH-01 — Open Questions Register

**Status:** Research only. This register intentionally records unresolved
questions; it makes no architecture decision and authorizes no implementation.

## Facts

The existing Tutor response contract can supply terminal text, suggested
actions, guided checks, and structured segment state, but it has no Canvas scene
or patch contract. The project simultaneously protects the normal
one-primary-Tutor-call baseline and requires expandable visual learning
artifacts. Those facts make explicit Product Owner and evidence gates necessary.

## Assumptions

No current uncommitted Studio shell visual validates learning value, provider
capability, Canvas safety, or multi-agent benefit.

## Risks

Prematurely resolving an open question in UI code could turn a presentational
experiment into a hidden durable protocol, second Tutor, or new safety surface.

## Contradictions

The main tension is not whether a Workspace is desirable; it is how much
semantic authority, latency, and persistence it may have while remaining one
coherent Tutor-guided experience.

## Options

The Synthesis may recommend a bounded proof, a design/protocol spike, a
provider evaluation, or retaining the one-call deterministic-renderer baseline.
None is selected here.

## Blocking before Synthesis

1. What exact learner outcome makes a Canvas update valuable rather than visual
   decoration, and how will the proof measure it?
2. Which authoritative representation should a future Canvas consume first:
   terminal Tutor text/actions/check, `structured_segment_state`, or a new
   versioned Studio projection?
3. Can the current single Tutor output semantically plan the first bounded
   renderer set, or is a specialist call demonstrably required?
4. What is the maximum acceptable added first-use and turn latency/cost for a
   Canvas specialist, and how will timeout/fallback behave?
5. What is the Product Owner's allowed first subject/use-case set for visual
   artifacts (for example, algebra steps versus geometry interaction)?

## Nonblocking

1. Which visual primitives form the first renderer registry and design system?
2. How should narrow-screen Studio presentation prioritize Canvas versus chat
   without changing the desktop-first product model?
3. What fixtures best represent Arabic, English, and mixed-direction learning
   content for Canvas accessibility verification?
4. What read-only learner navigation/history should a later Canvas expose?

## Requires Product Owner Decision

1. Whether a future Studio is permitted to add any model call beyond the
   protected primary Tutor call, and under which learner-value thresholds.
2. Whether the first scoped proof may persist Canvas scene lineage/events or
   stays entirely derived and ephemeral.
3. Whether OpenMAIC package evaluation is limited to renderer/DSL pieces and
   which candidate packages are in scope.
4. Whether specialist providers may differ from the normal Tutor provider, and
   the data-residency/privacy budget if they do.
5. What parent/investor-facing claims are prohibited until real learner use and
   safety/accessibility evidence exist.

## Requires Proof Spike

1. A source-bound, typed renderer can improve a concrete learning task without
   inventing Tutor content.
2. A Canvas state/patch protocol remains correct across delta, terminal turn,
   reload, cancellation, specialist failure, and a new student question.
3. Keyboard, focus, screen-reader, and Arabic/English/mixed direction remain
   usable for each first renderer.
4. A specialist canvas plan materially improves quality enough to justify its
   latency/cost versus deterministic renderers.
5. Privacy tracing can record lifecycle metadata without raw learner content or
   exposing hidden model reasoning.

## Requires Real-Use Evidence

1. Learners actually use the Workspace to understand, not merely admire, a
   visual explanation.
2. Tutor/Canvas coordination reduces confusion or increases observable guided
   success without increasing dependence.
3. Parents understand Canvas scope and do not mistake visual state for stable
   assessment, Evidence, or a safety decision.
4. The Studio remains calm and comprehensible for the intended age range across
   realistic devices and connectivity.

## Recommendations

### Maintain the register through Synthesis

- **Recommendation:** Use this register as the decision agenda for a separate
  Synthesis; close an item only with a cited Product Owner decision or proof.
- **Reason:** It prevents an attractive Studio mockup from silently deciding
  model topology, persistence, or learner authority.
- **Expected impact:** A traceable, bounded next architecture step.
- **Mandatory / Optional:** Mandatory process guardrail.
- **Priority:** P0.
- **Direct view:** Do not convert this list into implementation tickets before
  the Synthesis and explicit promotion into `TASKS.md`.
- **Risk of ignoring:** Architecture will drift through UI changes.
- **Confidence:** High.
