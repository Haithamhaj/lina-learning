"""Authentication and role-authorization primitives."""

from .clerk import get_current_principal, require_role
from .roles import AuthenticatedPrincipal, UserRole, role_from_claims

__all__ = [
    "AuthenticatedPrincipal",
    "UserRole",
    "get_current_principal",
    "require_role",
    "role_from_claims",
]