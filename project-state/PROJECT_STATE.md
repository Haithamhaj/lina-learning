# Project state

## Current goal

Pause further natural Lina use temporarily, correct the first real-use defects and calibration gaps exposed by E30, then resume controlled testing from a cleaner baseline.

The immediate product focus is:

- Student source-stream reliability;
- voice/STT reliability;
- Teaching Continuity / Next Learner Action for unfinished learning;
- real-account Core Profile bootstrap and later Personal Memory verification;
- Learning Intelligence mixed-evidence calibration;
- teaching-strategy fidelity, including preserving EXPLAIN_THEN_CHECK;
- post-deployment GPT-6 route acceptance and cost accounting;
- bounded JEV activation only where slice-specific evidence supports it.
- the frozen synthetic Golden Evaluation Set as a local Tutor regression gate.

## Current reality

Lina is deployed as a live GCP pilot.

Live Cloud Run configuration verified read-only on 2026-09-28:

- App: `lina-app-00024-6xs`, 100% traffic, OpenAI `gpt-6-luna` Primary Tutor.
- Worker: `lina-worker-00019-fsc`, 100% instance split, OpenAI `gpt-6-sol` Canvas route; shared default model is `gpt-6-luna`.
- Both use direct TypeSafe JEV (`jev-1.13.0`). App Visual Need is `active` and Visual Personalization is `shadow`; Worker exact Canvas reuse and Segment Rubric are `shadow`.
- The last documented database migration head is `c8e2f4a6b913`; it was not rechecked against production for this evaluation task.
- The current Tutor/Canvas batch started at `8954e633`; its accepted local changes have not yet been deployed.

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

SOURCE-STREAM-01 (R01) is locally closed after review. The request commits source/message lineage before the stream-owned Session loads the original; source preparation failures settle the admitted turn with a bounded SSE error. General Tutor stream error behavior remains at its pre-R01 contract. Real authenticated browser and deployed behavior are unverified.

VOICE-STT-01 (R02) is locally closed: local Chrome proves recording Stop, transcript-to-editable-draft/Send, failure recovery, and native WebM/Opus output; provider, PostgreSQL, and frontend tests pass. The actual Lina adapter and Gateway also transcribed disposable WAV and WebM through the authorized production-equivalent `MODEL_API_KEY`, twice each, with HTTP 200 and successful disposable AI executions. The five historical 502 response shapes remain unknown; authenticated/deployed Lina acceptance remains unverified.

CORE-PROFILE-BOOTSTRAP-01 (R03) is locally closed. After explicit Product Owner approval, its exact-Student operator command applied Lina's existing production Core Profile (E37). Independent read-only verification found one active GradePeriod and the existing Tutor context/model payload projected name, derived age and grade without raw DOB. No new Tutor turn or provider call tested learner-facing use; Parent linking remains separate.

The Tutor Golden Evaluation v1 contains 20 synthetic E16–E20/E30-pattern cases. It reuses the production payload and capacity path. A1 compared the current order and Current Turn Last in 60 paired repetitions: both passed all deterministic checks in 49/60 runs, with human review favoring the current order. A2 compared the current order and an evaluation-only Stable Prefix / Dynamic Suffix structure: 48/60 versus 46/60 full passes, with fewer learner next actions under A2. A2 lengthened the exact changing-turn text prefix, but a separate three-turn probe found no added cached tokens under unchanged implicit caching. Keep the current production structure. These synthetic evaluations are not live learner acceptance.

A locally accepted Daily UI slice shows Tutor-style Canvas lifecycle notices from existing composition status: preparation, authoritative ready, and terminal outcomes. Notice language follows the current conversation, with UI language fallback. Notices stay outside durable Chat and learning data; poll/reconnect deduplication is scoped to the browser tab and learning session. Authenticated local browser acceptance confirmed preparation, PENDING/RUNNING follow-up without duplicate Canvas admission, one authoritative READY notice with a visible Scene, and no same-tab reload replay. Terminal failure behavior passed deterministic fixtures; it was not forced in a learner session.

The accepted server-side Tutor guard repairs premature references to a newly requested Canvas visual before persistence and streaming. It leaves truthful preparation, existing READY-Canvas references, and non-Canvas turns unchanged, without another model call. The authenticated local browser showed no premature visibility wording.

The locally accepted Teaching Continuity slice asks for one reachable action when learning remains unfinished, including wrong answers, DID_NOT_HELP, targeted clarification, and relevant READY Canvas, while allowing natural closure. Four focused Golden cases improved from 4/12 in the saved production baseline to 12/12 in the final three-repeat run; a full 20-case pass scored 18/20 on raw model output. The two raw failures were new-Canvas references repaired before delivery by the accepted guard. The authenticated local browser also showed a concrete action using the READY visual. That browser run used GPT-5.6 Luna; GPT-6 Luna Tutor and GPT-6 Sol Canvas behavior remain the post-deploy smoke gate.

## Active decisions

- One Primary Tutor remains the learner-facing teaching authority.
- Current Student behavior outranks historical personalization.
- Core Profile, Personal Facts, Current Conversation, and Learning Intelligence remain separate authorities.
- Canvas is a representation and interaction surface, not a second Tutor.
- JEV is used only for bounded finite decisions; it is not a general agent or orchestration layer. Visual Need is now active on App; Visual Personalization, Exact Reuse, and Segment Rubric remain shadow on their deployed components.
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

- Local authenticated browser continuity passed with a relevant READY Canvas action; deployed GPT-6 pedagogical behavior is still unverified.
- Declared teaching strategy and learner-visible move are not always aligned.
- Repeated confusion does not always trigger a sufficiently different teaching method.
- Terminal Tutor buffering can make successful responses feel slow.
- Canvas CREATE reliability still needs continued real-use observation across varied concepts.
- Personalization can feel forced or repetitive if optional context is overused.
- JEV decision quality needs enough real examples before expanding its role.
- Golden rubric checks are deterministic screens and do not replace human review of educational quality.
- Longitudinal learning benefit is not yet established from controlled real use.

## Next recommended action

Verify and publish the accepted Tutor/Canvas batch without changing prompt order, model routing, JEV modes, memory count, or reasoning effort. After App and Worker deployment, run one authenticated GPT-6 Arabic Tutor → Canvas → READY continuation smoke with lifecycle-language, no-duplicate, and reload checks. Then resume controlled Lina testing and the separate source/voice, Core Profile/Memory, Learning Intelligence, and JEV acceptance work.

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
- ../evals/tutor_golden/README.md
- ../evals/tutor_golden/results/A1_REVIEW_2026-09-28.md
- ../evals/tutor_golden/results/A2_REVIEW_2026-09-28.md
- ../TASKS.md
- SYSTEM_MAP.html
