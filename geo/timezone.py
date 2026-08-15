"""Destination-local IANA timezone. No TimeZoneDB. PROJECT_SPEC §7.11."""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger("cuvoy.geo")

_finder = None


def _timezone_finder():
    global _finder
    if _finder is None:
        from timezonefinder import TimezoneFinder

        _finder = TimezoneFinder()
    return _finder


@lru_cache(maxsize=4096)
def iana_timezone(lat: float, lng: float) -> str:
    """Resolve coordinates to an IANA id (e.g. Asia/Tokyo). Fallback UTC."""
    try:
        zone = _timezone_finder().timezone_at(lng=lng, lat=lat)
    except Exception:
        logger.warning("timezonefinder_failed", extra={"stage": "timezone"})
        return "UTC"
    if not zone:
        zone = _timezone_finder().closest_timezone_at(lng=lng, lat=lat)
    return zone or "UTC"
