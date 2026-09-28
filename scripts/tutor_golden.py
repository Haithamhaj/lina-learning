"""Synthetic Tutor golden set using Lina's production context-to-request path.

No production data or AIExecution rows are read or written. Live calls are opt-in.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
from statistics import mean
from time import perf_counter
from urllib.request import Request, urlopen
from uuid import UUID, uuid5, NAMESPACE_URL

from services.intelligence.selection import RelevantIntelligence
from services.model_gateway.gateway import ModelRoute
from services.model_gateway.openai_provider import OpenAIResponsesProvider, _request_body, _response_text
from services.platform.config import get_settings
from services.platform.core_profile import StudentCoreContext
from services.platform.safety import SafetyAction
from services.studio.tutor_context import StudioTutorWorkspaceContext
from services.tutor.capacity import apply_context_capacity_guardrail
from services.tutor.context import (
    TutorContext, TutorContextDebug, partition_exchange_continuity,
)
from services.tutor.exchanges import ConversationExchangeContext
from services.tutor.runtime import _payload_from_context
from services.tutor.safety import TutorSafetyRuntime
from services.tutor.segments import StructuredSegmentState
from services.tutor.teaching_methods import (
    PriorTeachingMethodContext, TEACHING_METHOD_REGISTRY_VERSION, TeachingMethod,
)


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals/tutor_golden/cases.json"
PROBE_PATH = ROOT / "evals/tutor_golden/a2_cache_probe.json"
PAIRED_VARIANTS = ("current_turn_last", "stable_prefix_dynamic_suffix")

# These are headings in the runtime-built input, not copies of its teaching text.
# Fail closed if the production builder changes instead of silently omitting a block.
_SECTION_HEADINGS = (
    ("core", "Student Core Context ("),
    ("memory", "Personal Memory —"),
    ("current", "Current Turn:"),
    ("immediate", "Immediate Exchange:"),
    ("recent", "Recent raw complete Exchanges:"),
    ("older", "Relevant older complete Exchanges from current Segment:"),
    ("retrieval", "Retrieved curriculum:"),
    ("intelligence", "Relevant compact learning context:"),
    ("conditional_concept", "Conditional prior Concept context ("),
    ("studio", "Studio Workspace Context ("),
    ("visual_catalog", "Visual Personalization Catalogue ("),
    ("visual_catalog", "Visual Personalization selection is delegated"),
    ("visual_catalog", "No Visual Personalization Catalogue is available"),
    ("visual_need", "Bounded Visual Need signal ("),
    ("safety", "Age-handling directive:"),
    ("candidate", "Hidden Candidate Event source link:"),
    ("decisions", "TeachingMode definitions:"),
    ("prior_method", "Previous Tutor TeachingMethod:"),
    ("suggested_action", "Selected suggested-action source:"),
    ("segment_rules", "Hidden Segment relation:"),
    ("segment_state", "Latest confirmed Segment State ("),
    ("segment_state", "No valid latest Segment State is available."),
    ("parent_settings", "Effective Parent Boundary settings ("),
    ("parent_rules", "Parent Boundary semantic decision:"),
)
_PRODUCTION_SECTIONS = (
    "core", "memory", "current", "immediate", "recent", "older", "retrieval",
    "intelligence", "conditional_concept", "studio", "visual_catalog", "visual_need",
    "safety", "candidate", "decisions", "prior_method", "suggested_action",
    "segment_rules", "segment_state", "parent_settings", "parent_rules",
)
_A2_SECTIONS = (
    "decisions", "segment_rules", "parent_rules",  # stable input prefix
    "core", "memory", "retrieval", "intelligence", "conditional_concept",
    "studio", "visual_catalog", "visual_need", "safety", "parent_settings",
    "prior_method", "segment_state", "older", "recent", "immediate",
    "suggested_action", "candidate", "current",  # dynamic suffix
)
_REQUIRED_SECTIONS = {
    "core", "current", "immediate", "recent", "older", "retrieval",
    "intelligence", "decisions", "segment_rules", "segment_state",
    "parent_settings", "parent_rules",
}
SAFETY = TutorSafetyRuntime(
    action=SafetyAction.ALLOW,
    policy_source="system_baseline",
    policy_version=1,
    reason_code="SAFE_EDUCATIONAL_TURN",
    continue_to_tutor=True,
)


def _id(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"lina-tutor-golden-v1/{value}")


def load_cases() -> list[dict[str, object]]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if len(cases) != 20 or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Golden set must contain 20 uniquely named cases.")
    return cases


def load_cache_probe_cases() -> list[dict[str, object]]:
    """Three changing turns in one synthetic session, outside the frozen set."""
    fixture = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    base = next(case for case in load_cases() if case["id"] == fixture["base_case_id"])
    cases = [{**base, **turn} for turn in fixture["turns"]]
    if len(cases) != 3 or len({case["id"] for case in cases}) != 3:
        raise ValueError("A2 cache probe must contain three distinct turns.")
    return cases


def _exchange(case_id: str, index: int, pair: list[str]) -> ConversationExchangeContext:
    if len(pair) != 2 or not all(isinstance(value, str) and value.strip() for value in pair):
        raise ValueError(f"{case_id}: history entries must be complete Student/Tutor pairs.")
    moment = datetime(2026, 1, 1, 12, index, tzinfo=UTC)
    return ConversationExchangeContext(
        session_id=_id(f"{case_id}/session"),
        segment_id=_id(f"{case_id}/segment"),
        student_message_id=_id(f"{case_id}/student/{index}"),
        tutor_message_id=_id(f"{case_id}/tutor/{index}"),
        student_content=pair[0],
        tutor_content=pair[1],
        student_created_at=moment,
        tutor_created_at=moment,
    )


def _studio(case: dict[str, object]) -> StudioTutorWorkspaceContext | None:
    state = case.get("canvas_state")
    if not isinstance(state, dict):
        return None
    case_id = str(case["id"])
    scene_id = _id(f"{case_id}/scene")
    return StudioTutorWorkspaceContext(
        runtime_id=_id(f"{case_id}/runtime"),
        snapshot_schema_version="studio-snapshot-v1",
        through_sequence=0,
        snapshot_sequence=0,
        current_scene_id=scene_id if state["status"] == "READY" else None,
        current_scene_version=1 if state["status"] == "READY" else None,
        active_subject_key=str(case["subject"]),
        active_activity_key=None,
        state_payload={"learning_focus": state.get("learning_focus", "")},
        unseen_events=(),
        observation_id=None,
        canvas_composition={
            "status": state["status"],
            "current_scene_id": str(scene_id) if state["status"] == "READY" else None,
            "learning_focus": state.get("learning_focus", ""),
        },
    )


def _current_source_id(case: dict[str, object]) -> UUID:
    # Probe-only turn key gives successive synthetic Student messages distinct
    # lineage without changing any frozen Golden Set fixture.
    return _id(f"{case.get('current_source_key', case['id'])}/current")


def input_sections(value: str) -> list[tuple[str, str]]:
    """Read exact runtime-built sections for evaluation-only permutations."""
    positions = []
    for key, heading in _SECTION_HEADINGS:
        for match in re.finditer(r"(?m)^" + re.escape(heading), value):
            positions.append((match.start(), key))
    positions.sort()
    keys = [key for _, key in positions]
    if (not positions or positions[0][0] != 0 or len(keys) != len(set(keys))
            or not _REQUIRED_SECTIONS.issubset(keys)):
        raise ValueError("Runtime Tutor input section inventory changed; A2 cannot reorder it safely.")
    return [
        (key, value[start:positions[index + 1][0] if index + 1 < len(positions) else len(value)].strip("\n"))
        for index, (start, key) in enumerate(positions)
    ]


def a2_input(value: str) -> str:
    """Place unchanged rules first and changing Tutor context last."""
    sections = input_sections(value)
    keys = [key for key, _ in sections]
    if keys != [key for key in _PRODUCTION_SECTIONS if key in keys]:
        raise ValueError("Runtime Tutor input order changed; A2 needs revalidation.")
    by_key = dict(sections)
    reordered = [(key, by_key[key]) for key in _A2_SECTIONS if key in by_key]
    if Counter(sections) != Counter(reordered):
        raise ValueError("A2 failed to preserve every runtime-built Tutor section.")
    return "\n\n".join(text for _, text in reordered)


def build_request(
    case: dict[str, object], *, recent_exchange_count: int = 1,
    prompt_ordering: str = "production_current",
) -> dict[str, object]:
    """Replay a synthetic pre-context snapshot through runtime selection and payload code."""
    case_id = str(case["id"])
    session_key = str(case.get("session_key", case_id))
    history = tuple(_exchange(session_key, index, pair)
                    for index, pair in enumerate(case.get("history", [])))
    immediate = history[-1] if history else None
    recent, _older = partition_exchange_continuity(
        history, immediate, recent_exchange_count=recent_exchange_count,
    )
    # Semantic recall is not fabricated: these fixtures contain no embedding
    # projections. Older exchanges remain out of the model input, as in runtime.
    notes = tuple(
        RelevantIntelligence("synthetic_card", _id(f"{case_id}/intelligence/{index}"),
                             text, None, index)
        for index, text in enumerate(case.get("intelligence", []))
    )
    context = TutorContext(
        question=str(case["turn"]),
        subject=str(case["subject"]),
        grade_level=5,
        focus=None,
        session_messages=(),
        retrieval=(),
        intelligence=notes,
        debug=TutorContextDebug(
            focus=None, session_message_ids=(), retrieval_source_refs=(),
            intelligence_source_ids=tuple(note.source_id for note in notes),
            intelligence_source_kinds=tuple(note.source_kind for note in notes),
        ),
        student_core_context=StudentCoreContext("نور", 10, 5),
        personal_memory=case.get("personal_memory"),
        immediate_exchange=immediate,
        recent_exchanges=recent,
        studio_workspace=_studio(case),
    )
    prior_method = (
        PriorTeachingMethodContext(
            tutor_message_id=immediate.tutor_message_id,
            teaching_method_id=TeachingMethod(str(case["prior_method"])),
            registry_version=TEACHING_METHOD_REGISTRY_VERSION,
        )
        if immediate is not None and case.get("prior_method") else None
    )
    visual_need = case.get("visual_need")
    visual_signal = (
        {"visual_need": visual_need[0], "visual_category": visual_need[1],
         "source": "JEV", "authority": "advisory_current_turn"}
        if isinstance(visual_need, list) else None
    )
    source_id = _current_source_id(case)
    raw_segment_state = case.get("segment_state")
    segment_state = (
        StructuredSegmentState(
            schema_version="structured-segment-state-v1",
            active_goal=raw_segment_state.get("active_goal"),
            unresolved_point=raw_segment_state.get("unresolved_point"),
            active_references=raw_segment_state.get("active_references", []),
            established_facts=raw_segment_state.get("established_facts", []),
            source_message_ids=[immediate.tutor_message_id],
        )
        if isinstance(raw_segment_state, dict) and immediate is not None else None
    )
    guarded = apply_context_capacity_guardrail(
        context,
        capacity_limit=get_settings().tutor_context_capacity,
        payload_builder=lambda selected: _payload_from_context(
            selected,
            safety=SAFETY,
            candidate_source_message_id=source_id,
            prior_method=prior_method,
            latest_segment_state=segment_state,
            visual_need_signal=visual_signal,
            # App currently runs visual-personalization shadow, so v12 is active.
            visual_personalization_delegated=False,
        ),
    )
    payload = guarded.payload
    if prompt_ordering == "production_current":
        return payload
    if prompt_ordering == "stable_prefix_dynamic_suffix":
        return {**payload, "input": a2_input(str(payload["input"]))}
    if prompt_ordering != "current_turn_last":
        raise ValueError(f"Unsupported prompt ordering: {prompt_ordering}")
    # Experiment-only permutation of the *actual* runtime-built input. No
    # instruction, context section, schema, or current-turn text is rewritten.
    current_heading = "Current Turn:\nStudent question:\n"
    next_heading = "\n\nImmediate Exchange:\n"
    value = str(payload["input"])
    start = value.index(current_heading)
    end = value.index(next_heading, start)
    turn_block = value[start:end]
    moved = value[:start] + value[end + 2:] + "\n\n" + turn_block
    return {**payload, "input": moved}


def _visible_text(output: dict[str, object]) -> str:
    return str(output.get("text") or "")


def grade(case: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    """Conservative deterministic checks; semantic teaching quality stays reviewable."""
    expected = case["expect"]
    checks: dict[str, bool] = {}
    schema = build_request(case)["response_schema"]["schema"]
    checks["schema_shape_valid"] = (
        isinstance(output, dict)
        and set(output) == set(schema["required"])
        and isinstance(output.get("text"), str)
        and isinstance(output.get("suggested_actions"), list)
        and output.get("prior_method_relation") in schema["properties"]["prior_method_relation"]["enum"]
        and output.get("teaching_strategy") in schema["properties"]["teaching_strategy"]["enum"]
    )
    text = _visible_text(output)
    checks["teaching_response_screen"] = (
        0 < len(text.strip()) <= 1600
        and not re.search(r"candidate_metadata|source_message_id|AIExecution|\bJEV\b", text, re.IGNORECASE)
    )
    canvas = output.get("canvas_brief")
    relation = expected.get("relation")
    if relation is not None:
        checks["prior_method_relation"] = output.get("prior_method_relation") == relation
    if expected.get("method_change"):
        checks["method_change"] = output.get("teaching_method_id") not in {None, case.get("prior_method")}
    if expected.get("strategy"):
        checks["strategy_choice"] = output.get("teaching_strategy") in expected["strategy"]
    visual = expected.get("visual")
    if visual == "request":
        checks["visual_choice"] = isinstance(canvas, dict)
    elif visual in {"avoid", "no_duplicate"}:
        checks["visual_choice"] = canvas is None
    if expected.get("next_action"):
        actions = output.get("suggested_actions")
        checks["useful_next_action"] = bool(output.get("guided_check")) or (
            isinstance(actions, list) and len(actions) > 0
        ) or bool(re.search(r"[؟?]", text))
    if output.get("teaching_strategy") == "EXPLAIN_THEN_CHECK":
        checks["strategy_fidelity"] = bool(output.get("guided_check")) or bool(re.search(r"[؟?]", text))
    if expected.get("text_any"):
        checks["current_turn_understood"] = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in expected["text_any"]
        )
    if expected.get("text_none"):
        checks["current_over_history"] = not any(
            re.search(pattern, text, re.IGNORECASE) for pattern in expected["text_none"]
        )
    metadata = output.get("candidate_metadata")
    candidates = metadata.get("candidates", []) if isinstance(metadata, dict) else []
    if expected.get("no_misconception"):
        checks["no_invented_reasoning"] = not any(
            isinstance(item, dict) and item.get("event_type") == "misconception_signal"
            for item in candidates
        )
    source_id = str(_current_source_id(case))
    source_lineage_valid = all(
        isinstance(item, dict) and set(item.get("source_message_ids", [])).issubset({source_id})
        for item in candidates
    )
    unearned_visibility_claim = (
        case.get("canvas_state", {}).get("status") != "READY"
        and bool(re.search(
            r"(?:canvas|لوحة|رسم).{0,25}(?:visible|ظاهرة|أمامك|جاهز)"
            r"|(?:انظري|شاهدي|look at|see).{0,30}(?:الرسم|اللوحة|canvas)",
            text, re.IGNORECASE,
        ))
    )
    checks["authority_boundary"] = source_lineage_valid and not unearned_visibility_claim
    return {
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_passed": all(checks.values()),
        "review_note": "Deterministic signals only; a human reviews pedagogical nuance, visual quality, and factual accuracy.",
    }


def _key_from_env_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("MODEL_API_KEY="):
            return line.partition("=")[2].strip().strip('"').strip("'") or None
    return None


def run_live(
    case: dict[str, object], *, repeats: int, recent_exchange_count: int,
    reasoning_effort: str | None, prompt_ordering: str, env_file: Path | None,
) -> dict[str, object]:
    key = os.getenv("MODEL_API_KEY") or (_key_from_env_file(env_file) if env_file else None)
    if not key:
        raise RuntimeError("MODEL_API_KEY is unavailable; no live evaluation was run.")
    payload = build_request(case, recent_exchange_count=recent_exchange_count,
                            prompt_ordering=prompt_ordering)
    route = ModelRoute("openai", "gpt-6-luna")
    raw_responses: list[dict[str, object]] = []

    class CaptureResponse:
        def __init__(self, response):
            self.response = response

        def __enter__(self):
            self.response.__enter__()
            return self

        def __exit__(self, *args):
            return self.response.__exit__(*args)

        def read(self):
            content = self.response.read()
            raw_responses.append(json.loads(content))
            return content

    def sender(request: Request, timeout: float):
        if reasoning_effort is not None:
            body = json.loads(request.data)
            body["reasoning"] = {"effort": reasoning_effort}
            request = Request(request.full_url, data=json.dumps(body).encode(),
                              headers=dict(request.headers), method="POST")
        return CaptureResponse(urlopen(request, timeout=timeout))

    provider = OpenAIResponsesProvider(api_key=key, request_sender=sender)
    runs = []
    for index in range(repeats):
        started = perf_counter()
        result = provider.execute(route, payload)
        latency_ms = round((perf_counter() - started) * 1000)
        structured_output = json.loads(_response_text(raw_responses[-1]))
        rubric = grade(case, structured_output)
        runs.append({
            "run": index + 1, "rubric": rubric,
            "latency_ms": latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cached_input_tokens": result.cached_input_tokens,
            "cache_write_tokens": result.cache_write_tokens,
            "estimated_cost_usd": result.estimated_cost_usd,
            "output": structured_output,
        })
    return {
        "case_id": case["id"], "variant": {
            "recent_exchange_count": recent_exchange_count,
            "reasoning_effort": reasoning_effort,
            "prompt_ordering": prompt_ordering,
            "model": route.model,
        },
        "runs": runs,
        "summary": {
            "rubric_pass_rate": mean(int(run["rubric"]["all_passed"]) for run in runs),
            "mean_latency_ms": round(mean(run["latency_ms"] for run in runs)),
            "estimated_cost_usd": round(sum(run["estimated_cost_usd"] or 0 for run in runs), 10),
        },
    }


def compare_results(baseline: dict[str, object], variant: dict[str, object]) -> dict[str, object]:
    """Compare matching three-or-more-repeat live runs without reading response text."""
    if baseline.get("mode") != "live" or variant.get("mode") != "live":
        raise ValueError("Comparison requires two live result files.")
    base_cases = {case["case_id"]: case for case in baseline["cases"]}
    variant_cases = {case["case_id"]: case for case in variant["cases"]}
    if not base_cases or set(base_cases) != set(variant_cases):
        raise ValueError("Both results must contain the same case IDs.")

    def metrics(case: dict[str, object]) -> dict[str, float]:
        runs = case["runs"]
        if len(runs) < 3:
            raise ValueError("Each compared case needs at least three runs per variant.")
        return {
            "rubric_pass_rate": mean(int(run["rubric"]["all_passed"]) for run in runs),
            "mean_rubric_fraction": mean(run["rubric"]["passed"] / run["rubric"]["total"] for run in runs),
            "mean_latency_ms": mean(run["latency_ms"] for run in runs),
            "mean_input_tokens": mean(run["input_tokens"] or 0 for run in runs),
            "mean_output_tokens": mean(run["output_tokens"] or 0 for run in runs),
            "mean_cached_input_tokens": mean(run["cached_input_tokens"] or 0 for run in runs),
            "mean_cache_write_tokens": mean(run["cache_write_tokens"] or 0 for run in runs),
            "mean_estimated_cost_usd": mean(run["estimated_cost_usd"] or 0 for run in runs),
        }

    comparisons = []
    for case_id in sorted(base_cases):
        first = metrics(base_cases[case_id])
        second = metrics(variant_cases[case_id])
        comparisons.append({
            "case_id": case_id,
            "baseline": first,
            "variant": second,
            "delta_variant_minus_baseline": {
                key: round(second[key] - first[key], 10) for key in first
            },
        })
    return {"mode": "comparison", "baseline_variant": baseline["cases"][0]["variant"],
            "compared_variant": variant["cases"][0]["variant"], "cases": comparisons}


def paired_schedule(
    cases: list[dict[str, object]], repeats: int,
    variant_ordering: str = "current_turn_last",
) -> list[dict[str, object]]:
    """Alternate within each pair and balance the starting arm across cases."""
    if variant_ordering not in PAIRED_VARIANTS:
        raise ValueError(f"Unsupported paired variant: {variant_ordering}")
    schedule = []
    for case_index, case in enumerate(cases):
        for repetition in range(1, repeats + 1):
            baseline_first = (case_index + repetition) % 2 == 1
            order = (
                ("production_current", variant_ordering) if baseline_first
                else (variant_ordering, "production_current")
            )
            for slot, prompt_ordering in enumerate(order, 1):
                schedule.append({"case_id": case["id"], "repetition": repetition,
                                 "slot": slot, "prompt_ordering": prompt_ordering})
    return schedule


def run_paired_live(
    cases: list[dict[str, object]], *, repeats: int, recent_exchange_count: int,
    env_file: Path | None, output: Path, resume: bool,
    variant_ordering: str = "current_turn_last",
) -> dict[str, object]:
    """Checkpoint each paid call so an interrupted paired run can resume exactly."""
    schedule = paired_schedule(cases, repeats, variant_ordering)
    plan = {
        "cases": cases, "repeats": repeats,
        "recent_exchange_count": recent_exchange_count,
        "model": "gpt-6-luna", "reasoning_effort": None,
    }
    if variant_ordering != "current_turn_last":
        plan["variant_ordering"] = variant_ordering
    plan_identity = hashlib.sha256(json.dumps(
        plan, ensure_ascii=False, sort_keys=True,
    ).encode()).hexdigest()
    if output.exists():
        if not resume:
            raise FileExistsError(f"Paired result already exists: {output}; use --resume to continue it.")
        record = json.loads(output.read_text(encoding="utf-8"))
        if record.get("plan_sha256") != plan_identity:
            raise ValueError("Saved paired result does not match the current fixtures and settings.")
    else:
        record = {
            "mode": "paired_live", "plan_sha256": plan_identity,
            "design": {
                "model": "gpt-6-luna", "reasoning_effort_override": None,
                "recent_exchange_count": recent_exchange_count, "repeats_per_arm": repeats,
                "variant_ordering": variant_ordering,
                "ordering": "alternated within each repetition; starting arm balanced across cases",
                "cache_limit": "Repeated identical synthetic prompts may reuse provider cache. These measurements do not estimate production cross-turn cache improvement.",
            },
            "case_ids": [case["id"] for case in cases], "events": [],
            "complete": False,
        }
    by_id = {case["id"]: case for case in cases}
    events = record["events"]
    if len(events) > len(schedule):
        raise ValueError("Saved paired result has more calls than the planned schedule.")
    for prior, planned in zip(events, schedule, strict=False):
        if any(prior.get(key) != planned[key] for key in planned):
            raise ValueError("Saved paired result does not follow the planned call order.")
    for planned in schedule[len(events):]:
        case = by_id[planned["case_id"]]
        single = run_live(
            case, repeats=1, recent_exchange_count=recent_exchange_count,
            reasoning_effort=None, prompt_ordering=planned["prompt_ordering"],
            env_file=env_file,
        )
        events.append({**planned, "run": single["runs"][0]})
        record["estimated_cost_usd"] = round(sum(
            event["run"]["estimated_cost_usd"] or 0 for event in events
        ), 10)
        record["complete"] = len(events) == len(schedule)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
        if planned["slot"] == 2 and planned["repetition"] == repeats:
            print(json.dumps({"completed_case": planned["case_id"],
                              "completed_calls": len(events), "planned_calls": len(schedule),
                              "estimated_cost_usd": record["estimated_cost_usd"]}), flush=True)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", help="Case ID; may be repeated.")
    parser.add_argument("--all", action="store_true", help="Explicitly select every case for a live run.")
    parser.add_argument("--recent-exchange-count", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--prompt-ordering", choices=("production_current", *PAIRED_VARIANTS),
                        default="production_current")
    parser.add_argument("--live", action="store_true", help="Opt in to paid synthetic OpenAI calls.")
    parser.add_argument("--paired-live", action="store_true",
                        help="Run baseline and an evaluation variant in a checkpointed paired order.")
    parser.add_argument("--paired-variant", choices=PAIRED_VARIANTS,
                        default="current_turn_last")
    parser.add_argument("--cache-probe", action="store_true",
                        help="Run three changing synthetic turns in paired baseline/A2 order.")
    parser.add_argument("--resume", action="store_true", help="Resume the exact saved paired run.")
    parser.add_argument("--env-file", type=Path, help="Optional local env file; key is never printed.")
    parser.add_argument("--output", type=Path, help="Optional JSON result file; may contain synthetic model output.")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE", "VARIANT"),
                        help="Compare matching live JSON result files; at least three runs per case.")
    args = parser.parse_args()
    if args.compare:
        result = compare_results(*(
            json.loads(path.read_text(encoding="utf-8")) for path in args.compare
        ))
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(json.dumps({"mode": "comparison", "case_count": len(result["cases"]),
                              "output": str(args.output)}, ensure_ascii=False))
        else:
            print(rendered)
        return
    if args.cache_probe:
        if (args.live or args.paired_live or args.case or args.all or args.reasoning_effort
                or args.prompt_ordering != "production_current" or args.output is None):
            parser.error("A2 cache probe needs only --cache-probe and --output")
        result = run_paired_live(
            load_cache_probe_cases(), repeats=1, recent_exchange_count=1,
            env_file=args.env_file, output=args.output, resume=args.resume,
            variant_ordering="stable_prefix_dynamic_suffix",
        )
        print(json.dumps({"mode": "synthetic_cross_turn_cache_probe",
                          "complete": result["complete"], "completed_calls": len(result["events"]),
                          "estimated_cost_usd": result["estimated_cost_usd"],
                          "output": str(args.output)}, ensure_ascii=False))
        return
    if args.repeats < 1 or args.recent_exchange_count < 1:
        parser.error("repeats and recent-exchange-count must be positive")
    if (args.live or args.paired_live) and not (args.case or args.all):
        parser.error("Live mode requires at least one --case or explicit --all")
    if args.case and args.all:
        parser.error("Use --case or --all, not both")
    cases = [case for case in load_cases() if not args.case or case["id"] in args.case]
    if args.case and len(cases) != len(set(args.case)):
        parser.error("One or more case IDs are unknown")
    if args.paired_live:
        if args.live or args.reasoning_effort is not None or args.prompt_ordering != "production_current":
            parser.error("Paired evaluation uses the current reasoning default and baseline ordering")
        if args.repeats < 3 or args.output is None:
            parser.error("Paired Golden Set needs at least three repeats and an --output checkpoint path")
        result = run_paired_live(cases, repeats=args.repeats,
                                 recent_exchange_count=args.recent_exchange_count,
                                 env_file=args.env_file, output=args.output, resume=args.resume,
                                 variant_ordering=args.paired_variant)
        print(json.dumps({"mode": "paired_live", "complete": result["complete"],
                          "completed_calls": len(result["events"]),
                          "estimated_cost_usd": result["estimated_cost_usd"],
                          "output": str(args.output)}, ensure_ascii=False))
        return
    if not args.live:
        summary = []
        for case in cases:
            payload = build_request(case, recent_exchange_count=args.recent_exchange_count,
                                    prompt_ordering=args.prompt_ordering)
            body = _request_body(ModelRoute("openai", "gpt-6-luna"), payload)
            summary.append({"case_id": case["id"], "schema": body["text"]["format"]["name"],
                            "request_sha256": hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                            "request_characters": len(json.dumps(body, ensure_ascii=False))})
        result = {"mode": "dry-run", "cases": summary, "paid_cost_usd": 0}
    else:
        result = {"mode": "live", "cases": [
            run_live(case, repeats=args.repeats,
                     recent_exchange_count=args.recent_exchange_count,
                     reasoning_effort=args.reasoning_effort,
                     prompt_ordering=args.prompt_ordering, env_file=args.env_file)
            for case in cases
        ]}
        result["paid_cost_usd"] = round(sum(case["summary"]["estimated_cost_usd"] for case in result["cases"]), 10)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(json.dumps({"mode": result["mode"], "case_count": len(cases),
                          "paid_cost_usd": result["paid_cost_usd"], "output": str(args.output)},
                         ensure_ascii=False))
    else:
        print(rendered)


if __name__ == "__main__":
    main()
