# Teaching Continuity / Next Learner Action — local review (2026-09-28)

## Change and evidence boundary

The production Tutor instruction contract now says that an unfinished learning goal should leave one concrete, reachable learner action. It singles out wrong answers without shown reasoning, DID_NOT_HELP/confusion, one-step clarifications, and an existing relevant READY Canvas. It preserves natural closure for standalone factual answers, completed goals, and Safety/Parent boundaries. It does not change prompt section ordering, model, reasoning effort, memory count, JEV, Canvas lifecycle, response schema, or Golden fixtures. No new model call or automatic question suffix was added.

The frozen Golden harness still uses the production context selection, payload builder, capacity guardrail, and provider request adapter. The saved A2 **production_current** arm is the unchanged prior baseline (three runs per case). The new final focused result is also three runs per case with production ordering, GPT-6 Luna, default reasoning, and `recent_exchange_count=1`.

| Focused case | Saved baseline | Final local instruction |
| --- | ---: | ---: |
| g02 wrong, no shown reasoning | 1/3 | 3/3 |
| g04 DID_NOT_HELP, method change | 2/3 | 3/3 |
| g05 clarification, do not finish all steps | 1/3 | 3/3 |
| g13 existing READY Canvas continuation | 0/3 | 3/3 |
| **All applicable deterministic checks** | **4/12** | **12/12** |

Human review found reachable learner work in the final four cases. The g05 answers left a subtraction step for the learner; g04 changed method in every run; g02 did not invent the learner's reasoning. One of the three g13 replies used a valid guided check detached from the existing visual, despite passing the rubric. This remains a READY Canvas quality point for learner-facing acceptance. The focused first draft also improved the screen but exposed one over-solved clarification and a detached Canvas check, prompting the final instruction refinement.

## Frozen full-set regression

One run of each of the 20 cases passed every raw-output check in **18/20** cases. The prior three-repeat production arm passed **48/60**; these sample sizes differ and should not be read as a precise effect estimate. The two new raw failures were g03 and g06, each asking the learner to look at a newly requested drawing before it exists. The existing server-owned Canvas visibility guard repairs both before persistence/streaming while retaining their academic questions. Review found no forced question on the independent-success or short factual-answer controls, no duplicate Canvas request in pending/READY cases, and no obvious regression in strategy fidelity, visual choice, Personal Memory relevance, or current-turn-over-history. The ready-Canvas case used the visual in this full pass.

Reviewing the delivered text exposed a false match in the existing wording guard: it treated “in gas form” and “equal shape” as references to the new visual and removed useful teaching text. The guard now retains those ordinary academic phrases while still removing the premature drawing reference. This is a narrow wording repair, with no Canvas lifecycle architecture change. Focused guard and Tutor tests pass. The raw Golden rubric intentionally does not run this post-model server repair, so its 18/20 result remains recorded without alteration.

## Files, cost, and decision

- `teaching_continuity_focused_2026-09-28.json`: first 12-call draft, estimated **$0.009697465**.
- `teaching_continuity_focused_final_2026-09-28.json`: final 12-call focused run, estimated **$0.009729125**.
- `teaching_continuity_full_once_2026-09-28.json`: final 20-call full regression, estimated **$0.014628075**.
- **Total new provider cost:** approximately **$0.034054665** across 44 synthetic calls. A sandbox DNS failure completed no call. The estimate uses the harness rates and provider usage, not an invoice.

These are synthetic prompt-level and deterministic tests, not proof of authenticated Chat/Canvas delivery, longitudinal learning, or real learner acceptance. Repeated identical case prompts may reuse provider cache; no production cross-turn cache conclusion is drawn. The slice is ready for controlled acceptance review, not yet production accepted or deployed.
