# Project state

## Current goal

Pause further natural Lina use temporarily, correct the first real-use defects and calibration gaps exposed by E30, then resume controlled testing from a cleaner baseline.

The immediate product focus is:

- Student source-stream reliability;
- voice/STT reliability;
- proactive visual teaching / Canvas choice;
- real-account Core Profile bootstrap and later Personal Memory verification;
- Learning Intelligence mixed-evidence calibration;
- teaching-strategy fidelity;
- GPT-6 model-route migration and cost-rate correction;
- bounded JEV activation only where slice-specific evidence supports it.

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

SOURCE-STREAM-01 (R01) is locally closed after review in this uncommitted worktree. The request now commits source/message lineage before the stream-owned Session loads the original; source preparation failures settle the admitted turn with a bounded SSE error. General Tutor stream error behavior remains at its pre-R01 contract. Real authenticated browser and deployed behavior are unverified.

VOICE-STT-01 (R02) is locally closed in the same uncommitted worktree: local Chrome proves recording Stop, transcript-to-editable-draft/Send, failure recovery, and native WebM/Opus output; provider, PostgreSQL, and frontend tests pass. The actual Lina adapter and Gateway also transcribed disposable WAV and WebM through the authorized production-equivalent `MODEL_API_KEY`, twice each, with HTTP 200 and successful disposable AI executions. The five historical 502 response shapes remain unknown; authenticated/deployed Lina acceptance remains unverified.

CORE-PROFILE-BOOTSTRAP-01 (R03) is locally closed in this uncommitted worktree. After explicit Product Owner approval, its exact-Student operator command applied Lina's existing production Core Profile (E37). Independent read-only verification found one active GradePeriod and the existing Tutor context/model payload projected name, derived age and grade without raw DOB. No new Tutor turn or provider call tested learner-facing use; Parent linking remains separate.

## Active decisions

- One Primary Tutor remains the learner-facing teaching authority.
- Current Student behavior outranks historical personalization.
- Core Profile, Personal Facts, Current Conversation, and Learning Intelligence remain separate authorities.
- Canvas is a representation and interaction surface, not a second Tutor.
- JEV is used only for bounded finite decisions; it is not a general agent or orchestration layer. Existing Visual Personalization, Exact Reuse, and Segment Rubric roles remain unchanged; REAL-USE-REPAIR-01 adds a bounded Visual Need decision slice.
- Application code retains Safety, ownership, persistence, executable validation, stale-state admission, Evidence lifecycle, and fallback authority.
- Lina remains a modular monolith.
- Tutor availability does not depend on curriculum.
- Structured Studio support currently includes MATH, SCIENCE, ENGLISH, and ARABIC.
- Proactive use of the existing Canvas for high-value visual teaching is a current repair, not a V2 dependency. Generated educational images remain a separate planned capability, but selected V2 product rules may be promoted into the current release when they directly improve the learner experience without requiring unresolved provider/quota/safety work.

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

Do not continue natural Lina testing until the E30 repair/recalibration batch is accepted and deployed.

The current repair planning order is:

1. Retain SOURCE-STREAM-01's authenticated browser/live acceptance gate and retest the authenticated VOICE-STT-01 flow after authorized deployment;
2. Verify the applied Core Profile in one new authenticated Tutor turn, then assess MEMORY-LIVE-01 readiness;
3. VISUAL-CHOICE-01 plus STRATEGY-FIDELITY-01, preserving the E30 good DID_NOT_HELP method-change path;
4. LI-CALIBRATION-01 with mixed-evidence regression coverage;
5. MODEL-GPT6-01 and COST-RATE-01;
6. slice-specific JEV decision on whether to stay shadow or become active;
7. focused + affected regression, browser/provider proof, then one controlled deployment and Lina retest.

Generated educational-image capability, performance/buffering, personalization relevance beyond the observed cases, AUTH-01, and CALLS-01 remain separate unless explicitly promoted into this repair release.

## Critical references

- ../README.md
- ../docs/PROJECT_REFERENCE.md
- ../docs/IMPLEMENTATION_PLAN.md
- ../docs/LEARNING_INTELLIGENCE_SPEC.md
- ../docs/CHILD_SAFETY_POLICY.md
- ../docs/LEARNING_PRODUCT_ROADMAP.md
- ../docs/TUTOR_PEDAGOGY_REFERENCE.md
- ../docs/TUTOR_CANVAS_REPAIR_TRACKER.md
- ../docs/REAL_USE_REPAIR_01_IMPLEMENTATION_SPEC.md
- ../TASKS.md
- SYSTEM_MAP.html
