from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "lina-learning-api"}


def test_status_endpoint_reports_foundation_phase() -> None:
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    assert response.json()["phase"] == "phase-0"