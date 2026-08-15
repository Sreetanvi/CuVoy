from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, create_app

HEALTH_STATES = {"ok", "degraded", "unavailable"}


def test_health_returns_200_and_contract_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "cache", "db"}
    assert body["status"] in HEALTH_STATES
    assert body["cache"] in HEALTH_STATES
    assert body["db"] in HEALTH_STATES
    assert body["status"] in {"ok", "degraded"}


def test_health_without_keys_marks_dependencies_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as isolated:
            body = isolated.get("/health").json()
        assert body["cache"] == "unavailable"
        assert body["db"] == "unavailable"
        assert body["status"] == "degraded"
    finally:
        get_settings.cache_clear()
