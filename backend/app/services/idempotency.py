"""Idempotency keys — one credit and one pipeline run per key (PROJECT_SPEC §7.14)."""

from __future__ import annotations

from typing import Any

from cuvoy_contracts.constants import TTL_IDEMPOTENCY

from app.services.cache import CacheBackend, cache_get_json, cache_set_json

_IN_FLIGHT = {"status": "in_flight"}


def idempotency_key(raw: str) -> str:
    return f"idempotency:{raw}"


def regen_idempotency_key(plan_id: str, change_hash: str) -> str:
    return f"idempotency:{plan_id}:{change_hash}"


async def begin(cache: CacheBackend, raw_key: str) -> dict[str, Any] | None:
    """Return a cached body if this key already completed. Mark in-flight on miss."""
    key = idempotency_key(raw_key)
    existing = await cache_get_json(cache, key)
    if isinstance(existing, dict):
        return existing
    await cache_set_json(cache, key, _IN_FLIGHT, TTL_IDEMPOTENCY)
    return None


async def store_result(cache: CacheBackend, raw_key: str, body: dict[str, Any]) -> bool:
    payload = {**body, "status": "complete"}
    return await cache_set_json(cache, idempotency_key(raw_key), payload, TTL_IDEMPOTENCY)


async def clear(cache: CacheBackend, raw_key: str) -> None:
    await cache.delete(idempotency_key(raw_key))
