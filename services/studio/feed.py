"""Resumable PostgreSQL-backed Studio SSE feed.

``LISTEN/NOTIFY`` is only a commit-delayed wake-up hint.  Every emitted event
is re-read from the sequenced durable log using a short-lived SQLAlchemy
session, so notification loss or coalescing cannot change Studio truth.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from typing import Protocol
from uuid import UUID

import psycopg
from sqlalchemy.orm import Session

from services.platform.config import get_settings
from services.platform.db.connection import get_engine
from services.studio.protocol import (
    STUDIO_PROTOCOL_VERSION,
    StudioCursorConflict,
    StudioProtocolService,
    event_frame,
    snapshot_frame,
)
from services.studio.service import STUDIO_EVENT_NOTIFICATION_CHANNEL


STUDIO_FEED_HEARTBEAT_SECONDS = 15.0


class _Notification(Protocol):
    payload: str


class _Listener(Protocol):
    def execute(self, query: str) -> object: ...

    def notifies(self, *, timeout: float | None = None, stop_after: int | None = None) -> Iterator[_Notification]: ...

    def close(self) -> None: ...


def format_sse_frame(frame: dict[str, object], *, event_id: int | None = None) -> str:
    """Encode one protocol frame without exposing a transport-specific schema."""

    event_type = str(frame["type"])
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append("data: " + json.dumps(frame, separators=(",", ":"), ensure_ascii=False))
    return "\n".join(lines) + "\n\n"


def heartbeat_frame() -> str:
    return ": studio-heartbeat\n\n"


def _psycopg_connection_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _connect_listener() -> _Listener:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("Studio feed requires DATABASE_URL.")
    return psycopg.connect(_psycopg_connection_url(database_url), autocommit=True)


class StudioEventFeed:
    """Own a dedicated listener connection and never hold a web DB transaction open."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        listener_factory: Callable[[], _Listener] = _connect_listener,
        heartbeat_seconds: float = STUDIO_FEED_HEARTBEAT_SECONDS,
    ) -> None:
        self.session_factory = session_factory or (lambda: Session(get_engine()))
        self.listener_factory = listener_factory
        self.heartbeat_seconds = heartbeat_seconds

    def _snapshot_and_events(
        self,
        *,
        student_id: UUID,
        runtime_id: UUID,
        after_sequence: int | None,
    ) -> tuple[int, list[dict[str, object]], dict[str, object]]:
        """Read one transactionally consistent catch-up window then release it."""

        session = self.session_factory()
        try:
            # A repeatable-read window prevents a Snapshot at M from skipping
            # an Event that was committed between two independent reads.
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            protocol = StudioProtocolService(session)
            snapshot = protocol.snapshot(student_id=student_id, runtime_id=runtime_id)
            latest = snapshot.latest_event_sequence
            if after_sequence is not None and after_sequence > latest:
                raise StudioCursorConflict("Resume sequence is ahead of committed Studio history.")
            events = [] if after_sequence is None else protocol.events_after(
                student_id=student_id,
                runtime_id=runtime_id,
                after_sequence=after_sequence,
            )
            # The query above may see no later state than the same transaction's
            # snapshot.  Bound it explicitly to the snapshot watermark.
            frames = [event_frame(event) for event in events if event.sequence <= latest]
            session.commit()
            return latest, frames, snapshot_frame(snapshot)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def stream(self, *, student_id: UUID, runtime_id: UUID, after_sequence: int | None) -> Iterator[str]:
        """Yield initial/catch-up frames then committed live Event Log entries."""

        listener: _Listener | None = None
        try:
            listener = self.listener_factory()
            listener.execute(f"LISTEN {STUDIO_EVENT_NOTIFICATION_CHANNEL}")
            seen, catchup, snapshot = self._snapshot_and_events(
                student_id=student_id,
                runtime_id=runtime_id,
                after_sequence=after_sequence,
            )
            for frame in catchup:
                yield format_sse_frame(frame, event_id=int(frame["sequence"]))
            yield format_sse_frame(snapshot)

            while True:
                notifications = list(listener.notifies(timeout=self.heartbeat_seconds, stop_after=1))
                if not notifications:
                    yield heartbeat_frame()
                    continue
                try:
                    hint = json.loads(notifications[0].payload)
                    hinted_runtime = UUID(str(hint.get("runtime_id")))
                    hinted_sequence = int(hint.get("sequence"))
                except (TypeError, ValueError, json.JSONDecodeError):
                    # Hints are untrusted for authority. Ignore malformed hints;
                    # a later committed notification or reconnect catches up.
                    continue
                if hinted_runtime != runtime_id or hinted_sequence <= seen:
                    continue
                latest, frames, _snapshot = self._snapshot_and_events(
                    student_id=student_id,
                    runtime_id=runtime_id,
                    after_sequence=seen,
                )
                for frame in frames:
                    yield format_sse_frame(frame, event_id=int(frame["sequence"]))
                seen = latest
        except StudioCursorConflict:
            # The route validates cursors before response headers; this only
            # protects a race/alternative caller without exposing internals.
            yield format_sse_frame(
                {"protocol_version": STUDIO_PROTOCOL_VERSION, "type": "STUDIO_ERROR", "code": "STUDIO_PROTOCOL_ERROR"}
            )
        except Exception:
            yield format_sse_frame(
                {"protocol_version": STUDIO_PROTOCOL_VERSION, "type": "STUDIO_ERROR", "code": "STUDIO_FEED_UNAVAILABLE"}
            )
        finally:
            if listener is not None:
                listener.close()
