"""Pure, versioned reducer registry for generic Studio lifecycle events."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from services.studio.subjects import production_subject_registry
from services.studio.subjects.registry import SubjectCapabilityRegistry


CORE_EVENT_SCHEMA_VERSION = "studio-core-v1"
SNAPSHOT_SCHEMA_VERSION = "studio-snapshot-v1"


class UnknownStudioEvent(ValueError):
    """Raised before persistence when no registered reducer accepts an event."""


@dataclass(frozen=True)
class ReducerEvent:
    id: UUID
    sequence: int
    event_kind: str
    action_key: str | None
    event_schema_version: str
    actor: str
    scene_id: UUID | None
    base_scene_version: int | None
    resulting_scene_version: int | None
    subject_key: str | None
    activity_key: str | None
    payload: dict[str, object]
    activity_contract_version: str | None = None
    subject_profile_version: str | None = None
    payload_schema_version: str | None = None


SnapshotProjection = dict[str, object]
Reducer = Callable[[SnapshotProjection, ReducerEvent], SnapshotProjection]


def empty_snapshot() -> SnapshotProjection:
    return {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "latest_event_sequence": 0,
        "current_scene_id": None,
        "current_scene_version": None,
        "active_subject_key": None,
        "active_activity_key": None,
        "active_step_key": None,
        "last_meaningful_student_event_id": None,
        "state_payload": {},
    }


def _base(snapshot: SnapshotProjection, event: ReducerEvent) -> SnapshotProjection:
    next_snapshot = deepcopy(snapshot)
    if event.sequence <= int(next_snapshot["latest_event_sequence"]):
        raise ValueError("Studio event sequence must advance the snapshot.")
    next_snapshot["latest_event_sequence"] = event.sequence
    if event.actor == "STUDENT":
        next_snapshot["last_meaningful_student_event_id"] = event.id
    return next_snapshot


def _scene_projection(snapshot: SnapshotProjection, event: ReducerEvent) -> SnapshotProjection:
    if event.scene_id is None or event.resulting_scene_version is None:
        raise ValueError("Scene lifecycle events require a resulting Scene version.")
    snapshot["current_scene_id"] = event.scene_id
    snapshot["current_scene_version"] = event.resulting_scene_version
    snapshot["active_subject_key"] = event.subject_key
    snapshot["active_activity_key"] = event.activity_key
    return snapshot


def _accepted(snapshot: SnapshotProjection, event: ReducerEvent) -> SnapshotProjection:
    next_snapshot = _scene_projection(_base(snapshot, event), event)
    seed = event.payload.get("scene_seed")
    if not isinstance(seed, dict):
        raise ValueError("Accepted Scene event requires its bounded scene seed.")
    next_snapshot["state_payload"] = {"scene_seed": deepcopy(seed), "scene_status": "ACCEPTED"}
    return next_snapshot


def _activated(snapshot: SnapshotProjection, event: ReducerEvent) -> SnapshotProjection:
    next_snapshot = _scene_projection(_base(snapshot, event), event)
    state = dict(next_snapshot["state_payload"])
    state["scene_status"] = "ACTIVE"
    next_snapshot["state_payload"] = state
    return next_snapshot


def _status_changed(snapshot: SnapshotProjection, event: ReducerEvent) -> SnapshotProjection:
    next_snapshot = _scene_projection(_base(snapshot, event), event)
    status = event.payload.get("status")
    if not isinstance(status, str):
        raise ValueError("Scene status transition requires a status.")
    state = dict(next_snapshot["state_payload"])
    state["scene_status"] = status
    next_snapshot["state_payload"] = state
    return next_snapshot


def _recorded(snapshot: SnapshotProjection, event: ReducerEvent) -> SnapshotProjection:
    return _base(snapshot, event)


_REGISTRY: dict[tuple[str, str], Reducer] = {
    ("studio.runtime.initialized", CORE_EVENT_SCHEMA_VERSION): _recorded,
    ("studio.scene.accepted", CORE_EVENT_SCHEMA_VERSION): _accepted,
    ("studio.scene.activated", CORE_EVENT_SCHEMA_VERSION): _activated,
    ("studio.scene.status_changed", CORE_EVENT_SCHEMA_VERSION): _status_changed,
}


def registered_reducer(event_kind: str, event_schema_version: str) -> Reducer:
    try:
        return _REGISTRY[(event_kind, event_schema_version)]
    except KeyError as error:
        raise UnknownStudioEvent(
            f"Unsupported Studio event contract: {event_kind!r} / {event_schema_version!r}."
        ) from error


def reduce_snapshot(
    snapshot: SnapshotProjection,
    event: ReducerEvent,
    *,
    subject_registry: SubjectCapabilityRegistry | None = None,
) -> SnapshotProjection:
    """Apply a known event without database, model, or side-effect dependencies."""

    if (event.event_kind, event.event_schema_version) in _REGISTRY:
        return registered_reducer(event.event_kind, event.event_schema_version)(snapshot, event)
    if (
        event.subject_key is None
        or event.subject_profile_version is None
        or event.activity_key is None
        or event.activity_contract_version is None
        or event.action_key is None
    ):
        raise UnknownStudioEvent(
            f"Unsupported Studio event contract: {event.event_kind!r} / {event.event_schema_version!r}."
        )
    registry = subject_registry or production_subject_registry()
    action, _validation = registry.validate_subject_event(
        subject_key=event.subject_key,
        subject_profile_version=event.subject_profile_version,
        activity_key=event.activity_key,
        activity_version=event.activity_contract_version,
        action_key=event.action_key,
        payload_schema_version=event.payload_schema_version or "",
        payload=event.payload,
        activity_state=(
            snapshot["state_payload"]
            if isinstance(snapshot.get("state_payload"), dict)
            else None
        ),
    )
    del action, _validation
    activity = registry.resolve_activity(event.subject_key, event.subject_profile_version, event.activity_key, event.activity_contract_version)
    reducer = registry.resolve_reducer(event.subject_key, event.subject_profile_version, activity.reducer_key, activity.reducer_version)
    return reducer.reducer(snapshot, event)
