"""Deterministic Model Router: Gemini free → Groq free → OpenRouter free."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from app.ai_gateway.circuit_breaker import CircuitBreaker, CircuitState
from app.ai_gateway.models import is_paid_model, model_for
from app.ai_gateway.providers import gemini, groq, openrouter
from app.ai_gateway.providers.base import ProviderResult
from app.ai_gateway.rate_limit import RateLimiter
from app.ai_gateway.tasks import ModelRole
from app.config import Settings
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, NullCache
from app.services.quota import hit_provider, provider_allowed

FREE_ONLY = True
PAID_FALLBACK = False
PROVIDER_ORDER = ("gemini", "groq", "openrouter")

GenerateFn = Callable[..., Awaitable[ProviderResult]]

_ADAPTERS: dict[str, GenerateFn] = {
    "gemini": gemini.generate,
    "groq": groq.generate,
    "openrouter": openrouter.generate,
}


@dataclass
class RouteDecision:
    provider: str
    model: str
    skip_reason: str | None = None


class ModelRouter:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient,
        cache: CacheBackend | None = None,
        breaker: CircuitBreaker | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.settings = settings
        self.http = http
        self.cache = cache or NullCache()
        self.breaker = breaker or CircuitBreaker()
        self.limiter = limiter or RateLimiter()

    def api_key(self, provider: str) -> str:
        return {
            "gemini": self.settings.gemini_api_key,
            "groq": self.settings.groq_api_key,
            "openrouter": self.settings.openrouter_api_key,
        }[provider]

    async def eligible(
        self, provider: str, role: ModelRole, budget: PlanBudget | None
    ) -> RouteDecision | None:
        if budget is not None and budget.remaining.get("llm", 0) <= 0:
            return None
        key = self.api_key(provider)
        if not key:
            return None
        model = model_for(provider, role, self.settings)
        if FREE_ONLY and is_paid_model(provider, model):
            return None
        if not PAID_FALLBACK and is_paid_model(provider, model):
            return None
        if self.breaker.peek(provider) == CircuitState.OPEN:
            return None
        if not self.limiter.would_allow(provider):
            return None
        if not await provider_allowed(self.cache, provider):
            return None
        return RouteDecision(provider=provider, model=model)

    async def candidates(self, role: ModelRole, budget: PlanBudget | None) -> list[RouteDecision]:
        chosen: list[RouteDecision] = []
        for provider in PROVIDER_ORDER:
            decision = await self.eligible(provider, role, budget)
            if decision is not None:
                chosen.append(decision)
        return chosen

    async def generate(
        self,
        decision: RouteDecision,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
        timeout: float,
    ) -> ProviderResult:
        if not self.breaker.allow(decision.provider):
            return ProviderResult(ok=False, model=decision.model, error="circuit_open")
        if not self.limiter.allow(decision.provider):
            return ProviderResult(
                ok=False,
                model=decision.model,
                error="rpm_limited",
                status_code=429,
            )
        if not await hit_provider(self.cache, decision.provider):
            return ProviderResult(ok=False, model=decision.model, error="rpd_exhausted")
        adapter = _ADAPTERS[decision.provider]
        return await adapter(
            self.http,
            api_key=self.api_key(decision.provider),
            model=decision.model,
            system=system,
            user=user,
            max_output_tokens=max_output_tokens,
            timeout=timeout,
        )
