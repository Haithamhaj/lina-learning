from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.model_gateway.gateway import ModelResult
from services.tutor.visual_need_decision import decide_visual_need


class _Gateway:
    def __init__(self, output: dict[str, object] | None = None, error: Exception | None = None):
        self.output = output
        self.error = error
        self.calls: list[tuple[object, dict[str, object], object]] = []

    def execute(self, task, payload, *, lineage):
        self.calls.append((task, payload, lineage))
        if self.error is not None:
            raise self.error
        return ModelResult(output=self.output or {}, execution_id=uuid4())


def _decide(gateway=None, **overrides):
    values = {
        "student_text": "How does sunlight reach Earth?",
        "subject": "SCIENCE",
        "prior_teaching_method": "DECOMPOSITION",
        "current_canvas_status": None,
        "capability_available": True,
        "source_meaning_clear": True,
        "min_probability": 0.72,
        "policy_version": "jev-visual-need-v1",
        "student_id": uuid4(),
        "learning_session_id": uuid4(),
        "source_message_id": uuid4(),
    }
    values.update(overrides)
    return decide_visual_need(gateway, **values)


def test_explicit_visual_request_bypasses_model_and_is_strong() -> None:
    gateway = _Gateway(error=AssertionError("must not call provider"))
    decision = _decide(gateway, student_text="Please draw a diagram for me.")

    assert decision.status == "BYPASS"
    assert decision.visual_need == "STRONGLY_RECOMMENDED"
    assert decision.source == "EXPLICIT_VISUAL_REQUEST"
    assert gateway.calls == []


def test_explicit_no_visual_preference_bypasses_model_to_none() -> None:
    gateway = _Gateway(error=AssertionError("must not call provider"))
    decision = _decide(gateway, student_text="Just explain it in words, no picture.")

    assert decision.visual_need == "NONE"
    assert decision.source == "STUDENT_NO_VISUAL"
    assert gateway.calls == []


@pytest.mark.parametrize(
    "overrides,source",
    [
        ({"capability_available": False}, "NOT_ELIGIBLE"),
        ({"source_meaning_clear": False}, "NOT_ELIGIBLE"),
        ({"current_canvas_status": "PENDING"}, "EQUIVALENT_VISUAL_IN_FLIGHT"),
        ({"current_canvas_status": "RUNNING"}, "EQUIVALENT_VISUAL_IN_FLIGHT"),
    ],
)
def test_known_non_eligible_states_bypass_provider(overrides, source) -> None:
    gateway = _Gateway(error=AssertionError("must not call provider"))
    decision = _decide(gateway, **overrides)

    assert decision.visual_need == "NONE"
    assert decision.source == source
    assert gateway.calls == []


def test_process_visual_need_is_admitted_above_threshold() -> None:
    gateway = _Gateway(
        {
            "answers": {
                "visual_need": {
                    "choice": "STRONGLY_RECOMMENDED",
                    "probabilities": {
                        "NONE": 0.02,
                        "HELPFUL": 0.08,
                        "STRONGLY_RECOMMENDED": 0.90,
                    },
                },
                "visual_category": {
                    "choice": "PROCESS",
                    "probabilities": {
                        "NONE": 0.01,
                        "SHAPE": 0.02,
                        "STRUCTURE": 0.05,
                        "PROCESS": 0.90,
                        "SCENE": 0.02,
                    },
                },
            }
        }
    )

    decision = _decide(gateway)

    assert decision.status == "COMPLETED"
    assert decision.visual_need == "STRONGLY_RECOMMENDED"
    assert decision.visual_category == "PROCESS"
    assert decision.recommends_visual is True
    assert len(gateway.calls) == 1


def test_low_probability_helpful_is_downgraded_to_none() -> None:
    gateway = _Gateway(
        {
            "answers": {
                "visual_need": {
                    "choice": "HELPFUL",
                    "probabilities": {
                        "NONE": 0.20,
                        "HELPFUL": 0.60,
                        "STRONGLY_RECOMMENDED": 0.20,
                    },
                },
                "visual_category": {
                    "choice": "STRUCTURE",
                    "probabilities": {
                        "NONE": 0.05,
                        "SHAPE": 0.05,
                        "STRUCTURE": 0.80,
                        "PROCESS": 0.05,
                        "SCENE": 0.05,
                    },
                },
            }
        }
    )

    decision = _decide(gateway)

    assert decision.visual_need == "NONE"
    assert decision.visual_category == "NONE"


def test_provider_failure_is_fail_closed() -> None:
    decision = _decide(_Gateway(error=TimeoutError("slow")))

    assert decision.status == "FAILED"
    assert decision.visual_need == "NONE"
    assert decision.failure_code == "TimeoutError"
