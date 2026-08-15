"""Crowd Confidence — estimates, never live measurements. PROJECT_SPEC §10."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

from cuvoy_contracts.enrichment import CrowdConfidence, Weather
from cuvoy_contracts.enums import CrowdConfidenceLevel, CrowdLevel, WeatherSource

LEVELS = (
    (15, CrowdLevel.VERY_QUIET),
    (30, CrowdLevel.QUIET),
    (50, CrowdLevel.MODERATE),
    (70, CrowdLevel.BUSY),
    (100, CrowdLevel.VERY_BUSY),
)

WORSHIP = frozenset({"place_of_worship", "temple", "mosque", "church", "synagogue", "shrine"})
BEACH = frozenset({"beach", "coast", "swimming"})
MUSEUM = frozenset({"museum", "gallery", "theatre", "cinema"})


@dataclass
class CrowdInputs:
    on_date: date
    category: str
    is_holiday: bool = False
    holiday_name: str | None = None
    festival: str | None = None
    local_event: str | None = None
    peak_season: bool | None = None
    school_holiday: bool = False
    weather: Weather | None = None
    visit_time: time | None = None
    opens_at: time | None = None
    closes_at: time | None = None
    extra_reasons: list[str] = field(default_factory=list)


def _level(score: int) -> CrowdLevel:
    clamped = max(0, min(100, score))
    for upper, level in LEVELS:
        if clamped <= upper:
            return level
    return CrowdLevel.VERY_BUSY


def _rainy(weather: Weather | None) -> bool:
    if weather is None or not weather.summary:
        return False
    text = weather.summary.lower()
    return any(word in text for word in ("rain", "storm", "shower", "thunder"))


def _sunny(weather: Weather | None) -> bool:
    if weather is None or not weather.summary:
        return False
    text = weather.summary.lower()
    return "clear" in text or "sunny" in text


def _peak_month(on_date: date) -> bool:
    return on_date.month in {6, 7, 8, 12}


def crowd_confidence(inputs: CrowdInputs) -> CrowdConfidence:
    score = 35
    reasons: list[str] = []
    evidence = 0
    cat = inputs.category.lower()
    weekday = inputs.on_date.weekday()

    if weekday >= 5:
        score += 25
        reasons.append("Weekend")
        evidence += 1
    else:
        reasons.append("Weekday")
        evidence += 1

    if inputs.is_holiday:
        score += 30
        reasons.append(inputs.holiday_name or "Public holiday")
        evidence += 1
    if inputs.festival:
        score += 40
        reasons.append(f"Local festival ({inputs.festival})")
        evidence += 1
    if inputs.local_event:
        score += 35
        reasons.append(f"Local event ({inputs.local_event})")
        evidence += 1

    peak = inputs.peak_season if inputs.peak_season is not None else _peak_month(inputs.on_date)
    if peak:
        score += 20
        reasons.append("Peak tourist season")
        evidence += 1
    if inputs.school_holiday:
        score += 10
        reasons.append("School holidays")

    if weekday == 4 and any(token in cat or cat in WORSHIP for token in WORSHIP):
        score += 15
        reasons.append("Friday near place of worship")

    weather = inputs.weather
    if weather is not None:
        evidence += 1
        rainy = _rainy(weather)
        sunny = _sunny(weather)
        beach = cat in BEACH or "beach" in cat
        indoor = cat in MUSEUM or cat.startswith("museum")
        if rainy and beach:
            score -= 25
            reasons.append("Rain at beach")
        elif rainy and indoor:
            score -= 10
            reasons.append("Rain — museums less crowded")
        elif rainy:
            score -= 20
            reasons.append("Heavy rain")
        if sunny and beach:
            score += 10
            reasons.append("Sunny weather at beach")
        if weather.source != WeatherSource.FORECAST:
            reasons.append("Weather from historical climate (not a live forecast)")

    if inputs.visit_time and inputs.opens_at:
        open_minutes = inputs.opens_at.hour * 60 + inputs.opens_at.minute
        visit_minutes = inputs.visit_time.hour * 60 + inputs.visit_time.minute
        if 0 <= visit_minutes - open_minutes <= 60:
            score += 15
            reasons.append("Near opening hour")
            evidence += 1
    if inputs.visit_time and inputs.closes_at:
        close_minutes = inputs.closes_at.hour * 60 + inputs.closes_at.minute
        visit_minutes = inputs.visit_time.hour * 60 + inputs.visit_time.minute
        if 0 <= close_minutes - visit_minutes <= 60:
            score -= 15
            reasons.append("Near closing hour")
            evidence += 1

    reasons.extend(inputs.extra_reasons)
    if evidence >= 4:
        confidence = CrowdConfidenceLevel.HIGH
    elif evidence >= 2:
        confidence = CrowdConfidenceLevel.MEDIUM
    else:
        confidence = CrowdConfidenceLevel.LOW

    return CrowdConfidence(level=_level(score), confidence=confidence, reasons=reasons)
