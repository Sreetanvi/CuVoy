from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.cache import InMemoryCache
from tests.unit.test_pipeline import FakeExternal, FakeGateway, plan_request


def test_same_idempotency_key_reuses_plan_and_credit() -> None:
    get_settings.cache_clear()
    app = create_app()
    payload = plan_request().model_dump(mode="json")
    headers = {"Idempotency-Key": "e2e-idem-1"}
    try:
        with TestClient(app) as client:
            client.app.state.cache = InMemoryCache()
            client.app.state.external = FakeExternal()
            client.app.state.ai_gateway = FakeGateway()
            first = client.post("/api/v1/plan", json=payload, headers=headers)
            second = client.post("/api/v1/plan", json=payload, headers=headers)
            assert first.status_code == 202
            assert second.status_code == 202
            assert first.json()["plan_id"] == second.json()["plan_id"]
            third = client.post(
                "/api/v1/plan",
                json=payload,
                headers={"Idempotency-Key": "e2e-idem-2"},
            )
            assert third.status_code == 202
            assert third.json()["plan_id"] != first.json()["plan_id"]
    finally:
        get_settings.cache_clear()
