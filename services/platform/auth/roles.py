"""Stable role and principal contracts shared by protected API routes."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class UserRole(str, Enum):
    """Roles supported by the Phase 0 parent/student boundary."""

    PARENT_ADMIN = "PARENT_ADMIN"
    STUDENT = "STUDENT"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """The verified identity and role available to an API handler."""

    subject: str
    role: UserRole
    email: str | None = None
    claims: Mapping[str, Any] = field(default_factory=dict, repr=False)


def _role_candidate(value: Any) -> UserRole | None:
    if not isinstance(value, str):
        return None
    try:
        return UserRole(value.upper())
    except ValueError:
        return None


def role_from_claims(claims: Mapping[str, Any]) -> UserRole:
    """Read a role only from signed claims or Clerk public metadata.

    New Clerk users default to STUDENT. Promoting a user to PARENT_ADMIN is an
    explicit backend-controlled assignment and never happens because a claim is
    missing or supplied through user-writable metadata.
    """

    direct = _role_candidate(claims.get("role"))
    if direct is not None:
        return direct

    for key in ("public_metadata", "publicMetadata"):
        metadata = claims.get(key)
        if isinstance(metadata, Mapping):
            nested = _role_candidate(metadata.get("role"))
            if nested is not None:
                return nested

    return UserRole.STUDENT
