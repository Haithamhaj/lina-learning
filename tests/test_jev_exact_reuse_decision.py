from __future__ import annotations

from uuid import uuid4

import pytest

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.models import ModelTask
from services.studio.canvas_brief import CanvasBriefV1
from services.studio.exact_reuse_decision import (
    ExactReuseAction,
    decide_exact_reuse_action,
)


class _Session:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        self.rows.append(row)

    def flush(self) -> None:
        return None


class _Provider:
    def __init__(self, answer: dict[str, object]) -> None:
        self.answer = answer
        self.payload: dict[str, object] | None = None

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        self.payload = payload
        return ModelResult(output={"answers": {"reuse_action": self.answer}})


def _brief() -> CanvasBriefV1:
    return CanvasBriefV1.model_validate(
        {
            "version": "canvas-brief-v1",
            "subject_key": "MATH",
            "objective": "Explore multiples of seven on the same existing wheel",
            "student_request": "Show that wheel again exactly as before",
            "requested_representation": "interactive wheel",
            "facts": ["multiples of seven"],
            "relations": [],
            "quantities": [],
            "desired_student_action": "spin the wheel",
            "must_not_imply": [],
            "source_references": [],
            "locale": "en",
            "direction": "ltr",
        }
    )


def _action(action_id: str) -> ExactReuseAction:
    return ExactReuseAction(
        action_id=action_id,
        instance_id=uuid4(),
        version_id=uuid4(),
        semantic_purpose="multiplication wheel for seven",
        stable_slug="multiplication-wheel",
        parameters={"factor": 7},
        manifest_summary={"representation": "wheel", "interactions": [{"action": "STEP"}]},
    )


def _decide(answer: dict[str, object]):
    provider = _Provider(answer)
    session = _Session()
    gateway = ModelGateway(
        session,
        routes={ModelTask.CANVAS_REUSE_SELECTION: ModelRoute("fixture", "jev")},
        providers={"fixture": provider},
    )
    decision = decide_exact_reuse_action(
        gateway,
        brief=_brief(),
        actions=[_action("REUSE_0")],
        min_probability=0.90,
        min_margin=0.20,
        policy_version="reuse-v1",
        run_id=uuid4(),
        student_id=uuid4(),
        learning_session_id=uuid4(),
        source_message_id=uuid4(),
    )
    return decision, provider


def test_exact_reuse_accepts_only_high_probability_high_margin_action() -> None:
    decision, provider = _decide(
        {"choice": "REUSE_0", "probabilities": {"REUSE_0": 0.96, "NO_MATCH": 0.04}}
    )
    assert decision.status == "ACCEPTED"
    assert decision.selected_action_id == "REUSE_0"
    assert decision.margin == pytest.approx(0.92)
    criteria = provider.payload["questions"]["reuse_action"]["criteria"]
    assert set(criteria) == {"REUSE_0", "NO_MATCH"}
    assert "factor" in criteria["REUSE_0"]


def test_exact_reuse_falls_back_when_margin_is_too_small() -> None:
    decision, _provider = _decide(
        {"choice": "REUSE_0", "probabilities": {"REUSE_0": 0.91, "NO_MATCH": 0.79}}
    )
    assert decision.status == "FALLBACK"
    assert decision.selected_action_id is None


def test_exact_reuse_falls_back_to_composer_for_no_match() -> None:
    decision, _provider = _decide(
        {"choice": "NO_MATCH", "probabilities": {"REUSE_0": 0.01, "NO_MATCH": 0.99}}
    )
    assert decision.status == "FALLBACK"
    assert decision.selected_action_id is None
