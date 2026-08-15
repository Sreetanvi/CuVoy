"""Budget + quota gates. Cache hits do not consume the per-plan envelope."""

from __future__ import annotations

from app.services.budget import PlanBudget
from app.services.cache import CacheBackend
from app.services.quota import hit_provider, provider_allowed


async def can_call(
    cache: CacheBackend,
    budget: PlanBudget | None,
    *,
    envelope: str | None,
    quota_name: str | None,
) -> bool:
    if budget is not None and envelope is not None and not budget.consume(envelope):
        return False
    if quota_name is None:
        return True
    if not await provider_allowed(cache, quota_name):
        if budget is not None and envelope is not None:
            budget.remaining[envelope] = budget.remaining.get(envelope, 0) + 1
        return False
    if not await hit_provider(cache, quota_name):
        if budget is not None and envelope is not None:
            budget.remaining[envelope] = budget.remaining.get(envelope, 0) + 1
        return False
    return True
