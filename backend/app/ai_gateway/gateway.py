"""Single AI Gateway. Pipeline services never call Gemini/Groq/OpenRouter directly."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from cuvoy_contracts.constants import (
    HIGH_DEMAND_UI_MESSAGE,
    LLM_MAX_CONCURRENT,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
)
from pydantic import ValidationError

from app.ai_gateway.circuit_breaker import CircuitBreaker
from app.ai_gateway.fallback import run_fallback
from app.ai_gateway.json_cleaner import JSONCleanError, loads_llm_json
from app.ai_gateway.prompts import system_for
from app.ai_gateway.rate_limit import RateLimiter
from app.ai_gateway.router import ModelRouter
from app.ai_gateway.schemas import TASK_SCHEMA, RankedCandidates
from app.ai_gateway.tasks import AITask, ModelRole, profile_for
from app.config import Settings
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, NullCache

logger = logging.getLogger("cuvoy.ai")

FREE_ONLY = True
PAID_FALLBACK = "NEVER"


@dataclass
class AIRequest:
    task: AITask
    user_content: str
    fallback_payload: dict[str, Any] = field(default_factory=dict)
    known_place_ids: set[str] | None = None
    complexity: str | None = None


@dataclass
class AIResult:
    success: bool
    provider: str
    model: str
    output: dict[str, Any] | None
    parsed: object | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    fallback_used: bool = False
    retries: int = 0
    message: str | None = None
    prompt_version: str = ""


def _drop_unknown(data: Any, model_cls: type) -> Any:
    if not isinstance(data, dict):
        return data
    fields = getattr(model_cls, "model_fields", None)
    if not fields:
        return data
    return {key: value for key, value in data.items() if key in fields}


class AIGateway:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient,
        cache: CacheBackend | None = None,
        *,
        breaker: CircuitBreaker | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.settings = settings
        self.cache = cache or NullCache()
        self.breaker = breaker or CircuitBreaker()
        self.limiter = limiter or RateLimiter()
        self.router = ModelRouter(settings, http, self.cache, self.breaker, self.limiter)
        self._sema = asyncio.Semaphore(LLM_MAX_CONCURRENT)

    async def complete(self, request: AIRequest, budget: PlanBudget | None = None) -> AIResult:
        started = time.perf_counter()
        profile = profile_for(request.task)
        role = profile["role"]
        if request.complexity == "high":
            role = ModelRole.REASONING
        max_tokens = int(profile["max_output_tokens"])
        prompt_version = str(profile["prompt_version"])
        system = system_for(request.task)
        schema = TASK_SCHEMA[request.task.value]
        high_demand = False
        retries = 0

        async with self._sema:
            decisions = await self.router.candidates(role, budget)
            for decision in decisions:
                if budget is not None and not budget.consume("llm"):
                    break
                for attempt in range(LLM_MAX_RETRIES):
                    retries += 1 if attempt else 0
                    result = await self.router.generate(
                        decision,
                        system=system,
                        user=request.user_content,
                        max_output_tokens=max_tokens,
                        timeout=LLM_TIMEOUT_SECONDS,
                    )
                    if result.error in {"circuit_open", "rpm_limited", "rpd_exhausted"}:
                        if result.error == "rpm_limited":
                            high_demand = True
                        break
                    if result.status_code == 429:
                        high_demand = True
                        retry_after = result.retry_after
                        wait = retry_after if retry_after is not None else (0.5 * (2**attempt))
                        wait += random.uniform(0, 0.25)
                        await asyncio.sleep(min(wait, 8.0))
                        continue
                    if not result.ok:
                        self.breaker.record_failure(decision.provider)
                        if attempt < LLM_MAX_RETRIES - 1:
                            await asyncio.sleep(0.5 * (2**attempt) + random.uniform(0, 0.25))
                            continue
                        break
                    try:
                        raw = loads_llm_json(result.text)
                        cleaned = _drop_unknown(raw, schema)
                        parsed = schema.model_validate(cleaned)
                        parsed = self._post_validate(request, parsed)
                    except (JSONCleanError, ValidationError, ValueError):
                        logger.warning(
                            "llm_json_invalid",
                            extra={"provider": decision.provider, "stage": request.task.value},
                        )
                        if attempt < LLM_MAX_RETRIES - 1:
                            await asyncio.sleep(0.5 * (2**attempt) + random.uniform(0, 0.25))
                            continue
                        break
                    self.breaker.record_success(decision.provider)
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    logger.info(
                        "llm_ok",
                        extra={
                            "provider": decision.provider,
                            "stage": request.task.value,
                            "duration_ms": latency_ms,
                            "fallback_used": False,
                        },
                    )
                    return AIResult(
                        success=True,
                        provider=decision.provider,
                        model=result.model,
                        output=parsed.model_dump(mode="json"),
                        parsed=parsed,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        latency_ms=latency_ms,
                        retries=retries,
                        message=HIGH_DEMAND_UI_MESSAGE if high_demand else None,
                        prompt_version=prompt_version,
                    )

        parsed = run_fallback(request.task, request.fallback_payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "llm_deterministic_fallback",
            extra={
                "provider": "deterministic",
                "stage": request.task.value,
                "duration_ms": latency_ms,
            },
        )
        output = parsed.model_dump(mode="json") if hasattr(parsed, "model_dump") else None
        return AIResult(
            success=True,
            provider="deterministic",
            model="deterministic",
            output=output,
            parsed=parsed,
            latency_ms=latency_ms,
            fallback_used=True,
            retries=retries,
            message=HIGH_DEMAND_UI_MESSAGE if high_demand else None,
            prompt_version=prompt_version,
        )

    def _post_validate(self, request: AIRequest, parsed: object) -> object:
        if isinstance(parsed, RankedCandidates) and request.known_place_ids is not None:
            allowed = request.known_place_ids
            parsed = RankedCandidates(
                ranked=[item for item in parsed.ranked if item.place_id in allowed]
            )
        crowd = getattr(parsed, "estimates", None)
        if crowd is not None:
            for estimate in crowd:
                live = bool(getattr(estimate, "is_live", False))
                if live and not request.fallback_payload.get("live_crowd"):
                    estimate.is_live = False
        return parsed
