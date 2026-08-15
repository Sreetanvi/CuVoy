"""Meal windows in destination-local time. PROJECT_SPEC §5.5."""

from __future__ import annotations

from datetime import datetime, timedelta

from cuvoy_contracts.constants import MEAL_MIN_DURATION_MINUTES
from cuvoy_contracts.enums import ItineraryItemType
from cuvoy_contracts.itinerary import ItineraryItem
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import MealWindow

from app.schedule.clock import as_local, parse_hhmm, to_local_dt


def meal_duration_minutes(window: MealWindow) -> int:
    start = parse_hhmm(window.start_local)
    end = parse_hhmm(window.end_local)
    span = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if span <= 0:
        span += 24 * 60
    return max(window.min_duration_minutes, MEAL_MIN_DURATION_MINUTES, min(span, 180))


def should_insert_meal(now: datetime, window: MealWindow) -> bool:
    start = parse_hhmm(window.start_local)
    start_dt = now.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
    return now >= start_dt


def meal_item(
    *,
    kind: str,
    window: MealWindow,
    timezone: str,
    start: datetime,
    place: Place | None,
    cost,
) -> tuple[ItineraryItem, datetime]:
    minutes = meal_duration_minutes(window)
    end = start + timedelta(minutes=minutes)
    title = "Lunch" if kind == "lunch" else "Dinner"
    item = ItineraryItem(
        type=ItineraryItemType.MEAL,
        start=to_local_dt(start),
        end=to_local_dt(end),
        place=place,
        title=title,
        dwell_minutes=minutes,
        cost=cost,
    )
    return item, as_local(end, timezone)
