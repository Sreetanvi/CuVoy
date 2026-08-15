import pytest
from cuvoy_contracts.constants import PLAN_CREDITS_PER_DAY
from cuvoy_contracts.enums import PipelineStage

from app.config import get_settings, normalize_supabase_url
from app.services.budget import consume_credit, new_envelope
from app.services.cache import InMemoryCache, UpstashCache, cache_get_json, cache_set_json
from app.services.idempotency import begin, store_result
from app.services.identity import credit_identity
from app.services.jobs import (
    create_job,
    latest_completed_stage,
    next_stage,
    read_checkpoint,
    write_checkpoint,
)
from app.services.quota import PROVIDER_RPD, hit_provider
from app.services.supabase import NullSupabase


@pytest.fixture
def cache() -> InMemoryCache:
    return InMemoryCache()


def test_normalize_supabase_url_strips_rest_path() -> None:
    url = "https://vvwrlfsdfvbixuzcilvy.supabase.co/rest/v1/"
    assert normalize_supabase_url(url) == "https://vvwrlfsdfvbixuzcilvy.supabase.co"


def test_settings_strips_quoted_values(monkeypatch) -> None:
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", '"https://example.upstash.io"')
    get_settings.cache_clear()
    try:
        assert get_settings().upstash_redis_rest_url == "https://example.upstash.io"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_json_roundtrip(cache: InMemoryCache) -> None:
    assert await cache_set_json(cache, "places:paris", {"id": "1"}, 60)
    assert await cache_get_json(cache, "places:paris") == {"id": "1"}


@pytest.mark.asyncio
async def test_credits_reject_fourth_plan(cache: InMemoryCache) -> None:
    identity = credit_identity(user_id=None, ip="1.2.3.4", fingerprint="abc")
    for _ in range(PLAN_CREDITS_PER_DAY):
        result = await consume_credit(cache, identity)
        assert result.allowed is True
        assert result.enforced is True
    blocked = await consume_credit(cache, identity)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert "3 plans/day" in blocked.message


@pytest.mark.asyncio
async def test_regen_envelope_is_fractional() -> None:
    full = new_envelope("plan-1")
    regen = new_envelope("plan-1", regeneration=True)
    assert regen.remaining["llm"] < full.remaining["llm"]
    assert regen.remaining["mapbox_matrix"] >= 1


@pytest.mark.asyncio
async def test_idempotency_returns_cached_body(cache: InMemoryCache) -> None:
    assert await begin(cache, "abc-123") is None
    await store_result(cache, "abc-123", {"plan_id": "p1"})
    cached = await begin(cache, "abc-123")
    assert cached is not None
    assert cached["plan_id"] == "p1"
    assert cached["status"] == "complete"


@pytest.mark.asyncio
async def test_provider_quota_exhaustion(cache: InMemoryCache) -> None:
    cap = PROVIDER_RPD["gemini"]
    for _ in range(cap):
        assert await hit_provider(cache, "gemini") is True
    assert await hit_provider(cache, "gemini") is False


@pytest.mark.asyncio
async def test_job_checkpoint_resume(cache: InMemoryCache) -> None:
    job = await create_job(cache, NullSupabase(), identity="anon:test")
    job_id = job["job_id"]
    await write_checkpoint(cache, job_id, PipelineStage.DISCOVER, {"places": 12})
    saved = await read_checkpoint(cache, job_id, PipelineStage.DISCOVER)
    assert saved == {"places": 12}
    assert await latest_completed_stage(cache, job_id) == PipelineStage.DISCOVER
    assert next_stage(PipelineStage.DISCOVER) == PipelineStage.REDUCE


@pytest.mark.asyncio
async def test_upstash_ping_accepts_pong() -> None:
    class FakeRedis:
        async def ping(self) -> str:
            return "PONG"

    cache = UpstashCache("https://example.upstash.io", "token", redis=FakeRedis())
    assert await cache.ping() is True
