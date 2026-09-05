"""Small application-owned bridge from a persisted Tutor decision to exact activity adapters."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSession, StudioScene


def activate_known_workspace_activity(
    session: Session,
    *,
    learning_session: LearningSession,
    source_tutor_message: LearningMessage,
    source_segment_id: UUID | None,
    workspace_audit: Mapping[str, object] | None,
) -> StudioScene | None:
    """Give the persisted normal-Tutor audit to bounded exact activity adapters.

    This intentionally is not a registry or a second router: adapters verify all
    their own exact audit, profile, renderer, and source-lineage requirements.
    """

    from services.studio.make_ten_activation import activate_make_ten_from_workspace_decision
    from services.studio.process_sequence_activation import activate_process_sequence_from_workspace_decision
    from services.studio.sentence_ordering_activation import activate_sentence_ordering_from_workspace_decision

    for adapter in (
        activate_make_ten_from_workspace_decision,
        activate_process_sequence_from_workspace_decision,
        activate_sentence_ordering_from_workspace_decision,
    ):
        scene = adapter(
            session,
            learning_session=learning_session,
            source_tutor_message=source_tutor_message,
            source_segment_id=source_segment_id,
            workspace_audit=workspace_audit,
        )
        if scene is not None:
            return scene
    return None
