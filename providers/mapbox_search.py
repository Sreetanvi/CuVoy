"""Mapbox Search Box (POI discovery). Cache 30 days. PROJECT_SPEC §8, §17."""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx
from cuvoy_contracts.constants import TTL_PLACES
from cuvoy_contracts.enums import PlaceSource
from cuvoy_contracts.place import Place

from app.providers.cache_keys import places_key
from app.providers.gates import can_call
from app.providers.http import get_json
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")

SEARCH_URL = "https://api.mapbox.com/search/searchbox/v1/forward"


def _place_from_searchbox(feature: dict, index: int) -> Place | None:
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if len(coords) < 2:
        return None
    name = str(props.get("name") or "").strip()
    if not name:
        return None
    categories = props.get("poi_category") or props.get("category") or []
    if isinstance(categories, str):
        category = categories.split(",")[0].strip() or "poi"
    elif isinstance(categories, list) and categories:
        category = str(categories[0])
    else:
        category = str(props.get("feature_type") or "poi")
    mapbox_id = str(props.get("mapbox_id") or feature.get("id") or f"mapbox-{index}")
    return Place(
        id=f"mapbox:{mapbox_id}",
        name=name,
        lng=float(coords[0]),
        lat=float(coords[1]),
        category=category,
        address=props.get("full_address") or props.get("place_formatted"),
        source=PlaceSource.MAPBOX,
    )


def _place_from_geocoding(feature: dict, index: int) -> Place | None:
    center = feature.get("center") or []
    if len(center) < 2:
        return None
    name = str(feature.get("text") or "").strip()
    if not name:
        return None
    props = feature.get("properties") or {}
    place_types = feature.get("place_type") or ["poi"]
    category = str(props.get("category") or place_types[0])
    fid = str(feature.get("id") or f"geocode-{index}")
    return Place(
        id=f"mapbox:{fid}",
        name=name,
        lng=float(center[0]),
        lat=float(center[1]),
        category=category.split(",")[0].strip() or "poi",
        address=feature.get("place_name"),
        source=PlaceSource.MAPBOX,
    )


def dump_places(places: list[Place]) -> list[dict]:
    return [place.model_dump(mode="json") for place in places]


def load_places(raw: object) -> list[Place]:
    if not isinstance(raw, list):
        return []
    places: list[Place] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            places.append(Place.model_validate(item))
        except Exception:
            continue
    return places


async def search_places(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    token: str,
    query: str,
    *,
    proximity: tuple[float, float] | None = None,
    limit: int = 10,
    budget: PlanBudget | None = None,
) -> list[Place]:
    lng = proximity[1] if proximity else None
    lat = proximity[0] if proximity else None
    key = places_key(query, lng, lat)
    cached = await cache_get_json(cache, key)
    if cached is not None:
        logger.info("mapbox_search", extra={"provider": "mapbox", "cache_hit": True})
        return load_places(cached)
    if not token:
        return []
    if not await can_call(cache, budget, envelope="mapbox_search", quota_name="mapbox"):
        return []

    params: dict[str, str | int] = {
        "q": query,
        "access_token": token,
        "limit": max(1, min(limit, 10)),
        "language": "en",
    }
    if proximity is not None:
        params["proximity"] = f"{proximity[1]},{proximity[0]}"
    body = await get_json(http, SEARCH_URL, params=params, timeout=10.0, provider="mapbox")
    places: list[Place] = []
    if isinstance(body, dict):
        for index, feature in enumerate(body.get("features") or []):
            if isinstance(feature, dict):
                parsed = _place_from_searchbox(feature, index)
                if parsed is not None:
                    places.append(parsed)
    if not places:
        encoded = quote(query, safe="")
        geo = await get_json(
            http,
            f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json",
            params={"access_token": token, "limit": limit, "types": "poi"},
            timeout=10.0,
            provider="mapbox",
        )
        if isinstance(geo, dict):
            for index, feature in enumerate(geo.get("features") or []):
                if isinstance(feature, dict):
                    parsed = _place_from_geocoding(feature, index)
                    if parsed is not None:
                        places.append(parsed)

    await cache_set_json(cache, key, dump_places(places), TTL_PLACES)
    logger.info("mapbox_search", extra={"provider": "mapbox", "cache_hit": False})
    return places
