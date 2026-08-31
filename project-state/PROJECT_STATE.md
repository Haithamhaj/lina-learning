# Lina Personal Learning System — Project State

## Current goal

`DOC-SYNC-01 — Product Truth & Governing Documentation Synchronization` is **DONE / ACCEPTED** following Product Owner approval on 2026-08-31 and the final review-only governance/scope audit.

`RL-01 — Real-Use Environment & Integrated Intelligence Loop Verification` is the **NEXT APPROVED TRACK**.

The first RL-01 stage is **CURRENT REALITY AUDIT ONLY**:

```text
CURRENT REALITY
→ GAP
→ ROOT CAUSE
→ MINIMAL OPERATIONAL CHANGE
→ VERIFICATION
→ ACCEPTANCE
```

Do not implement, re-platform, or redesign deployment before that audit identifies a verified blocker and the minimum required change.

---

## Current reality

- The current implemented proving ground is a Math-first authenticated Student Tutor with persistent conversation, SSE streaming, child-safety enforcement, optional grounding, and relevant learner-intelligence context.
- Full-System Learning Intelligence Acceptance is **DONE / ACCEPTED**. The canonical architecture is **Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority**.
- Segment Review is the semantic-analysis unit. Session Finalization is deterministic and remains the durable Event/Evidence authority.
- One primary Tutor model call per normal Student turn is protected. No second normal-turn classifier, summarizer, or evidence call is approved.
- Candidate metadata remains provisional. Candidate ≠ Evidence. Raw interaction remains source authority.
- Current demonstrated behavior outranks historical personalization.
- `SCOPE-01`, `SUBJ-01`, `DEC-01`, `DEC-02`, `REP-01`, `LANG-01`, `CAND-03`, and `CAND-02` are accepted. Do not reopen them without a newly reproduced defect from real use.
- **Limited Real-Lina use has occurred.** Lina herself participated in part of a real persisted Tutor interaction; that interaction was then continued and used in subsequent testing/calibration.
- Limited Real-Lina interaction does **not** prove stable daily use, a complete recurring Lina `Session → Review → Evidence → Card → later Tutor` loop, or longitudinal real-use personalization across multiple natural sessions. Those remain unverified.
- Voice/STT, Vision/photo input, handwriting/drawing evidence, visual/interactive learning artifacts, Science production, broader Parent Intelligence UX, and Grade-transition production remain **approved product directions but sequenced/frozen for implementation** until explicitly promoted.
- Curriculum/book availability is optional grounding. The current Student question remains authoritative; no book or semantic extraction is required for Tutor availability.
- The repository contains a complete Worker entrypoint and DB-backed job system, but the current standard `.replit` Project workflow starts Web + API only. Treat that as an audit finding to verify against the actual chosen/current environment, not permission for deployment redesign.
- A single reliable daily-use environment combining Web, API, Worker, persistent DB, Clerk identity, and a real Model Gateway route has not yet been verified end-to-end. RL-01 exists to establish that operational reality and prove the recurring intelligence chain with minimum change.
- `MATH-01 — Structured Math Readability` remains **OPEN / CONFIRMED / Criticality 4** and is independent of RL-01.
- `ID-01 — Concurrent First-Identity Creation Race` remains **OPEN / INVESTIGATION REQUIRED / Criticality 3**; root cause must be reproduced before any fix.
- `EDU-ERR-01` remains approved/deferred; `REC-25` remains blocked; `LR-D04B` remains future/evidence-dependent. None is automatically promoted.

---

## Active decisions

1. **Product purpose:** Lina Learning is a personal AI learning system whose differentiator is evidence-grounded longitudinal learning intelligence and personalization, not basic LLM Q&A or book RAG.
2. **Current question authority:** Lina's current question/behavior outranks stale curriculum context and historical personalization.
3. **Grounding:** books, school material, captured pages, and trusted references are optional grounding sources, not teaching authority or permission to learn.
4. **Learning Intelligence:** Segment interprets; Session commits. Staged Segment findings are inactive until deterministic Session authorization.
5. **Normal Tutor path:** one primary Tutor model call; no extra normal-turn classifier/summarizer/evidence chain.
6. **Provider boundary:** application domains use the Model Gateway. The currently implemented real provider route is OpenAI, but provider/model choice is replaceable and evidence-driven.
7. **Deployment boundary:** Replit may be a convenient environment, but it is not product architecture. Deployment target is an operational choice.
8. **Approved deferred breadth:** Math + Science, multimodal input, visual/interactive representations, and Parent inspectability remain intentional product direction even when not required for the current proving ground.
9. **Real-use verification:** limited Lina interaction is historical fact; stable daily/longitudinal Lina use is a separate verification horizon.
10. **RL-01 boundary:** RL-01 is operational verification/stabilization of the existing system, not a deployment redesign project.

---

## Protected areas

```text
Raw interaction provenance
→ completed Segment semantic interpretation
→ Session-authorized Event/Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ relevant later personalization
```

Also protected:

- current behavior outranking history;
- one primary Tutor model call per normal turn;
- deterministic Session Finalization and no partial Session activation;
- exact Segment Review/Finding/Event/Evidence provenance;
- Candidate metadata remaining provisional only;
- Safety, conversation context, optional school/RAG context, Student Core Profile, and Learner Intelligence remaining separate authorities;
- original books/student work remaining distinct from AI-derived interpretations/artifacts;
- no second learner-memory/counter system;
- no resurrection of Current School Focus authority, mandatory curriculum semantics, or semantic Session summarization;
- no host/provider choice becoming permanent product architecture without an explicit decision.

---

## Active risks

- **RL-R1 — Integrated Real-Use Operational Loop Unverified — Criticality 5**  
  Existing Web, API, Worker, persistent DB, Clerk identity, and real model route have not yet been verified together as one reliable recurring Lina environment.

- **UX-R1 — Daily-Use Experience Remains Text-Heavy — Criticality 4**  
  The current proving ground is usable for Math/Text validation but does not yet include the approved Voice, Vision, and richer visual-representation capabilities expected for a natural child learning experience.

- **MATH-01 — Structured Math Readability — Criticality 4**  
  Plain-text long-division alignment is not reliably readable in proportional chat rendering. Any future fix must remain a bounded representation correction, not an implicit Artifact Engine unfreeze.

- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3**  
  One concurrent creation failure made a lookup→create race plausible but unproven. Diagnose before changing identity logic.

---

## Next recommended action

Run **RL-01 Current Reality Audit** only.

The audit must determine the actual current Web/API/Model Gateway/Auth/DB/Worker/Session Lifecycle/Segment Review/Session Finalization/downstream-intelligence/next-session-personalization/storage/runtime-environment state, classify each link, identify only true Gate-A blockers, and propose the minimum change set.

**Stop after the audit.** Do not make implementation/config/deployment changes during the audit. If a genuine Product/Deployment decision remains after technical inspection, surface one blocking question to the Product Owner.

Do not promote MATH-01, ID-01, EDU-ERR-01, REC-25, LR-D04B, Voice, Vision, Science, Learning Canvas, Artifact Engine, Parent Dashboard expansion, or another deployment architecture during RL-01 Current Reality Audit.

---

## Critical references

- `AGENTS.md` — agent operating rules and protected areas
- `docs/PROJECT_REFERENCE.md` — stable approved product truth
- `docs/LEARNING_INTELLIGENCE_SPEC.md` — Learning Intelligence semantic contract
- `docs/LEARNING_PRODUCT_ROADMAP.md` — approved product evolution/sequencing
- `docs/IMPLEMENTATION_PLAN.md` — implementation direction
- `docs/CHILD_SAFETY_POLICY.md` — child safety and Parent Boundary policy
- `TASKS.md` — durable execution/task state
- `project-state/SYSTEM_MAP.html` — architecture map plus readiness overlay
