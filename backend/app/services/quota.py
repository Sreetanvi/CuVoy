"""Layer 3 — global free-tier provider quotas. Never escalate to paid (PROJECT_SPEC §7.3, §30)."""

from __future__ import annotations

from datetime import UTC, datetime

from cuvoy_contracts.constants import TTL_CREDITS

from app.services.cache import CacheBackend

# Conservative free-tier caps. Adjust without code that calls paid APIs.
PROVIDER_RPD: dict[str, int] = {
    "gemini": 50,
    "groq": 100,
    "openrouter": 50,
    "mapbox": 1000,
    "overpass": 200,
    "opentripmap": 200,
}


def quota_key(provider: str, day: str | None = None) -> str:
    stamp = day or datetime.now(UTC).date().isoformat()
    return f"quota:{provider}:{stamp}"


async def provider_allowed(cache: CacheBackend, provider: str) -> bool:
    cap = PROVIDER_RPD.get(provider)
    if cap is None:
        return True
    raw = await cache.get(quota_key(provider))
    if raw is None:
        return True
    try:
        return int(raw) < cap
    except ValueError:
        return True


async def hit_provider(cache: CacheBackend, provider: str, amount: int = 1) -> bool:
    """Return False when the free-tier daily cap is exhausted (paid_fallback = NEVER)."""
    cap = PROVIDER_RPD.get(provider)
    if cap is None:
        return True
    count = await cache.incr(quota_key(provider), TTL_CREDITS)
    if count == 0:
        return True
    if count > cap:
        await cache.decr(quota_key(provider))
        return False
    return True
