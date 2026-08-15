"""Haversine and coarse category helpers. Never LLM-based matching."""

from __future__ import annotations

import math

EARTH_M = 6_371_000.0

# Walking / cycling / urban driving used only when Mapbox Matrix is unavailable.
SPEED_MPS: dict[str, float] = {
    "walking": 1.25,
    "cycling": 4.2,
    "driving": 8.3,
    "driving-traffic": 7.0,
}


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_M * math.asin(min(1.0, math.sqrt(a)))


def duration_seconds(distance_m: float, profile: str) -> int:
    speed = SPEED_MPS.get(profile, SPEED_MPS["driving"])
    return max(1, int(distance_m / speed))


def bbox_from_center(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """south, west, north, east."""
    dlat = radius_km / 111.32
    dlng = radius_km / (111.32 * max(0.2, math.cos(math.radians(lat))))
    return (lat - dlat, lng - dlng, lat + dlat, lng + dlng)
