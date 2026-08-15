import httpx
import pytest
from cuvoy_contracts.preferences import ExtractedPreferences

from app.ai_gateway.gateway import PAID_FALLBACK, AIGateway, AIRequest
from app.ai_gateway.models import OPENROUTER_MODELS, is_paid_model
from app.ai_gateway.router import PAID_FALLBACK as ROUTER_PAID_FALLBACK
from app.ai_gateway.router import PROVIDER_ORDER
from app.ai_gateway.tasks import AITask
from app.config import Settings
from app.services.cache import InMemoryCache
from app.services.quota import PROVIDER_RPD, hit_provider


def test_paid_fallback_is_never() -> None:
    assert PAID_FALLBACK == "NEVER"
    assert ROUTER_PAID_FALLBACK is False
    assert PROVIDER_ORDER == ("gemini", "groq", "openrouter")
    for model in OPENROUTER_MODELS.values():
        assert ":free" in model
        assert is_paid_model("openrouter", model) is False
    assert is_paid_model("openrouter", "meta-llama/llama-3.3-70b-instruct") is True


@pytest.mark.asyncio
async def test_exhausted_free_tier_uses_deterministic_not_paid() -> None:
    cache = InMemoryCache()
    for provider in PROVIDER_ORDER:
        for _ in range(PROVIDER_RPD[provider]):
            assert await hit_provider(cache, provider) is True
        assert await hit_provider(cache, provider) is False

    called: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(str(request.url))
        return httpx.Response(200, json={"error": "should not be called"})

    settings = Settings(
        gemini_api_key="g",
        groq_api_key="q",
        openrouter_api_key="o",
        openrouter_fast_model="openai/gpt-4o",
        openrouter_balanced_model="openai/gpt-4o",
        openrouter_reasoning_model="openai/gpt-4o",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        gateway = AIGateway(settings, http, cache)
        result = await gateway.complete(
            AIRequest(
                task=AITask.PREFERENCE_EXTRACTION,
                user_content="extract",
                fallback_payload={"user_prompt": "food tour in Tokyo, packed days"},
            )
        )
    assert called == []
    assert result.fallback_used is True
    assert result.provider == "deterministic"
    assert isinstance(result.parsed, ExtractedPreferences)
