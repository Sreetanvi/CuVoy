from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.cache import InMemoryCache
from tests.unit.test_pipeline import FakeExternal, FakeGateway, plan_request


def test_plan_http_flow() -> None:
    get_settings.cache_clear()
    app = create_app()
    try:
        with TestClient(app) as client:
            client.app.state.cache = InMemoryCache()
            client.app.state.external = FakeExternal()
            client.app.state.ai_gateway = FakeGateway()
            payload = plan_request().model_dump(mode="json")
            created = client.post("/api/v1/plan", json=payload)
            assert created.status_code == 202
            plan_id = created.json()["plan_id"]
            status = client.get(f"/api/v1/plan/{plan_id}/status")
            assert status.status_code == 200
            result = client.get(f"/api/v1/plan/{plan_id}")
            assert result.status_code == 200
            body = result.json()
            assert body["plan_id"] == plan_id
            assert body["timezone"]
            assert body["validation"]["valid"] is True
            pdf = client.get(f"/api/v1/plan/{plan_id}/export/pdf")
            assert pdf.status_code == 200
            assert pdf.json()["renderer"] == "client"
            ics = client.get(f"/api/v1/plan/{plan_id}/export/ics")
            assert ics.status_code == 200
            assert "BEGIN:VCALENDAR" in ics.text
            assert client.get("/api/v1/trips").status_code == 401
            regen = client.post(
                f"/api/v1/plan/{plan_id}/regenerate", json={"skip_stop_ids": []}
            )
            assert regen.status_code == 202
    finally:
        get_settings.cache_clear()


def test_openapi_lists_plan_routes() -> None:
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        spec = client.get("/openapi.json").json()
    assert "/api/v1/plan" in spec["paths"]
    assert "/api/v1/plan/{plan_id}/status" in spec["paths"]
    get_settings.cache_clear()
