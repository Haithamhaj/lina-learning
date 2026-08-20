import pytest
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWTError

from apps.api.main import app
from services.platform.auth import (
    AuthenticatedPrincipal,
    UserRole,
    get_current_principal,
    role_from_claims,
)
from services.platform.auth import clerk
from services.platform.config import Settings


client = TestClient(app)


def _principal(role: UserRole) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject=f"test-{role.value.lower()}",
        role=role,
        email=f"{role.value.lower()}@example.test",
    )


def test_role_claims_default_to_student_and_accept_parent_metadata() -> None:
    assert role_from_claims({}) is UserRole.STUDENT
    assert (
        role_from_claims({"public_metadata": {"role": "PARENT_ADMIN"}})
        is UserRole.PARENT_ADMIN
    )


@pytest.mark.parametrize("claim_key", ["metadata", "unsafe_metadata", "unsafeMetadata"])
def test_untrusted_metadata_parent_role_does_not_elevate_a_student(
    claim_key: str,
) -> None:
    assert (
        role_from_claims({claim_key: {"role": "PARENT_ADMIN"}})
        is UserRole.STUDENT
    )


@pytest.mark.parametrize(
    "authorized_party",
    ["https://app.example.com", "https://admin.example.com"],
)
def test_verified_token_accepts_configured_authorized_parties(
    monkeypatch: pytest.MonkeyPatch,
    authorized_party: str,
) -> None:
    claims = {"sub": "user_123", "azp": authorized_party}
    _mock_verified_clerk_token(monkeypatch, claims)

    principal = clerk.verify_clerk_token("test-token")

    assert principal.subject == "user_123"


def test_verified_token_rejects_an_untrusted_authorized_party(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_verified_clerk_token(
        monkeypatch,
        {"sub": "user_123", "azp": "https://attacker.example.com"},
    )

    with pytest.raises(PyJWTError, match="authorized party"):
        clerk.verify_clerk_token("test-token")


def test_verified_token_allows_absent_authorized_party_per_clerk_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_verified_clerk_token(monkeypatch, {"sub": "user_123"})

    assert clerk.verify_clerk_token("test-token").subject == "user_123"


def _mock_verified_clerk_token(
    monkeypatch: pytest.MonkeyPatch,
    claims: dict[str, str],
) -> None:
    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token: str):
            assert token == "test-token"
            return type("SigningKey", (), {"key": "test-key"})()

    monkeypatch.setattr(clerk, "_configured_jwks_url", lambda: "https://jwks.test")
    monkeypatch.setattr(clerk, "_jwks_client", lambda _: FakeJwksClient())
    monkeypatch.setattr(clerk.jwt, "decode", lambda *args, **kwargs: claims)
    monkeypatch.setattr(
        clerk,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            web_origin="https://app.example.com",
            allowed_origins=["https://admin.example.com"],
        ),
    )


@pytest.fixture(autouse=True)
def clear_auth_overrides():
    app.dependency_overrides.pop(get_current_principal, None)
    yield
    app.dependency_overrides.pop(get_current_principal, None)


def test_protected_routes_require_authentication() -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/student/shell").status_code == 401
    assert client.get("/api/v1/auth/parent/admin-shell").status_code == 401


def test_student_cannot_access_parent_admin_surface() -> None:
    app.dependency_overrides[get_current_principal] = lambda: _principal(
        UserRole.STUDENT,
    )

    assert client.get("/api/v1/auth/student/shell").status_code == 200
    response = client.get("/api/v1/auth/parent/admin-shell")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "This role cannot access the requested surface."
    )


def test_parent_can_access_admin_but_not_student_surface() -> None:
    app.dependency_overrides[get_current_principal] = lambda: _principal(
        UserRole.PARENT_ADMIN,
    )

    assert client.get("/api/v1/auth/parent/admin-shell").status_code == 200
    assert client.get("/api/v1/auth/student/shell").status_code == 403
