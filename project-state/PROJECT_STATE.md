# Project state

## Current goal

Use the deployed Lina system naturally, keep the canonical documentation aligned with the real implementation, and collect enough real evidence to decide the next corrections rather than expanding architecture from assumptions.

The immediate product focus is:

- controlled real Lina use;
- teaching-flow quality;
- Tutor and Canvas latency;
- personalization relevance;
- JEV bounded-decision quality;
- continued live end-to-end reliability.

## Current reality

Lina is deployed as a live GCP pilot.

Current repository mainline:

- origin/main includes the bounded JEV decision integrations.
- Runtime implementation baseline before this documentation-only reconciliation: `561ff16605b455c8f2b1b2d9bce4ccc9b4f8958c`.

Current live infrastructure observed during reconciliation:

- App: Cloud Run revision lina-app-00023-xt8.
- Worker: Cloud Run Worker Pool revision lina-worker-00018-ckk.
- Database migration head: c8e2f4a6b913.
- Primary Tutor / Canvas model route remains OpenAI GPT-5.6 Luna.
- JEV bounded decisions are available through OpenRouter Decisions.

The implemented product includes:

- Primary Tutor;
- Daily Student experience;
- Core Profile;
- Personal Facts / Personal Memory;
- Learning Intelligence;
- Student image/PDF/DOCX sources;
- voice/STT;
- optional Content/RAG;
- Studio durable Runtime/Scene/Event/Snapshot state;
- Full-Power Hybrid Canvas;
- reusable visual registry;
- REUSE / ADAPT / CREATE;
- custom visual sandbox;
- separate Worker;
- JEV bounded decisions for visual personalization, exact Canvas reuse, and Segment rubric comparison.

REPAIR-SLICE-01 and REPAIR-SLICE-02 are locally accepted. Real-use E2E and product-quality acceptance remain ongoing rather than inferred from local tests.

## Active decisions

- One Primary Tutor remains the learner-facing teaching authority.
- Current Student behavior outranks historical personalization.
- Core Profile, Personal Facts, Current Conversation, and Learning Intelligence remain separate authorities.
- Canvas is a representation and interaction surface, not a second Tutor.
- JEV is used only for bounded finite decisions; it is not a general agent or orchestration layer.
- Application code retains Safety, ownership, persistence, executable validation, stale-state admission, Evidence lifecycle, and fallback authority.
- Lina remains a modular monolith.
- Tutor availability does not depend on curriculum.
- Structured Studio support currently includes MATH, SCIENCE, ENGLISH, and ARABIC.
- Generated educational images remain a separate planned V2 capability.

## Protected areas

Do not change without explicit Product Owner approval:

- non-overridable child safety;
- Parent Learning Boundaries;
- ownership/privacy isolation;
- Core Profile authority;
- Personal Facts authority;
- Learning Intelligence / Evidence semantics;
- Primary Tutor authority;
- Studio durable-state authority;
- custom visual sandbox boundary;
- material production provider/model policy;
- destructive production data operations.

## Active risks

- Natural teaching can still end without a useful next learner affordance.
- Declared teaching strategy and learner-visible move are not always aligned.
- Repeated confusion does not always trigger a sufficiently different teaching method.
- Terminal Tutor buffering can make successful responses feel slow.
- Canvas CREATE reliability still needs continued real-use observation across varied concepts.
- Personalization can feel forced or repetitive if optional context is overused.
- JEV decision quality needs enough real examples before expanding its role.
- Longitudinal learning benefit is not yet established from controlled real use.

## Next recommended action

Continue natural Lina usage without scripting the conversation around features.

During the live pass:

1. record real defects and surprising behavior;
2. inspect logs/state only after observed behavior;
3. separate model variation from product-contract failure;
4. collect JEV comparison cases;
5. do not patch immediately unless a blocker prevents further testing.

After enough real evidence, the next likely implementation slice is teaching-flow integrity:

- CONV-MOMENTUM-01;
- STRATEGY-FIDELITY-01;
- PED-ADAPT-01.

Performance, Personalization relevance, JEV evaluation, generated educational images, AUTH-01, and CALLS-01 remain separate decisions.

## Critical references

- ../README.md
- ../docs/PROJECT_REFERENCE.md
- ../docs/IMPLEMENTATION_PLAN.md
- ../docs/LEARNING_INTELLIGENCE_SPEC.md
- ../docs/CHILD_SAFETY_POLICY.md
- ../docs/LEARNING_PRODUCT_ROADMAP.md
- ../docs/TUTOR_PEDAGOGY_REFERENCE.md
- ../docs/TUTOR_CANVAS_REPAIR_TRACKER.md
- ../TASKS.md
- SYSTEM_MAP.html
