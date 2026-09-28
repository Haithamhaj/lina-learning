"""Golden harness contracts; all fixtures and outputs are synthetic."""

from __future__ import annotations

from os.path import commonprefix

from services.model_gateway.gateway import ModelRoute
from services.model_gateway.openai_provider import _request_body
import pytest

from scripts import tutor_golden
from scripts.tutor_golden import (
    build_request, compare_results, grade, input_sections, load_cache_probe_cases,
    load_cases, paired_schedule,
)


def _case(case_id: str) -> dict[str, object]:
    return next(case for case in load_cases() if case["id"] == case_id)


def test_twenty_synthetic_cases_use_the_production_tutor_payload_and_wire_schema() -> None:
    cases = load_cases()
    assert len(cases) == 20
    for case in cases:
        payload = build_request(case)
        body = _request_body(ModelRoute("openai", "gpt-6-luna"), payload)
        assert payload["question"] == case["turn"]
        assert payload["response_schema"]["name"] == "tutor_turn_v12"
        assert body["store"] is False
        assert body["text"]["format"]["strict"] is True
        assert body["input"] == payload["input"]
        assert "Current Turn:\nStudent question:\n" in body["input"]
        assert "Student Core Context" in body["input"]
        assert "date_of_birth" not in body["input"]


def test_recent_exchange_count_reselects_actual_complete_exchanges() -> None:
    case = _case("g01_correct_independent")
    one = build_request(case, recent_exchange_count=1)
    two = build_request(case, recent_exchange_count=2)
    assert "حسبتها بجمع" in one["input"]  # immediate, protected from count changes
    assert "كم يساوي 7 × 4؟" in one["input"]
    assert "ما ناتج 7 × 2؟" not in one["input"]
    assert "ما ناتج 7 × 2؟" in two["input"]


def test_unfinished_learning_uses_the_runtime_typed_segment_state() -> None:
    payload = build_request(_case("g07_unfinished_arabic"))
    assert "Latest confirmed Segment State" in payload["input"]
    assert "تطبيق الفكرة على كلمة زهرة" in payload["input"]
    assert "structured-segment-state-v1" in payload["input"]


@pytest.mark.parametrize("case_id,context_anchor", [
    ("g02_wrong_no_reasoning", "35"),
    ("g04_did_not_help_change", "هذا الشرح لم يساعدني"),
    ("g05_clarification_not_failure", "ماذا أفعل بالآحاد"),
    ("g13_canvas_ready_continue", '"status": "READY"'),
])
def test_continuity_contract_reaches_the_production_payload_for_target_cases(
    case_id: str, context_anchor: str,
) -> None:
    payload = build_request(_case(case_id), recent_exchange_count=1)
    instructions = payload["instructions"]
    assert "When an active learning goal remains unfinished" in instructions
    assert "one concrete, reachable next action" in instructions
    assert "wrong answer without shown reasoning" in instructions
    assert "After confusion or a method that did not help" in instructions
    assert "asks for one step in an ongoing problem" in instructions
    assert "an existing READY Canvas" in instructions
    assert "inspect, compare or act on a specific part" in instructions
    assert "Do not force a question or action after a standalone factual answer" in instructions
    assert "If you select EXPLAIN_THEN_CHECK" in instructions
    assert context_anchor in payload["input"]
    assert payload["input"].index("Current Turn:") < payload["input"].index("Immediate Exchange:")


def test_current_turn_last_only_moves_the_runtime_built_turn_block() -> None:
    case = _case("g04_did_not_help_change")
    baseline = build_request(case)
    variant = build_request(case, prompt_ordering="current_turn_last")
    assert baseline["instructions"] == variant["instructions"]
    assert baseline["response_schema"] == variant["response_schema"]
    assert baseline["input"].count(case["turn"]) == 1
    assert variant["input"].count(case["turn"]) == 1
    assert baseline["input"].index("Current Turn:") < baseline["input"].index("Immediate Exchange:")
    assert variant["input"].rfind("Current Turn:") > variant["input"].index("Immediate Exchange:")
    assert variant["input"].endswith(f"Student question:\n{case['turn']}"
                                     f"\nCurrent Student raw source ID: [{baseline['candidate_source_message_id']}]")


def test_a1_request_envelopes_differ_only_in_input_order_for_all_cases() -> None:
    for case in load_cases():
        baseline = build_request(case, recent_exchange_count=1)
        variant = build_request(case, recent_exchange_count=1,
                                prompt_ordering="current_turn_last")
        assert {key: value for key, value in baseline.items() if key != "input"} == {
            key: value for key, value in variant.items() if key != "input"
        }
        first = _request_body(ModelRoute("openai", "gpt-6-luna"), baseline)
        second = _request_body(ModelRoute("openai", "gpt-6-luna"), variant)
        assert {key: value for key, value in first.items() if key != "input"} == {
            key: value for key, value in second.items() if key != "input"
        }


def test_a2_reorders_every_exact_runtime_section_without_changing_request_contract() -> None:
    for case in load_cases():
        baseline = build_request(case, recent_exchange_count=1)
        variant = build_request(case, recent_exchange_count=1,
                                prompt_ordering="stable_prefix_dynamic_suffix")
        assert {key: value for key, value in baseline.items() if key != "input"} == {
            key: value for key, value in variant.items() if key != "input"
        }
        assert dict(input_sections(baseline["input"])) == dict(input_sections(variant["input"]))
        keys = [key for key, _ in input_sections(variant["input"])]
        assert keys[:3] == ["decisions", "segment_rules", "parent_rules"]
        assert keys[-1] == "current"
        first = _request_body(ModelRoute("openai", "gpt-6-luna"), baseline)
        second = _request_body(ModelRoute("openai", "gpt-6-luna"), variant)
        assert {key: value for key, value in first.items() if key != "input"} == {
            key: value for key, value in second.items() if key != "input"
        }
        assert "prompt_cache_key" not in second
        assert "prompt_cache_options" not in second


def test_a2_cache_probe_changes_turn_and_session_context_but_extends_exact_prefix() -> None:
    cases = load_cache_probe_cases()
    assert len({case["session_key"] for case in cases}) == 1
    assert [len(case["history"]) for case in cases] == [0, 1, 2]
    assert len({case["turn"] for case in cases}) == 3
    baseline = [build_request(case) for case in cases]
    variant = [build_request(case, prompt_ordering="stable_prefix_dynamic_suffix")
               for case in cases]
    assert len({payload["candidate_source_message_id"] for payload in baseline}) == 3
    assert all(b["instructions"] == a["instructions"] and
               b["response_schema"] == a["response_schema"]
               for b, a in zip(baseline, variant, strict=True))
    for index in (1, 2):
        base_prefix = commonprefix([baseline[index - 1]["input"], baseline[index]["input"]])
        a2_prefix = commonprefix([variant[index - 1]["input"], variant[index]["input"]])
        assert len(a2_prefix) > len(base_prefix) + 4000


def test_rubric_catches_wrong_relation_missing_visual_and_invented_reasoning() -> None:
    case = _case("g02_wrong_no_reasoning")
    schema = build_request(case)["response_schema"]["schema"]
    output = dict.fromkeys(schema["required"])
    output.update({
        "text": "الإجابة 28. جرّبي التحقق منها؟",
        "suggested_actions": [],
        "prior_method_relation": "DID_NOT_HELP",
        "teaching_strategy": "EXPLAIN_THEN_CHECK",
        "candidate_metadata": {"candidates": [{
            "event_type": "misconception_signal", "source_message_ids": [],
        }]},
    })
    checks = grade(case, output)["checks"]
    assert checks["schema_shape_valid"]
    assert not checks["prior_method_relation"]
    assert not checks["no_invented_reasoning"]
    assert checks["strategy_fidelity"]


def test_visual_and_history_boundary_checks_are_case_specific() -> None:
    case = _case("g20_history_visual_overridden")
    schema = build_request(case)["response_schema"]["schema"]
    output = dict.fromkeys(schema["required"])
    output.update({
        "text": "سأرسم لك مخطط الصوت في الهواء.",
        "suggested_actions": [],
        "prior_method_relation": "CONTINUATION",
        "candidate_metadata": {"candidates": []},
    })
    checks = grade(case, output)["checks"]
    assert not checks["current_over_history"]
    assert checks["visual_choice"]


def test_unearned_canvas_visibility_claim_is_not_accepted() -> None:
    case = _case("g04_did_not_help_change")
    schema = build_request(case)["response_schema"]["schema"]
    output = dict.fromkeys(schema["required"])
    output.update({"text": "انظري إلى الرسم الآن.", "suggested_actions": [],
                   "candidate_metadata": {"candidates": []}})
    assert not grade(case, output)["checks"]["authority_boundary"]


def test_comparison_requires_three_matching_runs_and_reports_all_metrics() -> None:
    run = {
        "rubric": {"all_passed": True, "passed": 7, "total": 7},
        "latency_ms": 1000, "input_tokens": 5, "output_tokens": 20,
        "cached_input_tokens": 10, "cache_write_tokens": 0,
        "estimated_cost_usd": 0.001,
    }
    baseline = {"mode": "live", "cases": [{"case_id": "g01", "variant": {"name": "baseline"},
                                           "runs": [run, run, run]}]}
    variant = {"mode": "live", "cases": [{"case_id": "g01", "variant": {"name": "variant"},
                                          "runs": [run, run, run]}]}
    compared = compare_results(baseline, variant)
    assert set(compared["cases"][0]["baseline"]) == {
        "rubric_pass_rate", "mean_rubric_fraction", "mean_latency_ms",
        "mean_input_tokens", "mean_output_tokens", "mean_cached_input_tokens",
        "mean_cache_write_tokens", "mean_estimated_cost_usd",
    }
    assert all(value == 0 for value in compared["cases"][0]["delta_variant_minus_baseline"].values())
    variant["cases"][0]["runs"] = [run, run]
    with pytest.raises(ValueError, match="at least three"):
        compare_results(baseline, variant)


def test_paired_schedule_alternates_and_balances_starting_arm() -> None:
    schedule = paired_schedule(load_cases(), 3)
    assert len(schedule) == 120
    first = [step["prompt_ordering"] for step in schedule[:6]]
    second = [step["prompt_ordering"] for step in schedule[6:12]]
    assert first == ["production_current", "current_turn_last",
                     "current_turn_last", "production_current",
                     "production_current", "current_turn_last"]
    assert second == ["current_turn_last", "production_current",
                      "production_current", "current_turn_last",
                      "current_turn_last", "production_current"]
    assert sum(step["prompt_ordering"] == "production_current" for step in schedule) == 60
    assert sum(step["slot"] == 1 and step["prompt_ordering"] == "production_current"
               for step in schedule) == 30
    a2 = paired_schedule(load_cases(), 3, "stable_prefix_dynamic_suffix")
    assert len(a2) == 120
    assert sum(step["slot"] == 1 and step["prompt_ordering"] == "production_current"
               for step in a2) == 30
    assert sum(step["prompt_ordering"] == "stable_prefix_dynamic_suffix" for step in a2) == 60


def test_paired_runner_checkpoints_and_resume_never_repeats_paid_calls(tmp_path, monkeypatch) -> None:
    calls = []

    def fake_run(case, *, prompt_ordering, **kwargs):
        calls.append((case["id"], prompt_ordering))
        return {"runs": [{"estimated_cost_usd": 0.001, "rubric": {"all_passed": True}}]}

    monkeypatch.setattr(tutor_golden, "run_live", fake_run)
    cases = load_cases()[:2]
    path = tmp_path / "paired.json"
    first = tutor_golden.run_paired_live(
        cases, repeats=3, recent_exchange_count=1,
        env_file=None, output=path, resume=False,
    )
    assert first["complete"]
    assert len(first["events"]) == 12
    assert first["estimated_cost_usd"] == 0.012
    again = tutor_golden.run_paired_live(
        cases, repeats=3, recent_exchange_count=1,
        env_file=None, output=path, resume=True,
    )
    assert len(again["events"]) == 12
    assert len(calls) == 12
