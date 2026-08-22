"""Application-owned Parent-to-Student authorization boundary."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import ParentStudentRelationship, Student, User

from .roles import AuthenticatedPrincipal, UserRole


class ParentStudentAccessDenied(PermissionError):
    """Raised without disclosing whether a requested Student exists."""


def _parent_user_for_principal(
    session: Session,
    *,
    principal: AuthenticatedPrincipal,
    identity_provider: str,
) -> User:
    """Resolve a verified Parent principal to its application-owned User."""

    if principal.role is not UserRole.PARENT_ADMIN:
        raise ParentStudentAccessDenied("Parent access is required.")

    user = session.execute(
        select(User).where(
            User.identity_provider == identity_provider,
            User.external_subject == principal.subject,
        )
    ).scalar_one_or_none()
    if user is None or user.role != UserRole.PARENT_ADMIN.value:
        raise ParentStudentAccessDenied("Parent access is required.")
    return user


def require_parent_student_access(
    session: Session,
    *,
    principal: AuthenticatedPrincipal,
    student_id: UUID,
    identity_provider: str = "clerk",
) -> Student:
    """Return only the Student explicitly linked to the verified Parent.

    ``student_id`` is merely a route locator. It is never an authorization
    credential, and all denials deliberately have the same result for an
    unknown Student and for an unrelated Student.
    """

    parent_user = _parent_user_for_principal(
        session,
        principal=principal,
        identity_provider=identity_provider,
    )
    student = session.execute(
        select(Student)
        .join(
            ParentStudentRelationship,
            ParentStudentRelationship.student_id == Student.id,
        )
        .where(
            ParentStudentRelationship.parent_user_id == parent_user.id,
            Student.id == student_id,
        )
    ).scalar_one_or_none()
    if student is None:
        raise ParentStudentAccessDenied("Parent access to Student is unavailable.")
    return student


def grant_parent_student_access(
    session: Session,
    *,
    parent_user_id: UUID,
    student_id: UUID,
) -> ParentStudentRelationship:
    """Create an explicit server-side Parent/Student link for setup or fixtures.

    This is intentionally not an API action: product linking and invitations
    require a separately designed, authenticated workflow. The database unique
    constraint remains the authority that prevents duplicate links.
    """

    parent_user = session.get(User, parent_user_id)
    student = session.get(Student, student_id)
    if parent_user is None or parent_user.role != UserRole.PARENT_ADMIN.value:
        raise ValueError("A local Parent user is required to grant Student access.")
    if student is None:
        raise ValueError("A local Student profile is required to grant Parent access.")

    relationship = ParentStudentRelationship(
        parent_user_id=parent_user.id,
        student_id=student.id,
    )
    session.add(relationship)
    session.flush()
    return relationship
