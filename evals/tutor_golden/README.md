# Tutor Golden Evaluation v1

## Purpose and privacy

This is a small **synthetic** baseline for prompt experiments, especially Current Turn Last. The 20 cases reproduce the *educational situations* seen in E16–E20 and E30 (including successes and failures), not the learner's private wording, identifiers, or transcript. They contain no production database export, uploaded source, raw child conversation, or credential. Do not replace them with verbatim learner data.

## Design

Each case stores only pre-payload ingredients: current turn, completed synthetic exchanges, optional compact Learning Intelligence note, optional Personal Memory card, optional confirmed Segment State, optional Canvas lifecycle state, the prior persisted method identity, and the active Visual Need advisory signal. Synthetic UUIDs are generated deterministically at replay time.

The harness uses the same `partition_exchange_continuity` selection as `TutorContextBuilder`, constructs a typed `TutorContext`, and calls production `_payload_from_context` → `build_tutor_model_payload` through `apply_context_capacity_guardrail`. The OpenAI adapter then builds the actual strict Responses request. No simplified prompt text or duplicate schema is kept in the fixtures. The active App is in visual-personalization **shadow**, so replay uses the production `tutor_turn_v12` shape. The Visual Need signal is fixture-provided; this isolates the Primary Tutor experiment from an extra JEV call.

This is a **bounded pre-context snapshot**, not a replay of database retrieval, safety admission, JEV classification, or browser/Canvas delivery. Those boundaries have their own tests and acceptance. The fixtures assume an already allowed school-learning turn and contain no safety-sensitive request. A live model answer is therefore evidence about the Primary Tutor call only; it cannot prove complete learner experience or educational benefit.

`recent_exchange_count` reselects complete exchanges from stored synthetic history. Older exchanges without semantic embeddings remain omitted, matching the no-semantic-recall fixture state. `--prompt-ordering current_turn_last` moves the exact runtime-built Current Turn block to the end of the input for a later experiment; the production source and configuration are unchanged. `--reasoning-effort` is an evaluation-only wire override after the production provider builds its request. No override is applied by default.

A2's `stable_prefix_dynamic_suffix` mode parses the **runtime-built** input by its existing headings and fails if that inventory changes. It moves the existing TeachingMode/Strategy/Method/prior-method definitions, Segment relation rules, and Parent Boundary semantic rules to the start of `input`. It then places dynamic Core Profile, Personal Memory, curriculum, Learning Intelligence, Studio/Canvas and Visual Need context, effective policy settings, prior method/Segment State, older/recent/immediate exchanges, source lineage, and Current Turn after those rules. The top-level Tutor `instructions`, all section text, authorities, response schema, model, and provider settings are unchanged. The variant uses no cache key, explicit breakpoint, or production cache setting.

This order follows [OpenAI's current prompt-caching guidance](https://developers.openai.com/api/docs/guides/prompt-caching) about exact shared prefixes. The API's implicit cache breakpoints may still prevent a longer shared substring *inside one changing input message* from producing a cache hit. A2 therefore measures both the exact text prefix and provider-reported cached tokens; it does not assume one implies the other.

## Coverage

| Cases | Situation |
| --- | --- |
| g01–g02 | Independent correct answer; wrong answer without stated reasoning |
| g03–g05 | Explicit confusion, DID_NOT_HELP method change, ordinary clarification |
| g06–g08 | EXPLAIN_THEN_CHECK and unfinished Math/Arabic/Science teaching |
| g09–g12 | Science process/structure visual, visual negative control, explicit visual request |
| g13–g14 | Existing ready and pending Canvas states |
| g15–g17 | Relevant, irrelevant, and contradicted Personal Memory |
| g18–g20 | Mixed LI evidence and current-turn preference/independence over history |

## Deterministic rubric

The grader records pass/fail per applicable check, then a total. It compares permitted structured values and visible text features, never an exact full response:

- strict output shape at the top level, a bounded learner-facing response without internal metadata, relation, method change, and expected strategy choice;
- visual request or no duplicate/no decorative request;
- an actual check for a declared `EXPLAIN_THEN_CHECK`, plus a learner next action where the case needs one;
- simple case-specific content anchors and forbidden stale-history language;
- no misconception signal invented from an answer without reasoning;
- Candidate Event source IDs confined to the synthetic current Student message, and no unearned Canvas visibility claim.

The content anchors are deliberately modest. A passing score is a **screen**, not a semantic proof: a reviewer still checks factual accuracy, child-appropriate explanation, whether the proposed check genuinely tests the taught idea, Canvas brief quality, and whether memory is used naturally. A failing text anchor may be a false negative; inspect the synthetic output before concluding a regression. Record both per-run results and disagreement patterns across repeats.

## Commands

Use the repository Python environment with the API dependencies installed:

```bash
python -m scripts.tutor_golden --output /private/tmp/lina-tutor-golden-dry-run.json
python -m scripts.tutor_golden --case g04_did_not_help_change --recent-exchange-count 2 --prompt-ordering current_turn_last
python -m scripts.tutor_golden --live --case g04_did_not_help_change --repeats 3 --output /private/tmp/lina-tutor-golden-live.json
python -u -m scripts.tutor_golden --paired-live --all --repeats 3 --recent-exchange-count 1 --output /private/tmp/lina-tutor-golden-a1.json
python -u -m scripts.tutor_golden --paired-live --paired-variant stable_prefix_dynamic_suffix --all --repeats 3 --recent-exchange-count 1 --output /private/tmp/lina-tutor-golden-a2.json
python -u -m scripts.tutor_golden --cache-probe --output /private/tmp/lina-tutor-golden-a2-cache-probe.json
python -m scripts.tutor_golden --compare /private/tmp/baseline.json /private/tmp/current-turn-last.json --output /private/tmp/tutor-comparison.json
```

Live mode requires `MODEL_API_KEY` in the environment or `--env-file` pointing to a local, ignored file. It sends only synthetic data, uses `gpt-6-luna`, does not use the application database, and does not persist AIExecution rows. The default is dry run; live calls require `--live`. A three-repeat run is the minimum comparison unit for an experimental variant. Results include each run's rubric, latency, normal input/output tokens, cached input and cache-write tokens, and the versioned local cost estimate. The JSON result file contains synthetic model output; keep it out of Git unless reviewed.

Live mode also requires one or more `--case` values or explicit `--all`, so a 60-call run cannot start from `--live` alone.

The comparison command requires matching case IDs and at least three runs per case in both files. It reports rubric pass rate, mean rubric fraction, latency, normal input/output tokens, cached and cache-write tokens, and mean estimated cost, with variant-minus-baseline deltas. Review cache conditions before interpreting cost or latency differences.

For A1, `--paired-live` sends each case as adjacent baseline/variant pairs. Its three repetitions alternate A→B, B→A, A→B for one case and reverse that sequence for the next, balancing which arm goes first across the full set. It checkpoints after every successful call; `--resume` continues the same fixture/settings plan without repeating completed calls. **Cached tokens from repeated identical synthetic prompts are a feature of this evaluation schedule, not evidence of production cross-turn cache improvement.** A realistic multi-turn cache evaluation is separate.

For A2, `--paired-variant stable_prefix_dynamic_suffix` uses the same balanced schedule and checkpointing. `--cache-probe` runs three changing turns of one separate synthetic plant-learning session (`a2_cache_probe.json`) once per arm, with stable Tutor instructions and changed current-turn/Exchange content. It is a small cache observation, not a quality result or a replay of Lina's history. Keep repeated-case and changing-turn cache totals separate.

Before comparing variants, freeze this case file, record the Git commit and deployment configuration, run each variant at least three times per case, and review per-case failures as well as aggregate scores. Do not use this small set to infer longitudinal learning benefit or override the protected Safety, Evidence, or Canvas authority boundaries.

## Initial smoke result

`baseline_smoke_2026-09-28.json` records the earlier one-case, three-repeat harness proof for `g04_did_not_help_change`. All three generated a different method and a Canvas brief; two passed every deterministic check. One reply implied the drawing was already available before delivery was confirmed. Its estimated cost was $0.00227835; an earlier three-call provider-capture probe cost $0.003285825. These calls preceded A1 and are excluded from its cost total.

The completed 20-case paired A1 comparison is in `results/A1_REVIEW_2026-09-28.md`, with full call records and a derived summary beside it. A1 cost an estimated $0.07135452 for 120 calls. Its recommendation is to keep the production order for now; no Tutor production change was made.

The completed A2 comparison and separate changing-turn cache probe are in `results/A2_REVIEW_2026-09-28.md`. The exact A2 text prefix grew, but cached tokens did not increase on the changing turns under unchanged implicit caching. A2 passed fewer next-action checks, so its recommendation is also to keep the current production structure. Golden plus probe cost an estimated $0.074519995; neither run changed production.
