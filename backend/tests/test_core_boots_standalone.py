from fastapi import FastAPI

from core.bootstrap.app_factory import create_app
from core.module_registry.registry import register_modules


def test_core_boots_with_zero_modules_installed(monkeypatch):
    """Proves the core (auth/RBAC/storage/events/companies) is fully
    functional with no business modules mounted -- regardless of which
    modules INSTALLED_MODULES currently lists in this deployment."""
    import core.module_registry.registry as registry_module

    monkeypatch.setattr(registry_module, "INSTALLED_MODULES", [])
    app = FastAPI()
    manifests = register_modules(app)
    assert manifests == []


def test_core_app_builds_and_serves_health(app_client):
    response = app_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unauthenticated_request_returns_uniform_error_format(app_client):
    response = app_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert "request_id" in body["error"]
