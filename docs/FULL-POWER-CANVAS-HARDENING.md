# Full-Power Canvas hardening: engineering and acceptance evidence

> Historical hardening evidence. It records observed engineering results and limits; it does not authorize further hardening or define current production-use readiness.

Baseline: `ebac3fef92427ac203d241f7cd60eafdb1187c6c`, branch `codex/full-power-canvas-01`, checkout `.worktrees/full-power-canvas-01`. Root main and unrelated work are preserved. Runtime model: **gpt-5.6-luna**. No live-generated source was manually repaired. At the time of the evidence collection, no push, merge or deployment was authorized.

**Independent verification and automatic correction are implemented and live-proven. Broad production acceptance is not met.** Model and protected architecture remain unchanged.

## Findings and changes

1. **Instruction conflicts.** Development AGENTS described ordinary parameter/presentation binding as ADAPT; runtime guidance prohibited browser source while CREATE required it; example-specific scaffolding and a stale Tutor `workspace_intent` instruction conflicted with Full-Power `canvas_brief`. These now agree with the existing architecture. Custom source stays in immutable sandbox Builds; ordinary supported parameters are REUSE; generalized capability changes require ADAPT lineage.
2. **Avoidable model work.** Empty registry search consumed a first model turn. The composer now receives a bounded owner-filtered catalog and cannot call empty search/instantiate tools. Hosted content tools and typed composition tools are removed after selecting CREATE. Independent file text is cached locally; there is no cross-owner generated-content cache. Superseded preview images are removed from subsequent model requests; current images, source, text diagnostics and complete SDK traces remain.
3. **Unclear CREATE contracts.** Existing scalar, string, source, identifier and array bounds are exposed in the tool schema. Numbers and booleans retain their types. Provider argument/schema errors are distinguished from canonical Manifest failures and browser failures; redacted SDK errors are explicitly uncertain rather than falsely diagnosed as missing Manifest fields.
4. **Fragile correction/finalization.** Source correction uses 1–8 exact unique edits, preserving immutable parameters and Manifest. CREATE and source corrections have independent counters: at most two CREATE calls and at most three source corrections, **at most four authoring attempts total**. A successful first CREATE leaves up to three corrections; two CREATE calls leave only two corrections, within the existing five-minute/16-turn limit. A replacement CREATE requires an explicit immutable-parameter or Manifest reason. Retired candidates cannot reappear in the final Scene. Hash-based instance/revision identifiers avoid valid long-name collisions. One tool-less final-plan reference repair preserves canonical validation and cannot regenerate the lesson.
5. **Insufficient browser proof.** Rendering alone missed dead controls, mobile targets, discarded state and late geometry restoration. Production preview now uses the exact opaque sandbox in private Chrome with network blocked, a 25-second process-group deadline and bounded results. It exercises actual mouse/touch/keyboard controls, all declared actions, local drafts and short multi-step workflows. It checks **960×384 and 640×384 desktop panes** viewports, actual SVG font scaling, clipping, labels covered by controls, and restoration after **every** value-bearing action. A final reset can no longer hide earlier lost state. Inactive/initially bounded controls are retried after real state changes; successful unrelated actions do not establish a missing action.
6. **Sandbox interaction defects.** Typed state reads preserve zero and composite values. Semantic control handles bind real DOM elements and produce canonical string mutations. Document-level drag capture survives inner redraw and supports touch; duplicate release emission is suppressed. Generated source must rebind recreated elements and read the same semantic ID it emits. The iframe has no application/network authority; ownership, nonce, event validation, digest resolution and immutable provenance remain server-owned.
7. **Host delivery and container layout.** Rapid browser actions previously collided with a pending save and could leave unsaved local state visible. The actual renderer now queues bounded operations against committed versions, cancels queued work on rejection/Scene replacement, and reports failure honestly. It preserves each received action rather than silently coalescing learner work. The real container width controls iframe height through a shared preview/renderer function. Repeated objective/meaning prose is removed around custom visuals while accessible meaning remains.
8. **Quality and cost observability.** The same composer must review educational correctness, Semantic Manifest integrity, representation, interaction, responsive legibility, replay and text economy. Known technical defects veto finalization. Both successful and failed attempts retain observed usage/cost and timing; unknown usage remains unknown. Per-action replay initially repeated whole-scene text into model history; a sentence run reached **267,594 input tokens**. Compact grouped check coverage now preserves failed differences and all current screenshots without repeating successful text. Full observer results remain available.

9. **Self-review false positives.** A same-Luna verifier receives only the admitted brief, bounded learner context, current source/Manifest/parameters and actual screenshots. It has no tools, teaching or persistence authority and does not see the composer's self-assessment. A veto returns concrete defects to the existing composer. CREATE/refinement quotas and the shared 16-turn budget remain enforced; exhaustion is terminal and preserves observed usage. This supplements technical checks; it is not a guarantee of pedagogical correctness.
10. **Preview diagnostic loss.** Repeated dead gestures could consume the 25-second process deadline and return no screenshots. Interaction probes now stop within an eight-second per-layout budget and stop repeating failures without intervening state changes. Incomplete coverage remains rejected, with both layouts and actionable findings retained. A many-dead-control Chrome regression covers this behavior.

## Evidence boundaries

- The production renderer **component** and exact custom iframe source run in a disposable proof shell. Its outer CSS is harness CSS, not the complete authenticated Daily application. Actual owned Snapshot, Build, operation and Primary Tutor routes are used.
- A `COMPLETED` proof means Tutor → worker/Luna → Scene → synthetic protocol action → Tutor completed. It does **not** establish educational or human browser acceptance.
- Live original source remains unchanged. Corrections are model-emitted production tool calls. Re-auditing an immutable package is not a new CREATE or a repaired acceptance result.
- All costs below are the repository's configured Luna token estimates: $0.50/M input, $0.05/M cached input, $3/M output. They exclude hosted-tool fees and Tutor calls; they are not invoices or a refreshed external price claim.
- Harness elapsed time includes setup and Tutor turns. Summed Luna latency, preview time and worker settlement are reported separately. This is a small development sample, not a statistically controlled production benchmark.

## Cohorts and retained failures

Raw local evidence: `output/canvas-production-hardening/`. The unchanged six prompts are in `tests/fixtures/canvas_production_cases.json`: fraction relationship, triangle reflection, Arabic water cycle, Arabic sentence structure, material classification, and equivalent-balance state.

| Cohort | Full protocol completion | Interpretation |
|---|---:|---|
| baseline | 4/6 | 5/6 Canvas compositions settled; balance later failed stale Tutor intent; weaker preview, no six-visual acceptance |
| after-bounded | 1/6 | Development evidence |
| after-contract | 3/6 | Fraction later failed actual full-page state restoration |
| after-mobile | 3/6 | Narrow checks added; geometry restoration still incomplete |
| after-replay | 2/6 | Multi-step/compound-reset probe defects identified and corrected |
| after-independent-bounds | 4/6 | Separate CREATE/refine quotas; one fraction Build later qualified for its exact lesson |
| after-responsive-contract | 4/6 | Human review rejected false partition behavior and obscured classification labels; per-action replay subsequently rejected balance |
| final-per-action-replay | 1/6 | Intermediate restoration exposed more defects; repeated successful diagnostic text inflated sentence cost |
| independent-verification | 1/6 | Same-Luna independent review corrected and accepted sentence; vetoed water. Other candidates failed technical/self-review checks. |
| frozen-acceptance | 2/6 automatic protocols; 3/6 Canvas compositions settled | Fraction synthetic selector lacked SET_VALUE; real browser follow-up completed it. Human quality remained narrower. |

Exploratory `after-pilot*`, `after-editpilot*`, `after-controls*` and `after-diagnostics*` results are retained as well. No failed run is removed from the observed-cost denominator. Late development refinements to the per-action cohort included collapsed-label detection and retrying initially bounded controls; that cohort is diagnostic evidence, not a frozen performance comparison. `frozen-acceptance` records runtime source hashes per case.

## Measured CREATE cost and latency

Baseline per-case summed Canvas Luna usage, including failed attempts:

| Case | Calls | Luna seconds | Input tokens | Output tokens | Estimated USD |
|---|---:|---:|---:|---:|---:|
| Fraction | 4 | 48.004 | 38,821 | 5,608 | 0.032589 |
| Reflection | 4 | 54.455 | 37,951 | 5,741 | 0.032615 |
| Water | 5 | 83.109 | 57,243 | 9,412 | 0.053244 |
| Sentence | 3 | 28.331 | 24,721 | 2,404 | 0.016042 |
| Classification | 4 | 45.107 | 36,406 | 4,430 | 0.027847 |
| Balance | 7 | 91.704 | 61,525 | 8,498 | 0.049094 |

Baseline six-case totals: **256,667 input / 36,093 output tokens, $0.211431**, mean Luna latency **58.452s**, median **51.230s**. Preview total was 16.593s across all six. Generation/review dominates, not browser startup or deterministic settlement. Initial baseline system text was about 13.4–13.8k characters; necessary stronger runtime guidance means the final system text is not uniformly smaller. The old 17,225-character tool-schema observation counted all registered schemas, not the phase-enabled schemas actually transmitted.

The browser-qualified CREATE from `after-independent-bounds` used **3 calls, 55.588s, 37,486 input / 5,311 output / 4,313 cached tokens, $0.032735**. It is slower than baseline fraction and about the same token cost; it provides stronger replay proof. Do not claim universal CREATE speed/cost improvement from the REUSE result.

Final frozen cohort (all six cases had equal runtime source fingerprints):

| Case | Canvas settled | Calls | Luna seconds | Input tokens | Output tokens | Estimated USD |
|---|---|---:|---:|---:|---:|---:|
| Fraction | Yes | 3 | 42.624 | 33,643 | 4,163 | 0.027265 |
| Reflection | No | 5 | 81.058 | 63,733 | 9,005 | 0.053464 |
| Water | Yes | 4 | 50.878 | 52,145 | 5,403 | 0.040267 |
| Sentence | Yes | 5 | 54.976 | 56,132 | 6,563 | 0.046332 |
| Classification | No | 5 | 90.682 | 69,341 | 10,709 | 0.065258 |
| Balance | No | 4 | 50.088 | 61,073 | 4,720 | 0.042688 |

Totals: **336,067 input / 40,563 output tokens, $0.275274**, mean Luna latency **61.718s**. Against baseline, aggregate CREATE token cost increased about **30.2%** and mean model latency about **5.6%**, while the checks became substantially stricter. This does **not** demonstrate a general CREATE efficiency win. The qualified frozen fraction itself was 11.2% faster and 16.3% lower token cost than baseline fraction, but that single case must not substitute for the full table.

The formerly inflated sentence diagnostics fell from 267,594 input tokens in the diagnostic cohort to 56,132 in the frozen cohort. Outputs differ, so this is an observed comparison rather than a pure causal benchmark. A focused test separately proves successful replay repetition is compacted while failed differences remain.

An explicitly isolated `reasoning.effort=high` experiment kept Luna, source contracts and correction limits unchanged. Reflection still failed: **3 calls, 182.287s, 49,995 input / 18,299 output tokens, $0.079895**. It retained ID/geometry/font defects and did not establish a quality benefit; it was **not adopted as a production setting**. One failed experiment does not prove a fundamental model impossibility.

At the pre-desktop snapshot, **78 observed development runs / 318 Canvas model calls**, including failed attempts and the high-reasoning experiment, total **$3.382921** in observed Canvas token estimates. One additional read-only known-defect verification call cost $0.005315, making $3.388235 across 319 observed Canvas/checker calls. Unobserved usage, Tutor costs and hosted fees are outside that figure. The portable per-run record is `docs/FULL-POWER-CANVAS-HARDENING_METRICS.json`.

 `scripts/summarize_canvas_production_quality.py` rebuilds per-run metrics from all retained timing files, including model-turn phase, preview and tool-payload measurements.


Latest six-case same-Luna independent-verification cohort (failures included):

| Case | Calls | Luna seconds | Input | Output | Estimated USD |
|---|---:|---:|---:|---:|---:|
| balance_state | 4 | 67.400 | 56,437 | 5,743 | 0.043439 |
| classification | 3 | 40.851 | 26,149 | 3,982 | 0.021174 |
| fraction_relationship | 4 | 40.775 | 47,064 | 4,300 | 0.030982 |
| reflection | 4 | 58.480 | 50,436 | 6,297 | 0.038499 |
| sentence_structure | 7 | 98.131 | 66,229 | 9,297 | 0.057131 |
| water_cycle | 7 | 110.678 | 86,887 | 11,666 | 0.076427 |

Totals: **333,202 input / 41,285 output, $0.267651**, mean **69.386s**. Versus baseline, estimated token cost is **26.6% higher** and mean Luna time **18.7% higher**. Independent checks account for 31.449s across two sentence reviews and 23.244s for the water veto. Quality checks were strengthened; no broad CREATE speed/cost improvement is claimed.

## Selective promotion and true REUSE

Qualified source run: `5481a57a-bd61-4291-8276-011e5f820856`.

- Build `f79f3384-8783-44d2-8b15-dcd4c29856bf`.
- Promoted Version `56ced5b7-cd7b-4bda-9cdf-a7bbf9e206af`.
- Source digest `e06a692906c38aed972c093e076efec850b792ab1f86e1446afa3a1cff8a56ff`.
- Scope: **the exact 1/3 versus 2/5 lesson with original parameters**. General arbitrary-fraction suitability is not established; the generated feedback is specific to this pair.

Actual browser SET_VALUE `92ce19a8-7886-4e7f-8ab0-3f0022d13ecf` and SUBMIT `7f45cc82-c0b3-41d4-aba5-b40eec27c5fd` reached `COMPLETED`. The displayed 10/30 and 12/30 survived full reload. Wide/narrow/feedback screenshots are `output/playwright/fraction-qualified-*.png`.

REUSE run `30ed768d-c9e4-42ed-b768-827e221d828b` created a new runtime `5f466414-8d3b-45d3-82fe-2c3ec4551394` and Scene `7961f71e-ac35-4f29-8eba-291980e47aeb`, referencing that **same Build and digest**. The sole tool was `instantiate_reusable_visual`; there was no CREATE/source regeneration. The same parameters were intentionally used, rather than claiming untested parameter generalization.

REUSE: **2 Luna calls, 7.189s, 17,546 input / 373 output / 8,622 cached tokens, $0.0060121**. Persisted preflight 35ms; instantiate tool 1ms; package/persistence 26ms; settlement 201ms; total worker 7.498s. Compared with the qualified CREATE, observed Luna time fell 87.1% and estimated token cost 81.6%. This comparison is CREATE versus REUSE, not a before/after CREATE benchmark.

Actual reused-instance SET_VALUE `c61b99e8-25e7-4a61-87fb-0bf8603bdb97` completed and restored 30 after full reload. Screenshots: `output/playwright/reuse-qualified-{wide,narrow}.png`. Three sampled real browser interaction-to-Tutor completions took **11.47–12.67s**, separate from Canvas generation time. The current interaction/Tutor cadence therefore remains a latency consideration.

## ADAPT and rejected browser observations

Live structural ADAPT run `2936f494-6747-413a-831b-aa2e2d65037f` requested a synchronized number-line capability, selected the qualified parent Version, and retained parent/generalized-change metadata. Its generated child remained clipped/too small after bounded corrections and was rejected before settlement. This historical attempt is not accepted; the later desktop ADAPT proof below succeeded. Existing lineage/ownership/digest regression remains covered.

Specific rejected results are retained:

- Earlier fraction run `518fe50f-fcae-4b3e-9cb1-902b777dbba2` saved an operation but ignored it on full reload.
- `after-responsive-contract` fraction run `e341d511-c3ac-457a-82cf-b3e82f688f73` changed common-partition captions while its bars remained divided only by their original denominators. Model self-review marked it adequate; source review rejected the claimed control effect.
- Classification Build `191fc98f-647d-4f92-a10c-ed544fbe7ee0` hid material labels beneath phone controls. The final collapsed-label guard rejects all six obscured labels.
- Balance Build `3980fed6-eb63-4cc2-adac-4e4066aae562` read `removed_pairs` but emitted `remove_pair`; final reset masked the lost intermediate state. The per-action replay guard rejects it.
- Arabic sentence Build `cecaeb8f-15fb-4985-aab5-18eddafd6144` retained grammatical role labels and fixed decorative connectors regardless of reordered sentence structure, and hid connectors on narrow screens. Technical interaction/replay success does not qualify its educational meaning.
- Water-cycle run `7debbab4-c9b0-4d0b-bdf3-1a1eb9fcb7b8` has working Arabic controls and saved heating, but its rotated precipitation arrow and direct heating/rain toggle do not fully demonstrate the requested connected mechanism. It is not an unconditional educational acceptance.

## Verification and reproduction

- Integrated regression: **1420 passed, 12 skipped in 72.56s**, isolated disposable PostgreSQL **55438**; log `output/canvas-production-hardening/desktop-release-integrated-pytest-v2.log`. Live evidence uses **55434** and was not reset.
- Independent-verification/budget focused regression: **44 passed** in `tests/test_custom_visual_preview.py` and `tests/test_agentic_canvas_orchestrator.py`.
- `node scripts/check_custom_visual_preview.cjs`: actual Chrome click/events, typed/zero state, touch drag through redraw, duplicate release, dead/unbound controls, mount failure, lost/late/intermediate replay, local-draft workflow, compound reset, covered/collapsed labels and initially bounded controls.
- `node scripts/check_canvas_operation_queue.cjs`: actual renderer with deterministic delayed/rejected persistence; rapid mutations serialize against committed versions and rejection cancels queued work. This is a regression fixture, not a generated-learning acceptance artifact.
- Frontend TypeScript and full Next production build passed with the existing public Clerk key explicitly supplied; log `output/canvas-production-hardening/desktop-final-build.log`. No key absence or prerender exception is concealed.
- Repository truth and `git diff --check` passed. Protected safety/ownership/digest/lineage/event and historical paths are covered by the integrated suite; no protected semantics, provider model, infrastructure service or schema was changed.

Reproduce a fresh desktop live cohort with `LINA_TEST_DATABASE_PORT=55434 ../../.venv/bin/python -m scripts.prove_canvas_production_quality --live --env-file ../../.env --cases tests/fixtures/canvas_desktop_production_cases.json --output-dir output/canvas-production-hardening --label UNIQUE_LABEL`. Use `--owner-run-id` only for an existing verified disposable owner when testing registry lifecycle. Never source `.env`, reset the evidence DB, or overwrite a prior label.

No authenticated Clerk/Daily end-to-end login, deployment, real-Lina learning benefit or production traffic reliability is established by these disposable proofs. Existing promoted Versions still rely on selective qualification; no retroactive quality migration or deletion of historical Builds was performed.

## Historical quality observations

- Frozen fraction Build `a787b38e-0ba9-466f-8c29-83a909cc0495`, run `7aefe564-476d-4e06-9663-4a68f36c0d04`, is accepted for its requested exact-pair comparison. Real partition SET_VALUE `24353145-7c99-4023-90e4-135cb7985143` and comparison SET_VALUE `16a68eaf-7e94-4a54-9e57-ce8cf0b13dc3` reached completed Tutor handoffs. Full reload restored both the common partition and selected 2/5. Screenshots `output/playwright/frozen-fraction-{wide,narrow}.png` show the actual renderer. Its automatic protocol failure was a proof-helper limitation, not a failed Canvas composition.
- Frozen reflection, classification and balance failed bounded production checks and were not silently replaced by inferior visuals.
- Frozen water Build `137394f7-421c-4f92-ab4e-b0c5e99d3e97` passed the cohort protocol but produced severely stretched Arabic SVG labels. Post-cohort final typography validation checks both dimensions and nonuniform scaling and rejects that immutable output (1.6× wide / 2.6× narrow). A real Chrome regression covers this class. Original cohort results are retained unchanged; the later independent-verification cohort includes this additional veto.
- Frozen sentence run `898813da-7c3a-42ae-955e-8dfa3634db4c` retained old feedback after reordered work. Read-only replay through the production independent checker rejected it: 11.604s, 6,177 input / 742 output tokens. No source or stored Scene was changed. The admitted brief mentioned a verbal sentence while its facts expressed the intended meaning in subject-first order; the target ordering is therefore not a clean isolated Canvas-only comparison. Stale feedback is an independently confirmed defect.

Confidence is high that the **current system is not ready for unrestricted production CREATE**: different generations still violate semantic, interaction and responsive requirements after bounded autonomous correction, and same-composer review can miss false causal behavior or stale educational feedback. This is evidence about the tested configuration, not proof that Luna can never succeed.

The independent-verification cohort completed one of six full protocols. Its sentence run `9bd075d7-30a3-4218-8f9c-d462118c0bb0` demonstrates the entire autonomous veto → source-only correction → independent acceptance → immutable settlement path. Real browser SUBMIT `ca652398-81fd-4775-af9b-740f9bd06f6b` and subsequent MOVE `0f9178e8-bd6f-46b9-a8b7-f26c6ae76563` completed. Reordering cleared confirmation; phone layout and full reload preserved the moved words. Screenshots: `output/playwright/independent-sentence-{wide,narrow}.png`. This verifies that behavior, not a universal grammar lesson: fixed role labels across arbitrary word orders and duplicated role presentation still limit educational generalization and visual quality.

The same verifier rejected water for an incomplete causal process, mobile overlap and ambiguous RTL transformation arrows despite positive author self-review. Fraction failed small text; reflection and balance failed replay/responsiveness; classification exhausted preview time and prompted the diagnostic-deadline fix. These are retained failures, not accepted visuals.


The deadline follow-up classification run `6157ef78-0e1e-49e2-81c9-27a00ab9f77e` returned actionable wide/narrow preview findings and performed automatic corrections, but still failed small text and clipped submission UI. Its five Luna calls took 83.109s and $0.059220. Separately, the exact unchanged source that previously hit 25 seconds returned six screenshots and blocking diagnostics in **17.702s** with the new preview deadline (`deadline-immutable-classification-audit.json`). Neither observation is counted as visual acceptance.

## Current desktop acceptance scope — Product Owner 2026-09-13

The Product Owner explicitly deferred mobile during review. Current production preview and Luna review now target **960×384 and 640×384 desktop Workspace panes**. The earlier 320px cohorts remain historical evidence and must not block the current release solely for mobile layout. Existing sandbox mobile regression coverage remains available; no event, safety, ownership, source or replay validation is weakened. `canvas_desktop_production_cases.json` preserves the six learning tasks while replacing the phone request with the current desktop scope. Fresh desktop live acceptance is recorded below; the previous capability/model decision disposition is not the active gate.


## Desktop reliability corrections

- Independent review now runs immediately after each candidate preview, before spending the remaining authoring budget. The SDK public tool-result callback pauses composition; accepted candidates receive one tool-free plan finalization. Technical findings and independent semantic findings return together to the original composer. The same four authoring attempts and shared 16-turn ceiling remain; the checker cannot persist, teach or rewrite source.
- Static canonical state-read diagnostics use the existing TypeScript parser, with lexical scope and scalar constant resolution. Unknown dynamic expressions remain subject to actual browser checks. This catches emitted/read ID mismatches without semantic keyword routing or executing source outside the sandbox.
- Replay requires exact saved values, identities and text. Drawing coordinates may differ by at most one quarter CSS pixel after serialization; visible geometry, path, transform or value changes still fail. An unchanged reflection candidate that was falsely rejected for rounding passed the corrected check in 2.300s.
- Owner-filtered REUSE summaries now include bounded canonical representation descriptions and interaction meanings. This prevents a missing capability from being concealed by a purpose/schema-only catalog. An earlier request for bars plus a number line incorrectly reused bars alone; that protocol completion is explicitly not ADAPT acceptance.
- Private preview captures now foreground their own page and wait for both iframe and parent paint. A replay page could previously leave a white screenshot despite valid DOM content. The unchanged ADAPT candidate returned six nonblank images in 1.730s under the corrected capture. This is an evidence-capture correction, not acceptance of the generated lesson. A real Chrome regression decodes every initial/action/replay PNG and verifies rendered pixel content at both desktop widths.
- Runtime preview dependencies are declared directly and pinned: Playwright 1.63.0, Sucrase 3.35.1 and TypeScript 5.9.3. A clean production-only install in an isolated temporary directory ran the real preview and state replay successfully. No new service was introduced. The install audit also reported existing Next/PostCSS dependency advisories; no unrelated major upgrade was applied, and whole-application security clearance is not claimed.

The desktop early-review reflection run `0418915e-a6c1-4c65-8702-deb81fdb4878` settled after automatic correction. Actual MOVE `5e340990-c82f-4592-bb29-ebac6a9d0176` completed; dragging A moved its mirror with equal perpendicular distance and survived full reload. Screenshots `output/playwright/desktop-reflection-{initial,moved,restored-selected}.png` retain the browser evidence. Non-square grid cells, label crowding after movement and missing SVG accessibility labels limit its overall quality qualification.

The interrupted `desktop-final` cohort is diagnostic only: fraction completed; reflection finished rejected for overlapping labels. It was stopped between cases to correct blank screenshot capture. Its results are preserved. The subsequent `desktop-painted-acceptance` cohort was also paused between cases after a separate replay-page input defect was isolated; fraction/reflection/water results remain diagnostic. `desktop-painted-adapt` failed and remains retained. The `desktop-isolated` diagnostics then exposed exact-edit source escaping failures. The completed `desktop-verbatim-acceptance` and `desktop-verbatim-adapt` runs include unescaped source presentation.


Replay input isolation: a minimal generic two-button test reproduced loss of pointer events after the first mutation replay when both tabs shared a Chrome context. The failure followed the first layout even when width order was reversed. Moving replay into a separate, equally network-blocked browser context preserved actual pointer delivery. The original generated fraction source now reports only its real 11px text defect; its controls pass unchanged. The real Chrome suite passes with both pixel-capture and consecutive bottom-button regressions (`desktop-isolated-preview-regression.log`). Focus, animation-frame waiting, explicit window size and iframe display changes alone did not fix the input issue and were not adopted as substitutes for isolation.


Exact-edit transport: a fraction candidate correctly exposed a common-denominator labeling defect, but two automatic correction calls copied literal escaped newlines from JSON-embedded source. Both edits correctly failed exact matching and exhausted the existing quota. Candidate input now separates immutable package metadata from one verbatim, explicitly untrusted source text part. No source is normalized or repaired; matching remains exact and atomic. The correction prompt recommends short unique anchors. A focused regression distinguishes actual newlines from literal JavaScript escapes. The verifier's trusted bridge description also explicitly states that canonical mutation values are strings and typed reads parse them; String(number) alone is not a replay defect. Focused Python verification: 44 passed in 1.74s.


## Successful desktop ADAPT lifecycle

Run `326457d4-0c38-4c31-85b7-8028469c5e2b` completed CREATE + two automatic exact-source corrections + independent acceptance + immutable settlement + Primary Tutor handoff. No manual source edits were used. Child Version `575dde62-58a2-45d3-adbe-115f7aa4ae1d` references qualified parent `56ced5b7-cd7b-4bda-9cdf-a7bbf9e206af`. New Build `5a016bfe-cbf4-4d4a-b8f5-8da62a10d05a` has source digest `48a61b328db09fcb62132cd5ab3e524d56092c1c98a8881c0ddfed6fb2073e1a`; its recorded parent Build is `f79f3384-8783-44d2-8b15-dcd4c29856bf` and repair kind is `ADAPT_GENERALIZED`.

Actual browser partition SET_VALUE `a4aa8d4f-5bc6-45ef-8705-b3bda2dd6945`, SELECT `b9c57abc-df9d-4d00-a23e-5e23f4ad47b3`, SUBMIT `d21c1702-8ee4-4ce7-a2d7-4f2858e92e67` and post-confirmation SET_VALUE `f4235a71-d243-4f01-9d5f-9dad26444353` all reached completed Tutor handoffs. Partition 30 survived full reload; changing to 45 updated both representations and cleared old feedback. Screenshots `output/playwright/desktop-adapt-initial-640.png`, `desktop-adapt-feedback-640.png` and `desktop-adapt-updated-960.png` were visually inspected. This qualifies the requested exact-pair capability addition, not arbitrary parameter combinations.

Measured ADAPT: 7 Luna calls, 97.780s, 64,835 input / 8,596 output tokens, $0.058206 estimated token cost. Independent review accounted for 47.195s, initial CREATE 31.914s, source corrections 13.621s, final plan 5.050s; total preview time was 8.952s. The complete observer took 135.093s including Tutor/setup/settlement. These costs include failed candidates within this bounded successful run.

The later capability-aware true REUSE run `6bdb31f5-d81d-4769-a2df-03e5debbe24d` completed with only instantiate: 2 calls, 7.537s, 18,974 input / 364 output / 9,353 cached tokens, $0.006370. It does not regenerate source. The earlier REUSE browser qualification and same-Build proof remain separately recorded above.

The six-case `desktop-verbatim-acceptance` cohort completed 2/6 protocols (water and balance). Fraction retained a technical state-ID veto despite a positive independent review; reflection retained target/accessibility/label defects; sentence failed before a review; classification retained semantic binding and submission/replay defects. The correction request now puts both technical and independent findings first in one required-repairs list. No veto, quota or exact-edit rule is relaxed. The four-case `desktop-required-repairs` follow-up completed 1/4 protocols (fraction); `desktop-shared-budget` completed 1/3 (sentence). `desktop-diagnostics` and `desktop-activation` each completed 0/2 (reflection/classification). These are successive development configurations, not a combined frozen acceptance rate. Full cohort results and failed follow-ups remain in the metrics denominator.


## Final general corrections and desktop browser checks

The same four authoring attempts can now spend an unused replacement slot on source correction: one CREATE plus three refinements, or two CREATE plus two refinements. Failed calls consume attempts. The shared 16-turn ceiling and final-plan-only repair remain unchanged. This follows evidence that immutable replacement capacity was idle while fixable source defects exhausted the old two-refinement counter; it is not a higher total limit.

Syntax rejection still uses `node --check` without source execution. Corrections now receive a bounded line, column and allowlisted syntax category instead of only a generic rejection code. Raw stderr, source excerpts and host paths are excluded. A regression verifies valid throw statements are parsed without executing and private source text is not returned.

Optional `handle.activate(callback)` centralizes click/Enter/Space activation for newly generated controls. Native controls keep native keyboard behavior; non-native controls receive default focusability and button role only if absent. Rebinding replaces the helper's previous listeners. The callback still owns canonical emission/rendering; existing packages are unchanged. Real Chrome checks verify pointer/Enter/Space each emit once for SVG and native buttons, replacement binding avoids duplication, and key repeat is suppressed. This does not itself make every generated interaction accessible.

Tutor instructions now explicitly prohibit inventing grounded source-reference IDs: use exact supplied IDs or an empty list. The existing unauthorized-source gate is unchanged. The issue was observed before Canvas admission, so it is distinct from CREATE failure. Runtime guidance also connects actual width AND height scale to screen font/target size and requires equal axis scales when geometric units carry meaning; no subject or fixture-specific renderer was introduced.

Additional actual production-renderer browser evidence:

| Case / run | Observed behavior | Qualification limit |
|---|---|---|
| Fraction `54776c3a-f135-4cb2-80e8-e7c859e887d0` | Partition 15→30 displays 10/30 and 12/30 on equal wholes; SET_VALUE `2a18c9c0-0c29-4576-9b25-5943abfdf490` completed; full reload preserves 30 at 640px. Actual 2/5 choice `12d7f331-fbaa-4c37-8ec3-83a13e35b941` completed after the stream cancellation fix. | Exact pair only; modest visual styling and unnamed native select prevent a blanket accessibility/polish claim. |
| Balance `e57fcdac-98f9-4968-831c-e1086c1a21df` | Two paired removals preserve equality; answer 5 and SUBMIT `c2ad3e17-91dd-484c-b7e7-e32672578c8d` completed; revealed box quantity and state survive reload. | Exact lesson qualification, not arbitrary algebra or parameter combinations. |
| Arabic sentence `d1dde342-1408-4ad2-a220-9fdf76ca5629` | Real drag MOVE `8fea0c88-5b8f-437c-b495-9c98959afd6e` and SUBMIT `915fcd58-d55b-48e2-83b5-54a931c46351` completed. RTL reordered words survive wide full reload; no mastery claim. Build `ffdeecad-3635-4243-aaf6-2c01353ecc7a`. | Roles remain attached to the supplied words across arbitrary reorderings; confirmation is transient and clears on reload. This is manipulable sentence material for Tutor discussion, not verified general grammar interpretation. |
| Water `0858c958-0844-44e0-af07-d5c33ec84eee` | Heating and phase changes, precipitation selection and full reload worked at both desktop widths. | Human inspection found an ambiguous return arrow toward the Sun. Protocol success is therefore not unconditional educational acceptance. |

Inspected screenshots: `desktop-fraction-new-{initial-960,restored-640}.png`, `desktop-balance-{initial-640,restored-960}.png`, `desktop-sentence-new-{moved-640,restored-960}.png`, and `desktop-water-{initial-960,restored-640}.png`, all under `output/playwright/`. The ADAPT browser and lineage proof above remains independently qualified.

Closure regression on the current code: 1420 passed, 12 skipped on isolated PostgreSQL 55438. TypeScript, full Next production build with the configured public Clerk key, actual Chrome activation/preview and operation-queue checks, repository truth and diff checks passed. This is not an authenticated Clerk/Daily session, deployment, real-Lina learning-benefit or production-traffic acceptance.


## ASGI cancellation recovery — live reproduced and fixed

Reloading during a saved choice's Tutor stream left an interaction RUNNING. A subsequent request blocked on the Runtime row; live PostgreSQL showed one waiting transaction and an idle admission transaction. The inference that delayed generator finalization could contend with a later admission is consistent with that lock evidence. The independently reproduced root defect is narrower and certain: Starlette's synchronous iterator adapter did not close the owned event generator when transport cancellation happened while sending a frame. The old test closed its event loop, masking delayed cleanup.

The new regression checks persisted status **before** event-loop shutdown. Before the fix: one test failed with RUNNING rather than CANCELLED. The Canvas-specific streaming response now closes its owned generator on both iterator and ASGI completion/cancellation, under a cancellation shield and off the event loop. It also cancels an admitted request disconnected before its first body frame. Existing GeneratorExit handling preserves already-persisted Tutor truth and closes only unfinished interaction/observation state; no new execution authority or retry is added.

All 12 Studio API PostgreSQL tests passed, including actual ASGI disconnect at the terminal frame, explicit iterator close and disconnect before the body. A real Chrome reload produced interaction `e5729e1b-2983-405c-98f1-f1791279d522` → CANCELLED; PostgreSQL showed no lock wait, and the following choice `12d7f331-fbaa-4c37-8ec3-83a13e35b941` → COMPLETED. The old task-owned blocked proof server was restarted to release its in-flight test transactions; saved history was preserved. No claim of zero provider charges after disconnect is made: a provider call already in progress may complete before synchronous stream cleanup runs.

## Final six-case desktop wave

`desktop-release-wave` contains six completed attempts with identical captured Canvas runtime/source fingerprints. The later ASGI disconnect fix is separately verified above; it does not regenerate these immutable sources. Protocol completion was **2/6**, with no manual generated-source repair and no discarded failed attempts.

| Case | Protocol | Luna calls / seconds | Input / output tokens | Estimated USD | Final acceptance finding |
|---|---|---:|---:|---:|---|
| Fraction | Failed | 9 / 117.960 | 90,213 / 12,775 | 0.069723 | Captions intersect guide lines after bounded correction. Earlier exact-pair browser qualification remains separate. |
| Reflection | Completed | 6 / 113.977 | 63,811 / 11,780 | 0.061494 | Human review rejects rectangular grid cells despite the independent review claiming a square grid. |
| Water | Failed | 6 / 108.304 | 71,596 / 11,185 | 0.056178 | Missing canonical SELECT bindings, reversed Arabic relation arrows and small distorted labels. |
| Sentence | Failed | 8 / 132.761 | 72,752 / 13,690 | 0.077446 | RTL drop indexing and relationship-label collisions remain. |
| Classification | Completed | 5 / 63.578 | 45,746 / 6,424 | 0.042145 | Actual desktop drag, grouping state and Tutor handoff inspected; exact six-material discussion scope only. |
| Balance | Failed | 9 / 164.055 | 90,356 / 17,736 | 0.094499 | Binding, replay and early-submission defects remain after exact-edit correction failed. |

The final reflection run is `4d901aae-fbe1-4d23-9387-5bd3d46a7731`; screenshot `output/playwright/desktop-release-reflection-960.png` and its resolved immutable source show 536 horizontal versus 260 vertical drawing pixels over equal numeric ranges. This is a concrete false-positive semantic review, not a mobile defect or a mere missing screenshot.

Final six-case totals: **434,474 input / 73,590 output tokens, $0.401485**, mean Luna **116.773s**, median **115.969s**, total browser preview **57.487s**. Baseline was 256,667 / 36,093 tokens, $0.211431, mean 58.452s. The stronger bounded checks have **not demonstrated a general CREATE latency/cost or repeatability improvement**. They expose more real failures and support automatic corrections, but the same-Luna semantic veto can still both miss defects and request unnecessary feedback.

All observed development evidence now includes **124 runs / 601 Canvas calls, $6.202186** estimated Canvas token cost, plus the separately recorded read-only check: **602 calls / $6.207501**. Tutor calls, unknown response usage, hosted fees and billing reconciliation remain outside the estimate. All portable per-run values are in `FULL-POWER-CANVAS-HARDENING_METRICS.json`.

The hardening changes and concrete lifecycle fixes are regression-verified. **Unrestricted production CREATE remains unaccepted**: stricter deterministic validation cannot establish arbitrary educational truth, and this configuration's independent Luna review demonstrably misses some requested semantics. Selective qualified REUSE/ADAPT proofs do not remove that limitation. No release, model switch, protected architecture change, silent weaker fallback or unlimited retry is authorized or performed.


Final classification browser run `5d87711f-22ff-4573-907f-27e4eaff98b3`: actual salt MOVE `211cc047-ff28-4a2d-b222-59ac95c96b7b`, oil MOVE `234ae570-f45b-4b88-bbb2-bdba32fd48eb` and partial SUBMIT `2b56c8e2-47e6-4569-81f1-b4e53337fdce` reached completed Tutor handoffs. Full reload at 640px preserved salt in Dissolves and cooking oil in Does not dissolve; confirmation cleared. Screenshots `desktop-release-classification-submit-960.png` and `desktop-release-classification-restored-640.png` were visually inspected. The oil distinction is explicit text rather than a simulated liquid layer. This qualifies grouping/discussion and replay for the requested material set, not a physical dissolution simulation or a general learning-benefit claim.
