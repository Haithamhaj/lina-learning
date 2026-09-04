"""A streaming Tutor call remains one gateway-owned execution."""

from __future__ import annotations

import pytest

from services.model_gateway.gateway import (
    ModelGateway,
    ModelResult,
    ModelRoute,
    StreamComplete,
    StreamDelta,
)
from services.model_gateway.openai_provider import _normalize_output
from services.platform.db.models import ModelTask
from services.tutor.candidate_events import TUTOR_OUTPUT_RESPONSE_SCHEMA


class _RecordingSession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        self.rows.append(row)

    def flush(self) -> None:
        return None


def test_streaming_gateway_forwards_provider_deltas_and_records_one_execution() -> None:
    class Provider:
        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route, payload
            yield StreamDelta("Try ")
            yield StreamDelta("one step.")
            yield StreamComplete(ModelResult(output={"text": "Try one step."}, input_tokens=5, output_tokens=3))

    session = _RecordingSession()
    gateway = ModelGateway(
        session,
        routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
        providers={"fixture": Provider()},
    )

    events = list(gateway.stream(ModelTask.TUTOR, {"instructions": "Teach", "input": "Help"}))

    assert [event.text for event in events if isinstance(event, StreamDelta)] == ["Try ", "one step."]
    assert isinstance(events[-1], StreamComplete)
    assert events[-1].result.output == {"text": "Try one step."}
    assert len(session.rows) == 1
    assert session.rows[0].task == ModelTask.TUTOR.value


def test_structured_tutor_normalization_preserves_all_luna_semantic_decisions() -> None:
    """Catches a valid v6 decision being dropped before Tutor runtime validation."""

    output = _normalize_output(
        '{"text":"Use a fraction bar.","suggested_actions":[],"teaching_mode":"HOMEWORK","teaching_strategy":"HINT_FIRST","teaching_method_id":"VISUAL_REPRESENTATION","prior_method_relation":"CONTINUATION","segment_relation":"CONTINUE","structured_segment_state":null,"candidate_metadata":null,"workspace_intent":null}',
        {"response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA},
    )

    assert output["teaching_method_id"] == "VISUAL_REPRESENTATION"
    assert output["teaching_mode"] == "HOMEWORK"
    assert output["teaching_strategy"] == "HINT_FIRST"
    assert output["prior_method_relation"] == "CONTINUATION"
    assert output["segment_relation"] == "CONTINUE"
    assert output["structured_segment_state"] is None


def test_structured_v9_tutor_normalization_preserves_workspace_intent() -> None:
    """A v9 Tutor response keeps its strict Workspace Intent rather than taking the generic path."""

    output = _normalize_output(
        '{"text":"Try a number line.","suggested_actions":[],"workspace_intent":{"version":"workspace-intent-v1","action":"OPEN_ACTIVITY","subject_key":"MATH","concept_keys":["fraction-equivalence"],"learning_goal":"Compare equivalent fractions.","activity_hint":null,"representation_need":"VISUAL","expected_student_response_mode":"WORKSPACE","presentation_sequence":"PARALLEL","source_references":[],"safe_text_fallback":"Let us compare the fractions."}}',
        {"response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA},
    )

    assert output["workspace_intent"] == {
        "version": "workspace-intent-v1",
        "action": "OPEN_ACTIVITY",
        "subject_key": "MATH",
        "concept_keys": ["fraction-equivalence"],
        "learning_goal": "Compare equivalent fractions.",
        "activity_hint": None,
        "representation_need": "VISUAL",
        "expected_student_response_mode": "WORKSPACE",
        "presentation_sequence": "PARALLEL",
        "source_references": [],
        "safe_text_fallback": "Let us compare the fractions.",
    }
    assert output["candidate_metadata"] is None
    assert output["candidate_metadata_error"] == "candidate_metadata_missing"

    null_output = _normalize_output(
        '{"text":"Keep going.","suggested_actions":[],"candidate_metadata":null,"workspace_intent":null}',
        {"response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA},
    )
    assert null_output["workspace_intent"] is None


def test_structured_v9_tutor_normalization_rejects_missing_workspace_intent() -> None:
    """A missing v9 required field must not be converted to ordinary Workspace absence."""

    with pytest.raises(ValueError, match="workspace_intent"):
        _normalize_output(
            '{"text":"Try one step.","suggested_actions":[],"candidate_metadata":null}',
            {"response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA},
        )


def test_structured_v8_tutor_normalization_keeps_historical_absent_workspace_intent() -> None:
    """v8 predates WorkspaceIntent and remains provider-compatible without that field."""

    output = _normalize_output(
        '{"text":"Try one step.","suggested_actions":[],"candidate_metadata":null}',
        {"response_schema": {"name": "tutor_turn_v8", "schema": {"type": "object"}}},
    )

    assert "workspace_intent" not in output


def test_structured_v9_fallback_cannot_masquerade_as_a_valid_result() -> None:
    """A malformed v9 stream cannot use text fallback to bypass its required field contract."""

    with pytest.raises(ValueError, match="valid JSON"):
        _normalize_output(
            "not JSON",
            {"response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA},
            fallback_text="Try one small step.",
        )


def test_malformed_structured_tutor_fallback_does_not_invent_semantic_decisions() -> None:
    output = _normalize_output(
        "not JSON",
        {"response_schema": {"name": "tutor_turn_v8", "schema": {"type": "object"}}},
        fallback_text="Try one small step.",
    )

    assert output["text"] == "Try one small step."
    assert not {"teaching_mode", "teaching_strategy", "teaching_method_id", "prior_method_relation", "segment_relation", "structured_segment_state"} & output.keys()


def test_strict_non_tutor_schema_returns_its_complete_parsed_envelope() -> None:
    """Catches the OpenAI adapter assuming every strict task is a Tutor turn."""

    output = _normalize_output(
        '{"version":"segment-learning-review-v2","findings":[]}',
        {
            "response_schema": {
                "name": "segment_learning_review_v1",
                "schema": {
                    "type": "object",
                    "properties": {"version": {"type": "string"}, "findings": {"type": "array"}},
                    "required": ["version", "findings"],
                    "additionalProperties": False,
                },
            }
        },
    )

    assert output == {"version": "segment-learning-review-v2", "findings": []}
