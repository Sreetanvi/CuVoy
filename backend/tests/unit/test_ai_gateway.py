import json

import httpx
import pytest
from cuvoy_contracts.constants import HIGH_DEMAND_UI_MESSAGE
from cuvoy_contracts.preferences import ExtractedPreferences

from app.ai_gateway.fallback import fallback_preferences
from app.ai_gateway.gateway import AIGateway, AIRequest
from app.ai_gateway.models import is_paid_model
from app.ai_gateway.rate_limit import RateLimiter
from app.ai_gateway.tasks import AITask
from app.config import Settings
from app.services.cache import InMemoryCache
from app.services.quota import PROVIDER_RPD, hit_provider


def test_openrouter_without_free_suffix_is_paid() -> None:
    assert is_paid_model("openrouter", "meta-llama/llama-3.3-70b-instruct") is True
    assert is_paid_model("openrouter", "meta-llama/llama-3.3-70b-instruct:free") is False


def test_rpm_limiter_blocks_over_cap() -> None:
    limiter = RateLimiter(rpm={"gemini": 2})
    assert limiter.allow("gemini") is True
    assert limiter.allow("gemini") is True
    assert limiter.allow("gemini") is False
    assert limiter.would_allow("gemini") is False


def test_fallback_preferences_keywords() -> None:
    parsed = fallback_preferences("Relaxed 5-day temple trip with my parents, hidden gems")
    assert parsed.pace.value == "relaxed"
    assert "temples" in parsed.interests
    assert parsed.accessibility.elderly is True
    assert parsed.hidden_gems is True


@pytest.mark.asyncio
async def test_gateway_uses_deterministic_when_no_keys() -> None:
    settings = Settings(
        gemini_api_key="",
        groq_api_key="",
        openrouter_api_key="",
    )
    async with httpx.AsyncClient() as http:
        gateway = AIGateway(settings, http, InMemoryCache())
        result = await gateway.complete(
            AIRequest(
                task=AITask.PREFERENCE_EXTRACTION,
                user_content="extract",
                fallback_payload={"user_prompt": "food tour in Tokyo, packed days"},
            )
        )
    assert result.fallback_used is True
    assert result.provider == "deterministic"
    assert isinstance(result.parsed, ExtractedPreferences)
    assert result.parsed.pace.value == "packed"
    assert "food" in result.parsed.interests


@pytest.mark.asyncio
async def test_gateway_gemini_then_parse() -> None:
    body = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "interests": ["history"],
                                    "pace": "relaxed",
                                    "hidden_gems": True,
                                }
                            )
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "generativelanguage.googleapis.com" in str(request.url)
        return httpx.Response(200, json=body)

    settings = Settings(gemini_api_key="test-gemini", groq_api_key="", openrouter_api_key="")
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        gateway = AIGateway(settings, http, InMemoryCache())
        result = await gateway.complete(
            AIRequest(
                task=AITask.PREFERENCE_EXTRACTION,
                user_content="user",
                fallback_payload={"user_prompt": "x"},
            )
        )
    assert result.fallback_used is False
    assert result.provider == "gemini"
    assert result.parsed.pace.value == "relaxed"
    assert result.parsed.hidden_gems is True


@pytest.mark.asyncio
async def test_gateway_fails_over_gemini_to_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    groq_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"interests": ["nature"], "pace": "moderate"})
                }
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 8},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "generativelanguage.googleapis.com" in url:
            return httpx.Response(503, json={"error": "busy"})
        if "api.groq.com" in url:
            return httpx.Response(200, json=groq_payload)
        return httpx.Response(500, json={"error": "unexpected"})

    settings = Settings(
        gemini_api_key="g",
        groq_api_key="q",
        openrouter_api_key="",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = AIGateway(settings, http, InMemoryCache())

        async def _no_sleep(_seconds: float) -> None:
            return None

        monkeypatch.setattr("app.ai_gateway.gateway.asyncio.sleep", _no_sleep)
        result = await gateway.complete(
            AIRequest(
                task=AITask.PREFERENCE_EXTRACTION,
                user_content="user",
                fallback_payload={"user_prompt": "nature hike"},
            )
        )
    assert result.provider == "groq"
    assert result.parsed.interests == ["nature"]


@pytest.mark.asyncio
async def test_invalid_json_then_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "not json at all"}]}}]},
        )

    settings = Settings(gemini_api_key="g", groq_api_key="", openrouter_api_key="")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = AIGateway(settings, http, InMemoryCache())

        async def _no_sleep(_seconds: float) -> None:
            return None

        monkeypatch.setattr("app.ai_gateway.gateway.asyncio.sleep", _no_sleep)
        result = await gateway.complete(
            AIRequest(
                task=AITask.PREFERENCE_EXTRACTION,
                user_content="user",
                fallback_payload={"user_prompt": "temples and food"},
            )
        )
    assert result.fallback_used is True
    assert result.provider == "deterministic"
    assert "temples" in result.parsed.interests


@pytest.mark.asyncio
async def test_ranking_strips_unknown_place_ids() -> None:
    payload = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "ranked": [
                {"place_id": "p1", "score": 0.9, "reason": "fit"},
                {"place_id": "invented", "score": 0.8, "reason": "nope"},
            ]
        })}]}}]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    settings = Settings(gemini_api_key="g", groq_api_key="", openrouter_api_key="")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = AIGateway(settings, http, InMemoryCache())
        result = await gateway.complete(
            AIRequest(
                task=AITask.RANK_CANDIDATES,
                user_content="rank",
                known_place_ids={"p1"},
                fallback_payload={"candidates": [{"place_id": "p1"}]},
            )
        )
    assert [item.place_id for item in result.parsed.ranked] == ["p1"]


@pytest.mark.asyncio
async def test_http_429_sets_high_demand_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0"}, json={"error": "rate"})

    settings = Settings(gemini_api_key="g", groq_api_key="", openrouter_api_key="")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = AIGateway(settings, http, InMemoryCache())

        async def _no_sleep(_seconds: float) -> None:
            return None

        monkeypatch.setattr("app.ai_gateway.gateway.asyncio.sleep", _no_sleep)
        result = await gateway.complete(
            AIRequest(
                task=AITask.PACKING,
                user_content="pack",
                fallback_payload={"context": {}},
            )
        )
    assert result.fallback_used is True
    assert result.message == HIGH_DEMAND_UI_MESSAGE


@pytest.mark.asyncio
async def test_quota_exhaustion_skips_provider() -> None:
    cache = InMemoryCache()
    for _ in range(PROVIDER_RPD["gemini"]):
        assert await hit_provider(cache, "gemini") is True
    assert await hit_provider(cache, "gemini") is False

    called = {"gemini": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["gemini"] += 1
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    settings = Settings(gemini_api_key="g", groq_api_key="", openrouter_api_key="")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = AIGateway(settings, http, cache)
        result = await gateway.complete(
            AIRequest(
                task=AITask.PREFERENCE_EXTRACTION,
                user_content="user",
                fallback_payload={"user_prompt": "Kyoto temples"},
            )
        )
    assert called["gemini"] == 0
    assert result.fallback_used is True
