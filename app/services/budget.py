"""Layer 1 plan credits + Layer 2 per-plan API envelope (PROJECT_SPEC §7.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from cuvoy_contracts.constants import (
    BUDGET_LLM_CALLS,
    BUDGET_MAPBOX_MATRIX,
    BUDGET_MAPBOX_SEARCH,
    BUDGET_OSM,
    BUDGET_VERIFICATION,
    BUDGET_WEATHER,
    PLAN_CREDITS_PER_DAY,
    REGEN_BUDGET_FRACTION,
    TTL_CREDITS,
    TTL_SESSION,
)

from app.services.cache import CacheBackend, cache_get_json, cache_set_json

FULL_ENVELOPE: dict[str, int] = {
    "llm": BUDGET_LLM_CALLS,
    "mapbox_search": BUDGET_MAPBOX_SEARCH,
    "mapbox_matrix": BUDGET_MAPBOX_MATRIX,
    "osm": BUDGET_OSM,
    "weather": BUDGET_WEATHER,
    "verification": BUDGET_VERIFICATION,
}


@dataclass
class CreditResult:
    allowed: bool
    remaining: int
    enforced: bool
    message: str = ""


@dataclass
class PlanBudget:
    plan_id: str
    remaining: dict[str, int] = field(default_factory=lambda: dict(FULL_ENVELOPE))

    def consume(self, category: str, amount: int = 1) -> bool:
        current = self.remaining.get(category, 0)
        if current < amount:
            return False
        self.remaining[category] = current - amount
        return True


def credits_key(identity: str, day: date | None = None) -> str:
    stamp = (day or datetime.now(UTC).date()).isoformat()
    return f"credits:{identity}:{stamp}"


def budget_key(plan_id: str) -> str:
    return f"budget:{plan_id}"


async def consume_credit(cache: CacheBackend, identity: str) -> CreditResult:
    """Increment daily counter. 4th plan is rejected. Cache-down fails open with enforced=False."""
    key = credits_key(identity)
    count = await cache.incr(key, TTL_CREDITS)
    if count == 0:
        return CreditResult(
            allowed=True,
            remaining=PLAN_CREDITS_PER_DAY,
            enforced=False,
            message="Credit counter unavailable; allowing this request",
        )
    if count > PLAN_CREDITS_PER_DAY:
        await cache.decr(key)
        return CreditResult(
            allowed=False,
            remaining=0,
            enforced=True,
            message="3 plans/day limit reached",
        )
    return CreditResult(
        allowed=True,
        remaining=PLAN_CREDITS_PER_DAY - count,
        enforced=True,
    )


async def refund_credit(cache: CacheBackend, identity: str) -> None:
    """Server fault refund (PROJECT_SPEC §7.6)."""
    await cache.decr(credits_key(identity))


def new_envelope(plan_id: str, *, regeneration: bool = False) -> PlanBudget:
    budget = PlanBudget(plan_id=plan_id)
    if regeneration:
        budget.remaining = {
            name: max(1, int(value * REGEN_BUDGET_FRACTION)) if value else 0
            for name, value in FULL_ENVELOPE.items()
        }
    return budget


async def persist_budget(cache: CacheBackend, budget: PlanBudget) -> bool:
    return await cache_set_json(
        cache,
        budget_key(budget.plan_id),
        budget.remaining,
        TTL_SESSION,
    )


async def load_budget(cache: CacheBackend, plan_id: str) -> PlanBudget | None:
    remaining = await cache_get_json(cache, budget_key(plan_id))
    if not isinstance(remaining, dict):
        return None
    cleaned = {str(key): int(value) for key, value in remaining.items()}
    return PlanBudget(plan_id=plan_id, remaining=cleaned)
