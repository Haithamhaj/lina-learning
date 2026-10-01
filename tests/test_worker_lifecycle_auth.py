"""The scheduler tick must not become a public scale-control endpoint."""

from __future__ import annotations

from io import BytesIO
import json

import pytest
from fastapi import HTTPException

from apps.api.routes import worker_lifecycle as route
from services.platform.config import Settings
from services.platform import worker_lifecycle as lifecycle
from services.platform.worker_lifecycle import _count


@pytest.fixture
def settings(monkeypatch):
    configured = Settings(
        worker_lifecycle_enabled=True,
        worker_pool_project_id="test",
        worker_pool_region="local",
        worker_pool_name="lina-worker",
        worker_lifecycle_scheduler_audience="https://example.test/tick",
        worker_lifecycle_scheduler_email="scheduler@example.test",
    )
    monkeypatch.setattr(route, "get_settings", lambda: configured)
    return configured


def test_scheduler_token_is_required(settings):
    with pytest.raises(HTTPException) as error:
        route._verify_scheduler(None)
    assert error.value.status_code == 401


def test_verified_scheduler_email_is_exact(settings, monkeypatch):
    class Keys:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": "test-key"})()

    monkeypatch.setattr(route, "_google_keys", Keys())
    def decode(token, key, *, algorithms, audience, issuer):
        assert algorithms == ["RS256"]
        assert audience == settings.worker_lifecycle_scheduler_audience
        assert issuer == ["https://accounts.google.com", "accounts.google.com"]
        return {"email": "other@example.test", "email_verified": True}

    monkeypatch.setattr(route.jwt, "decode", decode)
    with pytest.raises(HTTPException) as error:
        route._verify_scheduler("Bearer signed-token")
    assert error.value.status_code == 403


def test_disabled_endpoint_returns_not_found(monkeypatch):
    monkeypatch.setattr(route, "get_settings", lambda: Settings())
    with pytest.raises(HTTPException) as error:
        route._verify_scheduler(None)
    assert error.value.status_code == 404


def test_zero_instance_count_may_be_omitted_by_cloud_run_json():
    assert _count({"scaling": {}}) == 0
    with pytest.raises(RuntimeError):
        _count({})


def test_cloud_run_adapter_patches_only_manual_instance_count(settings, monkeypatch):
    seen = []

    def open_request(request, *, timeout):
        seen.append((request.full_url, request.get_method(), request.data))
        payload = {"access_token": "fixture-token"} if "metadata.google.internal" in request.full_url else {
            "name": "projects/test/locations/local/operations/1"
        }
        return BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(lifecycle, "urlopen", open_request)
    client = lifecycle.CloudRunWorkerPoolClient(settings)
    assert client.set_instances(0) == "projects/test/locations/local/operations/1"
    assert seen[1][0] == (
        "https://run.googleapis.com/v2/projects/test/locations/local/workerPools/lina-worker"
        "?update_mask=scaling.manualInstanceCount"
    )
    assert seen[1][1] == "PATCH"
    assert json.loads(seen[1][2]) == {"scaling": {"manualInstanceCount": 0}}


def test_wake_reconciles_before_returning_from_the_request(settings, monkeypatch):
    monkeypatch.setattr(lifecycle, "get_settings", lambda: settings)
    monkeypatch.setattr(lifecycle, "_pool_requested_on", lambda: False)
    calls = []
    monkeypatch.setattr(lifecycle, "reconcile_worker_pool", lambda: calls.append("scale_requested") or "waking")
    lifecycle.request_worker_wake()
    assert calls == ["scale_requested"]
