"""Mapbox Geocoding v5. Cache 90 days. PROJECT_SPEC §17."""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx
from cuvoy_contracts.constants import TTL_GEOCODING

from app.geo.destinations import PLACE_ALIASES, query_matches_place_name
from app.providers.cache_keys import geocode_key
from app.providers.gates import can_call
from app.providers.http import get_json
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")

DEFAULT_COUNTRY_BIAS = "in"


def _country_code(feature: dict) -> str | None:
    for ctx in feature.get("context") or []:
        if isinstance(ctx, dict) and str(ctx.get("id", "")).startswith("country"):
            raw = ctx.get("short_code") or ctx.get("iso_3166_1")
            return str(raw).upper() if raw else None
    props = feature.get("properties") or {}
    if isinstance(props, dict) and props.get("short_code"):
        return str(props.get("short_code")).upper()
    return None


def _result_from_feature(feature: dict, query: str) -> dict | None:
    center = feature.get("center") or []
    if len(center) < 2:
        return None
    return {
        "lng": float(center[0]),
        "lat": float(center[1]),
        "name": feature.get("place_name") or feature.get("text") or query,
        "country_code": _country_code(feature),
        "text": feature.get("text") or query,
    }


def _match_score(feature: dict, query: str, *, country: str | None) -> int:
    text = str(feature.get("text") or "")
    place_name = str(feature.get("place_name") or text)
    score = 0
    if query_matches_place_name(query, text):
        score += 80
    if query_matches_place_name(query, place_name):
        score += 40
    needle = "".join(ch for ch in query.lower() if ch.isalpha())
    for alias in PLACE_ALIASES.get(needle, ()):
        blob = f"{text} {place_name}".lower()
        if alias in blob.replace(" ", ""):
            score += 50
            break
    types = feature.get("place_type") or []
    if isinstance(types, list) and any(kind in {"place", "locality"} for kind in types):
        score += 15
    if isinstance(types, list) and "poi" in types:
        score -= 20
    if country and (_country_code(feature) or "").lower() == country.lower():
        score += 25
    return score


def pick_geocode_feature(
    features: list,
    query: str,
    *,
    proximity: tuple[float, float] | None = None,
    country: str | None = None,
) -> dict | None:
    parsed = [row for row in features if isinstance(row, dict) and len(row.get("center") or []) >= 2]
    if not parsed:
        return None

    def sort_key(feature: dict) -> tuple[int, float]:
        score = _match_score(feature, query, country=country)
        penalty = 0.0
        if proximity is not None:
            center = feature.get("center") or [0, 0]
            penalty = (float(center[1]) - proximity[0]) ** 2 + (float(center[0]) - proximity[1]) ** 2
        return (-score, penalty)

    ranked = sorted(parsed, key=sort_key)
    best = ranked[0]
    text = str(best.get("text") or "")
    place_name = str(best.get("place_name") or text)
    if not query_matches_place_name(query, text) and not query_matches_place_name(query, place_name):
        return None
    return best


async def _geocode_request(
    http: httpx.AsyncClient,
    token: str,
    search: str,
    *,
    country: str | None,
    proximity: tuple[float, float] | None,
) -> list:
    encoded = quote(search, safe="")
    params: dict[str, str | int] = {
        "access_token": token,
        "limit": 5,
    }
    if proximity is not None:
        params["proximity"] = f"{proximity[1]},{proximity[0]}"
    if country:
        params["country"] = country.lower()
    body = await get_json(
        http,
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json",
        params=params,
        timeout=10.0,
        provider="mapbox",
    )
    if not isinstance(body, dict):
        return []
    return list(body.get("features") or [])


async def geocode(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    token: str,
    query: str,
    *,
    budget: PlanBudget | None = None,
    proximity: tuple[float, float] | None = None,
    country: str | None = None,
) -> dict | None:
    """Return {lat, lng, name, country_code} or None. Short names are biased to India."""
    bias = (country or DEFAULT_COUNTRY_BIAS).lower()
    key = geocode_key(query, bias)
    cached = await cache_get_json(cache, key)
    if isinstance(cached, dict) and "lat" in cached:
        logger.info("mapbox_geocode", extra={"provider": "mapbox", "cache_hit": True})
        return cached
    if not token:
        return None
    if not await can_call(cache, budget, envelope="mapbox_search", quota_name="mapbox"):
        return cached if isinstance(cached, dict) else None

    searches = [query]
    if bias == "in" and "," not in query:
        searches = [f"{query}, India", query]

    feature = None
    used_country: str | None = bias
    for search in searches:
        rows = await _geocode_request(http, token, search, country=bias, proximity=proximity)
        feature = pick_geocode_feature(rows, query, proximity=proximity, country=bias)
        if feature is not None:
            break
    if feature is None and country is None:
        used_country = None
        rows = await _geocode_request(http, token, query, country=None, proximity=proximity)
        feature = pick_geocode_feature(rows, query, proximity=proximity, country=None)

    if feature is None:
        return None
    result = _result_from_feature(feature, query)
    if result is None:
        return None
    if used_country and not query_matches_place_name(query, str(result.get("name") or result.get("text") or "")):
        return None
    await cache_set_json(cache, key, result, TTL_GEOCODING)
    logger.info("mapbox_geocode", extra={"provider": "mapbox", "cache_hit": False})
    return result
