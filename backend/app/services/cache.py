"""Cache backends. Production uses Upstash REST only — no in-process Redis.

See PROJECT_SPEC §17 and §31.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from cuvoy_contracts.constants import MAX_CACHE_PAYLOAD_BYTES

logger = logging.getLogger("cuvoy.cache")


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> bool: ...
    async def delete(self, key: str) -> bool: ...
    async def incr(self, key: str, ttl_seconds: int) -> int: ...
    async def decr(self, key: str) -> int: ...
    async def mget(self, keys: list[str]) -> list[str | None]: ...
    async def ping(self) -> bool: ...


class NullCache:
    """Used when Upstash is unset. Cache failure never breaks generation."""

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> bool:
        return False

    async def delete(self, key: str) -> bool:
        return False

    async def incr(self, key: str, ttl_seconds: int) -> int:
        return 0

    async def decr(self, key: str) -> int:
        return 0

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [None] * len(keys)

    async def ping(self) -> bool:
        return False


class InMemoryCache:
    """Test-only. Never used on Render (512 MB)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}

    def _read(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expires = item
        if expires is not None and expires < time.time():
            del self._store[key]
            return None
        return value

    async def get(self, key: str) -> str | None:
        return self._read(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> bool:
        expires = time.time() + ttl_seconds if ttl_seconds > 0 else None
        self._store[key] = (value, expires)
        return True

    async def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        return True

    async def incr(self, key: str, ttl_seconds: int) -> int:
        current = self._read(key)
        next_value = int(current or 0) + 1
        expires = None
        existing = self._store.get(key)
        if existing and existing[1] is not None:
            expires = existing[1]
        elif ttl_seconds > 0:
            expires = time.time() + ttl_seconds
        self._store[key] = (str(next_value), expires)
        return next_value

    async def decr(self, key: str) -> int:
        current = int(self._read(key) or 0)
        next_value = max(current - 1, 0)
        existing = self._store.get(key)
        expires = existing[1] if existing else None
        self._store[key] = (str(next_value), expires)
        return next_value

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [self._read(key) for key in keys]

    async def ping(self) -> bool:
        return True


class UpstashCache:
    """Official Upstash REST client (POST /pipeline, GET /ping) — never POST the root URL."""

    def __init__(self, url: str, token: str, redis: Any | None = None) -> None:
        from upstash_redis.asyncio import Redis

        self._redis = redis or Redis(url=url.rstrip("/"), token=token)

    def _as_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def get(self, key: str) -> str | None:
        try:
            return self._as_str(await self._redis.get(key))
        except Exception as exc:
            logger.warning("upstash_get_failed", extra={"provider": "upstash", "error": str(exc)})
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> bool:
        encoded = value.encode("utf-8")
        if len(encoded) > MAX_CACHE_PAYLOAD_BYTES:
            logger.warning(
                "cache_payload_skipped",
                extra={"provider": "upstash", "size": len(encoded)},
            )
            return False
        try:
            if ttl_seconds > 0:
                await self._redis.set(key, value, ex=ttl_seconds)
            else:
                await self._redis.set(key, value)
            return True
        except Exception as exc:
            logger.warning("upstash_set_failed", extra={"provider": "upstash", "error": str(exc)})
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self._redis.delete(key)
            return True
        except Exception as exc:
            logger.warning(
                "upstash_delete_failed",
                extra={"provider": "upstash", "error": str(exc)},
            )
            return False

    async def incr(self, key: str, ttl_seconds: int) -> int:
        try:
            count = int(await self._redis.incr(key))
            if count == 1 and ttl_seconds > 0:
                await self._redis.expire(key, ttl_seconds)
            return count
        except Exception as exc:
            logger.warning("upstash_incr_failed", extra={"provider": "upstash", "error": str(exc)})
            return 0

    async def decr(self, key: str) -> int:
        try:
            return int(await self._redis.decr(key))
        except Exception as exc:
            logger.warning("upstash_decr_failed", extra={"provider": "upstash", "error": str(exc)})
            return 0

    async def mget(self, keys: list[str]) -> list[str | None]:
        if not keys:
            return []
        try:
            raw = await self._redis.mget(*keys)
        except Exception as exc:
            logger.warning("upstash_mget_failed", extra={"provider": "upstash", "error": str(exc)})
            return [None] * len(keys)
        if not isinstance(raw, list):
            return [None] * len(keys)
        return [self._as_str(item) for item in raw]

    async def ping(self) -> bool:
        try:
            result = await self._redis.ping()
        except Exception as exc:
            logger.warning("upstash_ping_failed", extra={"provider": "upstash", "error": str(exc)})
            return False
        if result is True:
            return True
        return str(result).upper() == "PONG"


async def cache_get_json(cache: CacheBackend, key: str) -> Any | None:
    raw = await cache.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("cache_json_invalid", extra={"cache_hit": False})
        return None


async def cache_set_json(cache: CacheBackend, key: str, value: Any, ttl_seconds: int) -> bool:
    try:
        payload = json.dumps(value, separators=(",", ":"), default=str)
    except (TypeError, ValueError) as exc:
        logger.warning("cache_json_encode_failed", extra={"error": str(exc)})
        return False
    return await cache.set(key, payload, ttl_seconds)
