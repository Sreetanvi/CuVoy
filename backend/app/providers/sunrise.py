"""Sunrise-Sunset.org. PROJECT_SPEC §15."""

from __future__ import annotations

import logging
from datetime import date

import httpx
from cuvoy_contracts.constants import TTL_CREDITS

from app.providers.cache_keys import sunrise_key
from app.providers.http import get_json
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")


async def sunrise_sunset(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    lat: float,
    lng: float,
    day: date,
) -> dict | None:
    key = sunrise_key(lat, lng, day.isoformat())
    cached = await cache_get_json(cache, key)
    if isinstance(cached, dict):
        logger.info("sunrise", extra={"provider": "sunrise", "cache_hit": True})
        return cached
    body = await get_json(
        http,
        "https://api.sunrise-sunset.org/json",
        params={
            "lat": lat,
            "lng": lng,
            "date": day.isoformat(),
            "formatted": 0,
        },
        timeout=8.0,
        provider="sunrise",
    )
    if not isinstance(body, dict) or body.get("status") != "OK":
        return None
    results = body.get("results") or {}
    slim = {
        "sunrise": results.get("sunrise"),
        "sunset": results.get("sunset"),
        "day_length": results.get("day_length"),
    }
    await cache_set_json(cache, key, slim, TTL_CREDITS)
    logger.info("sunrise", extra={"provider": "sunrise", "cache_hit": False})
    return slim
