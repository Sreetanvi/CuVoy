"""Stage 1 — preference extraction + destination timezone. PROJECT_SPEC §7.22."""

from __future__ import annotations

import logging

from cuvoy_contracts.enums import PipelineStage
from cuvoy_contracts.preferences import ExtractedPreferences, TripControls

from app.ai_gateway.gateway import AIRequest
from app.ai_gateway.prompts.extract_preferences import user_message
from app.ai_gateway.tasks import AITask
from app.geo.destinations import (
    accept_geocoded_city,
    allocate_days,
    order_cities_corridor,
    parse_city_names,
    short_city_name,
)
from app.geo.timezone import iana_timezone
from app.pipeline.context import PipelineContext, resolve_mode, trip_day_count

logger = logging.getLogger("cuvoy.pipeline")


async def run(ctx: PipelineContext) -> dict:
    hint = None
    if ctx.request.trip_controls is not None:
        hint = ctx.request.trip_controls.model_dump_json()
    result = await ctx.gateway.complete(
        AIRequest(
            task=AITask.PREFERENCE_EXTRACTION,
            user_content=user_message(
                ctx.request.user_prompt,
                hint,
                location_query=ctx.request.location.query,
            ),
            fallback_payload={"user_prompt": ctx.request.user_prompt},
        ),
        ctx.budget,
    )
    prefs = result.parsed if isinstance(result.parsed, ExtractedPreferences) else None
    if prefs is None:
        prefs = ExtractedPreferences(dates=ctx.request.travel_dates)
    if prefs.dates is None:
        prefs.dates = ctx.request.travel_dates
    if prefs.budget is None:
        prefs.budget = ctx.request.budget
    if prefs.transportation is None:
        prefs.transportation = ctx.request.transportation
    if ctx.request.trip_controls:
        prefs.pace = ctx.request.trip_controls.pace
        prefs.hidden_gems = ctx.request.trip_controls.hidden_gems
        prefs.group = ctx.request.trip_controls.group
        prefs.accessibility = ctx.request.trip_controls.accessibility
        if ctx.request.trip_controls.daily_budget:
            prefs.budget = ctx.request.trip_controls.daily_budget
        if ctx.request.trip_controls.transportation:
            prefs.transportation = ctx.request.trip_controls.transportation

    names = parse_city_names(ctx.request.location.query, ctx.request.user_prompt)
    resolved: list[dict] = []
    proximity: tuple[float, float] | None = None
    country: str | None = None
    for query in names:
        geo = await ctx.external.geocode(
            query,
            budget=ctx.budget,
            proximity=proximity,
            country=country,
        )
        if geo is None:
            continue
        if not accept_geocoded_city(query, geo, resolved):
            logger.warning(
                "dropped_outlier_destination",
                extra={"stage": PipelineStage.EXTRACT.value, "query": query},
            )
            continue
        lat = float(geo["lat"])
        lng = float(geo["lng"])
        resolved.append(
            {
                "query": query,
                "name": short_city_name(str(geo.get("name") or query), query),
                "lat": lat,
                "lng": lng,
                "country_code": geo.get("country_code"),
                "timezone": iana_timezone(lat, lng),
                "day_count": 0,
            }
        )
        if proximity is None:
            proximity = (lat, lng)
        if not country and geo.get("country_code"):
            country = str(geo["country_code"])
    resolved = order_cities_corridor(resolved)
    if not resolved:
        raise RuntimeError("Could not resolve the destination. Check the location and try again.")
    counts = allocate_days(trip_day_count(ctx.request), len(resolved))
    ctx.destinations = [
        {**city, "day_count": count} for city, count in zip(resolved, counts, strict=False) if count > 0
    ]
    primary = ctx.destinations[0]
    ctx.dest_lat = float(primary["lat"])
    ctx.dest_lng = float(primary["lng"])
    ctx.dest_name = str(primary["name"])
    ctx.country_code = primary.get("country_code")
    ctx.timezone = str(primary.get("timezone") or iana_timezone(ctx.dest_lat, ctx.dest_lng))
    prefs.timezone = ctx.timezone
    ctx.preferences = prefs
    ctx.apply_controls()
    ctx.mode = resolve_mode(ctx.request, prefs)
    logger.info(
        "stage_complete",
        extra={"stage": PipelineStage.EXTRACT.value, "provider": result.provider},
    )
    return snapshot(ctx)


def snapshot(ctx: PipelineContext) -> dict:
    return {
        "preferences": ctx.preferences.model_dump(mode="json") if ctx.preferences else None,
        "controls": ctx.controls.model_dump(mode="json") if ctx.controls else None,
        "dest_lat": ctx.dest_lat,
        "dest_lng": ctx.dest_lng,
        "dest_name": ctx.dest_name,
        "destinations": ctx.destinations,
        "country_code": ctx.country_code,
        "timezone": ctx.timezone,
        "mode": ctx.mode.value,
        "request": ctx.request.model_dump(mode="json"),
    }


def restore(ctx: PipelineContext, payload: dict) -> None:
    raw = payload.get("preferences")
    if isinstance(raw, dict):
        ctx.preferences = ExtractedPreferences.model_validate(raw)
    ctrl = payload.get("controls")
    if isinstance(ctrl, dict):
        ctx.controls = TripControls.model_validate(ctrl)
    ctx.dest_lat = float(payload.get("dest_lat") or 0)
    ctx.dest_lng = float(payload.get("dest_lng") or 0)
    ctx.dest_name = str(payload.get("dest_name") or ctx.request.location.query)
    raw_dests = payload.get("destinations")
    ctx.destinations = [item for item in raw_dests if isinstance(item, dict)] if isinstance(raw_dests, list) else []
    ctx.country_code = payload.get("country_code")
    ctx.timezone = str(payload.get("timezone") or "UTC")
    mode = payload.get("mode")
    if mode:
        from cuvoy_contracts.enums import TransportMode

        ctx.mode = TransportMode(mode)
