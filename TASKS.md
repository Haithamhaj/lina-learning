# Lina — Active Execution Queue

This file contains the **current** execution queue. Historical implementation task lists belong under docs/history or retained closure and evidence documents.

An explicit current Product Owner instruction authorizes work. A task appearing here is not automatic authorization for protected changes, production deployment, paid provider evaluation, or data migration.

## Current state

The core Tutor, learner-context, Learning Intelligence, Student-source, Studio and Canvas, and live deployment foundations are implemented.

The current phase is **real-use repair and recalibration**. Controlled natural use is temporarily paused after the first real Lina sessions exposed blocking/important repair items; resume only after the agreed repair batch is locally accepted and deployed.

## 0. WORKER-LIFECYCLE-01 — Intermittent multi-user worker availability

**Status:** LIVE ACCEPTED; MONITOR

The deployed app-side controller records authenticated actions and requests worker startup before the response ends, using a database fast path on subsequent turns. A scheduled minute tick recovers delayed jobs, retries, session closure, and idle shutdown. One global 20-minute window runs from the last genuine activity across users. The worker claim gate protects stop decisions; running jobs renew their leases. Live 2026-09-30 acceptance verified natural idle stop, a real Student-turn wake, a second stop, scheduler-driven session closure and delayed-job wake, completed Learning Intelligence/Personal Facts/finalization jobs, and return to zero. See docs/WORKER_LIFECYCLE_OPERATIONS.md for exact times and rollback.

Local verification on 2026-09-30: affected PostgreSQL regression 220 passed; full Python suite 1650 passed, 12 skipped; web typecheck and production build passed in an isolated copy. Live activity wake reached Ready in about 38 seconds; delayed work reached first claim about 84 seconds after queueing. First Canvas latency from zero was not measured.

**Residual checks:** Keep the rollback anchors and monitor Scheduler health, first cold Canvas latency, lease renewal and restart overlap, concurrent use, and failed Admin API recovery. The owner approved Scheduler setup; no new app IAM role was added. The shared app identity already has Editor and worker-pool scaling permissions. The live stop/wake/finalization core behavior is accepted; do not represent the remaining stress cases as tested.

## 1. LIVE-VALIDATION-01 — Controlled natural use

**Status:** PAUSED AFTER E30 REAL-USE FINDINGS

**Purpose:** Use Lina naturally and capture real defects and behavior before additional architecture work. This activity is currently paused while the E30 repair/recalibration batch is defined and implemented.

**Expected output:**

- real conversation evidence;
- real Canvas behavior;
- recovery and session evidence;
- actual latency observations;
- new tracker items only when evidence supports them.

**Likely areas:** production logs and DB, docs/TUTOR_CANVAS_REPAIR_TRACKER.md, project-state/PROJECT_STATE.md.

**Verification required:**

- distinguish product defect from model variation;
- distinguish live or provider behavior from synthetic fixtures;
- no product patch during initial observation unless a blocker prevents testing.

**Depends on:** deployed App and Worker.

## 1A. REAL-USE-REPAIR-01 — E30 repair and recalibration batch

**Status:** APPROVED / IN PROGRESS — R01 LOCALLY CLOSED; R02 REOPENED AFTER LIVE NO-SPEECH FAILURES

**Implementation spec:** `docs/REAL_USE_REPAIR_01_IMPLEMENTATION_SPEC.md`

**R01 local result:** SOURCE-STREAM-01 passes focused and affected PostgreSQL tests, including the shared-stream scope review (E31-E33 in the repair tracker). Authenticated browser and deployed real-use acceptance remain pending; this does not advance R02 or the rest of the batch.

**R02 reopened result:** Three authenticated Windows/Chrome attempts on the deployed `416ed85` release reached `speech_to_text / openai / gpt-transcribe` with non-empty uploads and failed as `TranscriptionNoSpeechError`. A new synthetic known-speech fixture played through Web Audio and recorded by installed Chrome using the production Opus/WebM and 32 kbps configuration succeeded through Lina's real Gateway/provider path. This rules out a general Chrome WebM/provider incompatibility, but does not identify the physical Windows microphone cause. Local track/signal checks and a prominent recoverable no-speech alert passed focused unit, provider, TypeScript, and Chrome component/signal checks. Keep R02 open until real Windows/Chrome physical-mic recording produces an editable, unsent transcript twice and failure recovery is observed; do not deploy this slice before that gate.

**R03 local result:** CORE-PROFILE-BOOTSTRAP-01 has a preview-first operator command that updates only an exact existing Student's display name, DOB, and active GradePeriod through existing Core Profile services (E36). Disposable PostgreSQL proves preview rollback, idempotent apply, bounded Tutor context/model input without raw DOB, and no Parent/Personal Facts/Evidence/Pattern/AI execution writes. The known date-dependent Parent Grade test remains a separate baseline failure. At E36, no production data had been changed; the later approved application is recorded below. R04 is not started.

**R03 production data result:** With the Product Owner's explicit approval and supplied values, the operator command applied Lina's Core Profile to the exact existing Clerk Student (E37). Independent read-only production verification found one active GradePeriod, no Parent relationship or Personal Fact, and the existing Tutor context/model payload projected `display_name=لينا`, `age_years=9`, and `grade_level=5` without raw DOB. No model call, new Tutor turn, deployment, commit, or push occurred; live learner-facing use remains to be verified. R04 is not started.

**Current tracker scope:**

- SOURCE-STREAM-01;
- VOICE-STT-01;
- VISUAL-CHOICE-01;
- CORE-PROFILE-BOOTSTRAP-01;
- MEMORY-LIVE-01 acceptance;
- LI-CALIBRATION-01;
- STRATEGY-FIDELITY-01;
- MODEL-GPT6-01;
- COST-RATE-01.

**Purpose:** Correct the first real-use defects before further natural Lina testing, without reopening settled architecture.

**Scope rules:**

- preserve Primary Tutor, Evidence, Personal Facts, Core Profile, Studio, and Safety authority boundaries;
- use the current Canvas capability for proactive visual teaching before treating generated images as a required workaround;
- keep raw Evidence/provenance even when downstream LI calibration is weakened;
- migrate model routing intent rather than flattening every route to one model;
- evaluate each JEV decision slice separately.

**Verification required:**

- focused deterministic regressions for every changed contract;
- affected PostgreSQL tests;
- real provider checks for STT and GPT-6;
- actual browser proof for source/voice/Canvas-visible behavior;
- full affected regression before deployment;
- controlled Lina retest only after deployment.

## 1B. TUTOR-GOLDEN-EVAL-01 — Synthetic baseline before prompt ordering change

**Status:** GOLDEN SET ESTABLISHED; A1 AND A2 COMPLETE; KEEP CURRENT PRODUCTION STRUCTURE

**Artifact:** `evals/tutor_golden/README.md`, 20 synthetic cases, `baseline_smoke_2026-09-28.json`, and `results/A1_REVIEW_2026-09-28.md` / `results/A2_REVIEW_2026-09-28.md` with raw and derived results.

**Result:** The cases use the production Tutor context-selection seam, payload builder, capacity guardrail, strict response schema, and OpenAI adapter. A1 paired the frozen 20 cases three times per arm on GPT-6 Luna with only Current Turn block placement changed. Both arms passed all applicable deterministic checks in 49/60 runs. Manual review favored the current order for unfinished-learning next actions and fewer premature drawing references, while Current Turn Last used relevant Personal Memory more naturally and improved two prior-method metadata labels. A1 cost an estimated $0.07135452. No Tutor ordering, runtime configuration, JEV role, deployment, or production data changed.

**A2 result:** Stable Prefix / Dynamic Suffix paired the same frozen 20 cases three times per arm. Production passed every deterministic check in 48/60 runs and A2 in 46/60, with useful next action 19/27 versus 15/27. A2's exact changing-turn input prefix grew from 381 to 9,421 characters, but the separate three-turn probe found identical cached tokens on changed turns under unchanged implicit caching. A2 used fewer output tokens and was modestly faster in this run, without a measured cache gain. Golden plus probe cost an estimated $0.074519995. Keep the current production structure; no Tutor or caching setting was changed.

**Decision:** Keep the current production prompt order after A1 Current Turn Last and keep the current structure after A2 Stable Prefix / Dynamic Suffix. A2 measured no cross-turn cache benefit. The frozen Golden Set remains a local regression gate; cache controls, memory count, and reasoning effort need separate decisions.

## 1C. TUTOR-CANVAS-LIFECYCLE-01 — Chat lifecycle communication

**Status:** LOCAL SLICE ACCEPTED; AUTHENTICATED BROWSER FLOW ACCEPTED; GPT-6 POST-DEPLOY SMOKE PENDING

**Result:** Daily Chat presents run-scoped preparation, authoritative ready, and terminal notices from existing Canvas status. Notice language follows the current Student/Tutor conversation with UI language fallback. Notices remain presentation-only, never Student/Tutor messages or learning data. Ready requires `COMPLETED + scene_ready=true`; milestones are deduplicated across polling and same-tab reload/reconnect. The accepted server-owned wording guard repairs premature new-visual claims before persistence/streaming while preserving truthful preparation, READY-Canvas references, and non-Canvas turns.

**Browser acceptance:** Authenticated local Daily confirmed one preparing notice, PENDING/RUNNING progress with a usable Chat follow-up and no duplicate Canvas run, a rendered Scene with one authoritative ready notice, a concrete Tutor action using the READY visual, and no replay after same-tab reload. Durable Chat and AI execution checks confirmed notices were non-durable and non-evidentiary. Terminal failure copy was checked with deterministic fixtures, not a forced learner run. This browser acceptance used local GPT-5.6 Luna; the GPT-6 Luna/Sol production smoke remains the post-deploy gate.

## 1D. TUTOR-CANVAS-REPAIR-01 — Approved September 30 repair batch

**Status:** LOCAL IMPLEMENTATION PARTIAL; NOT DEPLOYED

E39/E40 implemented bounded Tutor provider failures, corrected Visual Need context, typed-scene readability checks, Agent-selected generated-image composition with owned assets, and Daily fixture coverage. E41's real anonymized atom replay passed active TypeSafe JEV and same-Tutor Canvas admission, then the Worker rejected four motion-control previews; no Scene was accepted. Production Image Generation remains withheld until learner-local day and visible-delivery quota ownership are defined. Historical ValueError causes, authenticated/physical-iPad acceptance, a real accepted image chain, and deployed repair behavior remain open. Full evidence and test results are in `docs/TUTOR_CANVAS_REPAIR_TRACKER.md` E39–E41.

## 1E. VISUAL-FIRST-CANVAS-01 — Local exploration, concise Tutor context and one answer

**Status:** LOCAL IMPLEMENTATION / E46 FIVE-CASE BATCH RUN; TWO BACKEND SCENES ACCEPTED, LEARNER QUALITY OPEN; NOT DEPLOYED

Keep one Primary Tutor and the existing `LOCAL` / `WORK` / `ANSWER` separation. Local controls act in the sandbox, saved work uses Studio, and the application submits the first accepted exact single-choice answer per attempt. Chat receives one bounded, Scene/version-bound current-visual card; browser values are advisory. Historical manifests and Builds retain their behavior. Focused PostgreSQL and actual Daily component browser fixtures have covered double taps, retries, reload, new attempts, local state and compact payload construction without provider calls.

E42/E43 spent 24 historical model requests across four disposable Tutor/Worker trials; none produced an accepted generated Scene. E44 recovered the exact atom source and corrected unchanged-state quota accounting; E45 improved that diagnostic candidate's presentation and measured the compact Tutor request, but did not promote it. Source, previews, equal-size pane screenshots and the complete payload inspection remain private in ignored `output/visual-first-live/retry-atom`. Do not reuse the historical call allowance or claim real Tutor continuation from that diagnostic. See the tracker E42–E45 for exact hashes, failures, costs and limits.

E46's approved one-batch evaluation ran all five frozen briefs once. Local Canvas author/reviewer were `gpt-6-luna` at medium reasoning with SDK retries disabled; the existing Tutor stayed `gpt-5.6-luna`. One initial custom source and at most one evidenced repair were enforced without changing shared production defaults. The refreshed frozen configuration is `output/visual-first-luna6/frozen-runtime-config.json` (SHA-256 `75fb0431a6f2124baf7a0c0ae9514b6c73c3cde34ff9b7915ce9ec1d332933e4`). The batch used 22 model requests, one hosted image call, no Code Interpreter calls, and USD 0.03887464 estimated model tokens plus a USD 0.25 image planning allowance (USD 0.28887464 total estimate; actual image charge unknown), below the approved 40/10/10/USD 5 ceilings. Addition and water cycle produced accepted backend Scenes. Addition rendered in Daily and its real single-answer/retry/conflict path and same-Tutor `gpt-5.6-luna` continuation passed. Water cycle rendered but visibly overlapped labels and crowded controls, so visual quality remains failed. Atom, solar-model and plant candidates were rejected; their first-pass/repaired artifacts remain private in the ignored output. See E46 and `gallery.html` there for all five.

E47 single-topic local live experiment is PARTIAL after a separate Product Owner authorization. The earlier zero-call preflight denial remains recorded. A disposable equivalent-fractions Tutor/Canvas run started five total model requests: two real `gpt-5.6-luna` Tutor turns and three explicit `gpt-6-luna` medium Canvas calls, including independent review. One generated custom visual passed production validation, independent review, owned local storage and 960/640 sandbox previews; exact owner-scoped API responses then rendered in the real Daily component at 690.6/666 px visual widths using browser transport fixtures. The saved Scene has no controls or answer attempt. Its 724-byte compact visual card reached the prepared same-Tutor payload; the real Tutor referred to the aligned shading. The handoff itself over-prescribed equal-sized bars and contained malformed `42f?`, so autonomous choice of teaching representation was not proved, although Canvas chose the custom-visual tool and source. Estimated model cost from durable executions is USD 0.00917701; actual billing is unknown. Focused E47 tests passed 18/18. Evidence is private under ignored `output/visual-teacher-spike/live-1`.

E48 HANDOFF CONTRACT REPAIR is LOCAL / UNCOMMITTED. New Tutor structured output delegates visual representation completely: it emits the learning objective and grounded educational content but not student_request, requested_representation, or must_not_imply. Application code binds the exact current Student message before Canvas admission; new briefs omit the two legacy prescription fields, while historical v1 briefs remain readable. Canvas/Tutor return-card behavior is unchanged. No provider call or visual regeneration was used for this repair.

E49 OPTIONAL MEMORY SUPPORT is LOCAL / UNCOMMITTED. Active JEV visual selection now evaluates only optional memory candidates: eligible Personal Facts plus already-selected Learning Intelligence Card entries. It returns at most three exact support keys; application code preserves each item's authority type in Visual Learner Context. JEV does not receive current conversation, source references, Core Profile or representation controls for this decision and cannot alter the Canvas learning objective. No provider call was used for this implementation.

E50 GENERAL TUTOR→CANVAS BOUNDARY REPAIR is LOCAL / UNCOMMITTED. Application code now owns Canvas source-reference identities in addition to the exact current learner request, across both ordinary Chat and Canvas-originated Tutor flows. Tutor output contains educational meaning only. Invalid/rejected Canvas brief or lifecycle metadata fails only the Canvas request, preserves safe Tutor text, removes unsupported visual promises, and records the rejection; security/ownership/provenance boundaries remain hard. Direct manipulation requests are covered by a general Canvas-surface guidance rule rather than topic-specific examples.

E51 FIVE-CASE E50 LIVE RERUN is COMPLETE / LOCAL. Three of five Tutor turns requested Canvas and passed E50 admission. Math accepted a first-pass custom interactive Scene and passed owner-scoped Daily API, real Daily browser rendering, LOCAL slider behavior and one real same-Tutor continuation. Pitch and diaphragm failed inside Canvas custom-visual quality/repair, not admission. Arabic direct-manipulation stayed Chat-only; lever stayed Chat-only. Pitch also demonstrates representation leakage through desired_student_action. E49 had no eligible memory candidates and therefore made zero JEV calls. Total evaluation usage including the Math continuation: 17 model requests, zero Image Generation, zero Code Interpreter, about USD 0.02758 ledger estimate. Review next: semantic handoff leakage, direct-manipulation surface selection, custom visual source/control repair reliability, and deterministic finalization after an accepted review.

E52 CORE VISUAL-TEACHING REPAIRS is LOCAL / UNCOMMITTED. Tutor-to-Canvas semantics now use a bounded learner-experience intent instead of free-form desired_student_action, preventing that field from prescribing waves/bars/sliders/layout. Primary Tutor output has an explicit auditable teaching_surface decision (CHAT or CANVAS) and instructions require Canvas when the requested learner action depends on direct visible manipulation that Chat cannot provide. Custom-visual authoring/repair now prioritizes runtime and interaction correctness, recommends truthful control semantics, discourages ambiguous DOM helpers, and preserves repair capacity when an exact source edit is rejected before changing source. Focused E52 regression: 276/276 passed. Full suite still has the known six fake-agent review failures plus three missing-DATABASE_URL PostgreSQL setup errors; those are not introduced by E52. No live provider validation has been run for E52 yet.

E53 E52 LIVE VALIDATION is COMPLETE / LOCAL. Arabic now deterministically routes direct manipulation to Canvas and generated an accepted typed Scene, but Daily proves the ORDERING renderer is unavailable-safe-fallback and the MATCHING UI is not yet learner-ready (mixed-language Place-in controls). Explicit visual-observation requests in Pitch/Biology initially remained Chat-only, so E53 generalized the existing surface-consistency repair to a narrow bilingual VISUAL_OBSERVATION guard; focused runtime regressions passed before rerun. Pitch and Biology then both reached Canvas with representation-neutral learner_experience briefs. Pitch custom controls functioned but the amplitude control remained outside the viewport after one repair; no Scene accepted. Biology custom phase control functioned with no browser technical findings, but independent review still rejected one remaining semantic/visual defect after repair. Total live usage: 16 model requests across both legs, ~USD 0.02236 ledger estimate, zero Image Generation, zero Code Interpreter. Next work should target typed ORDERING Daily support, matching-language UX, and reviewer-specific Pitch/Biology defects before another provider batch.

E54 LEARNER-FACING CANVAS REPAIRS is LOCAL / COMPLETE. Arabic typed ORDERING now renders in Daily with learner-controlled Arabic move actions and submit instead of the prior fallback; Arabic MATCHING controls are fully Arabic. Custom Visual sandbox has generic native-control containment and a regression for the Pitch two-column range-control overflow pattern. Custom visual authoring now warns against fixed CSS SVG heights that shrink actual screen text below acceptance, and both author/reviewer contracts prohibit causal strengthening beyond brief authority, addressing the Biology semantic-overclaim class. Verification: 205 relevant Python tests passed; 17/17 Agentic Canvas TS tests passed; E54 owner-scoped Daily browser passed; py_compile and diff check passed. The six known fake-agent reviewer tests remain baseline-only and unchanged. No live provider validation has been run after E54.

**Next gate:** E54 local repairs are complete. The next useful gate is one small live rerun of Arabic, Pitch and Biology to confirm the real Tutor/Canvas models honor the repaired learner-facing renderer, responsive authoring constraints, and causal-authority contract. Do not touch finalizer optimization or JEV in that rerun. A new paid-call authorization is required because prior allowances are closed.

Five-case Visual Teacher evaluation preparation (2026-10-01): The Product Owner supplied five new topics and explicitly requested no numeric request or cost ceiling. The current E48/E49 dirty worktree was inspected without reset or reconstruction; a disposable record-only harness and exact case strings were prepared. PostgreSQL `SELECT 1` passed in `lina_learning_test`; 98 focused E48/E49 tests and 23 harness/contract tests passed. Automatic approval review rejected the first provider command and a retry that cited the exact supplied attachment, because this review context did not accept attachment text as trusted paid-call authorization without numerical ceilings. No provider or hosted-tool request started and no five-case result exists. Preserve preparation and seek direct user authorization with explicit numerical ceilings before any paid execution; do not bypass review.

Five-case Visual Teacher execution (2026-10-01): The Product Owner then directly authorized one batch capped at 40 model requests, USD 5 estimated total, five image calls and five Code Interpreter calls. All five new synthetic Student turns ran once through the real `gpt-5.6-luna` Tutor on the disposable database; the shared ledger records five model requests, no JEV/Canvas/hosted-tool calls, and USD 0.01146883 durable-execution estimated cost (actual billing unverified). Math area/perimeter, pitch and diaphragm Tutor outputs each cited the current raw Student message ID as a Canvas source reference despite no selected retrieval source; the application bound the exact Student request, and the source authorization validator correctly rejected each brief. Those three provider executions succeeded but the foreground Tutor turns failed with no persisted Tutor reply. Arabic sentence order and lever mechanics produced persisted text replies without Canvas briefs. All optional-memory candidate lists were empty; no JEV selection ran. No Canvas candidate, independent review, accepted Scene, Daily screenshot, compact return card or same-Tutor continuation exists for this batch. No case was retried or repaired, and no architecture or production change was made. Evidence and per-case usage: ignored `output/visual-teacher-five-live/report.md` and `summary-private.json`. The unused batch capacity is not evidence of successful visual teaching.

## 2. TEACH-FLOW-01 — Teaching-flow integrity

**Status:** TEACHING CONTINUITY LOCALLY ACCEPTED; OTHER SUBSCOPES PENDING

**Teaching Continuity local result:** The Primary Tutor instructions now ask for one reachable learner action when an active goal remains unfinished, with explicit wrong-answer, DID_NOT_HELP, clarification, and relevant READY Canvas handling plus natural-closure exceptions. The frozen four-case focused Golden screen improved from 4/12 in the saved production baseline to 12/12 in the final three-repeat run. A single full 20-case regression pass scored 18/20 on raw model output; both failures were premature new-Canvas references repaired by the accepted server guard before delivery. The authenticated local browser also showed a concrete next action using a READY Canvas. This is local acceptance; GPT-6 deployed behavior remains to be checked. See `evals/tutor_golden/results/TEACHING_CONTINUITY_REVIEW_2026-09-28.md`.

**Tracker scope:**

- CONV-MOMENTUM-01
- STRATEGY-FIDELITY-01
- PED-ADAPT-01

**Purpose:** Make learner-visible teaching behavior match declared teaching semantics.

**Expected output:**

- unfinished guided learning leaves a useful next affordance when appropriate;
- EXPLAIN_THEN_CHECK contains an actual learner check when that strategy is selected;
- genuine DID_NOT_HELP causes a substantively different method or representation;
- legitimate targeted clarification is not misclassified as method failure.

**Likely areas:** services/tutor/runtime.py, teaching-decision contracts and tests, runtime/tutor/visual-guidance-v2.md.

**Verification required:**

- cross-subject fixture scenarios;
- no forced question after every answer;
- no new fixed teaching flow;
- live follow-up after local acceptance.

**Protected:** do not change Learning Intelligence semantics as a shortcut.

## 3. JEV-EVAL-01 — Bounded decision quality evaluation

**Status:** ACTIVE DATA COLLECTION

**Purpose:** Evaluate JEV where Lina already uses bounded decisions.

**Current decision slices:**

1. Visual Personalization fact selection.
2. Exact Canvas reuse selection.
3. Segment rubric comparison.
4. Visual Need decision — new repair-release slice; existing three semantic roles/modes remain unchanged.

**Expected output:**

- agreement and disagreement counts;
- representative disagreement cases;
- probability distributions;
- latency and cost;
- false-positive and false-negative patterns;
- recommendation per slice: retain current role, expand, narrow, or remove.

**Likely areas:** ai_executions, Canvas audit metadata, segment rubric decision records, and evaluation reporting.

**Verification required:**

- do not compare only synthetic examples;
- keep each decision slice separate;
- no authority expansion merely from popularity or a small sample.

**Blocked by:** enough real cases.

## 4. PERF-UX-01 — Tutor latency and buffering

**Status:** OPEN

**Tracker scope:** PERF-01, UX-BUFFER.

**Purpose:** Identify which phase creates learner-visible waiting.

Measure separately:

- context assembly;
- Primary Tutor provider time;
- bounded decision calls;
- terminal validation;
- persistence;
- proxy and SSE delivery;
- Canvas worker composition.

**Expected output:** phase-level latency evidence and one bounded recommendation.

**Do not:** redesign One Call or multi-call architecture before measurement.

## 5. PERSONALIZATION-RELEVANCE-01 — Relevance calibration

**Status:** IN REVIEW

**Purpose:** Prevent optional learner context from feeling forced or repetitive.

**Expected output:**

- identify repeated Personal-Fact use;
- verify source lineage;
- distinguish valid continuity from decorative insertion;
- tune selection only after multiple real cases.

**Protected:** Personal Facts must not become Learning Evidence or ability inference.

## 6. E2E-LIVE-01 — Real Tutor to Canvas acceptance

**Status:** IN REVIEW

**Purpose:** Continue validating the real deployed end-to-end path.

Expected path:

    Student
    → Primary Tutor
    → Canvas brief
    → Worker / Canvas
    → visible Scene
    → truthful Student action
    → Studio
    → same Primary Tutor

**Must observe:**

- graph and visual correctness;
- answer-hiding correctness;
- one foreground lane;
- recovery, reload, and retry behavior;
- no interaction storms;
- no false claim that a visual is visible;
- useful natural teaching continuation.

## 7. IMG-V2-01 — Educational generated images

**Status:** AGENT IMAGE-COMPOSITION INTEGRATION IMPLEMENTED LOCALLY UNDER 1D; BROADER GENERATED-IMAGE PRODUCT RULES STILL PLANNED

**Current agreed direction:**

- distinct capability;
- Science first;
- eligible need: shape, structure, process, or scene;
- structured Canvas remains Math-first;
- Canvas delivery;
- educational annotated output by default when useful;
- 10 successful visible generated images per learner per day;
- failed or invisible retries do not count;
- quota resets at learner-local midnight.

**Remaining before production enablement or broader implementation:**

- provider and model;
- questionable-output rejection and retry behavior;
- quota persistence and enforcement;
- exact annotation and delivery contract;
- acceptance plan.

## 8. AUTH-01 — Initial Daily auth refresh issue

**Status:** DEFERRED

Resolve only when it materially affects controlled use.

Do not mix it with Tutor or Canvas pedagogy work.

## 9. CALLS-01 — Foreground/background call responsibility study

**Status:** DEFERRED

When resumed, study:

- which background calls add real value;
- trivial-session suppression;
- candidate metadata responsibility;
- cost and latency;
- whether any call can move out of the foreground safely.

Do not start from a target call count.

## Completed foundations

The following are not active queues:

- Learning Intelligence core;
- Personal Facts and Core Profile;
- Student-source pipeline;
- Studio durable state;
- Agentic and Full-Power Canvas foundations;
- custom visual sandbox;
- reusable visual registry;
- REUSE, ADAPT, and CREATE;
- Tutor and Canvas repair slices E24 and E28;
- live App and Worker deployment baseline;
- JEV bounded-decision integration.

See docs/history, closure documents, and docs/TUTOR_CANVAS_REPAIR_TRACKER.md for detailed evidence.

## Verification baseline

For code changes:

- focused tests first;
- affected PostgreSQL tests;
- TypeScript typecheck when web is touched;
- actual browser proof for learner-visible visual behavior;
- python3 scripts/check_repository_truth.py;
- git diff --check;
- broader suite near closure when justified.

Always report unrun gates explicitly.
