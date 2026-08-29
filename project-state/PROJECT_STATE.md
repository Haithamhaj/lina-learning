# Lina Personal Learning System — Project State

## Current goal

CTX-03 remains the approved, technically verified Context v2 direction.
SEG-EVID-01 is the approved Learning Intelligence semantic architecture, but
is not implemented. Current code still uses legacy Session Evidence.
CAND-01 strict Structured Output compatibility correction is next before
SEG-EVID-01A; EDU-ERR-01 is blocked by SEG-EVID-01F.

## Current reality

- Segment semantic review is approved, asynchronous, and not implemented;
  Session remains the durable Evidence authority.
- Candidate Events are provisional hints. Staged Segment findings do not update
  current-session personalization; Pattern counters/lifecycle are unchanged.
- Existing Session Evidence remains the current/legacy implementation until
  SEG-EVID-01D. Historical Evidence remains valid, auditable, and rebuildable.
- Track A is COMPLETE / ACCEPTED; the authenticated Tutor works with zero
  content, uses optional question-driven grounding, and remains safety-first.
- CTX-03 preserves current-Segment-only context. `CONTINUE` stays in the
  current Segment; `NEW_SEGMENT` and `UNCERTAIN` persist a new Segment and
  complete the prior one. Session close completes the final Segment.
- One primary Tutor call, safety-first policy enforcement, question-driven RAG,
  and separation of Safety, context, RAG, Student Core Profile, and learner
  intelligence remain protected.
- The current strict Tutor schema defect blocks real-Luna inference before
  CAND-01 verification. EVID-01 remains an open legacy HTTPError defect but is
  off the new critical path. PERS-01 is absorbed into SEG-EVID-01F.

## Active decisions

- Segment = semantic review unit; Session = durable intelligence authority.
- Segment review is asynchronous/background; Session Finalization is
  deterministic by default with no semantic Session call after Reviews.
- Raw interaction outranks Candidate metadata; Candidate is provisional.
- No partial Session activation; Card updates only after Session authority.
- Current behavior outranks history; TeachingMethod identity is server-grounded;
  no learner-style/psychological labels or second learner-memory/counter system.
- Bounded authoritative historical anchors are allowed only when a rubric
  requires them. Cross-subject findings fail closed pending SCOPE-01/SUBJ-01.

## Protected areas

```text
Raw interaction provenance
→ completed Segment semantic interpretation
→ Session-authorized Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ personalization
```

Atomic reprocessing authority remains required. Safety, conversation context,
and RAG/curriculum remain separate authorities.

## Active risks

- **SEG-EVID-R1 — Segment Boundary Fidelity — 5**
- **SEG-EVID-R2 — Partial Session Activation — 5**
- **SEG-EVID-R3 — Cross-Subject Attribution — 5**
- **SEG-EVID-R4 — Legacy/New Authority Coexistence — 5**
- **SEG-EVID-R5 — Semantic Review Cost — 3**
- **CAND-01-SCHEMA — Strict Structured Output incompatibility — 5**
- **STATE-01 — Structured Segment State lineage reliability — OPEN / NON-BLOCKING**

## Next recommended action

Complete governing documentation alignment → independently review → fix only
CAND-01 strict Structured Output compatibility → SEG-EVID-01A. Do not start
EDU-ERR-01, SCOPE-01, SUBJ-01, REC-25, LR-D04B, archive retrieval, or frozen
future capabilities.

## Critical references

`AGENTS.md`; `docs/PROJECT_REFERENCE.md`; `docs/LEARNING_PRODUCT_ROADMAP.md`;
`docs/LEARNING_INTELLIGENCE_SPEC.md`; `docs/IMPLEMENTATION_PLAN.md`; `TASKS.md`.
