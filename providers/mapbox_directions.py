"""Mapbox Directions — road geometry after OR-Tools order. PROJECT_SPEC §27, §33."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx
from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES, TTL_DIRECTIONS
from cuvoy_contracts.enums import TransportMode

from app.providers.cache_keys import directions_key
from app.providers.geo import haversine_m
from app.providers.http import get_json
from app.providers.mapbox_matrix import mapbox_profile
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")

DIRECTIONS_MAX_COORDINATES = MAX_MATRIX_COORDINATES  # Mapbox driving/walking cap
# Walking Directions often fails beyond a few km; snap those legs to driving roads.
DRIVE_IF_FARTHER_THAN_M = 8_000


@dataclass
class SnappedLeg:
    geometry: str | None
    duration_seconds: int = 0
    distance_meters: int = 0
    snapped: bool = False


@dataclass
class DirectionsResult:
    geometry: str | None
    duration_seconds: int
    distance_meters: int
    cache_hit: bool
    legs: list[SnappedLeg] = field(default_factory=list)


def _open_lng_lat(coords: list[tuple[float, float]]) -> list[list[float]]:
    """`(lat, lng)` waypoints → open GeoJSON LineString coordinates. Never closes."""
    line: list[list[float]] = []
    for lat, lng in coords:
        try:
            point = [float(lng), float(lat)]
        except (TypeError, ValueError):
            continue
        if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            continue
        if not line or line[-1] != point:
            line.append(point)
    if len(line) >= 2 and line[0] == line[-1]:
        line.pop()
    return line


def _geojson_line(line: list[list[float]]) -> str | None:
    if len(line) < 2:
        return None
    if line[0] == line[-1]:
        line = line[:-1]
    if len(line) < 2:
        return None
    return json.dumps({"type": "LineString", "coordinates": line}, separators=(",", ":"))


def straight_line_geojson(coords: list[tuple[float, float]]) -> str | None:
    """Crow-flies fallback LineString (open)."""
    return _geojson_line(_open_lng_lat(coords))


def _coords_from_pairs(raw: list) -> list[list[float]]:
    line: list[list[float]] = []
    for pair in raw:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        try:
            point = [float(pair[0]), float(pair[1])]
        except (TypeError, ValueError):
            continue
        if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            continue
        if not line or line[-1] != point:
            line.append(point)
    if len(line) >= 2 and line[0] == line[-1]:
        line.pop()
    return line


def _coords_from_route(route: dict) -> list[list[float]]:
    geometry = route.get("geometry")
    raw: list | None = None
    if isinstance(geometry, dict):
        raw = geometry.get("coordinates")
    elif isinstance(geometry, list):
        raw = geometry
    if not isinstance(raw, list):
        return []
    return _coords_from_pairs(raw)


def _coords_from_geojson(raw: str | None) -> list[list[float]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, dict):
        return []
    coords = parsed.get("coordinates")
    if not isinstance(coords, list):
        return []
    return _coords_from_pairs(coords)


def _extend_line(line: list[list[float]], extra: list[list[float]]) -> None:
    for point in extra:
        if not line or line[-1] != point:
            line.append(point)


def _profile_for_leg(profile: str, origin: tuple[float, float], dest: tuple[float, float]) -> str:
    if profile == "driving":
        return profile
    try:
        meters = haversine_m(origin[0], origin[1], dest[0], dest[1])
    except Exception:
        return profile
    if meters >= DRIVE_IF_FARTHER_THAN_M:
        return "driving"
    return profile


async def _fetch_leg(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    token: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
    *,
    profile: str,
    budget: PlanBudget | None = None,
) -> tuple[list[list[float]] | None, int, int, bool]:
    """One Mapbox call for origin → dest. None coords means the caller should draw a straight leg."""
    del budget  # Directions must not share the 3-call matrix envelope.
    used_profile = _profile_for_leg(profile, origin, dest)
    pair = [origin, dest]
    key = directions_key(used_profile, pair)
    try:
        cached = await cache_get_json(cache, key)
    except Exception:
        cached = None
    if isinstance(cached, dict) and cached.get("geometry"):
        snapped = _coords_from_geojson(str(cached.get("geometry")))
        if len(snapped) >= 2:
            logger.info("mapbox_directions_leg", extra={"provider": "mapbox", "cache_hit": True})
            return (
                snapped,
                int(cached.get("duration_seconds") or 0),
                int(cached.get("distance_meters") or 0),
                True,
            )

    if not token:
        return None, 0, 0, False

    path = ";".join(f"{lng},{lat}" for lat, lng in pair)
    url = f"https://api.mapbox.com/directions/v5/mapbox/{used_profile}/{path}"
    try:
        body = await get_json(
            http,
            url,
            params={
                "access_token": token,
                "geometries": "geojson",
                "overview": "full",
            },
            timeout=15.0,
            provider="mapbox",
        )
    except Exception:
        logger.warning("mapbox_directions_leg_failed", extra={"provider": "mapbox", "cache_hit": False})
        return None, 0, 0, False

    if not isinstance(body, dict) or not (body.get("routes") or []):
        logger.warning("mapbox_directions_leg_failed", extra={"provider": "mapbox", "cache_hit": False})
        return None, 0, 0, False
    route = body["routes"][0]
    if not isinstance(route, dict):
        return None, 0, 0, False
    snapped = _coords_from_route(route)
    geometry = _geojson_line(snapped)
    if not geometry:
        logger.warning("mapbox_directions_leg_failed", extra={"provider": "mapbox", "cache_hit": False})
        return None, 0, 0, False
    result = {
        "geometry": geometry,
        "duration_seconds": int(route.get("duration") or 0),
        "distance_meters": int(route.get("distance") or 0),
    }
    try:
        await cache_set_json(cache, key, result, TTL_DIRECTIONS)
    except Exception:
        pass
    logger.info("mapbox_directions_leg", extra={"provider": "mapbox", "cache_hit": False})
    return snapped, result["duration_seconds"], result["distance_meters"], False


async def directions(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    token: str,
    coords: list[tuple[float, float]],
    *,
    mode: TransportMode = TransportMode.WALKING,
    budget: PlanBudget | None = None,
) -> DirectionsResult:
    """
    Mapbox Directions v5 after visit order is known.

    Fetches each consecutive pair (A→B, B→C, …) separately so one un-routable
    stop does not drop the whole day to crow-flies. Successful legs keep road
    geometry; only an explicit API failure falls back to a straight segment.
    `geometries=geojson&overview=full`. At most 25 waypoints.
    """
    profile = mapbox_profile(mode)
    waypoints = list(coords[:DIRECTIONS_MAX_COORDINATES])
    fallback = straight_line_geojson(waypoints)
    empty = DirectionsResult(
        geometry=fallback, duration_seconds=0, distance_meters=0, cache_hit=False, legs=[]
    )
    if len(waypoints) < 2:
        return empty

    line: list[list[float]] = []
    duration_seconds = 0
    distance_meters = 0
    cache_hits = 0
    snapped_legs: list[SnappedLeg] = []

    for origin, dest in zip(waypoints, waypoints[1:]):
        snapped, duration, distance, hit = await _fetch_leg(
            http,
            cache,
            token,
            origin,
            dest,
            profile=profile,
            budget=budget,
        )
        if snapped and len(snapped) >= 2:
            _extend_line(line, snapped)
            duration_seconds += duration
            distance_meters += distance
            if hit:
                cache_hits += 1
            snapped_legs.append(
                SnappedLeg(
                    geometry=_geojson_line(snapped),
                    duration_seconds=duration,
                    distance_meters=distance,
                    snapped=True,
                )
            )
            continue
        straight = _open_lng_lat([origin, dest])
        _extend_line(line, straight)
        snapped_legs.append(
            SnappedLeg(geometry=_geojson_line(straight), snapped=False)
        )

    geometry = _geojson_line(line) or fallback
    logger.info(
        "mapbox_directions",
        extra={
            "provider": "mapbox",
            "cache_hit": len(snapped_legs) > 0 and cache_hits == len(snapped_legs),
            "legs": len(snapped_legs),
        },
    )
    return DirectionsResult(
        geometry=geometry,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        cache_hit=len(snapped_legs) > 0 and cache_hits == len(snapped_legs),
        legs=snapped_legs,
    )


async def get_road_snapped_route(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    token: str,
    coords: list[tuple[float, float]],
    *,
    mode: TransportMode = TransportMode.WALKING,
    budget: PlanBudget | None = None,
) -> DirectionsResult:
    """Alias used by the scheduler for every intra-city and inter-city leg."""
    return await directions(http, cache, token, coords, mode=mode, budget=budget)
