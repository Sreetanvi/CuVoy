"""Mapbox Matrix. Reduced set only (≤25). PROJECT_SPEC §33."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES, TTL_MATRIX
from cuvoy_contracts.enums import TransportMode

from app.providers.cache_keys import matrix_key
from app.providers.gates import can_call
from app.providers.geo import duration_seconds, haversine_m
from app.providers.http import get_json
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")

PROFILE = {
    TransportMode.WALKING: "walking",
    TransportMode.BICYCLE: "cycling",
    TransportMode.BIKE: "cycling",
    TransportMode.CAR: "driving",
    TransportMode.CAMPER: "driving",
    TransportMode.TAXI: "driving",
    TransportMode.METRO: "driving",
    TransportMode.BUS: "driving",
    TransportMode.MIXED: "driving",
}


@dataclass
class TravelMatrix:
    durations: list[list[int]]
    distances: list[list[int]]
    approximate: bool
    cache_hit: bool
    profile: str


def mapbox_profile(mode: TransportMode) -> str:
    return PROFILE.get(mode, "driving")


def haversine_matrix(coords: list[tuple[float, float]], profile: str) -> TravelMatrix:
    n = len(coords)
    durations = [[0] * n for _ in range(n)]
    distances = [[0] * n for _ in range(n)]
    for i, (lat1, lng1) in enumerate(coords):
        for j, (lat2, lng2) in enumerate(coords):
            if i == j:
                continue
            meters = haversine_m(lat1, lng1, lat2, lng2)
            distances[i][j] = int(meters)
            durations[i][j] = duration_seconds(meters, profile)
    return TravelMatrix(
        durations=durations,
        distances=distances,
        approximate=True,
        cache_hit=False,
        profile=profile,
    )


def _parse_matrix(body: dict, n: int, profile: str, cache_hit: bool) -> TravelMatrix | None:
    raw_d = body.get("durations")
    raw_m = body.get("distances")
    if not isinstance(raw_d, list) or len(raw_d) != n:
        return None
    durations: list[list[int]] = []
    distances: list[list[int]] = []
    for i, row in enumerate(raw_d):
        if not isinstance(row, list) or len(row) != n:
            return None
        durations.append([int(x or 0) for x in row])
        if isinstance(raw_m, list) and i < len(raw_m) and isinstance(raw_m[i], list):
            distances.append([int(x or 0) for x in raw_m[i]])
        else:
            distances.append([0] * n)
    return TravelMatrix(
        durations=durations,
        distances=distances,
        approximate=False,
        cache_hit=cache_hit,
        profile=profile,
    )


async def travel_matrix(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    token: str,
    coords: list[tuple[float, float]],
    *,
    mode: TransportMode = TransportMode.WALKING,
    budget: PlanBudget | None = None,
) -> TravelMatrix:
    profile = mapbox_profile(mode)
    n = len(coords)
    if n < 2:
        zero = [[0] * n for _ in range(n)]
        return TravelMatrix(
            durations=zero,
            distances=zero,
            approximate=False,
            cache_hit=True,
            profile=profile,
        )
    if len(coords) > MAX_MATRIX_COORDINATES:
        logger.warning("matrix_too_large", extra={"provider": "mapbox"})
        return haversine_matrix(coords, profile)

    key = matrix_key(profile, coords)
    cached = await cache_get_json(cache, key)
    if isinstance(cached, dict):
        parsed = _parse_matrix(cached, len(coords), profile, cache_hit=True)
        if parsed is not None:
            logger.info("mapbox_matrix", extra={"provider": "mapbox", "cache_hit": True})
            return parsed

    allowed = token and await can_call(
        cache, budget, envelope="mapbox_matrix", quota_name="mapbox"
    )
    if not allowed:
        return haversine_matrix(coords, profile)

    path = ";".join(f"{lng},{lat}" for lat, lng in coords)
    url = f"https://api.mapbox.com/directions-matrix/v1/mapbox/{profile}/{path}"
    body = await get_json(
        http,
        url,
        params={"access_token": token, "annotations": "duration,distance"},
        timeout=15.0,
        provider="mapbox",
    )
    if isinstance(body, dict) and body.get("code") == "Ok":
        parsed = _parse_matrix(body, len(coords), profile, cache_hit=False)
        if parsed is not None:
            await cache_set_json(
                cache,
                key,
                {"durations": parsed.durations, "distances": parsed.distances},
                TTL_MATRIX,
            )
            logger.info("mapbox_matrix", extra={"provider": "mapbox", "cache_hit": False})
            return parsed
    logger.warning("matrix_fallback_haversine", extra={"provider": "mapbox"})
    return haversine_matrix(coords, profile)
