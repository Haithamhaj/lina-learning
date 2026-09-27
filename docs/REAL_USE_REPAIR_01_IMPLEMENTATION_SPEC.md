# REAL-USE-REPAIR-01 — Implementation Specification

**Project:** Lina Personal Learning System  
**Status:** APPROVED STRUCTURE / IMPLEMENTATION SPEC  
**Date:** 2026-09-27  
**Owner:** Product Owner  
**Execution target:** Codex / AI implementation agents  
**Implementation language:** English  
**Scope state:** Locked unless a verified blocker requires Product Owner review

---

## 1. Executive intent

The first real Lina sessions exposed several defects and calibration gaps that are more valuable than continuing broad natural-use testing on the current baseline.

Natural-use validation is therefore temporarily paused. The next release is a bounded repair and recalibration release, not a redesign.

The release goal is to return Lina to real use with the following known problems corrected:

- Student source/image turns no longer hang and die at the infrastructure timeout.
- Recorded voice reliably becomes an editable transcript.
- Real Student Core Profile values can be initialized directly by an authorized operator for the pilot.
- Personal Memory can be tested from an actually eligible durable Personal Fact.
- The Tutor proactively uses the existing Canvas when a visual representation materially improves learning.
- Declared teaching strategies match the learner-visible move.
- One isolated incorrect attempt cannot mechanically become a durable support-need conclusion when stronger nearby evidence contradicts that conclusion.
- OpenAI routing moves to GPT-6 without changing the existing model-role philosophy.
- Internal cost estimates reflect current model pricing.
- JEV keeps its previously approved bounded roles and gains one new bounded visual-need decision slice.
- JEV can use TypeSafe direct API without coupling domain logic to a single transport provider.

This release is successful only when these corrections pass local, database, provider, browser, and controlled-live acceptance. A green unit test alone is not release acceptance.

---

## 2. Repository and production baseline

Implementation MUST start from the clean authorized worktree:

```text
/Users/haitham/development/Lina Personal Learning System/.worktrees/tutor-canvas-ab-01
```

Current branch:

```text
codex/tutor-canvas-ab-01
```

Current repository baseline at specification time:

```text
HEAD        74b09a374ec4e1ed5aceb93cad124c60092e22cb
origin/main 74b09a374ec4e1ed5aceb93cad124c60092e22cb
origin/codex/tutor-canvas-ab-01
            74b09a374ec4e1ed5aceb93cad124c60092e22cb
```

Do not touch the old dirty local main worktree.

Current production baseline observed during E30:

- GCP project: `project-lina-2016`
- Region: `europe-west1`
- App revision: `lina-app-00023-xt8`
- Worker revision: `lina-worker-00018-ckk`
- Alembic head: `c8e2f4a6b913`
- App model: `gpt-5.6-luna`
- Worker default model: `gpt-5.6-luna`

- Worker Canvas model: `gpt-5.6-luna`
- App JEV Visual Personalization: `shadow`
- Worker JEV Exact Canvas Reuse: `shadow`
- Worker JEV Segment Rubric: `shadow`
- JEV transport today: OpenRouter Decisions / `typesafe/jev-1.13`

Documentation edits made while defining this repair are intentionally uncommitted until this specification is approved and implementation begins.

---

## 3. E30 real-use evidence register

| Finding | Real evidence | Classification | Required action |
| --- | --- | --- | --- |
| Student source hang | Two source turns reached `/source/turn/stream`, each ended at ~300s with Cloud Run 504 | Runtime defect | Repair |
| Detached source ORM | ASGI traceback: `StudentSourceAsset` detached after request-side commit | Runtime defect | Repair |
| Voice failure | Five real STT attempts reached backend/provider path and returned 502 with `TranscriptionResponseError` | Runtime/provider adapter defect | Repair |
| Text Tutor continuity | Ordinary Tutor turns completed successfully, median ~5.7s in first session | Positive evidence | Preserve |
| DID_NOT_HELP method change | Sunlight explanation: `DECOMPOSITION` -> learner “i dont understand” -> `DID_NOT_HELP` -> `ANALOGY` | Positive teaching evidence | Preserve |
| Missing Canvas choice | Same sunlight turns persisted `canvas_brief=null` and no visual order; later Tutor offered to “draw” while still requesting no Canvas | Teaching/visual-choice defect | Repair |
| Strategy mismatch | Real sunlight turn declared `EXPLAIN_THEN_CHECK` but produced no actual check | Teaching contract defect | Repair |
| LI overreaction | 3 independent correct 5-times-table answers + one intentional wrong answer + supported recovery produced `active_difficulty` and ACTIVE `support_need` | LI projection calibration defect | Repair |
| Raw Evidence truth | Wrong answer remained correctly represented as an incorrect attempt; later recovery was separately represented | Positive evidence | Preserve |
| JEV rubric comparison | One real applicable shadow comparison, six findings, three disagreements | Evaluation evidence | Do not generalize |
| Personal Facts extraction | End-of-session extraction completed with 0 candidates / 0 accepted | Correct for observed inputs | Preserve |
| Core Profile missing | Real Student has null display name, null DOB, no active GradePeriod | Pilot readiness gap | Repair |
| Parent link missing | Real Student has zero parent relationships | Not a current blocker by Product Owner decision | Defer |
| Session recovery | Closed-session 404/409 was followed by successful retry and new session 200 | Positive reliability evidence | Preserve |

The implementation agent MUST distinguish “defect” from “positive evidence.” Do not rewrite behavior that worked merely because it appeared in the same session as a defect.

---

## 4. Governing decisions

These are approved decisions, not implementation suggestions.

1. **One Primary Tutor remains the learner-facing teacher.**
2. **Canvas is a representation/interaction surface, not a second Tutor.**
3. **Current Student behavior outranks historical context.**
4. **Core Profile, Personal Facts/Memory, Learning Intelligence, and raw conversation remain separate authorities.**
5. **Raw Evidence/provenance is not deleted or rewritten merely because a downstream conclusion is recalibrated.**
6. **JEV remains a bounded typed-decision component, never a general orchestrator or free-form teaching model.**
7. **The three existing JEV slices stay in their previously chosen roles and production modes unless separately approved.**
8. **A fourth JEV slice, Visual Need Decision, is approved.**
9. **Luna remains the default OpenAI class.**
10. **Any route intentionally placed on old Sol or Terra maps to GPT-6 Sol.**
11. **Astra is not a default Lina runtime model.**
12. **Generated-image capability is not required to repair proactive visual teaching. Existing Canvas capability must be used first.**
13. **Science shape / structure / process / scene eligibility rules from the planned visual-image work may be promoted into V1 visual-choice logic.**
14. **Parent linking is not required for this pilot repair.**
15. **The Product Owner may supply Lina Core Profile values directly for controlled operator bootstrap.**
16. **No production data mutation occurs until separately approved at execution time.**
17. **No deployment occurs automatically after implementation.**

---

## 5. Protected boundaries

The following MUST NOT be changed as a shortcut:

- Child-safety policy and non-overridable safety gates.
- Parent learning-boundary semantics.
- Student ownership and privacy isolation.
- Primary Tutor authority.
- Core Profile authority.
- Personal Facts authority.
- Raw Evidence lineage and source provenance.
- Studio durable-state authority.
- Custom visual sandbox boundary.
- One-foreground-lane arbitration.
- Existing truthful Canvas interaction rules.
- Existing session-recovery invariants.
- JEV bounded finite-answer design.
- Current conversation precedence over Memory.
- “Personal Facts are not Learning Intelligence.”
- “Canvas activity is not Evidence merely because it occurred.”

Any implementation need that materially changes one of these boundaries is a blocker and MUST return to the Product Owner.

---

## 6. Explicit non-scope

The repair release does NOT include:

- a new multi-agent teaching architecture;
- a second learner-facing Tutor;
- a general JEV orchestrator;
- generated educational image provider integration;
- image-generation quota persistence;
- image-generation moderation/rejection workflow;
- parent dashboard redesign;
- required Parent ↔ Student linking;
- a generalized onboarding product flow;
- CALLS-01 redesign of foreground/background responsibilities;
- a new Evidence ontology;
- rewriting historical Evidence;
- performance architecture redesign before measurement;
- broad UI redesign;
- curriculum dependency for Tutor availability.

---

## 7. Target runtime shape after repair

```text
Student turn
    |
    +--> deterministic safety / ownership / session checks
    |
    +--> optional bounded Visual Need decision
    |       - explicit visual request bypasses this decision
    |       - TypeSafe JEV primary transport after acceptance
    |       - finite typed outputs only
    |
    +--> Primary Tutor (GPT-6 Luna default)
    |       - receives bounded visual-need signal when applicable
    |       - chooses teaching mode/method and student-facing text
    |       - authors educational Canvas meaning when a visual is used
    |
    +--> Application validation / Canvas admission
    |       - eligibility
    |       - active/pending Scene truth
    |       - Safety / ownership / stale-state checks
    |
    +--> Worker
            - exact-reuse JEV role unchanged
            - GPT-6 Sol only on routes that were intentionally Sol/Terra-class
            - Canvas execution / persistence
```

Learning pipeline remains separate:

```text
Raw messages / Student actions
    -> Candidate Events
    -> Segment Review
    -> Learning Events
    -> Evidence
    -> Current State / Patterns
    -> Learner Intelligence
```

Personal continuity remains separate:

```text
Student explicit safe durable facts
    -> Personal Fact extraction
    -> Personal Facts + provenance
    -> selective Personal Memory projection
```

---

# WORKSTREAM A — Student source reliability

## 8. SOURCE-STREAM-01

### 8.1 Verified root cause

The request-side route stores or loads a `StudentSourceAsset`, commits the request-side SQLAlchemy Session, then the SSE generator later references the ORM object across the transaction/session boundary.

Production raised:

```text
sqlalchemy.orm.exc.DetachedInstanceError:
Instance <StudentSourceAsset ...> is not bound to a Session
```

The request then survived until Cloud Run terminated it at ~300 seconds.

This is not an OpenAI timeout and not an object-storage upload failure.

### 8.2 Required design

No SQLAlchemy ORM entity may cross from the authenticated request transaction into the stream-owned transaction.

Before request-side commit, retain only immutable primitive lineage required outside that Session, such as:

- source asset UUID;
- admitted Student message UUID;
- learning session UUID;
- student UUID;
- immutable storage identity when required.

Within the SSE generator, reload the owned source asset through `stream_session` before constructing provider source input. Ownership/session checks must still apply.

The response header `X-Lina-Source-Asset-ID` MUST use the captured primitive UUID, never a post-commit ORM attribute access.

The generator must have a bounded failure path. An unexpected source rehydrate/storage/provider preparation error MUST settle the admitted Student message truthfully and terminate the SSE response; it must not wait for infrastructure timeout.

### 8.3 Preserve

- Immutable original source remains authority.
- Existing file/image/PDF/DOCX validation limits.
- Storage compensation on pre-commit failure.
- Student ownership isolation.
- No raw source bytes in metadata/logs.
- Source is not Evidence by itself.
- Current source grounding rules in Tutor.

### 8.4 Likely files

- `apps/api/routes/student.py`
- `services/student_sources/service.py` only if a small rehydrate helper is justified
- source-stream regression tests

### 8.5 Mandatory tests

1. New image upload crosses request commit -> stream Session -> Tutor provider without detachment.
2. Existing owned source reuse crosses the same boundary.
3. Foreign source ID remains rejected.
4. Missing/deleted object storage fails boundedly.
5. Stream cancellation settles admitted message correctly.
6. Source failure does not create duplicate Student messages.
7. Header source ID remains truthful.
8. No 300s wait in deterministic failure test.
9. Existing source safety/grounding tests remain green.

### 8.6 Acceptance

Real authenticated browser:
```text
attach image -> ask a question -> source visible in transcript -> Tutor responds -> request completes
```

No 504, no ASGI detached-instance traceback, no duplicate admission.

---

# WORKSTREAM B — Voice / speech-to-text

## 9. VOICE-STT-01

### 9.1 Verified reality

Browser recording is reaching the server. Five real requests reached:

```text
POST /api/v1/student/daily/session/{id}/voice/transcribe
```

All five failed quickly with HTTP 502 and durable failed `speech_to_text` AI executions using `gpt-transcribe`.

Therefore do not redesign the microphone UI as if recording never occurred.

### 9.2 Current official provider contract

The current OpenAI file-transcription API recommends `gpt-transcribe`, accepts completed WebM/WAV and other supported files, and returns JSON containing `text` by default.

Implementation MUST explicitly request the intended response format rather than depend on an implicit default.

Required provider probe before code finalization:

- one tiny known-valid WebM sample;
- one WAV sample;
- current production API key/project;
- exact raw HTTP status and response Content-Type;
- sanitized response shape only, never transcript content in logs unless test fixture.

### 9.3 Required adapter behavior

Prefer the smallest fix that makes the current adapter conform exactly to the documented provider contract.

At minimum:
- set explicit `response_format=json`;
- preserve extension-bearing filename;
- preserve supported MIME type;
- normalize only documented response shapes;
- distinguish provider HTTP error from invalid successful response;
- record failure code truthfully;
- do not persist raw audio.

Do not silently switch to browser OS dictation as the product solution.

If the current handwritten multipart adapter remains fragile after the provider probe, replacing only this adapter with the official OpenAI SDK is allowed, provided dependency impact is bounded and the same Model Gateway ledger contract is preserved.

### 9.4 User experience contract

```text
record
-> stop
-> transcribe
-> editable text appears in composer
-> Student can correct text
-> Student explicitly sends
```

Transcription itself MUST NOT create a Student learning statement.

### 9.5 Likely files

- `services/model_gateway/openai_transcription_provider.py`
- `services/voice/transcription.py`
- `apps/api/routes/student.py`
- Student composer voice component/tests

### 9.6 Tests

- documented JSON `text` response;
- malformed JSON;
- HTTP provider failure;
- provider timeout;
- empty transcript;
- WebM;
- WAV;
- max-size guard;
- unsupported MIME;
- no raw audio persistence;
- execution lineage on success/failure;
- browser microphone -> transcript -> editable composer.

### 9.7 Acceptance

One real Windows-laptop Chrome flow and one local deterministic browser fixture MUST pass before release.

---

# WORKSTREAM C — Core Profile and Personal Memory readiness

## 10. CORE-PROFILE-BOOTSTRAP-01

### 10.1 Current live state

The real Lina Student currently has:

```text
display_name = null
date_of_birth = null
active GradePeriod = none
ParentStudentRelationship = none
```

Existing application code already supports the underlying Core Profile model and active GradePeriod service.

Parent linking is explicitly NOT required for this pilot repair.

### 10.2 Approved pilot design

Add a controlled operator-only bootstrap path, preferably a script/command rather than a new public HTTP endpoint.

Recommended artifact:

```text
scripts/bootstrap_student_core_profile.py
```

It should:
- identify exactly one existing Student through an operator-supplied stable identifier;
- refuse ambiguous lookup;
- accept display name;
- accept date of birth;
- accept active Grade and start date;
- call existing Core Profile / GradePeriod service logic;
- be idempotent for the same supplied values;
- print a bounded before/after summary without secrets;
- perform no Parent linking;
- create no Personal Facts;
- create no Learning Evidence.

Production execution of this operator script is a protected data mutation and requires explicit Product Owner approval when actual values are supplied.

### 10.3 Core Profile authority

Core Profile remains the sole authority for:
- learner display identity;
- date of birth;
- derived age;
- active Grade.

A Student saying “my name is Lina” in chat does not require a Personal Fact duplicate.

### 10.4 Verification

After bootstrap, a Tutor context debug record must show the expected bounded Core Profile fields and still show no fabricated Personal Memory.

Canvas presentation context may receive only the already-approved bounded Core Profile fields.

### 10.5 MEMORY-LIVE-01

The first real session did NOT prove Memory failure.

Personal Fact extraction completed successfully with:
```text
candidate_count = 0
accepted_count = 0
```

That outcome matches the observed conversation:
- identity belongs to Core Profile;
- “Windows laptop” is transient context.

### 10.6 Memory acceptance scenario

After Core Profile is initialized, use one explicit safe durable fact naturally supplied by the Student.

Required proof:
```text
Student statement
-> Personal Fact candidate
-> accepted fact + provenance
-> later session selective retrieval
-> natural optional use only when relevant
```

Current conversation must override stale Personal Memory immediately.

The test must also prove that the Tutor can choose NOT to use an available fact.

---

# WORKSTREAM D — Proactive visual teaching

## 11. VISUAL-CHOICE-01

### 11.1 Verified defect

Real sunlight example:

```text
Student: how does the sun bring its light to us?
Tutor:
  TeachingMode = LEARN
  TeachingStrategy = EXPLAIN_WITH_EXAMPLE
  TeachingMethod = DECOMPOSITION
  Canvas = null

Student: i dont understand
Tutor:
  TeachingMode = LEARN
  TeachingStrategy = EXPLAIN_THEN_CHECK
  TeachingMethod = ANALOGY
  PriorMethodRelation = DID_NOT_HELP
  Canvas = null
```

The method change was good. The representation choice was weak.

A later Tutor reply offered to draw a picture while still emitting no Canvas request.

### 11.2 V1 visual eligibility promoted from planned V2

For the current release, proactively consider existing Canvas for Science needs that are primarily:

- SHAPE
- STRUCTURE
- PROCESS
- SCENE

These categories do not authorize generated images. They authorize consideration of the existing structured/full-power Canvas.

### 11.3 Deterministic bypasses

Do NOT call JEV Visual Need when code already knows the answer.

**Explicit visual request** such as “draw it”, “show me a diagram”, or an unambiguous equivalent:
- bypass Visual Need model decision;
- proceed directly to safety/capability/current-state checks;
- Tutor still authors educational meaning.

**Visual cannot be used** because of safety, unresolved source meaning, unavailable capability, or an already-running equivalent visual:
- do not ask JEV to override known application state.

### 11.4 New bounded decision slice

Add:

```text
ModelTask.VISUAL_NEED_DECISION
```

Proposed finite outputs:

```text
visual_need:
  NONE
  HELPFUL
  STRONGLY_RECOMMENDED

visual_category:
  NONE
  SHAPE
  STRUCTURE
  PROCESS
  SCENE
```

Every answer must include calibrated probabilities/confidence from the decision provider.

JEV does NOT author a Canvas brief, scene, explanation, tool call, teaching method, or safety decision.

### 11.5 Decision inputs

Use the minimum approved state necessary, for example:

- current Student text;
- immediately relevant prior Tutor text or bounded previous method summary;
- current visual/Canvas state summary;
- current source-clarity flag;
- known capability eligibility;
- explicit-visual-request flag;
- available subject hint when already known.

Do NOT send:
- broad learner history;
- raw Personal Memory;
- raw Learning Intelligence card;
- hidden safety internals;
- source bytes;
- private storage identifiers;
- full transcript by default.

### 11.6 Placement in Tutor flow

Target flow:

```text
context assembly
-> deterministic visual bypass checks
-> bounded Visual Need decision when applicable
-> add decision signal to Tutor model payload
-> Primary Tutor generates text + optional canvas_brief
-> application validates/admit Canvas
```

This is intentionally a small pre-Tutor decision. It may add hundreds of milliseconds, not a second full teaching-generation call.

### 11.7 Tutor instruction effect

A `STRONGLY_RECOMMENDED` visual signal means:
- when an accurate supported visual is available and no higher-priority boundary blocks it, the Tutor should normally make the visual part of the current teaching move;
- it is not permission to fabricate a visual;
- it does not override explicit Student preference against a visual.

`HELPFUL` is advisory.

`NONE` does not prohibit a later explicit Student visual request.

### 11.8 Initial rollout mode

Add independent configuration:

```text
JEV_VISUAL_NEED_MODE=off|shadow|active
JEV_VISUAL_NEED_POLICY_VERSION=...
JEV_VISUAL_NEED_MIN_PROBABILITY=...
```

Implementation acceptance sequence:
1. deterministic fixture matrix;
2. replay E30 real transcript states in shadow/offline evaluation;
3. direct TypeSafe contract test;
4. compare false positive / false negative cases;
5. only then configure the new slice `active` for the controlled repair deployment.

This does NOT change the modes of the three previously approved JEV slices.

### 11.9 Required scenario matrix

Must include at least:
- sunlight process -> visual helpful/strong;
- sunlight + DID_NOT_HELP -> strong;
- plant parts/structure -> visual helpful/strong;
- simple factual “how long does sunlight take?” -> likely Chat/NONE or HELPUL below activation threshold;
- greeting -> NONE;
- multiplication direct fact -> NONE unless representation need is evident;
- explicit “draw it” -> bypass JEV;
- source unreadable -> visual decision cannot authorize reconstruction;
- already-running same visual -> no duplicate;
- Student says “just explain it, no picture” -> NONE / code-owned preference.

---

# WORKSTREAM E — Teaching fidelity

## 12. STRATEGY-FIDELITY-01

The system must stop declaring one strategy while showing another behavior.

For `EXPLAIN_THEN_CHECK`, a completed learner-visible turn MUST contain an actual academic check unless the turn is interrupted by a higher-priority safety/parent/source constraint.

A valid check may be:
- one direct question;
- a guided check;
- one concrete learner attempt request.

A decorative “does that make sense?” is not automatically a meaningful academic check.

Do not add a check to every Tutor turn. The contract applies when that strategy is selected.

Real sunlight regression:
```text
EXPLAIN_THEN_CHECK + ANALOGY
=> explanation + an actual learner check
```

## 13. PED-ADAPT-01 preservation rule

Do not regress the E30 good path:

```text
DECOMPOSITION
-> Student: "i dont understand"
-> DID_NOT_HELP
-> ANALOGY
```

Only repair cases where genuine DID_NOT_HELP still reuses essentially the same method/representation.

A visual representation can be the method-supporting representation change when Visual Need is strong, but Canvas itself is not a TeachingMethod.

---

# WORKSTREAM F — Learning Intelligence calibration

## 14. LI-CALIBRATION-01

### 14.1 Raw sequence that exposed the defect

```text
5 × 3 = 15  -> independent success
5 × 4 = 20  -> independent success
5 × 5 = 25  -> independent success
5 × 6 = 45  -> incorrect attempt (intentional system test)
Tutor scaffold
5 × 6 = 30  -> guided success
strategy outcome -> helped
```

The raw incorrect attempt is real conversation evidence and MUST remain preserved.

### 14.2 Current downstream problem

Current deterministic pattern targeting treats:
- partial/not-demonstrated understanding as support need;
- moderate/substantial/full support as support need.

Therefore the same local episode can create multiple supporting links:

```text
incorrect_attempt -> support_need support
guided_success -> support_need support
strategy_outcome -> support_need support
```

The resulting count reached the ACTIVE threshold despite three independent successes immediately beforehand.

### 14.3 Required semantic correction

Do not solve this by deleting the incorrect Evidence.

Do not solve this merely by replacing Luna rubric output with JEV.

Recalibrate downstream Current State / Pattern semantics so that:
- one isolated incorrect attempt can create a short-lived/open learning signal when appropriate;
- recovery from that same attempt does not mechanically multiply support-need evidence;
- successful strategy outcome is primarily evidence about strategy effectiveness, not an additional independent proof of learner weakness;

- prior or later independent successes can counter/resolve a support-need conclusion when they concern the same concept and comparable task;
- durable ACTIVE support need requires genuinely repeated or sufficiently strong independent evidence, not multiple projections of one causal episode.

### 14.4 Causal grouping requirement

Evidence derived from the same candidate event / same Student attempt / same immediate correction episode must not be counted as independent repeated support signals merely because it produced multiple Evidence rows.

Prefer explicit causal/provenance-aware weighting or role assignment over arbitrary numeric threshold inflation.

### 14.5 Current State behavior

For the E30 sequence, acceptable outcomes include a bounded temporary/open learning-loop signal while the incorrect answer is unresolved.

After immediate successful recovery plus nearby independent successes, the system should not finish the session with an unqualified durable `active_difficulty` solely from that episode.

### 14.6 Pattern behavior

`support_need` must distinguish:
- repeated independent support-need observations;
- multiple semantic rows describing one support episode.

The latter must not satisfy recurrence by itself.

### 14.7 JEV rubric remains advisory

The real JEV shadow case disagreed with Luna on three of six findings. It was better on some recovery semantics and harsher on the wrong answer itself.

That is evidence for continued evaluation, not authority promotion.

### 14.8 Mandatory mixed-evidence tests

1. Three independent successes + one wrong + guided recovery.
2. One wrong with no recovery.
3. Repeated independent wrong attempts across distinct tasks.
4. One guided success with no prior independent proof.
5. Strategy outcome linked to same candidate event as guided success.
6. Independent later success countering an older support need.
7. Same evidence reprocessing remains idempotent.

8. Historical provenance remains intact.
9. Card/Tutor context reflects recalibrated State/Pattern without rewriting raw Evidence.

---

# WORKSTREAM G — JEV provider architecture

## 15. Existing JEV roles are preserved

The existing bounded slices remain:

1. Canvas Visual Personalization.
2. Exact Canvas Reuse.
3. Segment Rubric shadow comparison.

Do not move them to different semantic roles.

Production mode intent remains as currently configured unless separately approved:

```text
Visual Personalization = shadow
Exact Canvas Reuse     = shadow
Segment Rubric         = shadow
```

The new fourth slice is:

```text
Visual Need Decision
```

## 16. TypeSafe direct provider

### 16.1 Goal

Remove unnecessary coupling between “JEV” and “OpenRouter” while preserving the existing provider-neutral Model Gateway and AI execution ledger.

Target abstraction:

```text
create_jev_decision_gateway(...)
    -> configured Jev provider
       -> TypeSafe direct
       -> or OpenRouter compatibility route
```

### 16.2 Configuration

Add server-only settings similar to:

```text
JEV_PROVIDER=typesafe|openrouter
TYPESAFE_API_KEY=<secret>
TYPESAFE_API_BASE_URL=<documented direct API base>
OPENROUTER_API_KEY=<existing optional key>
JEV_MODEL_NAME=<configured Jev version>
JEV_TIMEOUT_SECONDS=5
```

A configured key alone MUST NOT enable any JEV slice.

Each slice keeps an independent mode and policy version.

### 16.3 Direct wire contract

Do not infer the TypeSafe native wire format from the OpenRouter alpha endpoint.

Implementation MUST use the authenticated TypeSafe documentation available with the direct account/API key at implementation time.

The adapter contract inside Lina remains domain-neutral:
- input: bounded `state` + typed finite `questions`;
- output: typed answers + probabilities/confidence + normalized usage/cost metadata when provided;
- timeout and provider failures normalized to a bounded provider error.

### 16.4 Provider selection policy

TypeSafe direct is the target primary transport after its contract tests pass.

OpenRouter remains available as:
- configuration rollback;
- comparison transport during migration;
- not an automatic hidden second call by default.

Do not cascade TypeSafe failure into OpenRouter automatically unless separately approved; domain fallbacks already exist and avoid hidden double cost/latency.

### 16.5 Fail-closed domain behavior

Visual Personalization JEV failure:
- no delegated fact selection; safe existing fallback behavior.

Exact Reuse JEV failure:
- no JEV reuse shortcut; continue normal validated Canvas path.

Segment Rubric JEV failure:
- shadow failure only; Luna review remains authoritative under current design.

Visual Need JEV failure:
- do not invent a strong visual recommendation;
- Tutor may continue with its normal current guidance and explicit visual requests still work deterministically.

### 16.6 Security

- Never commit either API key.
- Store TypeSafe key in GCP Secret Manager at deployment time.
- Suggested secret name: `lina-typesafe-api-key`.
- Do not print key material.
- Send only slice-minimal learner-derived state.
- Preserve child-safety and privacy policy for external decision providers.

### 16.7 Reliability risk

TypeSafe is early-access infrastructure and has had recent API incidents. Therefore direct-provider acceptance MUST include timeout/failure handling and a configuration rollback path.

---

# WORKSTREAM H — GPT-6 migration

## 17. MODEL-GPT6-01

### 17.1 Approved mapping

```text
gpt-5.6-luna  -> gpt-6-luna
old Sol route -> gpt-6-sol
old Terra route -> gpt-6-sol
Astra -> not a default runtime route
```

Do not flatten every task to Sol.

Do not promote a route merely because GPT-6 exists.

### 17.2 Route inventory gate

Before editing configuration, enumerate every actual model route in:
- Model Gateway factories;
- Canvas worker/agent settings;
- Personal Facts;
- Segment Evidence;
- development review;
- any explicit test/production override.

For each route record:
- current model;
- historical intent (Luna vs Sol/Terra class);
- latency sensitivity;
- structured-output contract;
- image input requirement;
- production criticality.

Only then apply the approved mapping.

### 17.3 API compatibility

Current Lina text generation already uses OpenAI Responses API with:
- streaming;
- strict JSON schema structured outputs;
- image/file input where applicable.

GPT-6 Luna and GPT-6 Sol officially support Responses API, streaming, structured outputs, and image input.

The migration should therefore be configuration/provider-contract oriented, not an application architecture rewrite.

### 17.4 No simultaneous prompt redesign

Keep:
- Tutor instructions;
- response schema;
- teaching contracts;
- Canvas brief schema;
- reasoning effort behavior

unchanged for the first GPT-6 acceptance unless a documented incompatibility requires a minimal fix.

This isolates model effects from prompt/architecture effects.

### 17.5 Acceptance matrix

At minimum compare GPT-5.6 Luna baseline vs GPT-6 Luna on:
- greeting;
- bilingual Arabic/English switch;
- multiplication practice;
- wrong-answer correction;
- DID_NOT_HELP;

- sunlight visual-choice input;
- strict `tutor_turn_v13`;
- Student image input after source repair;
- Segment Review;
- Personal Fact extraction.

Canvas Sol-class routes must separately prove the existing structured/agent contract on GPT-6 Sol.

---

# WORKSTREAM I — Cost ledger

## 18. COST-RATE-01

### 18.1 Verified defect

Current `services/model_gateway/pricing.py` stores only an older GPT-5.6 Luna rate card:

```text
input  $0.50 / MTok
cached $0.05 / MTok
write  $0.625 / MTok
output $3.00 / MTok
```

Current official GPT-5.6 Luna standard short-context pricing is lower, so historical E30 `estimated_cost_usd` values were overstated.

### 18.2 Required rate card

At implementation time, encode the current official standard short-context rates used by Lina.

Verified 2026-09-27:

```text
GPT-5.6 Luna
input        $0.20 / MTok
cached input $0.02 / MTok
cache write  $0.25 / MTok
output       $1.20 / MTok

GPT-6 Luna
input        $0.10 / MTok
cached input $0.01 / MTok
cache write  $0.125 / MTok
output       $0.50 / MTok

GPT-6 Sol
input        $2.00 / MTok
cached input $0.20 / MTok
cache write  $2.50 / MTok
output       $10.00 / MTok
```

Prompts above the provider long-context threshold must use the documented long-context rates for the full request.

### 18.3 TypeSafe/JEV cost

Prefer provider-reported cost when available.

TypeSafe publicly states Jev input pricing of $42 per billion input tokens ($0.042/MTok) and unmetered/free output tokens at specification time.

Do not hardcode this as a forever price without a provider-rate version/date.

### 18.4 Historical records

Do NOT rewrite old `ai_executions.estimated_cost_usd` rows in this repair.

Those rows are historical estimates under the code/rate card that existed when they were recorded.

If corrected historical reporting is later needed, calculate it in a separate analytical query/view with an explicit rate-card version.

### 18.5 Distinguish ledgers

- `ai_executions.estimated_cost_usd` = application model-call estimate/provider reported decision cost.
- BigQuery Cloud Billing export = actual GCP infrastructure/account billing.
- OpenAI invoice/platform spend = external provider billing.

Never present one as another.

---

## 19. External references verified for this spec

OpenAI:
- GPT-6 release changelog: https://developers.openai.com/api/docs/changelog
- GPT-6 Luna: https://developers.openai.com/api/docs/models/gpt-6-luna
- Model catalog / GPT-6 Sol: https://developers.openai.com/api/docs/models
- Pricing: https://developers.openai.com/api/docs/pricing
- GPT-5.6 Luna: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- Speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text

TypeSafe:
- Product/pricing overview: https://typesafe.ai/
- System One / Jev introduction: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Service status: https://status.typesafe.ai/
- Master customer agreement: https://typesafe.ai/legal/mca
- Data processing addendum: https://typesafe.ai/legal/data-processing

Authenticated TypeSafe native API documentation from the Product Owner's direct account is the implementation authority for the exact native request path/schema.

---

# WORKSTREAM J — Telemetry and audit

## 20. Required decision observability

For every bounded JEV call, the system must be able to answer:

```text
task
provider
resolved model
policy version
mode: shadow|active
source Student/session lineage
input-state schema version
typed answer
probabilities/confidence
threshold
applied? yes/no
application final action
latency
input/output usage when reported
estimated/provider-reported cost
failure code
```

Do not persist full hidden prompts or broad learner context merely for observability.

### 20.1 Visual Need audit

At minimum persist enough metadata to compare:
- JEV recommendation;
- Tutor actual Canvas request;
- application admission/rejection;
- final visible Scene outcome;
- explicit Student visual request vs inferred visual need.

This can live in existing AIExecution + Tutor message metadata unless a concrete query/audit need proves a new table necessary.

---

# WORKSTREAM K — Database and migration policy

## 21. Migration impact

Default position: **no new database table unless necessary**.

Expected changes that should NOT require a migration:
- source Session-boundary repair;
- STT adapter repair;
- visual guidance;
- JEV provider transport configuration;
- GPT-6 model config;
- pricing rate card;
- Core Profile operator script using existing tables.

Potential schema change:
- new `ModelTask.VISUAL_NEED_DECISION` may require only enum/application code if ModelTask is persisted as a string-backed enum; verify actual DB constraints before deciding.
- if a DB enum/check constraint exists, add the smallest migration required.

Do not create a VisualNeed table by default.

LI calibration should update deterministic projection logic, not schema, unless a causal-grouping field is proven necessary and cannot be derived safely from existing candidate/event/review lineage.

Any migration must:
- have upgrade/downgrade where project convention requires;
- preserve existing rows;
- be tested on disposable PostgreSQL;
- be applied before code that depends on it.

---

# WORKSTREAM L — File-level change map

## 22. Likely files by slice

### Source
- `apps/api/routes/student.py`
- `services/student_sources/service.py` if needed
- source streaming tests

### Voice
- `services/model_gateway/openai_transcription_provider.py`
- `services/voice/transcription.py`
- `apps/api/routes/student.py`
- Student web voice component/tests

### Core Profile
- `services/platform/core_profile.py` only if reusable helper is missing
- new controlled operator script under `scripts/`
- Core Profile tests

### Visual choice / JEV
- `services/platform/db/models.py` for new ModelTask
- `services/platform/config/settings.py`
- `.env.example`
- `services/model_gateway/factory.py`
- new TypeSafe decision provider under `services/model_gateway/`
- existing OpenRouter provider remains
- bounded visual-need decision module under an appropriate Tutor/decision package
- `services/tutor/runtime.py`
- `runtime/tutor/visual-guidance-v2.md`
- Tutor/JEV/provider tests

### Teaching fidelity
- `services/tutor/runtime.py`
- teaching-decision contracts/tests
- visual guidance only where representation guidance belongs

### Learning Intelligence
- `services/intelligence/current_state.py`
- `services/intelligence/patterns.py`
- session finalization / projection tests
- no Segment Review authority rewrite unless a verified bug is found there

### Model migration / cost
- `services/model_gateway/pricing.py`
- model configuration/deployment files
- factory tests
- production runbook/reference docs

### Documentation
- `TASKS.md`
- `project-state/PROJECT_STATE.md`
- `docs/TUTOR_CANVAS_REPAIR_TRACKER.md`
- this specification
- deployment docs after accepted implementation truth exists

No agent may make unrelated cleanup changes in these files while touching them.

---

# WORKSTREAM M — Acceptance matrix

## 23. Product and technical acceptance

| Scenario | Expected result |
| --- | --- |
| New image source + question | Tutor completes; no detached ORM; no infrastructure timeout |
| Existing owned image reused | Correct source grounding; one Student turn |
| Foreign source | Fail closed |
| Voice WebM | Transcript returns to editable composer |
| Voice WAV | Transcript returns |
| STT provider malformed response | Bounded failure, truthful execution |
| Greeting | No unnecessary Canvas |

| “How does sunlight reach us?” | Visual decision evaluated; no decorative visual required if below threshold |
| Sunlight + “I don't understand” | DID_NOT_HELP preserved; strong visual need should produce Canvas when eligible |
| Explicit “draw it” | Visual Need decision bypassed; capability checks proceed directly |
| Already-running same visual | No duplicate composition |
| Source unreadable | No fabricated reconstruction |
| EXPLAIN_THEN_CHECK | Contains actual academic check |
| DID_NOT_HELP | Method changes materially; E30 DECOMPOSITION->ANALOGY path remains valid |
| 3 correct + 1 wrong + recovery | Raw wrong Evidence remains; no exaggerated durable support need from one causal episode |
| Repeated independent wrong tasks | Support need can become active when policy threshold genuinely met |
| Core Profile bootstrap | Tutor receives name/age/grade authority |
| “My favorite X is Y” eligible fact | Durable PF with provenance when safe/eligible |
| Later relevant session | PF selectively retrievable |
| Later irrelevant session | PF may remain unused |
| GPT-6 Luna strict Tutor output | Valid `tutor_turn_v13` |
| GPT-6 Sol Canvas route | Existing agent/structured contract passes |
| TypeSafe direct healthy | Typed decision + probabilities + ledger |
| TypeSafe direct unavailable | Domain-safe fallback, no broken Tutor |
| Existing JEV slices | Same semantic roles and configured modes |

---

# WORKSTREAM N — Verification gates

## 24. Required verification order

Each execution slice runs its focused tests first. Near closure run the combined affected matrix.

Required gates:

1. **Static/source review**
   - exact diff scope;
   - no unrelated architecture churn.

2. **Focused unit/contract tests**
   - source boundary;
   - STT provider;
   - Visual Need decision;
   - Tutor strategy fidelity;
   - LI projection semantics;
   - TypeSafe adapter;
   - pricing.

3. **Disposable PostgreSQL**
   - source admission/lineage;
   - Core Profile/GradePeriod;
   - JEV ledger;
   - LI Current State/Pattern lifecycle;
   - session finalization/reprocess idempotency.

4. **TypeScript typecheck**
   - required when web code changes.

5. **Provider contract probes**
   - real OpenAI `gpt-transcribe`;
   - real GPT-6 Luna;
   - real GPT-6 Sol only on its intended slice;
   - real TypeSafe direct Jev.

6. **Browser proof**
   - source upload;
   - voice;
   - proactive Canvas;
   - no visual on trivial case;
   - Canvas recovery remains intact.

7. **Affected broad regression**
   - Tutor;
   - Studio/Canvas;
   - Learning Intelligence;
   - Personal Facts;
   - session lifecycle;
   - safety/ownership.

8. **Repository checks**
   - `python3 scripts/check_repository_truth.py`
   - `git diff --check`
   - clean intended worktree state before commit.

Known baseline failures must be distinguished from new regressions by exact evidence, never waved away generically.

---

# WORKSTREAM O — Deployment and rollback

## 25. Deployment prerequisites

No deployment until:
- all mandatory acceptance gates pass;
- implementation review confirms protected boundaries;
- Product Owner approves production change;
- TypeSafe API key is stored in Secret Manager if direct provider is included;
- Lina Core Profile values are supplied and the Product Owner separately approves the data mutation;
- migrations, if any, are reviewed.

### 25.1 Recommended deployment order

```text
1. migration (only if required)
2. secrets/config availability
3. Worker revision
4. App revision
5. health/startup checks
6. provider smoke
7. authenticated Student smoke
8. controlled Lina retest
```

### 25.2 Model/JEV configuration

Deployment must make the configured model/provider modes explicit in the closure record.

Expected target after acceptance:
- Primary/default: `gpt-6-luna`
- historical Sol/Terra-class route: `gpt-6-sol`
- existing JEV three modes unchanged
- new Visual Need: `active` only if its pre-deploy acceptance passes
- TypeSafe direct: selected provider only after native contract probe passes

### 25.3 Rollback

Rollback must be possible independently for:
- App revision;
- Worker revision;
- model names;
- JEV provider `typesafe|openrouter`;
- new Visual Need mode `active -> shadow/off`.

Rollback MUST NOT require deleting learning data.

If LI policy changes create new derived State/Pattern rows, use the project's versioned/reprocessing lifecycle for any rollback/recompute; do not mutate raw Evidence manually.

---

# WORKSTREAM P — Execution slices for Codex

## 26. Slice order

Do not send one giant Codex implementation prompt.

### R01 — Source stream boundary
**Purpose:** close SOURCE-STREAM-01.  
**Output:** no ORM entity crossing request -> SSE Session; bounded source failures.  
**Dependencies:** none.  
**Verification:** focused source tests + PostgreSQL.

### R02 — Voice STT
**Purpose:** close VOICE-STT-01.  
**Output:** provider-conformant file transcription and editable transcript UX.  
**Dependencies:** provider probe.  
**Verification:** adapter + route + browser + real provider.

### R03 — Core Profile operator bootstrap
**Purpose:** make real pilot Core Profile usable without Parent linking.  
**Output:** controlled idempotent operator script + tests.  
**Dependencies:** none for code; real values only at production execution.  
**Verification:** profile/grade context tests.

### R04 — TypeSafe direct provider foundation
**Purpose:** decouple JEV semantics from OpenRouter transport.  
**Output:** provider adapter, provider selection config, ledger normalization.  
**Dependencies:** authenticated direct API documentation/key for live probe.  
**Verification:** fixture adapter + real direct call + failure behavior.

### R05 — Visual Need bounded decision
**Purpose:** add fourth JEV slice without changing existing three.  
**Output:** typed decision, modes, thresholds, audit metadata, deterministic bypasses.  
**Dependencies:** R04 for direct provider; can be locally tested with fixture provider first.  
**Verification:** decision matrix + E30 replay.

### R06 — Tutor visual choice + strategy fidelity
**Purpose:** consume bounded visual signal and close VISUAL-CHOICE-01 / STRATEGY-FIDELITY-01 while preserving good DID_NOT_HELP.  
**Output:** Canvas used when materially useful; actual check when EXPLAIN_THEN_CHECK.  
**Dependencies:** R05 contract.  
**Verification:** Tutor scenario matrix + real Canvas browser proof.

### R07 — LI mixed-evidence calibration
**Purpose:** close LI-CALIBRATION-01.  
**Output:** causal episode no longer inflates recurrence; raw Evidence preserved.  
**Dependencies:** none on JEV.  
**Verification:** mixed-evidence PostgreSQL matrix + reprocess idempotency.

### R08 — GPT-6 route migration
**Purpose:** map existing model-role intent to GPT-6.  
**Output:** route inventory + model config change + provider acceptance.  
**Dependencies:** accepted representative model tests.  
**Verification:** GPT-6 Luna/Sol matrix.

### R09 — Cost rate card
**Purpose:** close COST-RATE-01.  
**Output:** versioned/current rates and long-context handling.  
**Dependencies:** final route inventory.  
**Verification:** token-category cost unit tests.

### R10 — Integrated repair acceptance
**Purpose:** prove slices work together.  
**Output:** combined technical acceptance report.  
**Dependencies:** R01-R09.  
**Verification:** affected broad suite + browser/provider proof.

### R11 — Deployment readiness / closure
**Purpose:** prepare exact commit/revision/migration/secret/config record.  
**Output:** release checklist; no deployment unless separately authorized.

---

## 27. Codex operating rules for this release

Every Codex slice prompt must state:

- inspect current code before editing;
- work only in the clean authorized worktree;
- preserve unrelated user changes;
- do not touch dirty main;
- do not broaden scope;
- do not invent product decisions;
- do not silently change JEV modes;
- do not silently change model routing beyond the approved mapping;
- do not deploy;
- do not mutate production data;
- run focused verification;
- report exact changed files;
- report exact unrun gates;
- stop and return if a protected boundary must change.

Commit only after independent review/acceptance for the slice or approved combined batch.

---

# WORKSTREAM Q — Risks, assumptions, open questions, recommendations

## 28. Risks

| Risk | Priority | Mitigation | Risk if ignored |
| --- | ---: | --- | --- |
| Visual Need over-triggers Canvas | 5 | typed categories, confidence threshold, deterministic bypasses, scenario matrix | clutter/latency and worse learning UX |
| LI recalibration becomes too permissive | 5 | preserve raw Evidence; repeated-independent-failure tests | real support needs get hidden |
| LI remains too sensitive | 5 | causal grouping + counter-evidence | learner gets mislabeled by one episode |
| TypeSafe direct instability | 4 | timeout, fail-closed behavior, config rollback to OpenRouter | Tutor/Canvas path becomes dependent on early-access outage |
| GPT-6 behavioral drift | 4 | same prompts/contracts first; A/B representative cases | model change confused with teaching change |
| STT fix based on guessed response shape | 4 | real provider probe + explicit format | repeated 502 continues |
| Core Profile script targets wrong Student | 5 | exact unambiguous lookup + dry-run/before-after summary | protected personal data written to wrong account |
| Memory test forces personalization | 3 | prove “available but unused” is valid | creepy/repetitive personalization |

## 29. Assumptions

These are assumptions to verify during implementation, not approved facts:

- Existing model gateway can support a second JEV transport with a small factory refactor.
- Existing AIExecution metadata is sufficient for Visual Need audit without a new table.
- Source streaming can be repaired without changing source storage schema.
- STT failure is adapter/provider-contract related; exact cause still requires the real provider probe.
- Visual Need pre-Tutor latency is acceptable if kept within a bounded decision call.
- Current Canvas capabilities can represent the initial Science process/structure scenarios without generated-image support.

If any assumption fails and changes architecture materially, return to Product Owner.

## 30. Open questions — non-blocking for implementation start

1. Exact Lina Core Profile values.
   - Collected only when production bootstrap is approved.
2. Exact TypeSafe native API wire path/schema.
   - Use authenticated current TypeSafe documentation during R04.
3. Final Visual Need probability threshold.
   - Calibrate from fixture + E30 replay; do not guess in production.
4. Whether TypeSafe model should use a pinned exact version or provider alias.
   - Prefer a pinned version when the direct API supports stable version pinning; verify current direct docs.
5. Whether generated educational images should be promoted after this release.
   - Decide only after current Canvas is actually used proactively.

None of these require Parent linking for the pilot.

## 31. Recommendations

### Recommendation 1 — Consolidated repair before more natural testing
**Mandatory:** Yes  
**Priority:** 5  
**Reason:** Current live evidence already exposes blockers and calibration errors.  
**Expected impact:** Cleaner second real-use baseline.  
**Risk of ignoring:** More learner data is collected through known-broken source/voice/LI/visual paths.

### Recommendation 2 — Use current Canvas before generated images
**Mandatory:** Yes for this release  
**Priority:** 5  
**Reason:** The sunlight defect is a selection problem, not lack of renderer capability.  
**Expected impact:** Immediate learning value without a new image-generation subsystem.  
**Risk of ignoring:** V2 becomes a workaround for a V1 teaching-choice defect.

### Recommendation 3 — Add JEV Visual Need as a bounded pre-Tutor signal
**Mandatory:** Yes under approved scope  
**Priority:** 4  
**Reason:** It is a System-One-shaped routing/classification decision and avoids a brittle rule tree.  
**Expected impact:** Fast, cheap, auditable visual-choice signal while Tutor retains educational authority.  
**Risk of ignoring:** Visual choice remains buried in a long generative Tutor response and may repeat E30 behavior.

### Recommendation 4 — Preserve existing JEV roles/modes
**Mandatory:** Yes  
**Priority:** 5  
**Reason:** Product Owner explicitly rejected changing previously chosen JEV placements as part of this repair.  
**Expected impact:** Clean attribution of new behavior to the new slice/provider transport.  
**Risk of ignoring:** Repair becomes an uncontrolled JEV authority expansion.

### Recommendation 5 — TypeSafe direct as primary transport after proof
**Mandatory:** No; recommended  
**Priority:** 3  
**Reason:** Removes one intermediary and gives direct provider control/telemetry.  
**Expected impact:** Simpler provider relationship and potentially lower latency; cost is already very low.  
**Risk of ignoring:** Continued OpenRouter dependency; not a correctness failure.

### Recommendation 6 — Core Profile direct operator bootstrap for pilot
**Mandatory:** Yes before personalization acceptance  
**Priority:** 5  
**Reason:** Core identity/age/Grade authority is empty for the real account.  
**Expected impact:** Age/Grade-aware Tutor and visual context can finally be evaluated.  
**Risk of ignoring:** Memory/personalization tests are evaluated against missing authoritative context.

### Recommendation 7 — Fix LI downstream semantics, not raw history
**Mandatory:** Yes  
**Priority:** 5  
**Reason:** Raw evidence was mostly truthful; projection recurrence was the defect.  
**Expected impact:** Better calibrated learner state without hiding mistakes.  
**Risk of ignoring:** One local episode can become an exaggerated durable learner label.

---

# WORKSTREAM R — Release exit criteria

## 32. Exit criteria before Real-Use Validation 02

All mandatory items must be true:

### Reliability
- [ ] Source image/file turn completes without detached ORM or infrastructure timeout.
- [ ] Voice transcription works on real supported browser audio.
- [ ] Session recovery regressions remain green.

### Learner context
- [ ] Controlled operator Core Profile bootstrap exists and is tested.
- [ ] Real Lina Core Profile can be populated only after explicit production-data approval.
- [ ] Personal Memory has one valid end-to-end acceptance case or is explicitly reported as not yet exercised.

### Teaching
- [ ] Visual Need decision contract accepted.
- [ ] Explicit visual requests bypass JEV decision appropriately.
- [ ] Science visual-choice scenarios use Canvas when the bounded signal/application rules require it.
- [ ] No unnecessary Canvas on trivial/casual scenarios.
- [ ] EXPLAIN_THEN_CHECK has an actual check.
- [ ] E30 DID_NOT_HELP method-change behavior remains valid.

### Learning Intelligence
- [ ] E30-like mixed evidence no longer creates exaggerated durable support need from one causal episode.
- [ ] Repeated independent difficulty can still create support need.
- [ ] Raw Evidence and provenance remain intact.
- [ ] Reprocessing remains idempotent.

### Models / decisions
- [ ] GPT-6 route inventory approved.
- [ ] GPT-6 Luna passes representative Tutor/Segment/PF contracts.
- [ ] GPT-6 Sol passes every route mapped from old Sol/Terra intent.
- [ ] Current three JEV slice roles/modes remain unchanged.
- [ ] New Visual Need slice passes provider/decision acceptance.
- [ ] TypeSafe direct either passes and is selected, or OpenRouter remains the explicit configured transport.

### Cost / operations
- [ ] OpenAI rate card matches current verified pricing.
- [ ] Long-context pricing behavior is tested.
- [ ] JEV cost/usage is recorded when provider supplies it.
- [ ] No secrets are committed.
- [ ] `git diff --check` passes.
- [ ] repository truth check passes.
- [ ] affected regression has no unexplained new failures.
- [ ] exact unrun gates are documented.

### Release control
- [ ] implementation commit(s) reviewed.
- [ ] migration plan reviewed if any.
- [ ] deployment config documented.
- [ ] Product Owner explicitly authorizes deployment.
- [ ] Product Owner explicitly authorizes any real Core Profile data mutation.
- [ ] controlled Lina retest begins only after deployment smoke passes.

---

## 33. What success should feel like in the next Lina session

The next real session should not require Lina to know product internals.

She should be able to:
- type naturally;
- record speech and get editable text;
- attach a worksheet/photo and receive a grounded response;
- say “I don't understand” and get a genuinely different teaching move;
- see a diagram/process when seeing it is materially better than more prose;
- continue in Chat when a visual adds no value;
- make one mistake without the system prematurely concluding a durable weakness;
- have age/Grade-aware presentation once Core Profile is supplied;
- be remembered only when she actually provides a safe durable personal fact;
- experience the same single Tutor identity across Chat and Canvas.

That is the baseline required before further feature expansion.

---

## 34. Source-of-truth hierarchy during implementation

When conflicts arise, use this order:

1. Product Owner decisions recorded in this specification and current tracker.
2. Current repository code and migrations.
3. Current `PROJECT_REFERENCE.md`, `IMPLEMENTATION_PLAN.md`, `PROJECT_STATE.md`, and `TASKS.md`.
4. Current governing domain specs/policies.
5. Historical review/closure documents only as evidence of why a behavior exists.
6. External provider documentation for provider-specific contracts/pricing only.

Do not let an old historical closure override current product decisions.

---

**End of REAL-USE-REPAIR-01 Implementation Specification**

