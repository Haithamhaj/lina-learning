"""Platform-owned resolution from verified external identity to Student profile."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import Student, User


def resolve_student_for_authenticated_identity(
    session: Session,
    *,
    identity_provider: str,
    subject: str,
    email: str | None,
) -> Student:
    """Resolve one application Student from an already verified external identity.

    The browser never supplies a Student identifier.  The verified identity
    provider/subject pair is authoritative, and the Student row lock preserves
    first-visit creation semantics under concurrent requests.
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
