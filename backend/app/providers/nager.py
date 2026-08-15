"""Nager.Date public holidays. Cache 30 days. PROJECT_SPEC §17."""

from __future__ import annotations

import logging

import httpx
from cuvoy_contracts.constants import TTL_HOLIDAYS

from app.providers.cache_keys import holidays_key
from app.providers.http import get_json
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")


async def public_holidays(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    country_code: str,
    year: int,
) -> list[dict]:
    if not country_code:
        return []
    key = holidays_key(country_code, year)
    cached = await cache_get_json(cache, key)
    if isinstance(cached, list):
        logger.info("nager", extra={"provider": "nager", "cache_hit": True})
        return cached
    body = await get_json(
        http,
        f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code.upper()}",
        timeout=10.0,
        provider="nager",
    )
    if not isinstance(body, list):
        return []
    slim = [
        {"date": item.get("date"), "name": item.get("name"), "localName": item.get("localName")}
        for item in body
        if isinstance(item, dict)
    ]
    await cache_set_json(cache, key, slim, TTL_HOLIDAYS)
    logger.info("nager", extra={"provider": "nager", "cache_hit": False})
    return slim
