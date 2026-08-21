"""Persistence operations for the authenticated Student Math entry path.

This module intentionally owns only open/resume/create and message persistence.
Tutor orchestration and automatic session close remain separate later tasks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSession, Student, User


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
) -> LearningSession:
    """Return the latest open Math session, creating one only when needed."""

    # Locking the Student row serializes simultaneous first/open requests for
    # this Student without imposing a global session constraint.
    session.execute(select(Student.id).where(Student.id == student_id).with_for_update()).scalar_one()
    learning_session = session.execute(
        select(LearningSession)
        .where(
            LearningSession.student_id == student_id,
            LearningSession.subject == "MATH",
            LearningSession.status == "OPEN",
        )
        .order_by(LearningSession.last_activity_at.desc(), LearningSession.opened_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if learning_session is None:
        learning_session = LearningSession(student_id=student_id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
    return learning_session


def owned_open_math_session(
    session: Session,
    *,
    student_id: UUID,
    session_id: UUID,
) -> LearningSession | None:
    """Look up an open Math session within the authenticated Student boundary."""

    return session.execute(
        select(LearningSession).where(
            LearningSession.id == session_id,
            LearningSession.student_id == student_id,
            LearningSession.subject == "MATH",
            LearningSession.status == "OPEN",
        )
    ).scalar_one_or_none()


def ordered_messages(session: Session, *, learning_session: LearningSession) -> list[LearningMessage]:
    return list(
        session.execute(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session.id)
            .order_by(LearningMessage.created_at, LearningMessage.id)
        ).scalars()
    )


def append_student_message(
    session: Session,
    *,
    learning_session: LearningSession,
    content: str,
) -> LearningMessage:
    """Persist one raw Student message and retain the session as open."""

    message = LearningMessage(
        session_id=learning_session.id,
        role="student",
        content=content,
        payload={"source": "student-session-v1"},
    )
    session.add(message)
    learning_session.last_activity_at = datetime.now(UTC)
    session.flush()
    return message
