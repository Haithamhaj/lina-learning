import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from services.platform.auth import (
    AuthenticatedPrincipal,
    UserRole,
    get_current_principal,
    role_from_claims,
)


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