from datetime import date, time

from cuvoy_contracts.enrichment import Weather
from cuvoy_contracts.enums import CrowdLevel, WeatherConfidence, WeatherSource

from app.scoring.crowd import CrowdInputs, crowd_confidence


def test_saturday_holiday_sunny_beach_is_busy() -> None:
    weather = Weather(
        source=WeatherSource.FORECAST,
        is_forecast=True,
        confidence=WeatherConfidence.HIGH,
        summary="Clear",
    )
    result = crowd_confidence(
        CrowdInputs(
            on_date=date(2026, 8, 15),  # Saturday
            category="beach",
            is_holiday=True,
            holiday_name="Independence Day",
            weather=weather,
        )
    )
    assert result.level in {CrowdLevel.BUSY, CrowdLevel.VERY_BUSY}
    assert "Weekend" in result.reasons
    assert any("holiday" in r.lower() or "Independence" in r for r in result.reasons)
    assert any("Sunny" in r or "beach" in r.lower() for r in result.reasons)


def test_rain_at_beach_is_quieter() -> None:
    dry = crowd_confidence(
        CrowdInputs(
            on_date=date(2026, 8, 12),  # Wednesday
            category="beach",
            weather=Weather(
                source=WeatherSource.FORECAST,
                is_forecast=True,
                confidence=WeatherConfidence.HIGH,
                summary="Clear",
            ),
        )
    )
    wet = crowd_confidence(
        CrowdInputs(
            on_date=date(2026, 8, 12),
            category="beach",
            weather=Weather(
                source=WeatherSource.FORECAST,
                is_forecast=True,
                confidence=WeatherConfidence.HIGH,
                summary="Rain",
            ),
        )
    )
    order = list(CrowdLevel)
    assert order.index(wet.level) <= order.index(dry.level)
    assert any("Rain at beach" in r for r in wet.reasons)


def test_opening_hour_modifier() -> None:
    result = crowd_confidence(
        CrowdInputs(
            on_date=date(2026, 8, 12),
            category="museum",
            visit_time=time(9, 15),
            opens_at=time(9, 0),
            closes_at=time(18, 0),
        )
    )
    assert "Near opening hour" in result.reasons
