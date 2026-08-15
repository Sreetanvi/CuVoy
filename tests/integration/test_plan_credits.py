from cuvoy_contracts.constants import PLAN_CREDITS_PER_DAY
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.cache import InMemoryCache
from tests.unit.test_pipeline import FakeExternal, FakeGateway, plan_request


def _client() -> TestClient:
    get_settings.cache_clear()
    app = create_app()
    client = TestClient(app)
    client.app.state.cache = InMemoryCache()
    client.app.state.external = FakeExternal()
    client.app.state.ai_gateway = FakeGateway()
    return client


def test_http_enforces_three_plans_per_day() -> None:
    payload = plan_request().model_dump(mode="json")
    with _client() as client:
        for _ in range(PLAN_CREDITS_PER_DAY):
            created = client.post("/api/v1/plan", json=payload)
            assert created.status_code == 202
        blocked = client.post("/api/v1/plan", json=payload)
        assert blocked.status_code == 429
        body = blocked.json()
        assert body["retryable"] is True
        assert "3 plans/day" in body["message"]
    get_settings.cache_clear()
