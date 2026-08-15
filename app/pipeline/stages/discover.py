"""Stage 2 — Mapbox search + OSM city batch + optional website verify. PROJECT_SPEC §8."""

from __future__ import annotations

import logging

from cuvoy_contracts.enums import PipelineStage
from cuvoy_contracts.place import Place

from app.geo.destinations import destination_key, place_near_city
from app.pipeline.context import PipelineContext, dump_places, load_places
from app.providers.osm_filters import should_drop_candidate
from app.providers.place_name import is_raw_place_id

logger = logging.getLogger("cuvoy.pipeline")


def _cities(ctx: PipelineContext) -> list[dict]:
    if ctx.destinations:
        return ctx.destinations
    return [
        {
            "query": ctx.request.location.query,
            "name": ctx.dest_name or ctx.request.location.query,
            "lat": ctx.dest_lat,
            "lng": ctx.dest_lng,
            "day_count": 1,
        }
    ]


def _usable(place: Place, city: dict) -> bool:
    if is_raw_place_id(place.name) or should_drop_candidate(
        place.name, place.category, address=place.address
    ):
        return False
    return place_near_city(place.lat, place.lng, city)


async def _discover_city(ctx: PipelineContext, city: dict, seen: set[str]) -> list[Place]:
    query = str(city.get("query") or city.get("name") or "")
    name = str(city.get("name") or query)
    lat = float(city.get("lat") or ctx.dest_lat)
    lng = float(city.get("lng") or ctx.dest_lng)
    radius = ctx.request.location.radius_km or 15.0
    interests = (ctx.preferences.interests if ctx.preferences else []) or ["attractions"]
    primary = interests[0]
    city_key = destination_key(city) or name
    found: list[Place] = []
    for search in (f"{primary} in {query}", f"{query} attractions"):
        hits = await ctx.external.search_places(
            search,
            proximity=(lat, lng),
            limit=10,
            budget=ctx.budget,
        )
        for place in hits:
            if place.id in seen or not _usable(place, city):
                continue
            seen.add(place.id)
            ctx.place_city[place.id] = city_key
            found.append(place)

    osm = [
        place
        for place in await ctx.external.osm_city_batch(
            query or name, lat=lat, lng=lng, radius_km=radius, budget=ctx.budget
        )
        if _usable(place, city)
    ]
    for place in osm:
        ctx.place_city[place.id] = city_key
    if found:
        found = ctx.external.match_and_enrich(found, osm)
        extra = [place for place in osm if place.id not in seen]
        found.extend(extra[:80])
    else:
        found = osm
    for place in found:
        ctx.place_city[place.id] = city_key
        if place.id not in seen:
            seen.add(place.id)
    return found


async def run(ctx: PipelineContext) -> dict:
    seen: set[str] = set()
    discovered: list[Place] = []
    for city in _cities(ctx):
        discovered.extend(await _discover_city(ctx, city, seen))

    verified = 0
    for place in discovered:
        if verified >= 5:
            break
        if not place.website:
            continue
        check = await ctx.external.verify_website(place.website, budget=ctx.budget)
        verified += 1
        snippet = (check.hours_snippet or "").lower()
        if "closed" in snippet:
            ctx.exclusions.append(
                {
                    "place_id": place.id,
                    "name": place.name,
                    "reason": "Official site indicates closed.",
                }
            )

    closed_ids = {item["place_id"] for item in ctx.exclusions}
    ctx.discovered = [place for place in discovered if place.id not in closed_ids]
    logger.info(
        "stage_complete",
        extra={"stage": PipelineStage.DISCOVER.value, "provider": "mapbox"},
    )
    return snapshot(ctx)


def snapshot(ctx: PipelineContext) -> dict:
    return {
        "discovered": dump_places(ctx.discovered),
        "exclusions": ctx.exclusions,
        "place_city": ctx.place_city,
    }


def restore(ctx: PipelineContext, payload: dict) -> None:
    ctx.discovered = load_places(payload.get("discovered"))
    raw = payload.get("exclusions")
    if isinstance(raw, list):
        ctx.exclusions = [item for item in raw if isinstance(item, dict)]
    else:
        ctx.exclusions = []
    mapping = payload.get("place_city")
    ctx.place_city = (
        {str(key): str(value) for key, value in mapping.items()}
        if isinstance(mapping, dict)
        else {}
    )
