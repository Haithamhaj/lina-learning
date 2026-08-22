"""Authentication and role-authorization primitives."""

from .clerk import get_current_principal, require_role
from .parent_student import (
    ParentStudentAccessDenied,
    grant_parent_student_access,
    require_parent_student_access,
)
from .roles import AuthenticatedPrincipal, UserRole, role_from_claims

__all__ = [
    "AuthenticatedPrincipal",
    "ParentStudentAccessDenied",
    "UserRole",
    "get_current_principal",
    "grant_parent_student_access",
    "require_parent_student_access",
    "require_role",
    "role_from_claims",
]
