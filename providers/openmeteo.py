"""Open-Meteo forecast vs historical climate. Never label climate as forecast. §29.2."""

from __future__ import annotations

import calendar
import logging
from datetime import UTC, date, datetime, timedelta

import httpx
from cuvoy_contracts.constants import (
    FORECAST_HORIZON_DAYS,
    TTL_WEATHER_CLIMATE,
    TTL_WEATHER_FORECAST,
)
from cuvoy_contracts.enrichment import Weather
from cuvoy_contracts.enums import WeatherConfidence, WeatherSource

from app.providers.cache_keys import weather_key
from app.providers.gates import can_call
from app.providers.http import get_json
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend, cache_get_json, cache_set_json

logger = logging.getLogger("cuvoy.providers")

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

WMO: dict[int, str] = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    61: "Rain",
    71: "Snow",
    80: "Rain showers",
    95: "Thunderstorm",
}


def _unavailable() -> Weather:
    return Weather(
        source=WeatherSource.UNAVAILABLE,
        is_forecast=False,
        confidence=WeatherConfidence.NONE,
        retrieved_at=datetime.now(UTC),
    )


def _from_cache(raw: object) -> Weather | None:
    if not isinstance(raw, dict):
        return None
    try:
        return Weather.model_validate(raw)
    except Exception:
        return None


async def _forecast(
    http: httpx.AsyncClient, lat: float, lng: float, day: date
) -> Weather | None:
    body = await get_json(
        http,
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lng,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            "timezone": "auto",
            "forecast_days": FORECAST_HORIZON_DAYS,
        },
        timeout=10.0,
        provider="openmeteo",
    )
    if not isinstance(body, dict):
        return None
    daily = body.get("daily") or {}
    times = daily.get("time") or []
    stamp = day.isoformat()
    if stamp not in times:
        return None
    idx = times.index(stamp)
    tmax = (daily.get("temperature_2m_max") or [None])[idx]
    tmin = (daily.get("temperature_2m_min") or [None])[idx]
    code = (daily.get("weathercode") or [None])[idx]
    summary = WMO.get(int(code), "Weather") if code is not None else None
    return Weather(
        source=WeatherSource.FORECAST,
        is_forecast=True,
        confidence=WeatherConfidence.HIGH,
        retrieved_at=datetime.now(UTC),
        temperature_min=float(tmin) if tmin is not None else None,
        temperature_max=float(tmax) if tmax is not None else None,
        summary=summary,
    )


async def _climate(
    http: httpx.AsyncClient, lat: float, lng: float, day: date
) -> Weather | None:
    prev = date(day.year - 1, day.month, 1)
    last = date(day.year - 1, day.month, calendar.monthrange(day.year - 1, day.month)[1])
    body = await get_json(
        http,
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lng,
            "start_date": prev.isoformat(),
            "end_date": last.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
        },
        timeout=15.0,
        provider="openmeteo",
    )
    if not isinstance(body, dict):
        return None
    daily = body.get("daily") or {}
    highs = [x for x in (daily.get("temperature_2m_max") or []) if x is not None]
    lows = [x for x in (daily.get("temperature_2m_min") or []) if x is not None]
    if not highs or not lows:
        return None
    return Weather(
        source=WeatherSource.HISTORICAL_CLIMATE,
        is_forecast=False,
        confidence=WeatherConfidence.MODERATE,
        retrieved_at=datetime.now(UTC),
        climate_period=f"{prev.isoformat()}/{last.isoformat()}",
        temperature_min=round(sum(lows) / len(lows), 1),
        temperature_max=round(sum(highs) / len(highs), 1),
        summary="Monthly climate baseline (not live forecast data)",
    )


async def weather_for_date(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    lat: float,
    lng: float,
    day: date,
    *,
    budget: PlanBudget | None = None,
    today: date | None = None,
) -> Weather:
    """Forecast if within horizon; else monthly climate. Never breaks planning."""
    now = today or datetime.now(UTC).date()
    use_forecast = now <= day <= now + timedelta(days=FORECAST_HORIZON_DAYS)
    kind = "forecast" if use_forecast else "climate"
    key = weather_key(lat, lng, day.isoformat(), kind)
    cached = _from_cache(await cache_get_json(cache, key))
    if cached is not None:
        logger.info("weather", extra={"provider": "openmeteo", "cache_hit": True})
        return cached

    ttl = TTL_WEATHER_FORECAST if use_forecast else TTL_WEATHER_CLIMATE
    allowed = await can_call(cache, budget, envelope="weather", quota_name=None)
    if not allowed:
        return _unavailable()

    result: Weather | None = None
    if use_forecast:
        result = await _forecast(http, lat, lng, day)
        if result is None:
            result = await _climate(http, lat, lng, day)
    else:
        result = await _climate(http, lat, lng, day)

    if result is None:
        logger.warning("weather_unavailable", extra={"provider": "openmeteo", "cache_hit": False})
        return _unavailable()
    await cache_set_json(cache, key, result.model_dump(mode="json"), ttl)
    logger.info("weather", extra={"provider": "openmeteo", "cache_hit": False})
    return result
