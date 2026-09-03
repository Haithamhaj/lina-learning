"""Unit contracts for the authenticated, resumable Studio protocol."""

from __future__ import annotations

from uuid import uuid4

import pytest

from services.studio.protocol import (
    STUDIO_PROTOCOL_VERSION,
    StudioCursorConflict,
    StudioOperationRequest,
    parse_resume_cursor,
)
from services.studio.feed import format_sse_frame


def test_resume_cursor_accepts_one_nonnegative_authoritative_value() -> None:
    """The feed must resume only from an explicit, bounded sequence."""

    assert STUDIO_PROTOCOL_VERSION == "studio-protocol-v1"
    assert parse_resume_cursor(last_event_id="0", after_sequence=None) == 0
    assert parse_resume_cursor(last_event_id=None, after_sequence=8) == 8
    assert parse_resume_cursor(last_event_id="8", after_sequence=8) == 8

    with pytest.raises(StudioCursorConflict, match="disagree"):
        parse_resume_cursor(last_event_id="8", after_sequence=9)
    with pytest.raises(StudioCursorConflict, match="non-negative"):
        parse_resume_cursor(last_event_id="-1", after_sequence=None)


def test_operation_request_exposes_only_student_operation_inputs() -> None:
    """The browser may request an action, never choose its durable semantics."""

    scene_id = uuid4()
    request = StudioOperationRequest(
        scene_id=scene_id,
        base_scene_version=3,
        action_key="fixture.numeric.submit",
        payload={"value": 0},
        idempotency_key="operation-1",
    )

    assert request.scene_id == scene_id
    assert request.action_key == "fixture.numeric.submit"
    with pytest.raises(Exception):
        StudioOperationRequest(
            scene_id=scene_id,
            base_scene_version=3,
            action_key="fixture.numeric.submit",
            payload={"value": 0},
            idempotency_key="operation-1",
            event_kind="caller-controlled",  # type: ignore[call-arg]
        )


def test_sse_frames_have_a_protocol_payload_and_event_sequence_id() -> None:
    """A browser reconnect cursor must be sourced from the durable sequence."""

    encoded = format_sse_frame(
        {"protocol_version": STUDIO_PROTOCOL_VERSION, "type": "STUDIO_EVENT_COMMITTED", "sequence": 7},
        event_id=7,
    )

    assert encoded.startswith("id: 7\nevent: STUDIO_EVENT_COMMITTED\ndata: {")
    assert encoded.endswith("\n\n")
