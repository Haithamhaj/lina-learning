"""Server-owned, bounded read access to older semantic Studio history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import StudioEvent, StudioRuntime
from services.studio.tutor_context import StudioTutorEventContext


STUDIO_HISTORY_POLICY_VERSION = "studio-history-v1"
# This is a bounded exceptional Tutor support lookup, not Event Log export.
# Current Snapshot plus unseen Events is the normal Tutor path.  The cap protects
# query and model-context size; it is deliberately revisited only through an
# explicit versioned policy based on production measurement.
MAX_STUDIO_HISTORY_EVENTS = 100


class StudioHistoryAccessDenied(ValueError):
    """A non-enumerating failure for an unavailable scoped Studio runtime."""


class StudioHistoryService:
    """Read-only semantic history boundary; it never exposes ORM query access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def events_through(
        self,
        *,
        student_id: UUID,
        learning_session_id: UUID,
        runtime_id: UUID,
        through_sequence: int,
        limit: int,
    ) -> tuple[StudioTutorEventContext, ...]:
        """Return the most recent bounded semantic Events through one sequence."""

        if not isinstance(limit, int) or limit <= 0 or limit > MAX_STUDIO_HISTORY_EVENTS:
            raise ValueError("Studio history limit must be a bounded positive count.")
        runtime = self._session.execute(
            select(StudioRuntime).where(
                StudioRuntime.id == runtime_id,
                StudioRuntime.student_id == student_id,
                StudioRuntime.learning_session_id == learning_session_id,
            )
        ).scalar_one_or_none()
        if runtime is None or through_sequence < 0 or through_sequence > runtime.latest_event_sequence:
            raise StudioHistoryAccessDenied("Studio history is unavailable for this scoped Runtime.")
        rows = list(
            self._session.execute(
                select(StudioEvent)
                .where(
                    StudioEvent.studio_runtime_id == runtime.id,
                    StudioEvent.student_id == student_id,
                    StudioEvent.learning_session_id == learning_session_id,
                    StudioEvent.sequence <= through_sequence,
                )
                .order_by(StudioEvent.sequence.desc())
                .limit(limit)
            ).scalars()
        )
        return tuple(_event_context(event) for event in reversed(rows))


def _event_context(event: StudioEvent) -> StudioTutorEventContext:
    return StudioTutorEventContext(
        sequence=event.sequence,
        actor=event.actor,
        event_kind=event.event_kind,
        action_key=event.action_key,
        subject_key=event.subject_key,
        activity_key=event.activity_key,
        base_scene_version=event.base_scene_version,
        resulting_scene_version=event.resulting_scene_version,
        payload_schema_version=event.payload_schema_version,
        payload=dict(event.payload),
    )
