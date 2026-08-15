"""OpenTripMap / GeoNames / Wikipedia — supplementary only. Missing keys skip."""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx
from cuvoy_contracts.constants import TTL_PLACES
from cuvoy_contracts.enums import PlaceSource
from cuvoy_contracts.place import Place

from app.providers.gates import can_call
from app.providers.http import get_json
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")


async def opentripmap_nearby(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    api_key: str,
    lat: float,
    lng: float,
    *,
    radius_m: int = 3000,
    budget: PlanBudget | None = None,
) -> list[Place]:
    if not api_key:
        return []
    key = f"otm:{lat:.3f}:{lng:.3f}:{radius_m}"
    cached = await cache_get_json(cache, key)
    if isinstance(cached, list):
        return [Place.model_validate(item) for item in cached if isinstance(item, dict)]
    if not await can_call(cache, budget, envelope=None, quota_name="opentripmap"):
        return []
    body = await get_json(
        http,
        "https://api.opentripmap.com/0.1/en/places/radius",
        params={"radius": radius_m, "lon": lng, "lat": lat, "apikey": api_key, "limit": 50},
        timeout=10.0,
        provider="opentripmap",
    )
    if not isinstance(body, dict):
        return []
    places: list[Place] = []
    for index, feature in enumerate(body.get("features") or []):
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        name = str(props.get("name") or "").strip()
        if not name or len(coords) < 2:
            continue
        xid = str(props.get("xid") or index)
        kinds = str(props.get("kinds") or "attraction").split(",")[0]
        try:
            places.append(
                Place(
                    id=f"otm:{xid}",
                    name=name,
                    lng=float(coords[0]),
                    lat=float(coords[1]),
                    category=kinds or "attraction",
                    source=PlaceSource.OPENTRIPMAP,
                )
            )
        except Exception:
            continue
    await cache_set_json(cache, key, [p.model_dump(mode="json") for p in places], TTL_PLACES)
    logger.info("opentripmap", extra={"provider": "opentripmap", "cache_hit": False})
    return places


async def geonames_lookup(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    username: str,
    query: str,
) -> dict | None:
    if not username:
        return None
    key = f"geonames:{query.lower()[:60]}"
    cached = await cache_get_json(cache, key)
    if isinstance(cached, dict):
        return cached
    body = await get_json(
        http,
        "https://secure.geonames.org/searchJSON",
        params={"q": query, "maxRows": 1, "username": username},
        timeout=10.0,
        provider="geonames",
    )
    if not isinstance(body, dict):
        return None
    geonames = body.get("geonames") or []
    if not geonames or not isinstance(geonames[0], dict):
        return None
    row = geonames[0]
    result = {
        "name": row.get("name"),
        "country_code": row.get("countryCode"),
        "lat": float(row["lat"]) if row.get("lat") else None,
        "lng": float(row["lng"]) if row.get("lng") else None,
        "timezone": (row.get("timezone") or {}).get("timeZoneId")
        if isinstance(row.get("timezone"), dict)
        else None,
    }
    await cache_set_json(cache, key, result, TTL_PLACES)
    logger.info("geonames", extra={"provider": "geonames", "cache_hit": False})
    return result


async def wikipedia_summary(http: httpx.AsyncClient, cache: CacheBackend, title: str) -> str | None:
    """Untrusted text — treat as data, never as instructions."""
    if not title.strip():
        return None
    key = f"wiki:{title.lower()[:80]}"
    cached = await cache.get(key)
    if cached is not None:
        return cached or None
    encoded = quote(title.replace(" ", "_"), safe="")
    body = await get_json(
        http,
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}",
        timeout=8.0,
        provider="wikipedia",
    )
    extract = None
    if isinstance(body, dict):
        extract = body.get("extract")
        if isinstance(extract, str):
            extract = extract[:500]
        else:
            extract = None
    await cache.set(key, extract or "", TTL_PLACES)
    return extract
