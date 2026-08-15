"""Stage 6 — LLM narrative/packing/explainability + validation gate. PROJECT_SPEC §7.22."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from cuvoy_contracts.api import PlanResult
from cuvoy_contracts.enrichment import (
    Alternatives,
    Explainability,
    MapBounds,
    MapMarker,
    MapPayload,
    PackingList,
    Provenance,
)
from cuvoy_contracts.enums import CrowdConfidenceLevel, ItineraryItemType, PipelineStage

from app.ai_gateway.gateway import AIRequest
from app.ai_gateway.prompts.explainability import user_message as explain_user
from app.ai_gateway.prompts.narrative import user_message as narrative_user
from app.ai_gateway.prompts.packing import user_message as packing_user
from app.ai_gateway.schemas import NarrativeOutput
from app.ai_gateway.tasks import AITask
from app.pipeline.context import PipelineContext
from app.validation.cross_schema import validate_plan

logger = logging.getLogger("cuvoy.pipeline")


GENERIC_EXCLUSION_NAMES = frozenset(
    {"", "nearby poi", "unnamed place", "unknown place", "general", "poi"}
)


def _keep_exclusion_names(
    explainability: Explainability | None, source: list[dict]
) -> Explainability | None:
    """LLM may rewrite names; keep the verified candidate label from reduction."""
    if explainability is None:
        return None
    by_id = {
        str(item.get("place_id")): str(item.get("name") or "").strip()
        for item in source
        if isinstance(item, dict) and item.get("place_id")
    }
    restored: list = []
    for item in explainability.exclusions:
        original = by_id.get(str(item.place_id or ""))
        name = item.name.strip() if item.name else ""
        if original:
            if original.lower().startswith("unnamed location"):
                continue
            restored.append(item.model_copy(update={"name": original}))
        elif not name or name.lower() in GENERIC_EXCLUSION_NAMES or name.lower().startswith(
            "unnamed location"
        ):
            continue
        else:
            restored.append(item)
    return explainability.model_copy(update={"exclusions": restored})


def _map_payload(ctx: PipelineContext) -> MapPayload:
    markers: list[MapMarker] = []
    lats: list[float] = []
    lngs: list[float] = []
    if ctx.itinerary:
        for day in ctx.itinerary.days:
            for item in day.items:
                if item.type != ItineraryItemType.ACTIVITY or item.place is None:
                    continue
                markers.append(
                    MapMarker(
                        place_id=item.place.id,
                        lat=item.place.lat,
                        lng=item.place.lng,
                        label=item.place.name,
                        day_index=day.day_index,
                    )
                )
                lats.append(item.place.lat)
                lngs.append(item.place.lng)
    bounds = None
    if lats and lngs:
        bounds = MapBounds(
            min_lat=min(lats), min_lng=min(lngs), max_lat=max(lats), max_lng=max(lngs)
        )
    return MapPayload(markers=markers, bounds=bounds)


def _routes(ctx: PipelineContext):
    routes = []
    if ctx.itinerary:
        for day in ctx.itinerary.days:
            for item in day.items:
                if item.route is not None:
                    routes.append(item.route)
    return routes


async def run(ctx: PipelineContext) -> dict:
    prefs_json = ctx.preferences.model_dump_json() if ctx.preferences else "{}"
    itin_json = ctx.itinerary.model_dump_json() if ctx.itinerary else "{}"
    narrative = await ctx.gateway.complete(
        AIRequest(
            task=AITask.NARRATIVE,
            user_content=narrative_user(itin_json, prefs_json),
            fallback_payload={"itinerary": json.loads(itin_json) if itin_json != "{}" else {}},
        ),
        ctx.budget,
    )
    if ctx.itinerary and isinstance(narrative.parsed, NarrativeOutput):
        ctx.itinerary.narrative = narrative.parsed.summary

    packing = await ctx.gateway.complete(
        AIRequest(
            task=AITask.PACKING,
            user_content=packing_user(
                json.dumps(
                    {
                        "destination": ctx.dest_name,
                        "timezone": ctx.timezone,
                        "preferences": json.loads(prefs_json),
                    }
                )
            ),
            fallback_payload={"context": {"destination": ctx.dest_name, "timezone": ctx.timezone}},
        ),
        ctx.budget,
    )
    explain = await ctx.gateway.complete(
        AIRequest(
            task=AITask.EXPLAINABILITY,
            user_content=explain_user(
                "Why were some places left out?",
                json.dumps({"exclusions": ctx.exclusions}),
            ),
            fallback_payload={"evidence": {"exclusions": ctx.exclusions}},
        ),
        ctx.budget,
    )

    prefs = ctx.preferences
    if prefs is None:
        from cuvoy_contracts.preferences import ExtractedPreferences

        prefs = ExtractedPreferences(dates=ctx.request.travel_dates, timezone=ctx.timezone)

    itinerary = ctx.itinerary
    if itinerary is None:
        from cuvoy_contracts.itinerary import Itinerary

        itinerary = Itinerary(days=[], timezone=ctx.timezone, currency="USD")

    packing_list = packing.parsed if isinstance(packing.parsed, PackingList) else None
    explainability = explain.parsed if isinstance(explain.parsed, Explainability) else None
    explainability = _keep_exclusion_names(explainability, ctx.exclusions)
    report = validate_plan(itinerary, ctx.controls)
    now = datetime.now(UTC)
    provenance = [
        Provenance(
            field="timezone",
            source="timezonefinder",
            retrieved_at=now,
            confidence=CrowdConfidenceLevel.HIGH,
        ),
        Provenance(field="places", source="mapbox+osm", retrieved_at=now),
        Provenance(
            field="matrix",
            source="mapbox" if ctx.matrix and not ctx.matrix.approximate else "haversine",
        ),
        Provenance(
            field="narrative",
            source=narrative.provider,
            retrieved_at=now,
            confidence=(
                CrowdConfidenceLevel.LOW
                if narrative.fallback_used
                else CrowdConfidenceLevel.MEDIUM
            ),
        ),
    ]
    ctx.result = PlanResult(
        plan_id=ctx.plan_id,
        timezone=ctx.timezone,
        preferences=prefs,
        itinerary=itinerary,
        map=_map_payload(ctx),
        routes=_routes(ctx),
        packing_list=packing_list,
        explainability=explainability,
        alternatives=Alternatives(),
        provenance=provenance,
        validation=report,
    )
    logger.info("stage_complete", extra={"stage": PipelineStage.NARRATIVE_VALIDATE.value})
    return snapshot(ctx)


def snapshot(ctx: PipelineContext) -> dict:
    if ctx.result is None:
        return {}
    return ctx.result.model_dump(mode="json")


def restore(ctx: PipelineContext, payload: dict) -> None:
    ctx.result = PlanResult.model_validate(payload)
    ctx.itinerary = ctx.result.itinerary
    ctx.preferences = ctx.result.preferences
    ctx.timezone = ctx.result.timezone
