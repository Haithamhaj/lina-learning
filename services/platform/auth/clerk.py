"""Clerk JWT verification and FastAPI role dependencies."""

from base64 import urlsafe_b64decode
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWKClientError, PyJWTError

from services.platform.config import get_settings

from .roles import AuthenticatedPrincipal, UserRole, role_from_claims

bearer_scheme = HTTPBearer(auto_error=False)


class ClerkConfigurationError(RuntimeError):
    """Raised when Clerk key-discovery configuration is incomplete."""


def _jwks_url_from_publishable_key(publishable_key: str) -> str:
    """Derive Clerk's JWKS endpoint from a publishable key."""

    try:
        encoded_instance = publishable_key.rsplit("_", 1)[1]
        padding = "=" * (-len(encoded_instance) % 4)
        instance = urlsafe_b64decode(encoded_instance + padding).decode("utf-8")
    except (IndexError, UnicodeDecodeError, ValueError) as exc:
        raise ClerkConfigurationError(
            "CLERK_PUBLISHABLE_KEY does not contain a readable Clerk instance."
        ) from exc

    instance = instance.rstrip("$")
    if not instance.startswith(("http://", "https://")):
        instance = f"https://{instance}"
    return f"{instance.rstrip('/')}/.well-known/jwks.json"


def _configured_jwks_url() -> str:
    settings = get_settings()
    if settings.clerk_jwks_url:
        return settings.clerk_jwks_url
    if settings.clerk_publishable_key:
        return _jwks_url_from_publishable_key(settings.clerk_publishable_key)
    raise ClerkConfigurationError(
        "Clerk JWT verification is not configured. "
        "Set CLERK_PUBLISHABLE_KEY or CLERK_JWKS_URL."
    )


def _validate_authorized_party(claims: dict[str, Any]) -> None:
    """Reject a present Clerk ``azp`` claim outside configured trusted origins."""

    authorized_party = claims.get("azp")
    if authorized_party is None:
        # Clerk's manual JWT-verification model permits session tokens without
        # this optional claim.
        return

    settings = get_settings()
    trusted_origins = {settings.web_origin, *settings.allowed_origins}
    if not trusted_origins:
        raise ClerkConfigurationError(
            "Clerk authorized-party verification requires trusted origins."
        )
    if not isinstance(authorized_party, str) or authorized_party not in trusted_origins:
        raise PyJWTError("Clerk token has an untrusted authorized party.")


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def verify_clerk_token(token: str) -> AuthenticatedPrincipal:
    """Verify a Clerk session token and return a local principal."""

    signing_key = _jwks_client(_configured_jwks_url()).get_signing_key_from_jwt(token)
    claims: dict[str, Any] = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )
    _validate_authorized_party(claims)
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise PyJWTError("Verified Clerk token has no subject.")

    email = claims.get("email")
    return AuthenticatedPrincipal(
        subject=subject,
        role=role_from_claims(claims),
        email=email if isinstance(email, str) else None,
        claims=claims,
    )


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedPrincipal:
    """Require a valid Clerk bearer token for an API request."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return verify_clerk_token(credentials.credentials)
    except (ClerkConfigurationError, PyJWKClientError, PyJWTError, OSError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication could not be verified.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def require_role(required_role: UserRole):
    """Create a dependency that enforces one explicit application role."""

    async def dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if principal.role is not required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role cannot access the requested surface.",
            )
        return principal

    return dependency
