from cuvoy_contracts.api import AccountDeleteResponse, SavedTrip, SharedTrip
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services.cache import InMemoryCache
from app.services.identity import credit_identity
from tests.fakes import MemorySupabase
from tests.unit.test_pipeline import FakeExternal, FakeGateway, plan_request


def _plan(client: TestClient, headers: dict[str, str] | None = None) -> str:
    created = client.post(
        "/api/v1/plan",
        json=plan_request().model_dump(mode="json"),
        headers=headers or {},
    )
    assert created.status_code == 202, created.text
    return created.json()["plan_id"]


def test_trips_require_login() -> None:
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        client.app.state.cache = InMemoryCache()
        client.app.state.supabase = MemorySupabase()
        client.app.state.external = FakeExternal()
        client.app.state.ai_gateway = FakeGateway()
        assert client.get("/api/v1/trips").status_code == 401
        assert client.post("/api/v1/trips", json={"plan_id": "x"}).status_code == 401
        assert client.delete("/api/v1/account").status_code == 401
    get_settings.cache_clear()


def test_save_list_share_and_gdpr_delete() -> None:
    get_settings.cache_clear()
    supabase = MemorySupabase()
    token = supabase.add_user("11111111-1111-1111-1111-111111111111")
    other = supabase.add_user(
        "22222222-2222-2222-2222-222222222222",
        email="other@example.com",
        token="other-token",
    )
    auth = {"Authorization": f"Bearer {token}"}
    with TestClient(create_app()) as client:
        client.app.state.cache = InMemoryCache()
        client.app.state.supabase = supabase
        client.app.state.external = FakeExternal()
        client.app.state.ai_gateway = FakeGateway()

        plan_id = _plan(client, auth)
        assert client.get(f"/api/v1/plan/{plan_id}").status_code == 200

        saved = client.post(
            "/api/v1/trips",
            json={"plan_id": plan_id, "title": "Bengaluru weekend"},
            headers=auth,
        )
        assert saved.status_code == 201
        body = SavedTrip.model_validate(saved.json())
        assert body.title == "Bengaluru weekend"
        assert body.share_url and body.share_url.endswith(f"/trip/{body.slug}")

        listed = client.get("/api/v1/trips", headers=auth)
        assert listed.status_code == 200
        assert len(listed.json()["trips"]) == 1

        owned = client.get(f"/api/v1/trips/{body.trip_id}", headers=auth)
        assert owned.status_code == 200
        assert owned.json()["result"]["plan_id"] == plan_id

        public = client.get(f"/api/v1/trips/shared/{body.slug}")
        assert public.status_code == 200
        shared = SharedTrip.model_validate(public.json())
        assert shared.read_only is True
        assert shared.result.plan_id == plan_id

        stranger = client.get("/api/v1/trips", headers={"Authorization": f"Bearer {other}"})
        assert stranger.status_code == 200
        assert stranger.json()["trips"] == []

        deleted = client.delete("/api/v1/account", headers=auth)
        assert deleted.status_code == 200
        payload = AccountDeleteResponse.model_validate(deleted.json())
        assert payload.deleted is True
        assert payload.trips_purged == 1
        assert "11111111-1111-1111-1111-111111111111" in supabase.deleted_auth
        assert client.get(f"/api/v1/trips/shared/{body.slug}").status_code == 404
        assert client.get("/api/v1/trips", headers=auth).status_code == 401
    get_settings.cache_clear()


def test_logged_in_credits_use_account_not_ip() -> None:
    get_settings.cache_clear()
    supabase = MemorySupabase()
    token = supabase.add_user("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    auth = {"Authorization": f"Bearer {token}"}
    cache = InMemoryCache()
    with TestClient(create_app()) as client:
        client.app.state.cache = cache
        client.app.state.supabase = supabase
        client.app.state.external = FakeExternal()
        client.app.state.ai_gateway = FakeGateway()
        for _ in range(3):
            _plan(client, auth)
        blocked = client.post(
            "/api/v1/plan",
            json=plan_request().model_dump(mode="json"),
            headers=auth,
        )
        assert blocked.status_code == 429
        anon = client.post("/api/v1/plan", json=plan_request().model_dump(mode="json"))
        assert anon.status_code == 202
    identity = credit_identity(
        user_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        ip="ignored",
        fingerprint=None,
    )
    assert any(identity in key for key in cache._store)
    get_settings.cache_clear()
