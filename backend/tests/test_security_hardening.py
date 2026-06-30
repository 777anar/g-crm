"""Covers RELEASE_CHECKLIST.md C2 (insecure default JWT secret) and H1
(login rate limiting)."""
import pytest


def test_app_refuses_to_start_with_default_secret_outside_development(monkeypatch):
    from core.bootstrap import app_factory
    from core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret_key", app_factory.DEFAULT_JWT_SECRET)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        app_factory.create_app()


def test_app_boots_in_production_with_a_real_secret(monkeypatch):
    from core.bootstrap import app_factory
    from core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret_key", "a-real-randomly-generated-secret")

    app = app_factory.create_app()
    assert app is not None


def test_app_boots_in_development_with_default_secret(monkeypatch):
    from core.bootstrap import app_factory
    from core.config import settings

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "jwt_secret_key", app_factory.DEFAULT_JWT_SECRET)

    app = app_factory.create_app()
    assert app is not None


def test_login_rate_limiter_blocks_after_threshold():
    from core.rbac.rate_limit import FixedWindowRateLimiter
    from core.api.errors import RateLimitedError

    limiter = FixedWindowRateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("1.2.3.4")

    with pytest.raises(RateLimitedError):
        limiter.check("1.2.3.4")


def test_login_rate_limiter_tracks_keys_independently():
    from core.rbac.rate_limit import FixedWindowRateLimiter

    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60)
    limiter.check("1.1.1.1")
    limiter.check("2.2.2.2")  # different key -- should not raise


def test_login_endpoint_returns_429_past_the_limit(app_client, monkeypatch):
    from core.rbac.rate_limit import login_rate_limiter

    monkeypatch.setattr(login_rate_limiter, "max_requests", 2)

    for _ in range(2):
        app_client.post("/api/v1/auth/login", json={"email": "nobody@test.example", "password": "wrong"})

    response = app_client.post("/api/v1/auth/login", json={"email": "nobody@test.example", "password": "wrong"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
