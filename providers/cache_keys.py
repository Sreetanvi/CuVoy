"""Cache key builders for external data (PROJECT_SPEC §17)."""

from __future__ import annotations

import hashlib
import json


def _slug(value: str) -> str:
    return " ".join(value.lower().split())[:80]


def places_key(query: str, lng: float | None, lat: float | None) -> str:
    near = f"{lng:.3f}:{lat:.3f}" if lng is not None and lat is not None else "none"
    return f"places:{_slug(query)}:{near}"


def geocode_key(query: str, country: str | None = None) -> str:
    bias = (country or "none").lower()
    return f"geocode:v3:{_slug(query)}:{bias}"


def osm_key(city: str, category: str = "all") -> str:
    # v4: allowlisted tourism/historic/leisure/natural/amenity; industrial + residential dropped.
    return f"osm:v4:{_slug(city)}:{category}"


def matrix_key(profile: str, coords: list[tuple[float, float]]) -> str:
    rounded = [(round(lat, 5), round(lng, 5)) for lat, lng in coords]
    digest = hashlib.sha256(json.dumps(rounded).encode()).hexdigest()[:16]
    return f"matrix:{profile}:{digest}"


def directions_key(profile: str, coords: list[tuple[float, float]]) -> str:
    rounded = [(round(lat, 5), round(lng, 5)) for lat, lng in coords]
    digest = hashlib.sha256(json.dumps(rounded).encode()).hexdigest()[:16]
    return f"directions:v2:{profile}:{digest}"


def weather_key(lat: float, lng: float, day: str, kind: str) -> str:
    return f"weather:{kind}:{lat:.3f}:{lng:.3f}:{day}"


def holidays_key(country: str, year: int) -> str:
    return f"holidays:{country.upper()}:{year}"


def sunrise_key(lat: float, lng: float, day: str) -> str:
    return f"sunrise:{lat:.3f}:{lng:.3f}:{day}"
