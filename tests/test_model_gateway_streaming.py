"""A streaming Tutor call remains one gateway-owned execution."""

from __future__ import annotations

from services.model_gateway.gateway import (
    ModelGateway,
    ModelResult,
    ModelRoute,
    StreamComplete,
    StreamDelta,
)
from services.platform.db.models import ModelTask


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
