# Daily-Use Lina Release 1 — Execution Tasks

**Status:** Product Owner approved on 2026-08-31  
**Authority:** Current bounded execution overlay for Daily-Use Lina Release 1.  
**Relationship to `TASKS.md`:** `TASKS.md` remains the preserved historical ledger.  
**Execution rule:** Only one task is `READY` at a time. After each task: verify, review, update `PROJECT_STATE.md`, then promote the next task explicitly.

---

# Learning Studio — Approved Execution Track

**Authority:** `docs/STUDIO_IMPLEMENTATION_PLAN.md` is the approved detailed
direction. This track controls Studio readiness and supersedes only earlier
FE-02/display-only Canvas execution assumptions. It does not rewrite the
preserved Daily-Use history below.

```text
STUDIO-GOV-01 — DONE / ACCEPTED
→ FE-02-PRESERVE-01 — DONE / ACCEPTED
→ STUDIO-STATE-01 — DONE / ACCEPTED
→ STUDIO-SUBJECT-01 — DONE / ACCEPTED
→ STUDIO-PROTOCOL-01 — DONE / ACCEPTED
→ STUDIO-RUNTIME-01 — DONE / ACCEPTED
→ STUDIO-RUNTIME-02 — DONE / ACCEPTED
→ STUDIO-RUNTIME-03 — DONE / ACCEPTED
→ STUDIO-ACT-MATH-01 — DONE / ACCEPTED
→ STUDIO-ACT-SCI-01 — DONE / ACCEPTED
→ STUDIO-ACT-EN-01 — DONE / ACCEPTED
→ FE-02-STUDIO-01 — DONE / ACCEPTED
→ STUDIO-ACT-AR-01 — DONE / ACCEPTED
→ CURR-RENDER-MATH-01A — BLOCKED UNTIL THE GRADE 5 MATH RENDERER IMPLEMENTATION GATE
→ independently reviewed Grade 5 renderer tasks — BLOCKED
→ STUDIO-ACCEPT-01 — BLOCKED
→ optional STUDIO-SPECIALIST-01 / STUDIO-REUSE-01 — BLOCKED
→ production deployment gate — BLOCKED
```

## STUDIO-GOV-01 — Verify and Promote Approved Studio Direction

**Status:** DONE / ACCEPTED
**Scope:** governance documentation only; no runtime, schema, API, renderer,
dependency, or frontend behavior change.

## FE-02-PRESERVE-01 — Preserve Prototype Shell

**Status:** DONE / ACCEPTED
**Purpose:** create a recoverable isolated prototype artifact without accepting
the FE-02 browser implementation as production Studio architecture.

**Accepted output:** branch `prototype/fe-02-studio-shell-2026-09-02`, commit
`8648371480b0aac116af2a49e2d3d7493d26360f`, parent
`059ff3aa6bfb983507470f484596bf05eae3b9b3`, and manifest
`prototype/FE-02_PROTOTYPE_MANIFEST.md`.

**Accepted verification:** seven focused Node tests, TypeScript typecheck,
production build, and SHA-256 identity passed. The prototype remains
non-production.

## STUDIO-STATE-01 — Durable Studio State

**Status:** DONE / ACCEPTED
**Dependencies:** accepted `STUDIO-GOV-01` and `FE-02-PRESERVE-01` only.

**Accepted result:** durable Runtime, Scene, semantic Event Log, Materialized
Snapshot, and persistence seams are at Alembic head `b6e4c2a9d7f1`; focused
Studio PostgreSQL verification and the accepted full isolated suite passed.

`STUDIO-SUBJECT-01` is `DONE / ACCEPTED` at Alembic head `c7d8e9f0a1b2`.
It provides the code-owned Subject Capability Registry, exact capability
versions, persisted Scene profile/action identity, bounded validation results,
and Student-only Activity-owned Tutor triggering. Production profiles have no
Student-facing Activities. `STUDIO-PROTOCOL-01` is `DONE / ACCEPTED`: its
authenticated open/snapshot/operation/feed boundary, resumable Event Log
recovery, PostgreSQL wake-up seam, and web protocol/controller are implemented.
`STUDIO-RUNTIME-01` is `DONE / ACCEPTED`: the existing Tutor call receives the
current Studio Snapshot and exact unseen Event range, and successful completed
Tutor consumption advances the durable Studio watermark. `STUDIO-RUNTIME-02`
is `DONE / ACCEPTED`: its strict WorkspaceIntent and deterministic,
non-mutating Workspace Router are implemented.

`STUDIO-RUNTIME-03` is `DONE / ACCEPTED`: authenticated Canvas-originated
Tutor streaming claims a declared StudentInteraction exclusively and uses one
primary Tutor execution without creating a fake Student LearningMessage. Real
Tutor messages retain exact Canvas provenance. The same call receives distinct
current-interaction context and Runtime-01 Workspace Snapshot/unseen-Event
context; continuity, observation/watermark finalization, causal supersession,
and post-persistence disconnect cancellation are durable and
PostgreSQL-authoritative. RECORD_ONLY does not supersede. This reuses the
shared Safety/Parent Boundary and Runtime-02 parser/Router contracts and makes
no direct Candidate, Evidence, Personal Facts, or Learning Intelligence
writes. The accepted mock-provider verification was `168 passed in 10.44s`
focused and `889 passed, 7 skipped in 41.52s` full; fresh independent review
reported 0 Critical, 0 Important, and 0 Minor findings. The seven skips are
the five opt-in cloud-writing S3 tests and two opt-in real-Luna tests, not
passes. Student-authored free-form language remains Chat-only, including
Voice-to-STT; Canvas uses bounded semantic controls and may display language.

`STUDIO-ACT-MATH-01`, `STUDIO-ACT-SCI-01`, `STUDIO-ACT-EN-01`,
`FE-02-STUDIO-01`, and `STUDIO-ACT-AR-01` are `DONE / ACCEPTED`. Arabic's
earlier deferral is preserved as history; English remains shared
text-oriented/mixed-direction foundation evidence, while the accepted Arabic
activity supplies bounded academic-subject RTL proof. `STUDIO-ACCEPT-01`
remains BLOCKED / NOT PROMOTED because full-system acceptance has not been
performed or separately authorized. All other later Studio and deployment tasks
remain blocked.
`CURR-RENDER-MATH-01A` is **BLOCKED UNTIL THE GRADE 5 MATH RENDERER
IMPLEMENTATION GATE**: it does not block Studio state, protocol, runtime,
cross-subject foundation activities, or FE-02 Studio integration.

---

## STUDIO-ACT-MATH-01 — Make-Ten Group Transfer

**Status:** DONE / ACCEPTED

**Purpose:** Deliver the bounded, cross-grade production
`ten_frame_group_transfer` activity and its minimal production renderer for the
accepted `9 + 6 → 10 + 5` flow. It proves bidirectional Studio behavior; it is
not a Grade 5 curriculum claim or coverage item.

**Accepted dependencies:** `STUDIO-STATE-01`, `STUDIO-SUBJECT-01`,
`STUDIO-PROTOCOL-01`, `STUDIO-RUNTIME-01`, `STUDIO-RUNTIME-02`, and
`STUDIO-RUNTIME-03` are `DONE / ACCEPTED`. `CURR-RENDER-MATH-01A` does not
block this foundation activity and Make-Ten remains outside the Grade 5
coverage denominator.

**Accepted production outputs:**

- a code-owned exact-version MATH Activity, Renderer, payload-validator,
  semantic-validator, and reducer contract for `ten_frame_group_transfer`;
- the typed `TRANSFER_ITEM` semantic operation and a contract-declared bounded
  submit/step-completion action. Exploration remains `RECORD_ONLY`; only the
  declared submit/step-completion action creates a Tutor-triggering
  `StudentInteraction`;
- a deterministic ten-frame/group-count reducer and validator that reach
  `10 + 5`, return bounded truthful validation results, and preserve
  authoritative invalid, duplicate, and stale-operation handling;
- a minimal production native React/SVG renderer with equivalent drag, touch,
  and keyboard/button interaction; accessible text/control equivalents;
  Arabic, English, and mixed-direction presentation; and a complete
  reduced-motion/static experience;
- durable typed Event/Snapshot state whose reload and rebuild exactly reproduce
  the accepted activity state; and
- Canvas-originated Tutor continuation through accepted Runtime-03 with real
  Tutor-message provenance and no fake Student LearningMessage. The known
  activity uses no Canvas Specialist or additional Canvas model call.

**Implemented code areas:**

- `services/studio/subjects/math_make_ten.py`, the subject registry/contracts,
  activation adapter, reducer/service/interaction path, and Tutor runtime now
  provide the exact activity, activation, durable operations, validation, and
  Runtime-03 continuation;
- `tests/test_studio_make_ten_postgres.py` and
  `tests/test_studio_workspace_intent.py` provide the bounded persistence,
  validation, activation, and source-truth regressions; and
- `apps/web/app/studio/make-ten-review/page.tsx`,
  `apps/web/components/studio/ten-frame-group-transfer.tsx`, and
  `apps/web/lib/studio/make-ten.{ts,test.ts}` provide only the mock-labelled
  isolated review mount and minimal React/SVG renderer, not a `/student/daily`
  renderer host.

**Existing contracts/services to reuse:** Use the project-owned Subject
Capability Registry, `CreateSceneCommand` / `AppendStudioEventCommand`,
`StudioStateService`, `StudioProtocolService`, reducer/rebuild path, dedicated
Studio feed, and Runtime-03 interaction lifecycle. Reuse the current web Studio
protocol/controller only as a server-authoritative transport client. Do not
replace these contracts with browser state, a chat runtime, or a new service.

**Confirmed implementation seams:** exact MATH contract/scene/action versions,
scene seed, validator feedback, and the smallest activity-specific exact Scene
activation adapter were confirmed. Activation is restricted to the full
accepted Scene identity, not source reference alone. The isolated review seam
was confirmed without `/student/daily` integration; full Daily Student App
integration remains `FE-02-STUDIO-01`.

**Verification and acceptance record:** The final browser matrix has 12 passes
for mouse/touch numeral and edge transfer, keyboard, cancellation/retry,
release-capture retry, mouse/touch outside retry, rejection, RTL/narrow layout,
reduced motion, and explicit submit; see
`output/playwright/make-ten-input-fixes-20260905/matrix-final/results.json`.
The two renderer/model tests passed via compiled Node test output. Latest web
`npm --prefix apps/web run typecheck` and `npm --prefix apps/web run build`
passed; `git diff --check` passed. Previous unchanged-backend evidence was
`895 passed, 7 skipped`; it was not re-run for the final frontend-only pointer
correction. The skips were the opt-in cloud-write S3 tests
`test_real_s3_round_trip_and_private_access`,
`test_real_s3_collision_protection_preserves_original`,
`test_real_s3_hmac_rejects_out_of_band_metadata_change`,
`test_real_s3_delete_removes_object`, and
`test_real_s3_secret_rotation_paginates_and_resumes`, plus opt-in real-Luna
tests `test_real_luna_segment_reviewer_representative_cases` and
`test_real_luna_primary_tutor_call_keeps_provisional_subject_optional_and_single`;
they are not passes. The prior disposable-test-DB `alembic check` succeeded
with no new upgrade operations (existing `ai_executions` / `learning_messages`
FK-cycle warning). Exact redacted commands and focused evidence are retained
under `output/playwright/make-ten-evidence-20260905/` and
`output/playwright/make-ten-input-fixes-20260905/`.

Final independent code/evidence inspection (not independent test re-execution)
is recorded at
`output/playwright/make-ten-input-fixes-20260905/independent-review.md` with
0 Critical / 0 Important / 0 Minor. The reported source-truth issue was
disproven for its stated scenario; the exact-activation and pointer/touch
findings were corrected and covered by the final review/evidence.

**Explicit non-scope:** No full FE-02 `/student/daily` integration; generic
Artifact Engine or renderer catalog; Grade 5 curriculum/coverage work;
Science, English, or Arabic activities; Canvas Specialist; unrestricted Canvas
language input; new frontend architecture; direct Candidate, Evidence,
Personal Facts, or Learning Intelligence writes; package installation; schema
change; dependency change; or a new Canvas model call.

**Closure gate:** accepted only with the complete reviewed implementation,
regression-test source, final browser runner, and this evidence record. The
generated screenshots, logs, traces, and result files remain local evidence
and are intentionally outside the source commit.

---

## STUDIO-ACT-SCI-01 — Process Sequence Workspace

**Status:** DONE / ACCEPTED

**Purpose:** Deliver one production `process_sequence_workspace` Science
activity using a bounded project-authored fixture. It proves the same
Studio architecture with stable Science stage identities and deterministic
sequence/relationship validation; it is not a water-cycle-only component,
generic ordering framework, Grade 5 Science curriculum claim, or replacement
for the later Science-production work. The water cycle is permitted but not
selected by this promotion.

**Accepted dependencies:** `STUDIO-STATE-01`, `STUDIO-SUBJECT-01`,
`STUDIO-PROTOCOL-01`, `STUDIO-RUNTIME-01`, `STUDIO-RUNTIME-02`,
`STUDIO-RUNTIME-03`, and `STUDIO-ACT-MATH-01` are `DONE / ACCEPTED`.
`CURR-RENDER-MATH-01A`, `TASK-035`, and a generic Artifact Engine do not block
this bounded cross-subject activity.

**Required production outputs:**

- an exact-version SCIENCE profile, Activity, Renderer, payload-validator,
  deterministic semantic-validator, reducer, fixture identity, and typed
  stable stage identities for `process_sequence_workspace`; preserve the
  current empty `SCIENCE / subject-profile-v1` for replay rather than changing
  its meaning;
- bounded reorder and submission Action contracts. Reordering is
  `RECORD_ONLY`; exactly one contract-declared submitted configuration creates
  a `StudentInteraction` and uses one existing Runtime-03 Tutor continuation;
- server-owned Event/Snapshot state, exact reload/rebuild, idempotency,
  ownership, rejection, and stale-operation handling. The submission must
  preserve the exact submitted configuration for Tutor context even if later
  record-only rearrangements change current Snapshot state;
- a deterministic, fixture-owned valid-order/relationship rule. The browser
  may submit only a one-to-one permutation of the declared stable stage IDs;
  unknown, duplicate, missing, extra, or Snapshot-mismatched identities reject
  without mutation. The implementation must explicitly decide and test whether
  the fixture permits alternative valid orders. Keep the answer key in a
  server-owned fixture map rather than a browser-visible Scene seed unless a
  later Product Owner decision authorizes a narrow alternative;
- a minimal React DOM/SVG renderer and mock-labelled isolated review seam, not
  `/student/daily`, with pointer, emulated touch, keyboard/button, accessible
  text/control equivalents, locale/direction, narrow layout, failure/rejection
  recovery, and reduced-motion/static verification; and
- no fake Student `LearningMessage`, direct Candidate/Evidence/Personal
  Facts/Intelligence write, additional Canvas/Specialist model call, or change
  to existing Safety, ownership, provenance, or supersession rules.

**Confirmed reusable seams and likely implementation areas:**

- reuse the production Subject Capability Registry;
  `CreateSceneCommand`/`AppendStudioEventCommand`; `StudioStateService`;
  `StudioProtocolService`; reducer/rebuild; dedicated Studio feed; web Studio
  operation/controller contracts; and the Runtime-03 interaction lifecycle;
- add a bounded Science activity module and profile registration under
  `services/studio/subjects/`, plus a specific activation adapter or a small
  application-owned activation dispatcher. The current Make-Ten adapter is an
  exact-activity reference, not a generic cross-subject activation system;
  any active-Scene replacement/supersession behavior must be explicit and
  tested rather than inferred;
- add focused PostgreSQL/Runtime-03 regressions beside the existing
  `tests/test_studio_make_ten_postgres.py` coverage, and an activity-specific
  review page/component/client helper under `apps/web/app/studio/`,
  `apps/web/components/studio/`, and `apps/web/lib/studio/`. Reuse the existing
  server-authoritative controller only; do not create browser-owned truth or a
  generic drag framework.

**Bounded implementation checks before completion:** record the exact profile,
activity, renderer, scene, Action/payload/event, reducer, validator, and
fixture/version literals; trusted/authored fixture provenance and source
rights; the stage/order or relationship contract; activation identity; and
the selected renderer interaction design. These are implementation choices not
settled by this promotion. Reuse the approved native React/SVG baseline where
it fits; do not install a package merely because it appears in the reuse
catalog.

**Required verification and independent-review gate:** prove exact
contract/registry resolution; activation identity/idempotency; durable
reorder/submit state; valid, invalid, alternative-valid-if-declared,
duplicate, missing, extra, stale, replay, and cross-Student cases; exact
rebuild/reload; submitted configuration versus later current state in the one
Runtime-03 Tutor continuation; no fake message or direct learning-intelligence
write; and zero additional Canvas calls. Independently review the final diff
and inspect the isolated browser matrix for pointer, emulated touch,
keyboard/button, locale/direction, accessibility, narrow layout, rejection,
and reduced motion. Do not treat prior Make-Ten tests as fresh Science
evidence.

**Explicit non-scope:** no full `/student/daily` integration; generic Artifact
Engine or drag framework; full Science curriculum, Grade 5 coverage, or
English/Arabic activity; Canvas Specialist; free-form Canvas language or
SafetyTextProjection; schema/dependency installation by default; deployment;
live-model/real-Lina execution; or implementation of any subsequent Studio
task.

### Accepted result — 2026-09-05

The exact-version `SCIENCE / subject-profile-v2` profile is current while the
empty `SCIENCE / subject-profile-v1` remains historical/replay truth. The
accepted bounded fixture is **project-authored bounded instructional fixture
based on elementary scientific fact**; it is not adapted from a named external
source and is not model-generated content.

| Fixture field | Accepted value |
| --- | --- |
| Fixture key | `sand_water_filtration` |
| Fixture version | `sand-water-filtration-fixture-v1` |
| Scientific proposition | A sand-and-water mixture can be separated by passing it through filter paper in a funnel and then collecting the filtered water. |
| Scope boundary | This is only the bounded filtration sequence used to test the architecture. It does not claim filtration alone makes arbitrary water safe or potable, and it makes no Grade 5 Science coverage claim. |

| Stable stage ID | Learner-visible English text | Learner-visible Arabic text |
| --- | --- | --- |
| `prepare-filter-funnel` | Set the filter paper in the funnel | جهّز القمع وورق الترشيح |
| `pour-sand-water-mixture` | Pour the sand-and-water mixture | اسكب خليط الرمل والماء |
| `allow-water-to-filter` | Let the water pass through the filter | اترك الماء يمر عبر المرشح |
| `collect-filtered-water` | Collect the filtered water | اجمع الماء المُرشَّح |

The only accepted order is, exactly: `prepare-filter-funnel` →
`pour-sand-water-mixture` → `allow-water-to-filter` →
`collect-filtered-water`. No alternative valid order exists in v1. The answer
is server-owned and absent from the browser-visible Scene seed. Submission
requires exactly one of every declared stable ID, exact agreement with the
authoritative current Snapshot, and then exact equality with that one accepted
order. The correct order returns `FILTRATION_SEQUENCE_COMPLETE`; a structurally
valid but scientifically wrong order persists a bounded invalid result,
`FILTRATION_SEQUENCE_NEEDS_REORDERING`, rather than a system error. This
intentionally narrow deterministic order represents the physical dependency of
preparing the filter, pouring the mixture, allowing filtration, and collecting
the output; it is not a general water-purification lesson.

`REORDER_STAGE` is `RECORD_ONLY`; `SUBMIT_CONFIGURATION` alone creates one
Runtime-03 Tutor continuation from the persisted submitted configuration.
Later record-only reorders can change the current Snapshot without changing
that source submission. Tests cover exact v1 preservation/v2 resolution,
fixture and operation validation, invalid-but-persisted scientific result,
reload/rebuild, idempotency, stale and cross-Student rejection, and the one
submit-only continuation. They also prove no fake Student message, direct
Candidate/Evidence/Personal Facts/Learning Intelligence write, or additional
Canvas model call.

**Recorded verification (not rerun during closure):** focused Science
PostgreSQL/Runtime tests `5 passed`; related Studio/Make-Ten/Runtime suite
`91 passed`; disposable full Python suite `900 passed, 7 skipped`; renderer
model tests `2 passed`; root TypeScript typecheck and production build passed;
the isolated real-Chromium review matrix passed all 12 cases (native mouse,
Chromium-emulated touch, keyboard, cancellation/capture/outside recovery,
rejection, Arabic RTL narrow layout, and reduced motion); Alembic check and
tracked/untracked diff checks passed. The seven skips are existing opt-in
checks, not passes: five cloud-writing S3 tests and two real-Luna tests, as
listed in the accepted `STUDIO-RUNTIME-03` record.

**Independent review:** the initial read-only review reported the Minor
localization finding that the renderer had an English-only eyebrow and an
English-only live-drag stage label. The final localization-only independent
source/evidence addendum inspected the post-fix lines at
`apps/web/components/studio/process-sequence-workspace.tsx:37`, `:83`, `:168`,
and `:201` and reported `0 Critical / 0 Important / 0 Minor`. That final review
was source/evidence inspection, not an independent test re-run.

**Committed evidence boundary:** commit the production/test source, this task
record, and the reproducible browser runner/README. Retain generated browser
screenshots, traces, logs, and `results.json` as local evidence; do not add the
entire output directory.

---

## STUDIO-ACT-EN-01 — English Sentence Ordering

**Status:** DONE / ACCEPTED

**Purpose:** Prove that the accepted Studio Core can support one bounded,
text-oriented English Workspace with stable token identities and deterministic
authored-answer validation. This is not unrestricted Student language input,
a general text editor, a grammar-tutoring system, or English curriculum
coverage. Canvas may display declared English tokens, let the Student reorder
or select them through bounded controls, and submit that bounded ordered
configuration. It must not collect a Student-written sentence, explanation,
or reasoning. Free-form language remains in Chat, including Voice-to-STT-to-
Chat.

**Accepted dependencies:** `STUDIO-STATE-01`, `STUDIO-SUBJECT-01`,
`STUDIO-PROTOCOL-01`, `STUDIO-RUNTIME-01`, `STUDIO-RUNTIME-02`,
`STUDIO-RUNTIME-03`, `STUDIO-ACT-MATH-01`, and `STUDIO-ACT-SCI-01` are
`DONE / ACCEPTED`.

**Required production outputs:**

- add one exact new ENGLISH subject-profile extension while retaining every
  persisted historical ENGLISH profile version with its existing meaning;
  register one bounded sentence-ordering Activity, text-oriented Renderer,
  typed token/action payloads, deterministic authored-answer validator, and
  reducer through the Subject Capability Registry;
- model each token with a stable typed identity independent of its display
  label. The declared fixture may contain repeated visible words, so identity
  must never be derived solely from text. The server-owned answer key, not the
  browser-visible Scene seed, decides the permitted order;
- admit only bounded `REORDER_TOKEN` operations and an explicit
  `SUBMIT_CONFIGURATION` action. Reorder is `RECORD_ONLY`; only submit is
  `TUTOR_TRIGGERING` and creates exactly one Runtime-03
  `StudentInteraction` from a declared submitted ordered configuration;
- preserve exact durable Event and Snapshot state, validation result, scene
  identity, ownership, stale-operation rejection, idempotency, and
  reload/rebuild behavior. A structurally valid but academically wrong order
  must persist a truthful bounded validation result rather than fail as a
  malformed request;
- make the one Runtime-03 Tutor continuation receive the exact submitted token
  IDs in submitted order and the deterministic validation result. If a later
  record-only reorder changes the current Workspace, the Tutor context must
  retain that source submission and expose the later current Workspace state
  separately, without fabricating Student prose or a Student `LearningMessage`;
- provide a minimal text-oriented renderer and mock-labelled isolated review
  seam, not `/student/daily`. English academic tokens must render LTR even
  when the surrounding Tutor/UI explanation is Arabic RTL; mixed direction
  must preserve visual token sequence and keyboard focus order; and
- make no direct Candidate, Evidence, Personal Facts, or Learning Intelligence
  write; no additional Canvas/Specialist model call; and no change to the
  existing Safety, Parent Boundary, ownership, provenance, Router, or
  supersession rules.

**Fixture boundary:** Fixture selection is an implementation check, not an
implicit lesson approval. It must be project-authored or clearly rights-safe,
one simple English sentence with stable token IDs, academically modest, and
suited to deterministic validation. It uses one valid order unless an
alternative-valid policy is explicitly justified and tested. Record fixture
key/version/provenance and the exact token IDs plus visible labels before
completion; do not claim curriculum or Grade coverage.

**Confirmed reusable seams and likely implementation areas:**

- reuse the Subject Capability Registry, `StudioStateService`,
  `StudioProtocolService`, `CreateSceneCommand`, `AppendStudioEventCommand`,
  reducer/rebuild path, dedicated Studio feed, Runtime-03 interaction
  lifecycle, and existing web Studio controller/operation contracts;
- inspect and extend the existing `services/studio/activity_activation.py`
  entry point only where its exact-activity adapter pattern is genuinely
  reusable. It currently dispatches bounded Make-Ten and Science adapters; an
  English implementation may add one exact adapter there after verifying its
  exact activation identity. Do not introduce a second activation framework,
  generic plugin engine, generic drag/drop framework, browser-owned activity
  truth, new Router, or Canvas-language safety subsystem; and
- use the existing local React/Tailwind/shadcn and native React DOM/SVG
  baseline where it fits. Do not add a dependency by default or transfer
  `useChat`, `UIMessage`, transport, runtime, session, or safety ownership.

**Bounded implementation checks before completion:** explicitly resolve and
record the ENGLISH profile version; Activity and Renderer keys/versions; Scene,
token, Action, Event, payload, validator, and reducer schema/versions; fixture
key/version/provenance; exact stable IDs and visible labels; valid-order and
duplicate-token policies; exact activation identity; and renderer interaction
design. These are implementation checks, not Product Owner questions unless a
genuine product decision appears.

**Required implementation verification and independent-review gate:**

- prove historical ENGLISH profile preservation and exact current-version
  resolution; fixture seed and stable tokens; correct validation; a
  structurally valid but academically wrong persisted result; malformed,
  unknown, duplicate, missing, extra, stale, replay/idempotent, and
  cross-Student rejection; exact reload/rebuild; record-only reorder; one
  submit-only `StudentInteraction`; exactly one Runtime-03 Tutor execution;
  submitted order remaining source truth after later record-only reorder; no
  fake message/direct intelligence or Personal Facts write; and zero extra
  Canvas calls;
- independently inspect the isolated renderer with pointer/mouse reorder,
  Chromium-emulated touch, keyboard/button equivalent, cancellation/retry,
  outside release, rejection reconciliation, one explicit submit, English LTR
  token correctness, Arabic surrounding UI, mixed direction, narrow viewport,
  accessible focus/live status, and reduced motion; and
- obtain a fresh independent review of the final implementation diff. Math or
  Science tests and evidence do not count as fresh English verification.

**Explicit non-scope:** free-form Canvas sentence composition, paragraph
writing, explanation/reasoning textboxes, grammar tutoring, full English
curriculum, Grade coverage, vocabulary platform, generic text editor, generic
Artifact Engine, Canvas Specialist, a new model call or `SafetyTextProjection`,
full `/student/daily` integration, Arabic academic activity, schema/dependency
installation by default, deployment, or real-Lina execution. All later Studio
tasks remain `BLOCKED`.

### Accepted result — 2026-09-05

The current exact-version `ENGLISH / subject-profile-v2` profile resolves the
bounded `sentence_ordering_workspace` while prior English profile versions
remain unchanged for historical/replay truth. The fixture is a project-authored,
rights-safe architecture activity, not an English curriculum or coverage claim.

| Fixture field | Accepted value |
| --- | --- |
| Fixture key | `english_sentence_ordering_fixture_slate` |
| Fixture version | `english-sentence-ordering-fixture-slate-v1` |
| Canonical authority | Server-owned only; no browser answer/order metadata |
| Server-only canonical order | `tok-c820 → tok-43bd → tok-7f2c → tok-a91e` |
| Browser catalogue order | `tok-7f2c → tok-a91e → tok-43bd → tok-c820` |
| Browser initial/current order | `tok-a91e → tok-c820 → tok-7f2c → tok-43bd` |

| Stable opaque token ID | Learner-visible label |
| --- | --- |
| `tok-c820` | `Birds` |
| `tok-43bd` | `fly` |
| `tok-7f2c` | `over` |
| `tok-a91e` | `clouds` |

The IDs are fixture-owned opaque stable identities: they encode neither visible
labels nor canonical positions, remain deterministic across reload and Event
rebuild, and keep duplicate labels representable as different semantic objects.
Visible words are presentation data. The Scene seed/catalog/current order and
renderer metadata expose no canonical answer field; neither catalogue order nor
initial/current order equals the server-owned order.

`REORDER_TOKEN` remains `RECORD_ONLY`; `SUBMIT_CONFIGURATION` alone is
`TUTOR_TRIGGERING`. Exact activation identity and idempotent reuse, durable
Event/Snapshot state, exact rebuild/reload, bounded wrong-order feedback,
malformed/unknown/duplicate/missing/extra rejection without mutation, stale and
cross-Student rejection, and submitted-source truth after later record-only
reorder are accepted. The sole submission creates one Runtime-03 Tutor
execution and one real Tutor LearningMessage, with no fake Student message,
direct Candidate/Evidence/Personal Facts/Learning Intelligence write, or
additional Canvas/Specialist model call.

Academic English token order stays LTR while surrounding instructions can be
Arabic RTL or mixed direction; focus traversal is visible and usable. Native
mouse, Chromium-emulated touch, and keyboard/button paths emit equivalent
bounded `REORDER_TOKEN` intent, and explicit Submit remains a distinct
once-only action. Canvas contains no free-form Student-authored language,
contenteditable, composition field, explanation/reasoning field, or second
Student language channel: free-form language remains Chat or Voice-to-STT-to-
Chat.

**Recorded verification (not rerun during closure):** focused English
PostgreSQL/activation/rebuild/Runtime-03 tests `6 passed`; renderer/model tests
`4 passed`; the isolated Chromium matrix passed `16/16` cases, including
Chromium-emulated touch and Arabic RTL/English LTR keyboard-focus evidence; the
full isolated Python suite passed `906 passed, 7 skipped`; TypeScript typecheck
and production build passed; Alembic found no new upgrade operations; and
tracked/relevant-untracked whitespace checks passed. The seven skips remain the
five opt-in cloud-writing S3 tests and two opt-in real-Luna tests already
documented above, not passes.

**Final independent review:** the focused final source/evidence inspection
reported `0 Critical / 0 Important / 0 Minor`; it was not independent test
re-execution. The authoritative reproducible runner and README describe the
16-case matrix. Generated screenshots, traces, and `results.json` remain local
evidence; the historical generated `results.json` descriptive label was
intentionally not normalized.

**Committed evidence boundary:** commit the English production source,
activation integration, PostgreSQL tests, renderer/model/component/review-mount
source, implementation record, reproducible runner/README, and acceptance
governance. Do not commit generated screenshots, traces, or `results.json`.

**Historical deferral record — 2026-09-06, superseded:** Arabic was intentionally
deferred until after real FE-02 integration. English had already proved a
bounded text-oriented Workspace; stable opaque token identity; record-only
text-token manipulation; submit-triggered Runtime-03 continuation; English
academic LTR inside Arabic RTL surrounding UI; mixed-direction keyboard/focus
behavior; mouse, emulated touch, and keyboard semantic equivalence; and no
free-form Canvas language channel. Arabic retained incremental academic-subject,
RTL token/span, and Arabic-specific annotation/ordering value. Explicit Product
Owner approval after FE-02 acceptance ended that deferral and promoted the
unchanged bounded proof to READY; this historical record does not mark the task
implemented or accepted.

---

## STUDIO-ACT-AR-01 — Arabic Sentence Annotation/Ordering

**Status:** DONE / ACCEPTED

**Historical decision:** the intentional post-FE-02 deferral ended through
explicit Product Owner promotion. It remains history. The bounded implementation
and final acceptance below are current; no later Studio task, schema/dependency
work, deployment, or Replit work is implied.

**Purpose:** prove Arabic as an academic subject, not merely Arabic surrounding
UI, with one bounded RTL sentence annotation/ordering Activity. It must use
stable token/span identities and Arabic-specific academic interaction. It must
not become a grammar engine, Arabic curriculum, text editor, or multiple
independent Activity family.

**Accepted implementation:** the project-authored fixture
`arabic_sentence_ordering_fixture_orchid /
arabic-sentence-ordering-fixture-orchid-v1` uses `ARABIC /
subject-profile-v2`, `arabic_sentence_ordering_workspace /
arabic-sentence-ordering-workspace-activity-v1`,
`arabic-sentence-ordering-workspace /
arabic-sentence-ordering-workspace-renderer-v1`,
`arabic-sentence-ordering-workspace-scene-v1`, and
`arabic-sentence-ordering-token-v1`; historical Arabic profiles are unchanged.
Its opaque `tok-6d3a`, `tok-f18c`, and `tok-2b7e` identities preserve
`تكتبُ`, `الطالبةُ`, and `الدرسَ` respectively, separate from position and
display. The safe catalog's deterministic initial order is subject/object/verb.
The server-only policy accepts both case-marked verb-initial answers
`تكتبُ الطالبةُ الدرسَ` and `تكتبُ الدرسَ الطالبةُ`; it does not claim other
Arabic constructions are generally ungrammatical. Browser parsing strictly
checks exact catalogue/state identity but does not contain academic correctness.

**Recorded contract and boundaries:** one project-authored or
rights-safe Arabic fixture and provenance; exact learner-visible text and
linguistic validity; the selected bounded annotation/ordering interaction and
why it satisfies Section 22.7; stable token/span IDs independent of display
text and answer position; duplicate-label policy where applicable; deterministic
valid-answer policy including justified alternatives; exact subject/profile/
activity/renderer/seed/action/event/reducer/validator versions; and exact
activation identity with a browser-safe Scene seed. Do not silently choose an
arbitrary lesson, claim curriculum coverage, or treat an implementation proposal
as a completed approved contract. Preserve existing `ARABIC` profile meanings
through exact versioning, and keep the answer key server-owned and absent from
browser seed/catalog/renderer metadata.

**Accepted reuse and bounded integration:** the Subject Capability
Registry; Studio state, Event/Snapshot, protocol, feed, and rebuild authority;
the existing exact activation seam; Runtime-03 continuation/provenance; and the
accepted Student-owned Daily session with Chat/Workspace composition. Make the
smallest exact-contract Arabic extension to `/student/daily`'s Renderer Host.
An isolated review mount may supplement testing but cannot be the only
integration evidence. Do not add a Router, feed, browser-owned durable reducer,
session type, generic drag framework, broad FE-02 refactor, direct Canvas
Candidate/Evidence/Personal Facts/Intelligence write, or free-form Canvas
language channel. Preserve `ARABIC → LANGUAGE_ARTS` and `LiveSubjectContext`.

**Accepted interaction and truth:** exploration/rearrangement/label selection is
contract-defined `RECORD_ONLY`; one explicit contract-owned submitted
configuration is the only Tutor-triggering action. Preserve submitted
configuration as source truth independently from later current Snapshot state.
It creates one Runtime-03 Tutor execution with no fake Student message. Arabic
academic direction, keyboard/focus semantics, accessible names/status, RTL
semantic/visual order, narrow layout, and relevant mixed-direction content are
part of the Activity contract. Free-form explanation stays in Chat or
Voice-to-STT-to-Chat; Voice/STT is not implemented here.

**Accepted verification:**

- backend evidence: exact versions and historical-profile preservation;
  fixture/answer validity with browser answer-key non-disclosure; stable
  identities, including duplicate visible labels where applicable; malformed,
  unknown, duplicate, missing, stale, and cross-Student rejection; structurally
  valid but academically wrong attempts persisted truthfully; exact activation
  and idempotent reuse; Event/Scene/Snapshot consistency, reload, and rebuild;
  record-only versus one submission-triggered Tutor continuation; original
  submission versus later current Workspace state; and no regression to
  accepted session, subject, feed, or provenance authority;
- authenticated browser evidence on real `/student/daily`: Arabic academic
  content, correct RTL semantic/visual order, keyboard navigation, visible
  focus, accessible names/status, pointer and genuinely evidenced
  Chromium-emulated touch where applicable, equivalent semantic results across
  supported input methods, cancellation/retry, rejection reconciliation,
  reload, reduced motion, narrow/mixed-direction layout, and one explicit
  submission with correct Tutor continuation; and
- focused tests, affected shared regressions, web typecheck/build,
  proportional full-suite verification, and fresh independent review of the
  final implementation diff. Keep physical-device, emulated-touch,
  mock-provider, and live-model evidence distinct. Prior English or FE-02 passes
  are not new Arabic evidence. Final isolated Python was 953 passed / 7 skipped
  / 0 failures/errors (pytest and wrapper exit 0); focused 66 passed overlaps
  that suite; web was 34 passed; typecheck, production build, Alembic and
  whitespace passed. Fresh independent review found 0 Critical / 0 Important /
  0 Minor. The authenticated prepared-Scene test scenario recorded 14 Events,
  three completed submissions, one original Student message and four Tutor
  messages including the initial Chat response. Evidence and limits are in
  `docs/STUDIO_ACT_AR_01_IMPLEMENTATION_RECORD.md` and the local retained
  Arabic acceptance evidence directory.

**Explicit non-scope:** generic Artifact/text/editor/drag infrastructure; full
Arabic curriculum, grammar, or vocabulary platform; Canvas Specialist; new
model call or `SafetyTextProjection`; Voice/STT implementation; schema or
dependency work by default; deployment/Replit; or real-Lina execution.

---

## FE-02-STUDIO-01 — Connect Real Studio to Daily Student App

**Status:** DONE / ACCEPTED

**Accepted result:** at FE-02 acceptance, real authenticated `/student/daily` was separate from
protected legacy `/student`. One Student-owned LearningSession identity is
shared by Chat and Studio, retained as `?session=`, and resumed only by that
exact ID; new Daily sessions use only the no-ID request. The accepted surface
uses the server-authoritative active Scene contract plus answer-safe seed and
exact Math/Science/English Renderer Host dispatch. It reconciles operations,
Snapshots, feed resume, reload, and server rejection without a second Studio
client, reducer, feed, activation router, or Tutor. Free-form Student language
remains Chat; Canvas creates neither fake Student messages nor direct
Candidate/Evidence/Personal Facts writes.

Unknown or cross-Student IDs fail closed; closed/non-resumable IDs receive the
implemented bounded response and require an explicit no-ID new-session request.
There is no `DAILY` academic-subject discriminator: `LiveSubjectContext` and
reviewed-Segment authority remain independent of the technical session.

**Acceptance evidence and limits:** 37 PASS is one NEW Chromium/CDP-emulated
touch case plus 36 REUSED applicable cases, not 37 freshly rerun cases. The
new trace proves trusted `ones-group-06` touch → one accepted `TRANSFER_ITEM`
→ 9+6 to 10+5 → version 2 to 3 → same OPEN-session reload, with no Submit or
additional Tutor execution. Full isolated Python was 941 passed / 7 skipped;
web tests 28 passed; typecheck/build/Alembic evidence is recorded with its
source applicability. The two recovered historical 401 episodes remain OPEN
OBSERVATIONS with unknown cause; the old expiry 409 is separate; neither
recurred during the final touch test. Acceptance does not establish live-model
pedagogical quality, physical-device coverage, deployment, unrestricted daily
use, Real-Lina history, or final Studio acceptance.

**Purpose:** deliver the smallest complete production integration slice that
connects accepted Studio Core and the accepted Math, Science, and English
Activities to the real greenfield Daily Student App at `/student/daily`. This
is real product integration, not another isolated activity review mount.

**Dependencies and retained boundaries:** `STUDIO-RUNTIME-03`,
`STUDIO-ACT-MATH-01`, `STUDIO-ACT-SCI-01`, and `STUDIO-ACT-EN-01` are
`DONE / ACCEPTED`. `STUDIO-ACT-AR-01` is DONE / ACCEPTED after FE-02 acceptance
and does not reopen this accepted integration; its accepted implementation extends
the same exact Renderer Host. `CURR-RENDER-MATH-01A` remains blocked and does
not block this integration. The current `/student` page and `StudentMathSession` are protected
legacy/experimental regression assets: do not import, wrap, extract from,
restyle, modify, or route through them. The preserved FE-02 prototype is
reference evidence only; do not merge it or make it production architecture.

### Accepted production outputs

1. **Greenfield Daily Student App.** Create/complete only `/student/daily` as
   the production target: Learning Chat plus a conditional Adaptive Learning
   Workspace. Chat occupies the available width when no actual active Studio
   Scene exists. Workspace appears only for an active real Scene; it never
   renders a permanent empty panel, fake capability, or placeholder card.
2. **Production Studio controller.** Connect the existing web Studio contracts
   and controller to authenticated runtime/session acquisition, initial
   Snapshot load, active-Scene presentation, typed semantic operations,
   dedicated Studio feed, reconnect/resume, and server-rejection
   reconciliation. Browser state is presentation/optimistic state only; the
   durable server Snapshot/Event history remains authoritative.
3. **Application-owned renderer host.** Dispatch only registered, exact
   Activity/Renderer contracts. Support the accepted Make-Ten, Science Process
   Sequence, and English Sentence Ordering activities. Do not parse activity
   prose, infer renderers from Tutor text, or create a generic arbitrary
   artifact executor.
4. **Tutor/Workspace composition.** Keep existing Tutor SSE as conversational
   authority and the dedicated Studio feed as Workspace-state authority. Reuse
   Runtime-03 for Canvas-originated continuation; do not create a second Tutor
   or mix independent Studio lifecycle into Tutor delta text.
5. **Real lifecycle presentation.** Cover Chat-only; active Workspace open;
   interaction; optimistic pending; accepted update; stale/rejected
   reconciliation; Tutor streaming while Studio follows accepted concurrency
   rules; reconnect/feed resume; Scene/activity replacement; renderer/error
   fallback; and close/empty Workspace where current contracts support it.
   Do not simulate future functionality.

### Confirmed reusable seams and exact version mapping

**Backend/server authority to reuse:**

- `apps/api/routes/studio.py`: authenticated Student-scoped runtime open,
  Snapshot, typed operation, and SSE feed routes;
  `services/studio/protocol.py`: `StudioProtocolService`, bounded protocol
  frames, cursor validation, and server rejection contracts;
  `services/studio/service.py`, `services/studio/reducer.py`, and
  `services/studio/feed.py`: durable Event/Snapshot authority, reconstruction,
  and sequenced resumable feed;
- `services/studio/activity_activation.py` plus its three exact adapters, and
  `services/studio/subjects/`: existing bounded activity activation and
  immutable Subject Capability Registry; do not add an activation router;
- `apps/api/routes/student.py` and `services/studio/interactions.py`: existing
  Student session/auth/Safety/Tutor authority, normal Tutor stream, and
  Runtime-03 Canvas-interaction stream/provenance/supersession lifecycle.

**Web authority to reuse:**

- `apps/web/lib/studio/contracts.ts`, `controller.ts`, and `sse.ts`: the
  project-owned protocol parser, authenticated command client, cursor/feed
  behavior, and SSE parser; do not create a second Studio client, event
  reducer, or SSE abstraction without demonstrated need;
- `apps/web/lib/tutor-stream-turn-protocol.ts` and
  `tutor-stream-lifecycle-trace.ts`, plus the existing Student API contract:
  preserve Tutor provisional `delta`, terminal `turn`, rollback, Safety/error,
  and content-free lifecycle behavior without importing legacy presentation;
- `apps/web/components/studio/*` and `apps/web/lib/studio/*` below: reuse the
  accepted renderer components and state/operation readers, but never the
  review-mount-only `applyMock*Operation` functions as production authority.

| Subject/profile | Exact activity/renderer contract | Reuse in Renderer Host |
| --- | --- | --- |
| `MATH / subject-profile-v2` | `ten_frame_group_transfer / ten-frame-group-transfer-activity-v1`; `ten-frame-group-transfer / ten-frame-group-transfer-renderer-v1` | `TenFrameGroupTransfer`, `readMakeTenState`, and typed operation builders. |
| `SCIENCE / subject-profile-v2` | `process_sequence_workspace / process-sequence-workspace-activity-v1`; `process-sequence-workspace / process-sequence-workspace-renderer-v1` | `ProcessSequenceWorkspace`, `readProcessSequenceState`, and typed operation builders. |
| `ENGLISH / subject-profile-v2` | `sentence_ordering_workspace / sentence-ordering-workspace-activity-v1`; `sentence-ordering-workspace / sentence-ordering-workspace-renderer-v1` | `SentenceOrderingWorkspace`, `readSentenceOrderingState`, and typed operation builders. |

### Required implementation checks before code

Record the resolved result for each item in the implementation change/review;
these are code-grounded checks, not Product Owner questions about internal
function names:

- The exact greenfield `/student/daily` baseline. At this promotion it is not
  tracked on `codex/ctx-03`; the prototype branch is archival reference only.
- The exact authenticated Chat transport/session/opening seam, including how
  the new route uses the existing Student session and Tutor SSE contract
  without importing `StudentMathSession` or creating another Chat runtime.
- Studio runtime acquisition from that authenticated LearningSession, initial
  Snapshot load, active Scene selection, and Studio SSE `after_sequence` /
  `Last-Event-ID` resume semantics.
- The renderer-host contract and exact persisted profile/activity/renderer
  identity supplied to it. The current public Snapshot frame exposes scene,
  active subject/activity, and state but not the full profile/activity/renderer
  version tuple; resolve a server-authoritative exact-identity path before
  dispatch. Do not infer a latest version or add a client-only registry guess.
- The mapping above from each accepted exact Activity/Renderer to its component,
  state reader, typed operations, fallback, locale, and direction behavior.
- Ownership of optimistic projections, operation idempotency, server conflict
  reconciliation, feed replay idempotency, and the prohibition on
  activity-specific React persistence or `applyMock*Operation` truth.
- Tutor-stream versus Studio-feed concurrency; record-only behavior during a
  Tutor stream; one and only one Runtime-03 continuation for a
  Tutor-triggering Activity action; superseded/cancelled provisional state.
- Workspace open, close, replacement, reconnect, error/fallback, narrow/mobile
  composition, keyboard/focus transition, reduced motion, and Arabic RTL /
  English LTR / mixed-direction behavior.

If a required safe contract extension or an unresolved lifecycle behavior
requires a genuine Product decision, surface it before inventing behavior.

### Protected product behavior

- One Student-facing Tutor; no fake Student messages; free-form Student
  language remains Chat or Voice-to-STT-to-Chat.
- Canvas is bounded semantic interaction only: no direct Candidate, Evidence,
  Personal Facts, Current State, Pattern, or Learning Intelligence writes; no
  extra Canvas model call for known activities.
- Server-owned durable state; Student isolation; Safety/Parent Boundaries;
  exact-version Activity/Renderer resolution; Runtime-03 provenance and
  supersession remain unchanged.
- React + Tailwind + checked-in shadcn/ui remain the functional baseline.
  assistant-ui remains rejected for runtime/session/stream architecture;
  ThreeUI/Spline are visual references only. Add no frontend dependency by
  default, no Three.js/R3F architecture, generic Artifact Engine, Canvas
  Specialist, or generated-media expansion. Adapt the warm, intelligent, calm
  visual character to the Daily App; do not copy an isolated review mount
  wholesale.

### Explicit non-scope

`STUDIO-ACT-AR-01` implementation or its final proof decision;
`CURR-RENDER-MATH-01A`; Grade 5 renderer batches; Canvas Specialist; generic
Artifact Engine; attachments; image/PDF/generated-image/video/3D pipelines;
new curriculum work; Voice/STT; Vision; deployment; Real-Lina production
history; redesign of accepted Studio Core; or replacement of the Chat/Tutor
backend.

### Required future verification and independent-review gate

Acceptance requires real authenticated `/student/daily` flows, not mock review
mounts alone:

1. **Chat-only:** full usable Chat width, no empty fake Workspace.
2. **Math:** real accepted Make-Ten Scene via the Renderer Host; mouse,
   emulated touch, and keyboard reach the real backend; Snapshot/feed update;
   submit starts one Runtime-03 continuation.
3. **Science:** real Process Sequence through the same host/protocol/state
   architecture with no Math-specific frontend assumption.
4. **English:** real text-oriented renderer through the same host; English LTR
   tokens in Arabic RTL UI; no answer-key leakage or free-form Canvas input.
5. **Persistence/recovery:** reload restores active Workspace; resume does not
   duplicate; accepted operations survive reload; stale/rejected optimism
   reconciles to server truth.
6. **Concurrency:** record-only Canvas action during Tutor streaming follows
   accepted Runtime rules; a Tutor-triggering action creates exactly one
   continuation; superseded/cancelled state is truthful.
7. **UX/accessibility:** desktop and narrow/mobile; Arabic RTL, English LTR,
   mixed direction; keyboard focus and Workspace open/close transition;
   reduced motion; loading, reconnect, and error states.
8. **Architecture regression:** legacy `/student` and `StudentMathSession`
   unchanged; prototype unchanged; no second state/runtime authority; known
   Activities make zero Canvas Specialist calls.

Run focused backend/web integration tests; authenticated production-intent
browser tests; web typecheck/build; relevant Python regressions; the full
isolated regression suite when shared source changes justify it; tracked and
relevant-untracked diff checks; and a fresh independent review. Isolated
activity review mounts are not FE-02 acceptance evidence.

**Final Studio acceptance boundary:** `STUDIO-ACCEPT-01` remains **BLOCKED /
NOT PROMOTED**. FE-02 and the original bounded Arabic activity are accepted.
Full-system Studio acceptance has not been performed or separately authorized.

---

# Approved Sequence

```text
RL-01A Accepted Runtime Alignment — DONE / ACCEPTED
→ RL-01B Fresh Shared DB + Runtime Composition — DONE / ACCEPTED
→ RL-01C Clerk + OpenAI Operational Verification — DONE / ACCEPTED
→ RL-01D Controlled Full Intelligence Loop — DONE / ACCEPTED
→ TASK-027A Student Core Profile — DONE / ACCEPTED
→ PF-01 Personal Facts Contract — DONE / ACCEPTED
→ PF-02 Personal Facts Extraction/Reconciliation — DONE / ACCEPTED
→ PF-02A Existing-Fact-Aware Personal Facts Extraction — DONE / ACCEPTED
→ PF-03 Relevant Facts in Tutor Context — ACCEPTED / COMPLETED
→ FE-01 Visual System + Library Capability + Reuse Decision Record — ACCEPTED / COMPLETED
→ FE-02 Daily Student Experience — BLOCKED
→ TASK-032 Voice / STT — BLOCKED
→ TASK-033 Vision / Student Work — BLOCKED
→ TASK-034 Original-Image Annotation — BLOCKED
→ DEPLOY-01 Private Daily Environment — BLOCKED
→ LINA-R1 Clean Real-Use Baseline — BLOCKED
```

Post-launch work is not a Release-1 blocker: measured RAG evaluation, selected renderer/artifact expansion, Science production, Grade transition, advanced Parent Insights, clustering/ML, and optional illustrative image generation.

---

## RL-01A — Accepted Runtime Alignment
**Status:** DONE / ACCEPTED

## RL-01B — Fresh Shared Application DB & Runtime Composition
**Status:** DONE / ACCEPTED  
**Accepted commit:** `dc76195bcb9ba7577b5f6dbbf0804f5bff6c43ff`

**Accepted result:** fresh shared PostgreSQL/pgvector DB, aligned Web/API/Worker runtime, standard Worker command, Worker recovery smoke, and Student-scoped shared-DB isolation.

## RL-01C — Clerk + OpenAI Operational Verification
**Status:** DONE / ACCEPTED

**Accepted result:** real Clerk Student/Parent auth and signed backend roles, explicit Parent→Student authorization, real OpenAI Tutor/Segment Review/embedding routes through Model Gateway, AI execution lineage, and real-auth cross-Student isolation.

## RL-01D — Controlled Full Intelligence Loop
**Status:** DONE / ACCEPTED

**Accepted result:** real multi-turn Tutor interaction with one primary call per normal turn; natural Session/Segment lifecycle; real Segment Learning Review; deterministic Session Finalization with zero semantic Session LLM calls; source-linked Event/Evidence/State/Pattern/Decision materialization; relevant later intelligence selection without full historical transcript; irrelevant fraction intelligence excluded from an unrelated Math question; healthy recovery from a transient review-provider failure; cross-Student scoping preserved.

**Accepted streaming fix:** `3af613484266e2c21d9e91a20d09ef217b05c16e`.

---

# User Knowledge Foundation

## TASK-027A — Student Core Profile & Tutor Student Context

**Status:** DONE / ACCEPTED  
**Dependencies:** RL-01D accepted  
**Accepted commit:** `57a763bbd538157c6503c10f64d0010a91dc2c46`  
**Alembic head:** `f9b1c2d3e4f5`

**Accepted result:**
- existing Student identity reused; nullable `date_of_birth` added;
- age derived deterministically and never stored independently;
- GradePeriod reused with Student-scoped deterministic effective-period resolution;
- future Grade scheduling preserves the current effective Grade through the day before transition and rejects conflicting overlaps;
- linked Parent/System Core Profile GET/PUT boundary established;
- Tutor receives only compact `display_name`, `age_years`, and effective `grade_level`;
- raw DOB/IDs/Parent metadata excluded from model-facing Core Context;
- Personal Facts and Learner Intelligence remain separate;
- existing Retrieval caller uses resolved effective grade without RAG redesign;
- one primary Tutor model call remains unchanged;
- cross-Student Core Profile isolation verified.

---

## PF-01 — Personal Facts Contract

**Status:** DONE / ACCEPTED
**Dependencies:** TASK-027A accepted

**Accepted contract:** `docs/PERSONAL_FACTS_SPEC.md`.

### Approved source authority

- Personal Facts are **Student-asserted**.
- They come from explicit Student statements about herself/her ordinary world.
- Parent claims do not automatically become Student Personal Facts.
- Repeated topic discussion without an explicit assertion does not become an inferred preference, interest, personality trait, or talent.

### Approved simple model

Release 1 uses:

```text
Personal Fact
+
Personal Fact Observations
```

A Fact is identified by:
- `student_id`;
- controlled category;
- stable `fact_key` representing the topic/semantic slot;
- normalized value representing the explicit assertion.

Example:

```text
fact_key = preference:drawing
value = LIKE
```

A different explicit value for the same key is a separate Fact, not an overwrite:

```text
preference:drawing = LIKE
preference:drawing = DISLIKE
```

The current value for a `fact_key` is determined at read time from the most recently observed explicit Fact. Older Facts remain historical context.

### Observation / count contract

Every explicit support for an exact Fact creates a source-linked Observation.

The Fact exposes or can cheaply derive:
- `support_count`;
- `first_observed_at`;
- `last_observed_at`.

Repeated explicit support strengthens the historical relationship by increasing count and refreshing recency. Do **not** store arbitrary confidence percentages.

Observation rows/source lineage remain the trustworthy basis for count/history; a cached count is allowed only if it remains rebuildable from observations.

### Qualification boundary

Good Release-1 Personal Facts include ordinary durable personal context such as:
- explicit preferences/favorites/interests;
- recurring activities;
- pets;
- ordinary non-sensitive relationships;
- other safe durable personal context that can make later conversation naturally personalized.

Not Personal Facts:
- one-off future plans or calendar events;
- temporary daily states;
- inferred interests from repetition alone;
- transcript summaries;
- Core Profile competitors such as authoritative age/Grade;
- Learning Intelligence/Evidence or academic judgments;
- personality/psychology/diagnosis/intelligence/learning-style/talent conclusions;
- unsafe sensitive personal information.

Examples:
- “I like drawing.” → Personal Fact.
- “I play basketball every Thursday.” → Personal Fact.
- “I’m going to Jeddah next weekend.” → Conversation Context only.
- “I’m tired today.” → Conversation Context only.
- repeated football discussion without “I like football.” → no Personal Fact.
- “I’m bad at math.” → not Personal Fact; current conversation may respond naturally, while learning conclusions require the Learning Intelligence evidence path.
- “I’m shy.” → conversation-only; no personality memory.

`TEMPORAL_EVENT` is not part of the Release-1 Personal Facts taxonomy.

### Safety/privacy boundary

Do not persist sensitive child information into Personal Facts merely because it appears in conversation, including credentials, precise address/live location, contact details, financial/account information, highly sensitive medical/private information, sexual/private information, or safety-risk secrets. Existing raw-history and Safety policies remain separate authorities.

### Authority separation

```text
Student Core Profile = Parent/System-authoritative application facts
Personal Facts       = Student-asserted factual personal context
Learner Intelligence = learning-derived evidence-backed state
Conversation Context = current/raw conversational continuity
Safety               = safety authority
RAG                  = curriculum/reference grounding
```

Personal Facts never become Learning Evidence merely because they exist.

### Parent inspection

- Parent may inspect stored Personal Facts for the linked Student.
- Parent may see the Fact plus count/first/last-observed support/history where useful.
- Inspection does not make Parent a Personal-Fact source.
- No separate hidden child-facts database is required.

### Isolation/rebuildability

- every Fact and Observation is Student-scoped;
- every Observation traces to a Student-authored source message/interaction;
- Student A Facts can never be selected/reconciled/displayed for Student B;
- Fact counts/current state remain reconstructable from source-linked observations/history.

### PF-03 direction — SUPERSEDED / REQUIRES NEW PF-03 DESIGN

Personal Facts are optional Tutor assistance, not a teaching dependency.

Do **not** add a vector-memory platform and do **not** mix Personal Facts into curriculum RAG.

The previous deterministic lexical/key-matching direction is superseded and is **not** an approved semantic-relevance implementation decision. PF-03 requires a new bounded design decision before implementation. Retain the protected constraints: Student scoping, latest-explicit current-state semantics, bounded optional context, no extra normal-turn model call, and no vector-memory platform by default.

### PF-02 handoff direction

Keep reconciliation simple:
- new `(student_id, fact_key, value)` → `ADD` Fact + first Observation;
- same exact Fact asserted again → `SUPPORT` existing Fact with another Observation;
- same `fact_key` with a different explicit value → `ADD` a new historical Fact for that key; latest explicit Fact becomes current at read time;
- ineligible/sensitive/inferred/authority-conflicting statement → `NOOP`.

Do not require a complex supersession/invalidation state machine for Release 1.

### Verification

PF-01 is complete only when the contract unambiguously defines:
- explicit durable vs conversation-only vs prohibited memory;
- `fact_key` + normalized value identity;
- observation/source lineage;
- support count + first/last observed history;
- latest-explicit-current behavior for conflicting values;
- child-sensitive storage exclusions;
- Parent inspection;
- cross-Student isolation;
- cheap optional retrieval direction that remains separate from RAG and Learning Intelligence.

### Explicit exclusions

PF-01 does **not** implement:
- LLM/model extraction;
- Worker jobs;
- Fact/Observation database models or migration;
- Tutor Personal Facts selection/injection;
- vector Personal Facts retrieval;
- Parent Insights;
- frontend memory UI;
- graph/Graphiti or generic memory frameworks;
- PF-02 or PF-03.

**Completion:** Product Owner accepted the concise Release-1 Fact + Observation History contract, including latest-explicit-current read semantics, child privacy exclusions, a derived Personal Memory Document, and the separate PF-02 Session-level extraction boundary.

---

## PF-02 — Personal Facts Extraction & Reconciliation

**Status:** DONE / ACCEPTED
**Dependencies:** PF-01 accepted  
**Purpose:** One dedicated asynchronous Personal Facts Model Gateway call per completed Learning Session, separate from Tutor teaching and Segment Learning Review. Candidates must cite Student-authored source messages; deterministic reconciliation performs only `ADD` / `SUPPORT` / `NOOP`, with no second reconciliation model call. Refresh the derived Personal Memory Document deterministically after reconciliation. This path does not write Learning Events, Evidence, Current State, or Patterns.

**Accepted result:** additive migration `a1d2e3f4b5c6`; dedicated `PERSONAL_FACTS_EXTRACTION` job/handler through the existing Worker and `ModelTask.PERSONAL_FACTS`; strict Student-source/safety validation; canonical fact-key/value validation; deterministic `ADD` / `SUPPORT` / `NOOP`; Fact plus Observation persistence; retry-safe extraction runs; capacity-skip semantics; and an on-demand latest-fact document projection. There is no Tutor, Segment Review, or RAG coupling. Fresh-migration full Python verification: `770 passed, 7 skipped`. The Daily-Use DB remains at this head with its pre-existing Student/Session/Message rows preserved. No PF-03 behavior is included.

---

## PF-02A — Existing-Fact-Aware Personal Facts Extraction

**Status:** DONE / ACCEPTED
**Dependencies:** PF-02 accepted
**Purpose:** Extend the existing single completed-Session Personal Facts model request with a compact, Student-scoped catalog of all known Fact identities, including historical contrary values. The same call chooses `SUPPORT_EXISTING` for a supplied Fact ID or `ADD_NEW` for a genuinely new canonical identity; server validation and deterministic Observation reconciliation remain authoritative. No new model call, schema, Worker architecture, Tutor, Segment Review, Learning Intelligence, or RAG behavior is added.

**Accepted result:** the existing PF model call receives all target-Student Fact identities, including historical contrary values, and semantically chooses `SUPPORT_EXISTING` versus `ADD_NEW`. The server deterministically validates grounding, ownership, safety, canonical structure, and idempotent persistence. Known Facts are untrusted reference data only; there is no extra model call, embedding/vector matching, schema/migration change, or cross-Student leakage.

---

## PF-03 — Relevant Personal Facts in Tutor Context

**Status:** ACCEPTED / COMPLETED
**Dependencies:** PF-02A accepted
**Purpose:** Read-only injection of the full compact current Personal Memory Card as a separate optional Tutor context block beside Conversation Context, Student Core Context, Learner Intelligence, optional curriculum RAG, and Safety. The Tutor decides semantic usefulness inside the existing primary call; there is no pre-Tutor lexical/key matching, retrieval, PF model call, embedding call, or vector-memory platform.

**Acceptance:** Product Owner accepted commit `6436b358ff42425fd729af316cb9525e6511f534`; PF-03 `7 passed`, protected regression `182 passed`, and diff/show checks passed. Pushed to `origin/codex/ctx-03`. No FE-01 work was performed.

---

# Lina Frontend — Daily-Use Launch UX

## FE-01 — Visual System + Library Capability + Reuse Decision Record
**Status:** ACCEPTED / COMPLETED — DOCUMENTATION ONLY
**Dependencies:** PF-03 accepted

**Scope:** Code-grounded documentation only. Define Learning Chat + Adaptive
Learning Workspace, classify reusable UI/library candidates, map FE-02's
present and future-ready Workspace capabilities, and preserve current Student
session/SSE contracts. No UI code, dependency, API, Tutor, Personal Facts,
migration, Voice, Vision, attachment, generated-image, video, 3D, artifact,
or deployment implementation is in scope.

**Decision record:** `docs/FE-01_VISUAL_SYSTEM_LIBRARY_DECISION.md`.

**Acceptance:** Product Owner accepted documentation commit
`8601ed5f485ff29fdb467db7abfb8f7ad44711b0`. Scope: Visual System + Library
Capability + Learning Chat + Adaptive Learning Workspace for learners roughly
10–18, with Lina as the first private daily-use Student. This task changed no
UI code, dependencies, tests, runtime behavior, or PF-03 behavior. Its
`FE-02 remains BLOCKED / NOT STARTED` statement is historical; current Studio
readiness is governed by the Studio track at the top of this file.

## FE-02 — Daily Student Experience
**Status:** BLOCKED  
**Dependencies:** FE-01 accepted

**2026-09-02 Product Owner scope clarification:** The existing /student page and StudentMathSession are protected experimental/legacy functional shell and behavioral regression-harness assets. FE-02 is no longer an evolution of that UI. The Daily Student App must be a separate greenfield surface at /student/daily, reusing accepted backend/session/SSE/Tutor/Safety/PF-03 contracts rather than the existing UI implementation. Do not import, wrap, extract from, restyle, modify, or route through the legacy Student components.

**Completed fit check:** assistant-ui presentation primitives are REJECTED for
FE-02. Its runtime-bound behavior or required adapter/state bridge is not safe
as presentation-only use for this slice; it cannot own runtime, backend,
transport, session, safety, or stream lifecycle. The local path remains a new
React/Tailwind/shadcn surface with a project-owned SSE controller.

**Completed FE-CHAT-UI-01:** Existing local React/Tailwind/shadcn primitives
are ADOPT PATTERN; official shadcn chat patterns are PARTIAL ADOPT PATTERN; AI
Elements, VLLNT, and shadcn.io are UX REFERENCE ONLY; 21st.dev Agent Elements
is REJECT. FE-02 needs no chat-library installation and retains project-owned
SSE/controller/message/composer/action/guided-check/direction/error/rollback/
lifecycle behavior.

**Next pre-code gates:** Product Owner approval of the first-screen visual
brief and explicit FE-02 implementation authorization.

**Deferred by this task:** Three.js/React Three Fiber, attachments, image/PDF handling, generated images, video, Artifact Engine, MathLive, JSXGraph, Konva, and all backend/API/SSE schema changes remain out of scope unless separately approved.

---

# Multimodal Launch Capabilities

## TASK-032 — Voice Input / STT
**Status:** BLOCKED  
**Dependencies:** FE-02 accepted; RL-01C Model Gateway operational

## TASK-033 — Student Image / Handwriting / Drawing Understanding
**Status:** BLOCKED  
**Dependencies:** TASK-032 accepted; durable/private storage; RL-01C Model Gateway operational

## TASK-034 — Annotate Original Image First
**Status:** BLOCKED  
**Dependencies:** TASK-033 accepted

---

# Private Daily-Use Deployment

## DEPLOY-01 — Lina Private Daily Environment
**Status:** BLOCKED  
**Dependencies:** TASK-034 accepted

## LINA-R1 — Clean Real-Use Baseline
**Status:** BLOCKED  
**Dependencies:** DEPLOY-01 accepted

---

# Post-Launch — Not Release 1 Blockers

## RAG-EVAL-01 — Measured Retrieval Evaluation
**Status:** BLOCKED

## TASK-035 — Interactive Learning Artifacts
**Status:** BLOCKED

## PARENT-INSIGHT-01 — Facts × Learning Exploration
**Status:** BLOCKED / FUTURE / DATA-DEPENDENT

---

# Still Deferred / Independent

Not promoted by this launch plan unless separately approved: `MATH-01`, `ID-01` unless reproduced, `EDU-ERR-01`, `REC-25`, `LR-D04B`, Science production, retention/proactive learning, Grade transition production, advanced gamification, graph/Graphiti, Redis/Celery, advanced ML before real data, and broad Parent Dashboard expansion beyond specifically promoted needs.
