"""Stage 5 — OR-Tools order + local-time schedule. PROJECT_SPEC §7.10, §5."""

from __future__ import annotations

import logging
from datetime import time as time_cls

from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES
from cuvoy_contracts.enums import ItineraryItemType, Pace, PipelineStage, TransportMode
from cuvoy_contracts.itinerary import Itinerary, ItineraryDay

from app.geo.destinations import destination_key, place_near_city
from app.optimize.ortools_solver import optimize_visit_order
from app.pipeline.context import PipelineContext, trip_dates
from app.providers.mapbox_directions import DirectionsResult
from app.providers.mapbox_matrix import TravelMatrix
from app.schedule.builder import build_day, max_leg_seconds, slice_daily_stops
from app.schedule.travel_days import build_travel_day, intercity_transit_item
from app.scoring.crowd import CrowdInputs, crowd_confidence

logger = logging.getLogger("cuvoy.pipeline")


def _city_places(ctx: PipelineContext, city: dict, places: list) -> list:
    key = destination_key(city)
    name = str(city.get("name") or ctx.dest_name)
    labels = {key, name, str(city.get("query") or "")} - {""}
    matched = [
        place
        for place in places
        if ctx.place_city.get(place.id) in labels and place_near_city(place.lat, place.lng, city)
    ]
    if matched:
        return matched
    return [place for place in places if place_near_city(place.lat, place.lng, city)]


async def _order_city_places(ctx: PipelineContext, places: list) -> tuple[list, TravelMatrix | None]:
    if len(places) < 2:
        return list(places), ctx.matrix
    matrix = ctx.matrix
    if matrix is None or len(getattr(matrix, "durations", []) or []) != len(places):
        try:
            matrix = await ctx.external.travel_matrix(
                [(place.lat, place.lng) for place in places],
                mode=ctx.mode,
                budget=ctx.budget,
            )
        except Exception:
            matrix = None
    durations = matrix.durations if matrix else []
    id_to_index = {place.id: index for index, place in enumerate(places)}
    locked = [id_to_index[pid] for pid in ctx.locked_stop_ids if pid in id_to_index]
    order_idx = list(range(len(places)))
    if durations and len(durations) == len(places):
        solved = optimize_visit_order(
            durations,
            locked=locked,
            max_leg_seconds=max_leg_seconds(ctx.controls),
        )
        order_idx = solved.order
    return [places[index] for index in order_idx if 0 <= index < len(places)], matrix


async def _road_snap(
    ctx: PipelineContext,
    waypoints: list[tuple[float, float]],
    *,
    mode: TransportMode,
) -> DirectionsResult | None:
    if len(waypoints) < 2:
        return None
    try:
        return await ctx.external.directions(waypoints, mode=mode, budget=ctx.budget)
    except Exception:
        logger.warning(
            "directions_failed",
            extra={"stage": PipelineStage.OPTIMIZE_SCHEDULE.value},
        )
        return None


def _apply_leg_geometry(day: ItineraryDay, stops: list, snapped: DirectionsResult | None) -> None:
    if snapped is None:
        return
    pairs = list(zip(stops, stops[1:], strict=False))
    legs = list(snapped.legs or [])
    for item in day.items:
        if item.route is None:
            continue
        matched = None
        for index, (origin, dest) in enumerate(pairs):
            if item.route.from_place_id == origin.id and item.route.to_place_id == dest.id:
                if index < len(legs):
                    matched = legs[index]
                break
        if matched is not None and matched.geometry:
            item.route.geometry = matched.geometry
            if matched.duration_seconds:
                item.route.duration_seconds = matched.duration_seconds
                item.route.distance_meters = matched.distance_meters
            continue
        if item.route.geometry is None and snapped.geometry:
            item.route.geometry = snapped.geometry


async def run(ctx: PipelineContext) -> dict:
    places = list(ctx.reduced.matrix_places) if ctx.reduced else []
    meals = list(ctx.reduced.meal_places) if ctx.reduced else []
    days_meta = trip_dates(ctx.request)
    pace = ctx.controls.pace if ctx.controls else None
    cities = [row for row in ctx.destinations if int(row.get("day_count") or 0) > 0]
    if len(cities) > 1:
        slices = []
        city_for_day: list[dict] = []
        for city in cities:
            city_places = _city_places(ctx, city, places)
            n_days = int(city.get("day_count") or 1)
            if not city_places:
                slices.extend([] for _ in range(n_days))
                city_for_day.extend(city for _ in range(n_days))
                continue
            ordered, _ = await _order_city_places(ctx, city_places)
            for chunk in slice_daily_stops(ordered, n_days, pace or Pace.MODERATE):
                slices.append(chunk)
                city_for_day.append(city)
        while len(slices) < len(days_meta):
            slices.append([])
            city_for_day.append(cities[-1])
        slices = slices[: len(days_meta)]
        city_for_day = city_for_day[: len(days_meta)]
    else:
        scoped = _city_places(ctx, cities[0], places) if cities else places
        ordered, _ = await _order_city_places(ctx, scoped or places)
        slices = slice_daily_stops(ordered, len(days_meta), pace or Pace.MODERATE)
        city_for_day = [cities[0] if cities else {"name": ctx.dest_name, "lat": ctx.dest_lat, "lng": ctx.dest_lng}] * len(
            days_meta
        )
    currency = "USD"
    daily_budget = None
    if ctx.preferences and ctx.preferences.budget:
        currency = ctx.preferences.budget.currency
        daily_budget = ctx.preferences.budget.daily_amount
    elif ctx.request.budget:
        currency = ctx.request.budget.currency
        daily_budget = ctx.request.budget.daily_amount

    holidays: set[str] = set()
    if ctx.country_code and days_meta:
        rows = await ctx.external.holidays(ctx.country_code, days_meta[0].year)
        holidays = {str(row.get("date")) for row in rows if isinstance(row, dict)}

    weather = None
    if days_meta:
        weather = await ctx.external.weather(
            ctx.dest_lat, ctx.dest_lng, days_meta[0], budget=ctx.budget
        )

    days: list[ItineraryDay] = []
    prev_dest: dict | None = None
    for index, (on_date, stops) in enumerate(zip(days_meta, slices, strict=False)):
        dest = city_for_day[index] if index < len(city_for_day) else {"name": ctx.dest_name}
        city_name = str(dest.get("name") or ctx.dest_name)
        city_changed = bool(
            prev_dest and destination_key(prev_dest) != destination_key(dest)
        )
        corridor = None
        if city_changed and prev_dest is not None:
            corridor = await _road_snap(
                ctx,
                [
                    (float(prev_dest["lat"]), float(prev_dest["lng"])),
                    (float(dest.get("lat") or ctx.dest_lat), float(dest.get("lng") or ctx.dest_lng)),
                ],
                mode=TransportMode.CAR,
            )
        if not stops and index > 0:
            days.append(
                build_travel_day(
                    day_index=index,
                    on_date=on_date,
                    timezone=ctx.timezone,
                    from_city=str(prev_dest.get("name") if prev_dest else ctx.dest_name),
                    to_city=city_name,
                    controls=ctx.controls,
                    mode=TransportMode.CAR,
                    travel_seconds=corridor.duration_seconds if corridor else None,
                    distance_m=corridor.distance_meters if corridor else None,
                    geometry=corridor.geometry if corridor else None,
                )
            )
            prev_dest = dest
            continue
        waypoints = [(place.lat, place.lng) for place in stops[:MAX_MATRIX_COORDINATES]]
        snapped = await _road_snap(ctx, waypoints, mode=ctx.mode)
        city_meals = [
            meal
            for meal in meals
            if ctx.place_city.get(meal.id) in {destination_key(dest), city_name}
        ] or [meal for meal in meals if place_near_city(meal.lat, meal.lng, dest)]
        day = build_day(
            day_index=index,
            on_date=on_date,
            timezone=ctx.timezone,
            city=city_name,
            ordered=stops,
            matrix=ctx.matrix,
            matrix_places=stops or places,
            mode=ctx.mode,
            controls=ctx.controls,
            meal_places=city_meals,
            currency=currency,
            daily_budget=daily_budget,
        )
        _apply_leg_geometry(day, stops, snapped)
        if city_changed and prev_dest is not None:
            day.items.insert(
                0,
                intercity_transit_item(
                    from_city=str(prev_dest.get("name") or ctx.dest_name),
                    to_city=city_name,
                    on_date=on_date,
                    timezone=ctx.timezone,
                    controls=ctx.controls,
                    mode=TransportMode.CAR,
                    travel_seconds=corridor.duration_seconds if corridor else None,
                    distance_m=corridor.distance_meters if corridor else None,
                    geometry=corridor.geometry if corridor else None,
                ),
            )
        prev_dest = dest
        day.weather = weather
        holiday = on_date.isoformat() in holidays
        for item in day.items:
            if item.type != ItineraryItemType.ACTIVITY or item.place is None:
                continue
            start = item.start.local_time
            visit = None
            try:
                clock = start.split("T")[-1][:5]
                hh, mm = clock.split(":")
                visit = time_cls(int(hh), int(mm))
            except Exception:
                visit = None
            item.crowd = crowd_confidence(
                CrowdInputs(
                    on_date=on_date,
                    category=item.place.category,
                    is_holiday=holiday,
                    weather=weather,
                    visit_time=visit,
                )
            )
        days.append(day)

    ctx.itinerary = Itinerary(days=days, timezone=ctx.timezone, currency=currency)
    logger.info("stage_complete", extra={"stage": PipelineStage.OPTIMIZE_SCHEDULE.value})
    return snapshot(ctx)


def snapshot(ctx: PipelineContext) -> dict:
    if ctx.itinerary is None:
        return {}
    return {"itinerary": ctx.itinerary.model_dump(mode="json")}


def restore(ctx: PipelineContext, payload: dict) -> None:
    raw = payload.get("itinerary")
    if isinstance(raw, dict):
        ctx.itinerary = Itinerary.model_validate(raw)
