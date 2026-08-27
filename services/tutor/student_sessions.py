"""Persistence operations for the authenticated Student Math entry path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSession, Student, User
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


def student_for_authenticated_subject(
    session: Session,
    *,
    identity_provider: str,
    subject: str,
    email: str | None,
) -> Student:
    """Return the Student profile anchored to a verified Clerk subject.

    The browser never supplies a Student identifier. A first authenticated
    Student visit receives an application-owned profile for that identity.
    """

    user = session.execute(
        select(User).where(
            User.identity_provider == identity_provider,
            User.external_subject == subject,
        )
    ).scalar_one_or_none()
    if user is None:
        user = User(
            identity_provider=identity_provider,
            external_subject=subject,
            email=email,
            role="STUDENT",
        )
        session.add(user)
        session.flush()
    elif user.role != "STUDENT":
        raise PermissionError("The verified Student identity has no Student profile.")

    student = session.execute(
        select(Student).where(Student.user_id == user.id).with_for_update()
    ).scalar_one_or_none()
    if student is None:
        student = Student(user_id=user.id, display_name=user.display_name)
        session.add(student)
        session.flush()
    return student


def open_or_resume_math_session(
    session: Session,
    *,
    student_id: UUID,
    now: datetime | None = None,
    lifecycle_policy: SessionLifecyclePolicy | None = None,
) -> LearningSession:
    """Resume an eligible Math session or close-and-replace an expired one."""

    # Locking the Student row serializes simultaneous first/open requests for
    # this Student without imposing a global session constraint.
    session.execute(select(Student.id).where(Student.id == student_id).with_for_update()).scalar_one()
    current = now or datetime.now(UTC)
    policy = lifecycle_policy or session_lifecycle_policy()
    learning_session = session.execute(
        select(LearningSession)
        .where(
            LearningSession.student_id == student_id,
            LearningSession.subject == "MATH",
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
            subject="MATH",
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

    statement = select(LearningSession).where(
        LearningSession.id == session_id,
        LearningSession.student_id == student_id,
        LearningSession.subject == "MATH",
        LearningSession.status == "OPEN",
    )
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

    latest_tutor_message = session.execute(
        select(LearningMessage)
        .where(LearningMessage.session_id == learning_session.id, LearningMessage.role == "tutor")
        .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
        .limit(1)
    ).scalar_one_or_none()
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
