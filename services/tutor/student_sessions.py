"""Persistence operations for the authenticated Student Math entry path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSession, Student, StudioStudentInteraction
from services.tutor.candidate_events import (
    PersistedGuidedLearningCheck,
    SuggestedAction,
    normalize_suggested_actions,
    persisted_guided_learning_check,
)
from services.tutor.teaching_methods import PriorTeachingMethodContext, prior_teaching_method_context_from_payload
from services.tutor.session_lifecycle import (
    SessionLifecyclePolicy,
    close_session_if_eligible,
    session_lifecycle_policy,
)


class DailySessionNotFound(ValueError):
    """The requested exact session is unavailable to this Student."""


class DailySessionNotResumable(ValueError):
    """The owned session has ended under the existing lifecycle policy."""


class DailySessionReplacementNotAllowed(ValueError):
    """A replacement was requested for a session that can still be resumed."""


FOREGROUND_TUTOR_TURN_KEY = "foreground_tutor_turn"
FOREGROUND_TUTOR_TURN_VERSION = "foreground-tutor-turn-v1"


class ForegroundTutorBusy(ValueError):
    """Another admitted foreground Tutor request owns this Daily session."""


def _active_chat_foreground_message(session: Session, *, learning_session_id: UUID) -> LearningMessage | None:
    messages = session.execute(
        select(LearningMessage).where(
            LearningMessage.session_id == learning_session_id,
            LearningMessage.role == "student",
        ).order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
    ).scalars()
    for message in messages:
        payload = message.payload if isinstance(message.payload, dict) else {}
        foreground = payload.get(FOREGROUND_TUTOR_TURN_KEY)
        if isinstance(foreground, dict) and foreground.get("status") == "RUNNING":
            return message
    return None


def _active_canvas_foreground_interaction(
    session: Session, *, learning_session_id: UUID
) -> StudioStudentInteraction | None:
    return session.execute(
        select(StudioStudentInteraction).where(
            StudioStudentInteraction.learning_session_id == learning_session_id,
            StudioStudentInteraction.status.in_(("PENDING", "RUNNING")),
        ).order_by(StudioStudentInteraction.created_at, StudioStudentInteraction.id).limit(1)
    ).scalar_one_or_none()


def lock_foreground_tutor_lane(
    session: Session, *, learning_session_id: UUID, student_id: UUID
) -> LearningSession:
    """Serialize Tutor-triggering Chat and Canvas admission on one LearningSession."""

    learning_session = session.execute(
        select(LearningSession).where(
            LearningSession.id == learning_session_id,
            LearningSession.student_id == student_id,
            LearningSession.status == "OPEN",
        ).with_for_update()
    ).scalar_one_or_none()
    if learning_session is None:
        raise ValueError("Open learning session was not found.")
    if _active_chat_foreground_message(session, learning_session_id=learning_session_id) is not None:
        raise ForegroundTutorBusy("A foreground Tutor response is already pending for this learning session.")
    if _active_canvas_foreground_interaction(session, learning_session_id=learning_session_id) is not None:
        raise ForegroundTutorBusy("A foreground Tutor response is already pending for this learning session.")
    return learning_session


def admit_foreground_student_message(
    session: Session,
    *,
    learning_session: LearningSession,
    content: str,
    interaction_payload: dict[str, object] | None = None,
) -> LearningMessage:
    """Lock the shared lane and durably admit one truthful Chat foreground turn."""

    locked = lock_foreground_tutor_lane(
        session,
        learning_session_id=learning_session.id,
        student_id=learning_session.student_id,
    )
    payload = {
        **(interaction_payload or {}),
        FOREGROUND_TUTOR_TURN_KEY: {
            "version": FOREGROUND_TUTOR_TURN_VERSION,
            "origin": "CHAT",
            "status": "RUNNING",
        },
    }
    return append_student_message(
        session,
        learning_session=locked,
        content=content,
        interaction_payload=payload,
    )


def settle_foreground_student_message(
    session: Session, *, message_id: UUID, status: str
) -> None:
    """Give an admitted Chat turn one explicit terminal state."""

    if status not in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise ValueError("Foreground Tutor terminal status is unsupported.")
    # Legacy direct-runtime fixtures and non-persistent callers never used the
    # durable admission lane. Their Session doubles intentionally expose only
    # add/flush; there is no foreground marker to settle.
    if not callable(getattr(session, "execute", None)):
        return
    message = session.execute(
        select(LearningMessage).where(LearningMessage.id == message_id).with_for_update()
    ).scalar_one_or_none()
    if message is None or message.role != "student":
        return
    payload = dict(message.payload) if isinstance(message.payload, dict) else {}
    foreground = payload.get(FOREGROUND_TUTOR_TURN_KEY)
    if not isinstance(foreground, dict) or foreground.get("status") != "RUNNING":
        return
    payload[FOREGROUND_TUTOR_TURN_KEY] = {**foreground, "status": status}
    message.payload = payload
    session.flush([message])


@dataclass(frozen=True)
class ResolvedSuggestedAction:
    """A server-validated action and the exact Tutor message that offered it."""

    action: SuggestedAction
    source_tutor_message_id: UUID


@dataclass(frozen=True)
class ResolvedGuidedLearningCheck:
    """A server-validated choice bound to its persisted Tutor check."""

    guided_check: PersistedGuidedLearningCheck
    source_tutor_message_id: UUID


def open_or_resume_math_session(
    session: Session,
    *,
    student_id: UUID,
    now: datetime | None = None,
    lifecycle_policy: SessionLifecyclePolicy | None = None,
) -> LearningSession:
    """Resume an eligible Math session or close-and-replace an expired one."""

    return _open_or_resume_student_session(
        session,
        student_id=student_id,
        session_subject="MATH",
        now=now,
        lifecycle_policy=lifecycle_policy,
    )


def open_or_resume_daily_session(
    session: Session,
    *,
    student_id: UUID,
    learning_session_id: UUID | None = None,
    replacement_for_session_id: UUID | None = None,
    now: datetime | None = None,
    lifecycle_policy: SessionLifecyclePolicy | None = None,
) -> LearningSession:
    """Create, resume an exact ID, or idempotently replace one ended owned ID."""

    session.execute(select(Student.id).where(Student.id == student_id).with_for_update()).scalar_one()
    current = now or datetime.now(UTC)
    if learning_session_id is not None and replacement_for_session_id is not None:
        raise ValueError("Daily session resume and replacement references are mutually exclusive.")
    if replacement_for_session_id is not None:
        replaced = session.execute(
            select(LearningSession).where(
                LearningSession.id == replacement_for_session_id,
                LearningSession.student_id == student_id,
            ).with_for_update()
        ).scalar_one_or_none()
        if replaced is None:
            raise DailySessionNotFound("Daily session not found.")
        if replaced.status == "OPEN" and not close_session_if_eligible(
            session,
            learning_session=replaced,
            now=current,
            policy=lifecycle_policy or session_lifecycle_policy(),
        ):
            raise DailySessionReplacementNotAllowed(
                "This learning session is still open and must not be replaced."
            )
        replacement_id = uuid5(
            NAMESPACE_URL,
            f"lina:daily-session-replacement-v1:{student_id}:{replacement_for_session_id}",
        )
        learning_session = session.execute(
            select(LearningSession).where(
                LearningSession.id == replacement_id,
                LearningSession.student_id == student_id,
            ).with_for_update()
        ).scalar_one_or_none()
        if learning_session is None:
            learning_session = LearningSession(
                id=replacement_id,
                student_id=student_id,
                status="OPEN",
                opened_at=current,
                last_activity_at=current,
            )
            session.add(learning_session)
        elif learning_session.status != "OPEN":
            raise DailySessionNotResumable(
                "This replacement learning session has ended. Start a new session to continue."
            )
        else:
            learning_session.last_activity_at = current
    elif learning_session_id is None:
        # Keep the model's compatibility default, never a route-kind subject.
        learning_session = LearningSession(student_id=student_id, status="OPEN", opened_at=current, last_activity_at=current)
        session.add(learning_session)
    else:
        learning_session = session.execute(
            select(LearningSession).where(
                LearningSession.id == learning_session_id,
                LearningSession.student_id == student_id,
            ).with_for_update()
        ).scalar_one_or_none()
        if learning_session is None:
            raise DailySessionNotFound("Daily session not found.")
        if learning_session.status != "OPEN" or close_session_if_eligible(
            session, learning_session=learning_session, now=current,
            policy=lifecycle_policy or session_lifecycle_policy(),
        ):
            raise DailySessionNotResumable("This learning session has ended. Start a new session to continue.")
        learning_session.last_activity_at = current
    session.flush()
    return learning_session


def _open_or_resume_student_session(
    session: Session,
    *,
    student_id: UUID,
    session_subject: str,
    now: datetime | None,
    lifecycle_policy: SessionLifecyclePolicy | None,
) -> LearningSession:
    """Shared technical lifecycle; entry contracts choose their own identity."""

    # Locking the Student row serializes simultaneous first/open requests for
    # this Student without imposing a global session constraint.
    session.execute(select(Student.id).where(Student.id == student_id).with_for_update()).scalar_one()
    current = now or datetime.now(UTC)
    policy = lifecycle_policy or session_lifecycle_policy()
    learning_session = session.execute(
        select(LearningSession)
        .where(
            LearningSession.student_id == student_id,
            LearningSession.subject == session_subject,
            LearningSession.status == "OPEN",
        )
        .order_by(LearningSession.last_activity_at.desc(), LearningSession.opened_at.desc())
        .with_for_update()
        .limit(1)
    ).scalar_one_or_none()
    if learning_session is not None and close_session_if_eligible(
        session,
        learning_session=learning_session,
        now=current,
        policy=policy,
    ):
        learning_session = None
    if learning_session is None:
        learning_session = LearningSession(
            student_id=student_id,
            subject=session_subject,
            status="OPEN",
            opened_at=current,
            last_activity_at=current,
        )
        session.add(learning_session)
        session.flush()
    else:
        learning_session.last_activity_at = current
        session.flush()
    return learning_session


def owned_open_math_session(
    session: Session,
    *,
    student_id: UUID,
    session_id: UUID,
    lock: bool = False,
) -> LearningSession | None:
    """Look up an open Math session within the authenticated Student boundary."""

    return _owned_open_student_session(
        session,
        student_id=student_id,
        session_id=session_id,
        session_subject="MATH",
        lock=lock,
    )


def owned_open_daily_session(
    session: Session,
    *,
    student_id: UUID,
    session_id: UUID,
    lock: bool = False,
) -> LearningSession | None:
    """Resolve the exact owned Daily technical session, never a Math fallback."""

    return _owned_open_student_session(
        session,
        student_id=student_id,
        session_id=session_id,
        session_subject=None,
        lock=lock,
    )


def _owned_open_student_session(
    session: Session,
    *,
    student_id: UUID,
    session_id: UUID,
    session_subject: str | None,
    lock: bool,
) -> LearningSession | None:
    """Resolve one exact open technical session inside its Student boundary."""

    statement = select(LearningSession).where(
        LearningSession.id == session_id,
        LearningSession.student_id == student_id,
        LearningSession.status == "OPEN",
    )
    if session_subject is not None:
        statement = statement.where(LearningSession.subject == session_subject)
    if lock:
        statement = statement.with_for_update()
    return session.execute(statement).scalar_one_or_none()


def ordered_messages(session: Session, *, learning_session: LearningSession) -> list[LearningMessage]:
    return list(
        session.execute(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session.id)
            .order_by(LearningMessage.created_at, LearningMessage.id)
        ).scalars()
    )


def latest_tutor_suggested_action(
    session: Session,
    *,
    learning_session: LearningSession,
    label: str,
) -> ResolvedSuggestedAction | None:
    """Resolve an action claim solely from the latest persisted Tutor message."""

    latest_tutor_message = session.execute(
        select(LearningMessage)
        .where(LearningMessage.session_id == learning_session.id, LearningMessage.role == "tutor")
        .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_tutor_message is None:
        return None
    payload = latest_tutor_message.payload if isinstance(latest_tutor_message.payload, dict) else {}
    action = next(
        (action for action in normalize_suggested_actions(payload.get("suggested_actions")) if action.label == label),
        None,
    )
    if action is None:
        return None
    return ResolvedSuggestedAction(action=action, source_tutor_message_id=latest_tutor_message.id)


def latest_tutor_guided_check_choice(
    session: Session,
    *,
    learning_session: LearningSession,
    guided_check_id: UUID,
    label: str,
) -> ResolvedGuidedLearningCheck | None:
    """Accept only an exact visible choice from the latest persisted Tutor check."""

    if hasattr(session, "execute"):
        latest_tutor_message = session.execute(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session.id, LearningMessage.role == "tutor")
            .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
            .limit(1)
        ).scalar_one_or_none()
    else:
        messages = [
            row for row in getattr(session, "rows", ())
            if isinstance(row, LearningMessage)
            and row.session_id == learning_session.id
            and row.role == "tutor"
        ]
        latest_tutor_message = max(
            messages,
            key=lambda message: (message.created_at, str(message.id)),
            default=None,
        )
    if latest_tutor_message is None:
        return None
    payload = latest_tutor_message.payload if isinstance(latest_tutor_message.payload, dict) else {}
    guided_check = persisted_guided_learning_check(payload.get("guided_check"))
    if (
        guided_check is None
        or guided_check.id != guided_check_id
        or label not in {choice.label for choice in guided_check.choices}
    ):
        return None
    return ResolvedGuidedLearningCheck(
        guided_check=guided_check,
        source_tutor_message_id=latest_tutor_message.id,
    )


def latest_prior_tutor_teaching_method(
    session: Session,
    *,
    learning_session: LearningSession,
    before_message: LearningMessage,
) -> PriorTeachingMethodContext | None:
    """Resolve only the immediately previous, valid Tutor method in this session."""

    if hasattr(session, "execute"):
        message = session.execute(
            select(LearningMessage)
            .where(
                LearningMessage.session_id == learning_session.id,
                LearningMessage.role == "tutor",
                LearningMessage.created_at < before_message.created_at,
            )
            .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
            .limit(1)
        ).scalar_one_or_none()
    else:
        rows = [
            row for row in getattr(session, "rows", ())
            if isinstance(row, LearningMessage)
            and row.session_id == learning_session.id
            and row.role == "tutor"
            and row.created_at < before_message.created_at
        ]
        message = max(rows, key=lambda row: (row.created_at, str(row.id)), default=None)
    if message is None:
        return None
    return prior_teaching_method_context_from_payload(
        tutor_message_id=message.id,
        payload=message.payload,
    )


def append_student_message(
    session: Session,
    *,
    learning_session: LearningSession,
    content: str,
    interaction_payload: dict[str, object] | None = None,
) -> LearningMessage:
    """Persist one raw Student message and retain the session as open."""

    message = LearningMessage(
        session_id=learning_session.id,
        role="student",
        content=content,
        payload={"source": "student-session-v1", **(interaction_payload or {})},
        created_at=datetime.now(UTC),
    )
    session.add(message)
    learning_session.last_activity_at = datetime.now(UTC)
    session.flush()
    return message
