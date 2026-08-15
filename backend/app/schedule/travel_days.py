"""Inter-city travel days are excluded from intra-city transit limits. PROJECT_SPEC §7."""

from __future__ import annotations

from datetime import date, timedelta

from cuvoy_contracts.constants import DEFAULT_DAY_START_LOCAL, DEFAULT_LUNCH_START
from cuvoy_contracts.enums import ItineraryItemType, TransportMode
from cuvoy_contracts.itinerary import ItineraryDay, ItineraryItem, RouteLeg
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import TripControls

from app.schedule.clock import combine_local, parse_hhmm, to_local_dt
from app.schedule.meals import meal_duration_minutes


def destinations_need_travel(from_id: str | None, to_id: str | None) -> bool:
    if not from_id or not to_id:
        return False
    return from_id != to_id


def build_travel_day(
    *,
    day_index: int,
    on_date: date,
    timezone: str,
    from_city: str,
    to_city: str,
    controls: TripControls | None = None,
    evening_place: Place | None = None,
    mode: TransportMode = TransportMode.MIXED,
    travel_seconds: int | None = None,
    distance_m: int | None = None,
    cost=None,
    geometry: str | None = None,
) -> ItineraryDay:
    start_hh = controls.day_start_local if controls else DEFAULT_DAY_START_LOCAL
    lunch = controls.lunch if controls else None
    start = combine_local(on_date, parse_hhmm(start_hh), timezone)
    items: list[ItineraryItem] = []

    checkout_end = start + timedelta(minutes=45)
    items.append(
        ItineraryItem(
            type=ItineraryItemType.TRAVEL_DAY,
            start=to_local_dt(start),
            end=to_local_dt(checkout_end),
            title=f"Hotel checkout · {from_city}",
        )
    )
    transit_minutes = max(60, (travel_seconds or 3 * 3600) // 60)
    transit_end = checkout_end + timedelta(minutes=transit_minutes)
    items.append(
        ItineraryItem(
            type=ItineraryItemType.TRANSIT,
            start=to_local_dt(checkout_end),
            end=to_local_dt(transit_end),
            title=f"Travel {from_city} → {to_city}",
            travel_minutes=transit_minutes,
            travel_minutes_buffered=transit_minutes,
            cost=cost,
            route=RouteLeg(
                from_place_id=from_city,
                to_place_id=to_city,
                duration_seconds=travel_seconds or transit_minutes * 60,
                duration_buffered_seconds=travel_seconds or transit_minutes * 60,
                distance_meters=distance_m or 0,
                mode=mode,
                cost=cost,
                geometry=geometry,
            ),
        )
    )
    cursor = transit_end
    if lunch:
        minutes = meal_duration_minutes(lunch)
        lunch_end = cursor + timedelta(minutes=minutes)
        items.append(
            ItineraryItem(
                type=ItineraryItemType.MEAL,
                start=to_local_dt(cursor),
                end=to_local_dt(lunch_end),
                title="Lunch (en route or at destination)",
                dwell_minutes=minutes,
            )
        )
        cursor = lunch_end
    else:
        lunch_start = combine_local(on_date, parse_hhmm(DEFAULT_LUNCH_START), timezone)
        if cursor < lunch_start:
            cursor = lunch_start
        lunch_end = cursor + timedelta(minutes=60)
        items.append(
            ItineraryItem(
                type=ItineraryItemType.MEAL,
                start=to_local_dt(cursor),
                end=to_local_dt(lunch_end),
                title="Lunch (en route or at destination)",
                dwell_minutes=60,
            )
        )
        cursor = lunch_end

    checkin_end = cursor + timedelta(minutes=45)
    items.append(
        ItineraryItem(
            type=ItineraryItemType.TRAVEL_DAY,
            start=to_local_dt(cursor),
            end=to_local_dt(checkin_end),
            title=f"Hotel check-in · {to_city}",
        )
    )
    cursor = checkin_end
    if evening_place:
        evening_end = cursor + timedelta(minutes=60)
        items.append(
            ItineraryItem(
                type=ItineraryItemType.ACTIVITY,
                start=to_local_dt(cursor),
                end=to_local_dt(evening_end),
                place=evening_place,
                title=evening_place.name,
                dwell_minutes=60,
            )
        )

    return ItineraryDay(
        day_index=day_index,
        date=on_date,
        timezone=timezone,
        city=to_city,
        is_travel_day=True,
        items=items,
    )


def intercity_transit_item(
    *,
    from_city: str,
    to_city: str,
    on_date: date,
    timezone: str,
    controls: TripControls | None = None,
    mode: TransportMode = TransportMode.CAR,
    travel_seconds: int | None = None,
    distance_m: int | None = None,
    geometry: str | None = None,
) -> ItineraryItem:
    """Visible Ooty → Coonoor (etc.) block on the first day in the next city."""
    start_hh = controls.day_start_local if controls else DEFAULT_DAY_START_LOCAL
    start = combine_local(on_date, parse_hhmm(start_hh), timezone)
    transit_minutes = max(45, (travel_seconds or 90 * 60) // 60)
    end = start + timedelta(minutes=transit_minutes)
    return ItineraryItem(
        type=ItineraryItemType.TRANSIT,
        start=to_local_dt(start),
        end=to_local_dt(end),
        title=f"Travel {from_city} → {to_city}",
        travel_minutes=transit_minutes,
        travel_minutes_buffered=transit_minutes,
        route=RouteLeg(
            from_place_id=from_city,
            to_place_id=to_city,
            duration_seconds=travel_seconds or transit_minutes * 60,
            duration_buffered_seconds=travel_seconds or transit_minutes * 60,
            distance_meters=distance_m or 0,
            mode=mode,
            geometry=geometry,
        ),
    )
