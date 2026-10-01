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
- the approved Tutor/Canvas stream, proactive visual, typed readability, and generated-image composition repair (E39/E40), still uncommitted and not deployed.
- the approved visual-first Canvas simplification: local exploration, concise same-Tutor visual context, and one durable single-choice answer per attempt.

## Current reality

Lina is deployed as a live GCP pilot.

Live Cloud Run revisions and key model/JEV flags rechecked read-only on 2026-10-01:

- App: `lina-app-00028-lz9`, 100% traffic, OpenAI `gpt-6-luna` Primary Tutor.
- Worker: `lina-worker-00023-j7j`, 100% instance split, OpenAI `gpt-6-sol` Canvas route; shared default model is `gpt-6-luna`.
- Current read-only env inspection confirmed App Visual Need `active` and Worker exact Canvas reuse `shadow`. Direct TypeSafe JEV (`jev-1.13.0`), Visual Personalization `shadow`, and Segment Rubric `shadow` are the last documented settings from 2026-09-30; they were not rechecked here.
- The last documented database migration head is `c8e2f4a6b913`; it was not rechecked against production for this evaluation task.
- Remote `main` is `d8ad868` while this dirty repair worktree remains at `416ed85`; the deployed revision source commits were not checked in this read-only route inspection. The earlier authenticated GPT-6 Arabic Tutor → Canvas → READY continuation and same-tab reload remain historical evidence.

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

E39–E41 Tutor/Canvas repair remains local and partial at unchanged HEAD `416ed85`. Bounded provider failures, Visual Need context/status, typed readability checks, and Agent-selected generated-image composition are implemented. E41's real anonymized atom replay passed active TypeSafe JEV and same-Tutor Canvas admission before an explicit tool demand; the real Worker then chose a custom visual whose motion control failed four previews and independent reviews, so no Scene was accepted. Lina's exact historical seed package was digest-verified and rendered through disposable Studio/API and DailyStudentApp at 736.6/712/968 px desktop/tablet-emulated panes: four readable static stages, no interaction. Browser auth used a disposable owner override and Clerk stub; physical iPad remains untested. Affected tests passed 76/76; the full disposable PostgreSQL gate passed 1642 with 12 skipped, and web typecheck passed. The twelve-request live budget ended before real solar success/retry or an independently accepted generated-image chain. Production Image Generation is locally withheld because learner-local timezone and visible-delivery acknowledgement are undefined for the approved ten-successful-visible-images-per-local-day allowance. Historical September 29 ValueError causes remain unknown. See E41 in the repair tracker. No deployment or production data mutation occurred; voice work remains uncommitted.

VISUAL-FIRST-CANVAS-01 is locally implemented on the same uncommitted worktree. The existing Manifest distinguishes sandbox-local exploration, durable work, and application-owned single-choice answers in the same Tutor Chat. The E44 atom source is recovered exactly; its E45 presentation-only revision remains a private diagnostic candidate. Equal-size actual-Daily pane captures, 960/640 sandbox preview, local controls, Scene replacement, assembled Tutor payload, and disposable PostgreSQL/browser answer retry/reload regressions pass without provider calls. One current-visual card uses the existing `visual_description` and current Scene-bound values; the saved atom's Workspace context is 1,995 UTF-8 bytes versus 4,849 before, within a 4,096-byte card target. Four earlier real Tutor/Worker runs used 24 model requests and produced no accepted Scene. The retry addition remains unaccepted and outside this cleanup. No generated Scene reached actual Daily/backend; no real Tutor continuation or learner review was proved. Failed source/previews remain private under ignored `output/visual-first-live`; no deployment or production data mutation occurred.

E46's single approved five-case local batch is complete. Frozen briefs/configuration and the five-case gallery are private under ignored `output/visual-first-luna6`. Canvas author/reviewer used explicit disposable `gpt-6-luna` medium with SDK retries disabled; the Tutor stayed on root `.env` `gpt-5.6-luna`. All cases started with the same available Canvas tools. The batch used 22 model requests, one image call, no Code Interpreter calls and USD 0.28887464 estimated total including a USD 0.25 image planning allowance; actual image billing is unknown. Addition and water cycle reached backend Scenes. Addition's real local answer retry/conflict and same-Tutor continuation passed; its Daily panes were readable. Water cycle reached Daily but its labels overlap and controls are crowded. Atom, solar-model and plant were rejected with saved first-pass/repair artifacts. No learner-facing acceptance, physical iPad, production change or deployment followed. See E46 in the tracker.

E47's separately authorized single-topic live run is complete locally. The earlier zero-call denial and deterministic probe remain preserved. The real `gpt-5.6-luna` Tutor supplied an equivalent-fractions goal but also prescribed bars and included malformed `42f?` in `requested_representation`; representation autonomy remains unproved. Three `gpt-6-luna` medium Canvas calls produced one custom visual, independently accepted on its first candidate. It was stored under the disposable owner, rendered in 960/640 sandbox previews, and owner-scoped API payloads rendered in the actual Daily component through browser transport fixtures at 690.6/666 px visual widths. The static Scene has no controls. Its compact card reached a real same-Tutor continuation that referenced the aligned shading. Five of eight model requests, zero of one image invocations, and USD 0.00917701 durable-execution estimated model cost were used; actual billing is unknown. Ignored evidence is under `output/visual-teacher-spike/live-1`. This does not prove authenticated browser delivery, physical iPad use or learner comprehension.

E48 fixes the visual-teaching handoff contract locally without a provider call. New Tutor model output no longer contains student_request, requested_representation, or must_not_imply: the application binds the exact current Student turn (up to the existing 4,000-character API limit), while representation choice stays with the Canvas visual teacher and educational fidelity is carried positively in objective/facts/relations. Legacy persisted CanvasBrief v1 records remain readable and retain their legacy fields when they originally supplied them. Focused contract/runtime/Canvas/provider tests pass; no visual was regenerated, committed, pushed or deployed.

E49 narrows JEV's Canvas role to optional memory support. In active visual-personalization mode, the server builds a candidate pool only from safe visual Personal Facts and the already-selected Learning Intelligence Card entries. JEV sees the fixed educational target only as a relevance reference, selects up to three support keys, and the server resolves them into separate Personal Fact and Learning Intelligence fields for Canvas. Current Student request, conversation, curriculum/FAQ grounding, Core Profile, learning goal, representation and tools remain outside this selector's authority. Legacy off/shadow Personal Fact behavior remains readable. This change is local/uncommitted and used no provider call.

E50 generalizes the Tutor→Canvas boundary repair across Chat and Canvas-originated Tutor turns. New Tutor Canvas output no longer owns source-reference IDs; application code binds the exact current learner request plus authorized source refs. Canvas brief/change-intent mismatches now reject only the Canvas request and preserve safe Tutor Chat after removing false visual promises; safety/ownership/provenance remain hard failures. Primary Tutor guidance now treats requested direct manipulation of visible state as a general Canvas-surface need when Chat cannot provide the requested action. This is not tied to the five evaluation topics. No provider call, deployment, commit, push or production mutation was used for E50.

E51 completed the unchanged five-case E50 live rerun. Math, pitch and diaphragm passed the repaired Tutor-to-Canvas admission. Math produced a first-candidate accepted custom Scene, passed owner-scoped Daily API and real Daily browser rendering, and its LOCAL slider changed 1x12/P26 to 3x4/P14 while preserving area 12 with zero Studio/Tutor calls. A real same-Tutor continuation consumed the compact current-visual card and continued correctly. Pitch reached Canvas but failed after one repair because its LOCAL hum_step control still produced no visible change; its Tutor brief also leaked a wave-pattern representation through desired_student_action. Diaphragm reached Canvas but generated custom source failed mount (parent.appendChild is not a function) and did not recover within the repair bound. Arabic sentence ordering remained Chat-only despite an explicit manipulation request; lever mechanics remained Chat-only with a coherent text explanation. All optional-memory pools were empty, so active E49 made zero JEV selection calls. Five initial cases used 16 model requests; one same-Tutor continuation brought the evaluation to 17 requests, zero Image Generation, zero Code Interpreter and about USD 0.02758 consolidated ledger estimate. The successful Math reviewer accepted the immutable first candidate before a separate no-tool finalizer call, making that finalizer a strong optimization candidate but not yet removed. Evidence is under ignored output/visual-teacher-five-live-e50. No deployment or production mutation occurred.

E52 is locally implemented and not yet live-validated. Representation leakage is narrowed by replacing Tutor-authored free-form desired_student_action with a required bounded learner_experience enum; application binding converts that intent to representation-neutral Canvas semantics. The Primary Tutor now emits an explicit teaching_surface (CHAT/CANVAS) for every instructional move, with direct-manipulation consistency guidance, and that decision is retained in Tutor audit payloads. Custom-visual reliability guidance now favors native value controls, discrete STEP controls, unambiguous DOM/SVG helpers, and blocker-first repair; rejected exact-edit arguments that never changed source no longer consume an authoring/refinement attempt. E52-focused regression passes 276/276. The full Python suite remains at the pre-existing environment/baseline state: 831 passed, 854 skipped, six fake-agent review failures, and three PostgreSQL setup errors because DATABASE_URL is absent. No provider call, commit, push, merge, deployment or production mutation was used for E52.

E53 live-validates E52 under one bounded approval (24 model requests / USD 1 / max 2 image / max 2 code calls). The first clean batch used six requests: Arabic direct manipulation routed to Canvas and produced an accepted typed Scene; Pitch and Biology initially stayed Chat-only despite explicit visual-observation wording. Root cause was that deterministic surface consistency enforced DIRECT_MANIPULATION but not explicit VISUAL_OBSERVATION. A narrow bilingual visual-observation guard and one same-Tutor surface-repair path were added and locally regressed before rerunning only Pitch/Biology with the remaining allowance. Both then admitted representation-neutral briefs (Pitch learner_experience OBSERVE/COMPARE/EXPLORE; Biology OBSERVE/COMPARE/EXPLAIN). Arabic's accepted Scene rendered in the real Daily component, but its ORDERING block currently falls back with 'Ordering is not available safely in Canvas yet' while the MATCHING block renders mixed Arabic/English Place-in controls; therefore Arabic is not learner-ready despite Scene acceptance. Pitch produced two operable interactive custom candidates; both browser previews passed SET_VALUE interactions, but independent review rejected them because the amplitude control remained outside the viewport at 960/640 after repair. Biology produced two operable inhale/exhale custom candidates; browser previews had no technical findings and the phase SET_VALUE worked at both widths, but independent review still rejected the repaired candidate on one remaining semantic/visual defect. Across both live legs: 16 model requests, about USD 0.02236 ledger estimate, zero Image Generation, zero Code Interpreter. No commit, push, merge, deployment or production mutation occurred. Evidence is preserved under output/visual-teacher-e52-live-current and output/visual-teacher-e52-live-current-r2.

E54 is locally complete and not live-validated. The accepted E53 Arabic typed Scene now renders learner-facing ORDERING in the real Daily component instead of the prior safe fallback: it starts in an unsolved deterministic order, exposes Arabic move-up/move-down controls and submit, and Arabic MATCHING uses Arabic-only placement copy with no mixed English controls. The exact owner-scoped E53 Scene passed the E54 Daily browser harness at desktop and tablet-emulated widths. Custom Visual sandbox applies generic box-sizing/max-width protection to native controls; the Pitch failure pattern is covered by a local preview regression showing full-width native range controls remain within the viewport. Authoring guidance now explicitly forbids fixed-height SVG/viewBox combinations that shrink child-facing text below actual-screen acceptance. Canvas author and independent reviewer contracts now preserve relationship authority: they must not strengthen a supplied relation into unsupported causal mechanisms such as pushes, pulls, forces, causes, drives, or prevents. Local verification: 205 relevant Python tests passed, 17/17 Agentic Canvas TypeScript tests passed, E54 real Daily browser passed, Python compile and git diff --check passed. The six pre-existing fake-agent reviewer tests that lack model/model_settings remain outside this green subset and are unchanged. No provider call, commit, push, merge, deployment, or production mutation occurred.

The newly authorized five-case E48/E49 live evaluation ran each synthetic Student turn once with hard 40-request/USD 5/five-image/five-code ceilings. Five `gpt-5.6-luna` Tutor calls used USD 0.01146883 durable estimated cost; no JEV, Canvas or hosted-tool call occurred. Three authored briefs incorrectly used the raw Student message ID as a source reference and were rejected by the source-authorization gate; their foreground Tutor turns failed without a saved Tutor reply. Arabic and lever turns completed as text but requested no Canvas. The application-bound Student request was exact in all three authored-brief diagnostics, with no representation fields. All optional-memory candidate pools were empty. No generated visual, review, Scene, Daily screenshot, return card or same-Tutor continuation was reached. No case was rerun; report is private under `output/visual-teacher-five-live`.

SOURCE-STREAM-01 (R01) is locally closed after review. The request commits source/message lineage before the stream-owned Session loads the original; source preparation failures settle the admitted turn with a bounded SSE error. General Tutor stream error behavior remains at its pre-R01 contract. Real authenticated browser and deployed behavior are unverified.

VOICE-STT-01 (R02) is reopened. On 2026-09-28, three authenticated Windows/Chrome attempts reached deployed STT with non-empty audio and failed as `TranscriptionNoSpeechError`; the learner saw no transcript. A new known-speech WAV → Web Audio → Chrome-native Opus/WebM recording succeeded through Lina's real Gateway/provider using a disposable test owner. The production recorder uses that MIME/bitrate path, so a general WebM/provider incompatibility is not supported. Local near-silence/track checks and a prominent no-speech error pass focused verification. The exact physical Windows microphone cause remains unknown; real Windows physical-mic acceptance is mandatory before deployment or closure.

CORE-PROFILE-BOOTSTRAP-01 (R03) is locally closed. After explicit Product Owner approval, its exact-Student operator command applied Lina's existing production Core Profile (E37). Independent read-only verification found one active GradePeriod and the existing Tutor context/model payload projected name, derived age and grade without raw DOB. No new Tutor turn or provider call tested learner-facing use; Parent linking remains separate.

The Tutor Golden Evaluation v1 contains 20 synthetic E16–E20/E30-pattern cases. It reuses the production payload and capacity path. A1 compared the current order and Current Turn Last in 60 paired repetitions: both passed all deterministic checks in 49/60 runs, with human review favoring the current order. A2 compared the current order and an evaluation-only Stable Prefix / Dynamic Suffix structure: 48/60 versus 46/60 full passes, with fewer learner next actions under A2. A2 lengthened the exact changing-turn text prefix, but a separate three-turn probe found no added cached tokens under unchanged implicit caching. Keep the current production structure. These synthetic evaluations are not live learner acceptance.

A locally accepted Daily UI slice shows Tutor-style Canvas lifecycle notices from existing composition status: preparation, authoritative ready, and terminal outcomes. Notice language follows the current conversation, with UI language fallback. Notices stay outside durable Chat and learning data; poll/reconnect deduplication is scoped to the browser tab and learning session. Authenticated local browser acceptance confirmed preparation, PENDING/RUNNING follow-up without duplicate Canvas admission, one authoritative READY notice with a visible Scene, and no same-tab reload replay. Terminal failure behavior passed deterministic fixtures; it was not forced in a learner session.

The accepted server-side Tutor guard repairs premature references to a newly requested Canvas visual before persistence and streaming. It leaves truthful preparation, existing READY-Canvas references, and non-Canvas turns unchanged, without another model call. The authenticated local browser showed no premature visibility wording.

The deployed Teaching Continuity slice asks for one reachable action when learning remains unfinished, including wrong answers, DID_NOT_HELP, targeted clarification, and relevant READY Canvas, while allowing natural closure. Four focused Golden cases improved from 4/12 in the saved production baseline to 12/12 in the final three-repeat run; a full 20-case pass scored 18/20 on raw model output. The two raw failures were new-Canvas references repaired before delivery by the accepted guard. Authenticated post-deploy GPT-6 smoke showed a concrete action using the READY visual.

## Active decisions

- One Primary Tutor remains the learner-facing teaching authority.
- Current Student behavior outranks historical personalization.
- Core Profile, Personal Facts, Current Conversation, and Learning Intelligence remain separate authorities.
- Canvas Agent chooses how to teach visually within the Primary Tutor's bounded goal; it is not a second learner-facing Tutor.
- JEV is used only for bounded finite decisions; it is not a general agent or orchestration layer. Visual Need is now active on App; Visual Personalization, Exact Reuse, and Segment Rubric remain shadow on their deployed components.
- Application code retains Safety, ownership, persistence, executable validation, stale-state admission, Evidence lifecycle, and fallback authority.
- Lina remains a modular monolith.
- Tutor availability does not depend on curriculum.
- Structured Studio support currently includes MATH, SCIENCE, ENGLISH, and ARABIC.
- Proactive use of Canvas and Agent-selected generated-image composition are part of the approved local E39 repair. Production image eligibility/quota and authenticated learner acceptance still require their own release gate.
- For visual-first custom Scenes, local controls stay in the sandbox; Studio owns saved work and first accepted choice per explicit attempt; the same Tutor receives a version-bound concise description and exact accepted-answer context.

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

- VOICE-STT-01 has three production no-speech failures with non-empty uploads; microphone device/track/signal conditions on the Windows machine have not been observed.
- Declared teaching strategy and learner-visible move are not always aligned.
- Repeated confusion does not always trigger a sufficiently different teaching method.
- Terminal Tutor buffering can make successful responses feel slow.
- Canvas CREATE reliability still needs continued real-use observation across varied concepts.
- Personalization can feel forced or repetitive if optional context is overused.
- JEV decision quality needs enough real examples before expanding its role.
- E39's historical Lina Tutor ValueErrors are not root-caused; local failure categories improve future diagnosis, not historical certainty.
- E41's real atom worker failed four custom-visual motion checks; the exact historical seed is locally readable but static. Neither result proves authenticated Daily, physical-iPad, or learner comprehension.
- VISUAL-FIRST-CANVAS-01 lacks accepted generated atom/addition Scenes and actual Daily/backend live interaction proof. The first addition brief omitted explicit choices; the revised retry carried them, but both Workers still failed. Local deterministic controls do not close this gate.
- Golden rubric checks are deterministic screens and do not replace human review of educational quality.
- Longitudinal learning benefit is not yet established from controlled real use.

## Next recommended action

Review the five-case E48/E49 evidence before implementation: distinguish authorized retrieval source refs from raw Student message IDs in Tutor output, and decide how an invalid Canvas brief can fail without losing a safe Tutor reply or falsely promising a visual. Re-evaluate Arabic manipulation and lever visual routing after that decision. Keep the E47 artifact and earlier no-call approval history separate from this failed five-case batch. Do not reuse unused batch capacity as a new evaluation authorization. Authenticated Daily delivery, physical iPad, learner comprehension and deployment remain separate gates. Preserve the uncommitted voice and repair slices.

Performance/buffering, personalization relevance beyond the observed cases, AUTH-01, and CALLS-01 remain separate.

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
