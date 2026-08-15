"""Build a local-time day: dwell, transit buffers, meals, 4–6 stops. PROJECT_SPEC §5."""

from __future__ import annotations

from datetime import date, time, timedelta

from cuvoy_contracts.constants import (
    DEFAULT_DAY_END_LOCAL,
    DEFAULT_DAY_START_LOCAL,
    DEFAULT_DWELL_MINUTES,
    MAX_TRANSIT_MINUTES,
    TRANSIT_BUFFER,
)
from cuvoy_contracts.enums import (
    ItineraryItemType,
    MaxTransitPreset,
    Pace,
    TransportMode,
    WarningCode,
)
from cuvoy_contracts.itinerary import ItineraryDay, ItineraryItem, RouteLeg
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import TripControls

from app.providers.mapbox_matrix import TravelMatrix
from app.schedule.clock import combine_local, parse_hhmm, to_local_dt
from app.schedule.conflicts import place_warnings, reservation_info
from app.schedule.meals import meal_item, should_insert_meal
from app.scoring.costs import activity_cost, daily_cost, meal_cost, transport_cost

# Extra dwells are planning defaults, not facts. Spec §5.4 lists three categories.
DWELL_FALLBACK: dict[str, int] = {
    **DEFAULT_DWELL_MINUTES,
    "temple": 60,
    "place_of_worship": 45,
    "historical_site": 90,
    "historic": 90,
    "beach": 120,
    "market": 90,
    "park": 90,
    "garden": 60,
    "hiking": 180,
    "cafe": 60,
    "shopping": 120,
    "gallery": 90,
    "theme_park": 180,
    "zoo": 120,
    "artwork": 30,
}

PACE_DWELL = {Pace.RELAXED: 1.25, Pace.MODERATE: 1.0, Pace.PACKED: 0.85}
PACE_STOPS = {Pace.RELAXED: 4, Pace.MODERATE: 5, Pace.PACKED: 6}

BREAK_AFTER_STOPS = 3
BREAK_MINUTES = 15


def dwell_minutes(place: Place, pace: Pace) -> int:
    cat = place.category.lower()
    base = DWELL_FALLBACK.get(cat, DEFAULT_DWELL_MINUTES.get(cat, 75))
    for key, minutes in DWELL_FALLBACK.items():
        if key in cat:
            base = minutes
            break
    return max(20, int(base * PACE_DWELL.get(pace, 1.0)))


def buffer_seconds(duration: int, mode: TransportMode) -> int:
    return int(duration * (1.0 + TRANSIT_BUFFER.get(mode, 0.10)))


def max_leg_seconds(controls: TripControls | None) -> int | None:
    if controls is None:
        minutes = MAX_TRANSIT_MINUTES[MaxTransitPreset.BALANCED]
        return None if minutes is None else minutes * 60
    if controls.max_transit_preset == MaxTransitPreset.CUSTOM:
        return (controls.max_transit_minutes or 40) * 60
    cap = MAX_TRANSIT_MINUTES.get(controls.max_transit_preset)
    return None if cap is None else cap * 60


def stops_per_day(pace: Pace) -> int:
    return PACE_STOPS.get(pace, 5)


def _index_of(places: list[Place], place_id: str) -> int | None:
    for i, place in enumerate(places):
        if place.id == place_id:
            return i
    return None


def _leg(
    matrix: TravelMatrix | None,
    matrix_places: list[Place],
    frm: Place,
    to: Place,
    mode: TransportMode,
    currency: str,
    show_transport: bool,
    city: str | None,
) -> tuple[int, int, RouteLeg]:
    i = _index_of(matrix_places, frm.id)
    j = _index_of(matrix_places, to.id)
    duration = 15 * 60
    distance = 0
    if matrix is not None and i is not None and j is not None:
        duration = matrix.durations[i][j]
        distance = matrix.distances[i][j]
    buffered = buffer_seconds(duration, mode)
    cost = transport_cost(
        mode,
        distance_m=distance,
        currency=currency,
        city=city,
        show_transport=show_transport,
    )
    leg = RouteLeg(
        from_place_id=frm.id,
        to_place_id=to.id,
        duration_seconds=duration,
        duration_buffered_seconds=buffered,
        distance_meters=distance,
        mode=mode,
        cost=cost,
    )
    return duration, buffered, leg


def build_day(
    *,
    day_index: int,
    on_date: date,
    timezone: str,
    city: str | None,
    ordered: list[Place],
    matrix: TravelMatrix | None = None,
    matrix_places: list[Place] | None = None,
    mode: TransportMode = TransportMode.WALKING,
    controls: TripControls | None = None,
    meal_places: list[Place] | None = None,
    currency: str = "USD",
    daily_budget: float | None = None,
) -> ItineraryDay:
    pace = controls.pace if controls else Pace.MODERATE
    start_hh = controls.day_start_local if controls else DEFAULT_DAY_START_LOCAL
    end_hh = controls.day_end_local if controls else DEFAULT_DAY_END_LOCAL
    show_transport = controls.show_transport_cost if controls else False
    lunch = controls.lunch if controls else None
    dinner = controls.dinner if controls else None
    cap = stops_per_day(pace)
    coords = matrix_places if matrix_places is not None else ordered
    meals = list(meal_places or [])
    day_start = combine_local(on_date, parse_hhmm(start_hh), timezone)
    day_end = combine_local(on_date, parse_hhmm(end_hh), timezone)
    cursor = day_start
    items: list[ItineraryItem] = []
    lunch_done = False
    dinner_done = False
    prev: Place | None = None
    stops = 0
    meal_idx = 0

    def next_meal_place() -> Place | None:
        nonlocal meal_idx
        if meal_idx >= len(meals):
            return None
        place = meals[meal_idx]
        meal_idx += 1
        return place

    for place in ordered:
        if stops >= cap:
            break
        travel_min = 0
        buffered_min = 0
        route = None
        if prev is not None:
            duration, buffered, route = _leg(
                matrix, coords, prev, place, mode, currency, show_transport, city
            )
            travel_min = duration // 60
            buffered_min = buffered // 60
            transit_end = cursor + timedelta(seconds=buffered)
            trans_item = ItineraryItem(
                type=ItineraryItemType.TRANSIT,
                start=to_local_dt(cursor),
                end=to_local_dt(transit_end),
                title=f"Transit to {place.name}",
                travel_minutes=travel_min,
                travel_minutes_buffered=buffered_min,
                cost=route.cost,
                route=route,
                warnings=(
                    [WarningCode.COST_UNAVAILABLE]
                    if show_transport and route.cost and route.cost.amount is None
                    else []
                ),
            )
            items.append(trans_item)
            cursor = transit_end

        if lunch and not lunch_done and should_insert_meal(cursor, lunch):
            cost = meal_cost(currency=currency, daily_budget=daily_budget)
            item, cursor = meal_item(
                kind="lunch",
                window=lunch,
                timezone=timezone,
                start=cursor,
                place=next_meal_place(),
                cost=cost,
            )
            items.append(item)
            lunch_done = True
        if dinner and not dinner_done and should_insert_meal(cursor, dinner):
            cost = meal_cost(currency=currency, daily_budget=daily_budget)
            item, cursor = meal_item(
                kind="dinner",
                window=dinner,
                timezone=timezone,
                start=cursor,
                place=next_meal_place(),
                cost=cost,
            )
            items.append(item)
            dinner_done = True

        stay = dwell_minutes(place, pace)
        arrive = time(cursor.hour, cursor.minute)
        end = cursor + timedelta(minutes=stay)
        if end > day_end and stops >= 1:
            break
        warnings = place_warnings(place, on_date, arrive)
        act_cost = activity_cost(place, currency=currency, daily_budget=daily_budget)
        items.append(
            ItineraryItem(
                type=ItineraryItemType.ACTIVITY,
                start=to_local_dt(cursor),
                end=to_local_dt(end),
                place=place,
                title=place.name,
                dwell_minutes=stay,
                wait_minutes=0,
                travel_minutes=travel_min,
                travel_minutes_buffered=buffered_min,
                cost=act_cost,
                warnings=warnings,
                reservation=reservation_info(place),
                route=route,
            )
        )
        cursor = end
        prev = place
        stops += 1
        if pace != Pace.PACKED and stops % BREAK_AFTER_STOPS == 0 and cursor < day_end:
            brk = cursor + timedelta(minutes=BREAK_MINUTES)
            items.append(
                ItineraryItem(
                    type=ItineraryItemType.BREAK,
                    start=to_local_dt(cursor),
                    end=to_local_dt(brk),
                    title="Rest break",
                    dwell_minutes=BREAK_MINUTES,
                )
            )
            cursor = brk

    if lunch and not lunch_done:
        cost = meal_cost(currency=currency, daily_budget=daily_budget)
        item, cursor = meal_item(
            kind="lunch",
            window=lunch,
            timezone=timezone,
            start=max(cursor, combine_local(on_date, parse_hhmm(lunch.start_local), timezone)),
            place=next_meal_place(),
            cost=cost,
        )
        items.append(item)
    if dinner and not dinner_done:
        cost = meal_cost(currency=currency, daily_budget=daily_budget)
        item, cursor = meal_item(
            kind="dinner",
            window=dinner,
            timezone=timezone,
            start=max(cursor, combine_local(on_date, parse_hhmm(dinner.start_local), timezone)),
            place=next_meal_place(),
            cost=cost,
        )
        items.append(item)

    return ItineraryDay(
        day_index=day_index,
        date=on_date,
        timezone=timezone,
        city=city,
        is_travel_day=False,
        items=items,
        daily_cost=daily_cost(items, currency=currency, show_transport=show_transport),
    )


def slice_daily_stops(places: list[Place], n_days: int, pace: Pace) -> list[list[Place]]:
    """4–6 stops per day depending on pace. Extra places unused (alternates)."""
    per = stops_per_day(pace)
    days: list[list[Place]] = []
    idx = 0
    for _ in range(max(1, n_days)):
        days.append(places[idx : idx + per])
        idx += per
    return days
