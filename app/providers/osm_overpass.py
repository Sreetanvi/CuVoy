"""One Overpass query per city/region — never per attraction. PROJECT_SPEC §8, §31."""

from __future__ import annotations

import gzip
import json
import logging
from base64 import b64decode, b64encode

import httpx
from cuvoy_contracts.constants import (
    MAX_CACHE_PAYLOAD_BYTES,
    OVERPASS_TIMEOUT_SECONDS,
    TTL_OSM_POI,
)
from cuvoy_contracts.enums import PlaceSource
from cuvoy_contracts.place import Place

from app.providers.cache_keys import osm_key
from app.providers.gates import can_call
from app.providers.http import post_text
from app.providers.osm_filters import (
    OVERPASS_AMENITY,
    OVERPASS_EXCLUDE,
    is_allowlisted_tags,
    osm_display_name,
    should_drop_candidate,
)
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend

logger = logging.getLogger("cuvoy.providers")

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

def overpass_ql(south: float, west: float, north: float, east: float) -> str:
    """Named tourism / historic / leisure / natural / allowlisted amenity only."""
    bbox = f"{south},{west},{north},{east}"
    named = '["name"]'
    return (
        f"[out:json][timeout:25];("
        f'nwr["tourism"]{named}{OVERPASS_EXCLUDE}({bbox});'
        f'nwr["historic"]{named}{OVERPASS_EXCLUDE}({bbox});'
        f'nwr["leisure"]{named}{OVERPASS_EXCLUDE}({bbox});'
        f'nwr["natural"]{named}{OVERPASS_EXCLUDE}({bbox});'
        f'nwr["amenity"~"{OVERPASS_AMENITY}"]{named}{OVERPASS_EXCLUDE}({bbox});'
        f");out center tags;"
    )


def _category(tags: dict) -> str:
    if tags.get("tourism"):
        return str(tags["tourism"])
    if tags.get("amenity"):
        return str(tags["amenity"])
    if tags.get("leisure"):
        return str(tags["leisure"])
    if tags.get("historic"):
        return f"historic:{tags['historic']}" if tags["historic"] != "yes" else "historic"
    if tags.get("natural"):
        return str(tags["natural"])
    return "poi"


def _coords(element: dict) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def normalize_overpass(payload: dict) -> list[Place]:
    """Filter, normalize, dedupe. Never pass raw Overpass JSON to cache/LLM."""
    seen: set[str] = set()
    places: list[Place] = []
    for element in payload.get("elements") or []:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        if not is_allowlisted_tags(tags):
            continue
        name = osm_display_name(tags)
        if not name:
            continue
        category = _category(tags)
        address = tags.get("addr:full") or tags.get("addr:street")
        description = tags.get("description") or tags.get("note")
        if should_drop_candidate(
            name,
            category,
            description=str(description) if description else None,
            address=str(address) if address else None,
            tags=tags,
        ):
            continue
        coords = _coords(element)
        if coords is None:
            continue
        lat, lng = coords
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        osm_id = f"osm:{element.get('type', 'node')}/{element.get('id')}"
        geo_key = f"{name.lower()}|{round(lat, 5)}|{round(lng, 5)}"
        if osm_id in seen or geo_key in seen:
            continue
        seen.add(osm_id)
        seen.add(geo_key)
        hours = tags.get("opening_hours")
        website = tags.get("website") or tags.get("contact:website")
        phone = tags.get("phone") or tags.get("contact:phone")
        try:
            places.append(
                Place(
                    id=osm_id,
                    name=name,
                    lat=lat,
                    lng=lng,
                    category=category,
                    opening_hours=str(hours) if hours else None,
                    website=str(website) if website else None,
                    phone=str(phone) if phone else None,
                    address=str(address) if address else None,
                    source=PlaceSource.OSM,
                )
            )
        except Exception:
            continue
    return places


def _pack(places: list[Place]) -> str:
    raw = json.dumps([p.model_dump(mode="json") for p in places], separators=(",", ":"))
    if len(raw.encode()) <= 40_000:
        return raw
    compressed = b64encode(gzip.compress(raw.encode("utf-8"))).decode("ascii")
    return "gz:" + compressed


def _unpack(raw: str) -> list[Place]:
    text = raw
    if raw.startswith("gz:"):
        text = gzip.decompress(b64decode(raw[3:])).decode("utf-8")
    data = json.loads(text)
    if not isinstance(data, list):
        return []
    places: list[Place] = []
    for item in data:
        if isinstance(item, dict):
            try:
                places.append(Place.model_validate(item))
            except Exception:
                continue
    return places


async def _store_partitioned(cache: CacheBackend, city: str, places: list[Place]) -> None:
    packed = _pack(places)
    if len(packed.encode()) <= MAX_CACHE_PAYLOAD_BYTES:
        await cache.set(osm_key(city, "all"), packed, TTL_OSM_POI)
        return
    by_cat: dict[str, list[Place]] = {}
    for place in places:
        by_cat.setdefault(place.category, []).append(place)
    index = list(by_cat)
    for category, group in by_cat.items():
        await cache.set(osm_key(city, category), _pack(group), TTL_OSM_POI)
    await cache.set(osm_key(city, "_index"), json.dumps(index), TTL_OSM_POI)


async def _load_cached(cache: CacheBackend, city: str) -> list[Place] | None:
    all_raw = await cache.get(osm_key(city, "all"))
    if all_raw:
        return _unpack(all_raw)
    index_raw = await cache.get(osm_key(city, "_index"))
    if not index_raw:
        return None
    try:
        names = json.loads(index_raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(names, list):
        return None
    combined: list[Place] = []
    for name in names:
        part = await cache.get(osm_key(city, str(name)))
        if part:
            combined.extend(_unpack(part))
    return combined or None


async def fetch_city_pois(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    city: str,
    bbox: tuple[float, float, float, float],
    *,
    budget: PlanBudget | None = None,
) -> list[Place]:
    """Single city/region batch. `bbox` is (south, west, north, east)."""
    cached = await _load_cached(cache, city)
    if cached is not None:
        logger.info("osm_batch", extra={"provider": "overpass", "cache_hit": True})
        return cached
    if not await can_call(cache, budget, envelope="osm", quota_name="overpass"):
        return []

    query = overpass_ql(*bbox)
    payload = None
    for url in OVERPASS_URLS:
        payload = await post_text(
            http,
            url,
            content=query,
            timeout=OVERPASS_TIMEOUT_SECONDS,
            provider="overpass",
        )
        if isinstance(payload, dict):
            break
    if not isinstance(payload, dict):
        logger.warning("osm_batch_failed", extra={"provider": "overpass", "cache_hit": False})
        return []
    places = normalize_overpass(payload)
    await _store_partitioned(cache, city, places)
    logger.info("osm_batch", extra={"provider": "overpass", "cache_hit": False})
    return places
