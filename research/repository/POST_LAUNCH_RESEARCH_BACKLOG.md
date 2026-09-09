# Post-Launch Research Backlog

## Purpose

This file stores ideas that are intentionally **deferred until the product is working in real use**.

Items here are not current implementation requirements, acceptance criteria, or blockers. They exist so useful ideas can be searched, discussed, researched, measured, and developed later using real production evidence instead of assumptions.

An item should move out of this backlog only after there is enough real usage evidence to justify investigation or implementation.

---

# PLR-CTX-01 — Adaptive Context Capacity Management

**Status:** DEFERRED / POST-LAUNCH RESEARCH  
**Area:** Tutor Context / Cost / Latency / Context Quality  
**Related current architecture:** CTX-03 Hybrid Segment Context, especially CTX-03D Final Capacity Guardrail

## Why this is deferred

The current product should first use a simple, understandable context pipeline and collect real behavior before introducing a sophisticated capacity-allocation system.

The initial system already limits context structurally:

- Current Turn is bounded.
- Full Immediate Exchange is protected.
- Recent Raw context is a small number of complete Exchanges.
- Semantic Recall selects only relevant older complete Exchanges from the current Segment.
- Curriculum RAG has its own budget.
- Learner Intelligence has its own budget.
- Structured Segment State is compact.
- Safety / Parent Boundaries remain separate authority.

CTX-03D should therefore remain a **simple final guardrail**, not a new relevance engine.

## Current baseline principle

Each context source should select its own relevant content first:

```text
Conversation
→ best complete Exchanges

Curriculum
→ best relevant blocks

Learner Intelligence
→ best relevant notes/cards

Structured Segment State
→ compact conversational orientation
```

Then a final capacity guardrail asks only:

> Does the selected context fit within the healthy model-input budget?

If yes, send it.

If no, reduce context by removing lower-value **whole units**, not by slicing critical raw conversation text positionally.

Protected components should include at least:

- Current Turn
- Full Immediate Exchange
- Safety / Parent policy context
- Tutor instructions / structured output contract

Structured Segment State should normally remain because it is intentionally compact and useful for orientation.

## Important non-goal for the first product version

Do **not** build a complex mathematical score that directly compares unlike sources such as:

```text
conversation relevance = 0.82
vs
curriculum relevance = 0.76
vs
learner-intelligence priority = 0.71
```

These scores come from different systems and are not automatically comparable.

CTX-03D should not become the authority that decides what is relevant. Relevance remains owned by the source-specific selectors. The final guardrail only handles capacity pressure after relevance selection has already occurred.

## Why this may matter after launch

Even with a structurally small context, total input can grow because one or more selected components may be large:

```text
Current Turn
+ Full Immediate Exchange
+ Recent Raw Exchange(s)
+ Semantic Recall Exchange(s)
+ Structured Segment State
+ Curriculum RAG
+ Learner Intelligence
+ Safety / Parent context
+ Tutor instructions
+ response schema
```

The practical risks are not limited to model context-window overflow. Earlier pressure may appear as:

- higher latency,
- higher token cost,
- weaker attention to the current Student question,
- stale context influencing the answer too strongly,
- unnecessary curriculum or learner-history content,
- multimodal context making turns materially larger later.

## Post-launch research questions

When real usage exists, investigate:

1. What is the actual distribution of Tutor input size by component?
2. Which layers most often create capacity pressure?
3. At what input size do latency, cost, or answer quality start degrading materially?
4. Does a fixed per-layer budget remain sufficient, or is adaptive allocation useful?
5. When capacity is tight, which whole components can be removed with the least effect on learning continuity?
6. Should different Tutor situations use different capacity profiles, such as homework, explanation, casual conversation, or multimodal turns?
7. Does semantic recall remain useful enough at higher context sizes to justify its token cost?
8. How should future image/audio/multimodal inputs affect the final capacity policy?
9. Would model-specific context policies improve cost/quality when multiple Tutor models are available?
10. Can prompt/schema overhead itself be reduced without weakening safety, lineage, or structured output guarantees?

## Candidate experiments

Possible post-launch experiments include:

- Measure context composition by component without storing additional raw Student content.
- Compare fixed capacity allocation with adaptive allocation.
- Compare different whole-unit drop orders.
- Measure answer quality before and after dropping one semantic-recall Exchange.
- Measure answer quality before and after dropping a lower-ranked Curriculum block.
- Measure whether additional Learner Intelligence materially improves the current answer.
- Compare model latency/cost at different input-token ranges.
- Evaluate whether a smaller model-specific context profile performs as well for simple turns.
- Test multimodal turns separately because image/audio token pressure may differ substantially from text-only turns.

## Metrics to collect before making a decision

Useful evidence may include:

- total input tokens,
- input tokens by context layer,
- latency,
- model cost,
- number/type of components dropped by guardrail,
- Tutor completion/incomplete rate,
- Student correction or clarification requests,
- repeated explanation requests,
- continuity failures,
- retrieval usefulness,
- Parent/Lina qualitative acceptance where appropriate.

Do not interpret any single metric as proof of learning quality.

## Possible future directions

Only if production evidence supports the need, investigate options such as:

### Option A — Fixed priority whole-unit dropping

Simple ordered removal of lower-priority selected units when capacity is exceeded.

**Advantage:** simple, inspectable, predictable.  
**Risk:** may waste capacity in situations where another layer is temporarily more valuable.

### Option B — Adaptive per-layer budgets

Adjust Conversation / Curriculum / Learner Intelligence allocations by Tutor situation.

**Advantage:** more efficient use of available context.  
**Risk:** introduces policy complexity and requires evidence that adaptation improves outcomes.

### Option C — Evidence-calibrated capacity controller

Use real operational evidence to choose among a small set of predefined capacity profiles.

**Advantage:** adaptive without requiring one opaque global scoring formula.  
**Risk:** should not be attempted until enough production data exists.

## Guardrails for future development

Any future optimization should preserve these principles unless explicitly re-approved:

- Current Student behavior outranks history.
- Full Immediate Exchange remains protected.
- Conversation Exchanges remain complete raw units when selected.
- Do not reintroduce blind head/tail or character slicing as the conversation-selection algorithm.
- Safety and Parent policy authority are never sacrificed for token savings.
- Curriculum, conversational recall, and Learner Intelligence remain separate authorities.
- Raw conversation remains the source of truth.
- Capacity management must not silently become personalization or Evidence logic.
- Any new thresholds are implementation calibration until validated by evidence.

## Revisit trigger

Re-open this research item only after the product is operational and at least one of the following is observed:

- repeated capacity pressure,
- material latency/cost growth,
- quality degradation correlated with larger contexts,
- frequent whole-unit dropping,
- meaningful multimodal context growth,
- a model/provider change that materially changes context economics,
- sufficient production evidence to compare alternative strategies.

Until then, keep the production implementation simple.
