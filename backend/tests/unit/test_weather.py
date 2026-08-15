from datetime import date

import httpx
import pytest
from cuvoy_contracts.enums import WeatherSource

from app.providers.openmeteo import weather_for_date
from app.services.cache import InMemoryCache


def _forecast_body() -> dict:
    return {
        "daily": {
            "time": ["2026-08-20"],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [22.0],
            "weathercode": [1],
        }
    }


def _climate_body() -> dict:
    return {
        "daily": {
            "time": ["2025-12-01", "2025-12-02"],
            "temperature_2m_max": [18.0, 20.0],
            "temperature_2m_min": [8.0, 10.0],
        }
    }


@pytest.mark.asyncio
async def test_near_term_is_forecast_not_climate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.open-meteo.com" in str(request.url)
        return httpx.Response(200, json=_forecast_body())

    cache = InMemoryCache()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        weather = await weather_for_date(
            http,
            cache,
            12.97,
            77.59,
            date(2026, 8, 20),
            today=date(2026, 8, 14),
        )
    assert weather.is_forecast is True
    assert weather.source == WeatherSource.FORECAST
    assert weather.temperature_max == 31.0


@pytest.mark.asyncio
async def test_beyond_horizon_uses_monthly_climate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "archive-api.open-meteo.com" in str(request.url)
        return httpx.Response(200, json=_climate_body())

    cache = InMemoryCache()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        weather = await weather_for_date(
            http,
            cache,
            48.85,
            2.35,
            date(2027, 12, 10),
            today=date(2026, 8, 14),
        )
    assert weather.is_forecast is False
    assert weather.source == WeatherSource.HISTORICAL_CLIMATE
    assert weather.climate_period is not None
    assert weather.is_forecast is False
    assert "climate" in (weather.summary or "").lower()
    assert weather.temperature_max == 19.0
    assert weather.temperature_min == 9.0
