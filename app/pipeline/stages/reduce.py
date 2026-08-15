"""Stage 3 — rank + candidate reduction before Matrix. PROJECT_SPEC §33."""

from __future__ import annotations

import json
import logging

from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES
from cuvoy_contracts.enums import Pace, PipelineStage
from cuvoy_contracts.place import Cluster

from app.ai_gateway.gateway import AIRequest
from app.ai_gateway.prompts.rank_candidates import user_message
from app.ai_gateway.schemas import RankedCandidates
from app.ai_gateway.tasks import AITask
from app.geo.candidate_reduce import ReducedCandidates, reduce_candidates
from app.geo.destinations import destination_key, place_near_city
from app.pipeline.context import PipelineContext, dump_places, load_places
from app.providers.place_name import display_place_name, is_raw_place_id
from app.schedule.builder import stops_per_day

logger = logging.getLogger("cuvoy.pipeline")


async def run(ctx: PipelineContext) -> dict:
    skip = set(ctx.skip_stop_ids)
    pool = [p for p in ctx.discovered if p.id not in skip]
    cities = [row for row in ctx.destinations if int(row.get("day_count") or 0) > 0]
    pace = ctx.controls.pace if ctx.controls else Pace.MODERATE
    if len(cities) > 1:
        merged = ReducedCandidates(relevant=[], strong=[], meal_places=[], dropped_ids=[])
        used: set[str] = set()
        for city in cities:
            labels = {
                destination_key(city),
                str(city.get("name") or ""),
                str(city.get("query") or ""),
            } - {""}
            subset = [
                place
                for place in pool
                if ctx.place_city.get(place.id) in labels and place_near_city(place.lat, place.lng, city)
            ]
            if not subset:
                subset = [
                    place
                    for place in pool
                    if place.id not in used and place_near_city(place.lat, place.lng, city)
                ]
            part = reduce_candidates(
                subset,
                preferences=ctx.preferences,
                controls=ctx.controls,
                destination_id=destination_key(city).lower().replace(" ", "_") or str(city.get("name") or "").lower(),
            )
            cap = max(4, min(MAX_MATRIX_COORDINATES, int(city.get("day_count") or 1) * stops_per_day(pace)))
            merged.relevant.extend(part.relevant)
            merged.strong.extend(part.strong)
            merged.meal_places.extend(part.meal_places)
            merged.matrix_places.extend(part.matrix_places[:cap])
            merged.dropped_ids.extend(part.dropped_ids)
            merged.clusters.extend(part.clusters)
            used.update(place.id for place in subset)
        reduced = merged
    else:
        reduced = reduce_candidates(
            pool,
            preferences=ctx.preferences,
            controls=ctx.controls,
            destination_id=ctx.request.location.query.lower().replace(" ", "_"),
        )
    slim = [
        {"place_id": p.id, "name": p.name, "category": p.category}
        for p in reduced.strong[:40]
    ]
    if slim:
        ranked = await ctx.gateway.complete(
            AIRequest(
                task=AITask.RANK_CANDIDATES,
                user_content=user_message(
                    (ctx.preferences.model_dump_json() if ctx.preferences else "{}"),
                    json.dumps(slim),
                ),
                fallback_payload={"candidates": slim},
                known_place_ids={p.id for p in reduced.strong},
            ),
            ctx.budget,
        )
        parsed = ranked.parsed if isinstance(ranked.parsed, RankedCandidates) else None
        if parsed and parsed.ranked:
            order = {item.place_id: item.score for item in parsed.ranked}
            reduced.strong = sorted(
                reduced.strong, key=lambda p: order.get(p.id, 0.0), reverse=True
            )
            reduced.matrix_places = sorted(
                reduced.matrix_places, key=lambda p: order.get(p.id, 0.0), reverse=True
            )
    for pid in ctx.locked_stop_ids:
        locked = next((p for p in pool if p.id == pid), None)
        if locked and locked.id not in {p.id for p in reduced.matrix_places}:
            reduced.matrix_places.insert(0, locked)
            if locked.id not in {p.id for p in reduced.strong}:
                reduced.strong.insert(0, locked)
    ctx.reduced = reduced
    by_id = {place.id: place for place in pool}
    named_exclusions = []
    for pid in reduced.dropped_ids[:20]:
        place = by_id.get(pid)
        name = place.name.strip() if place and place.name.strip() else display_place_name(place)
        if not name or is_raw_place_id(name) or name.lower().startswith("unnamed location"):
            continue
        named_exclusions.append(
            {
                "place_id": pid,
                "name": name,
                "category": place.category if place else None,
                "reason": "Removed during candidate reduction.",
            }
        )
    ctx.exclusions.extend(named_exclusions)
    logger.info("stage_complete", extra={"stage": PipelineStage.REDUCE.value})
    return snapshot(ctx)


def snapshot(ctx: PipelineContext) -> dict:
    reduced = ctx.reduced
    if reduced is None:
        return {}
    return {
        "relevant": dump_places(reduced.relevant),
        "strong": dump_places(reduced.strong),
        "meal_places": dump_places(reduced.meal_places),
        "dropped_ids": reduced.dropped_ids,
        "matrix_places": dump_places(reduced.matrix_places),
        "clusters": [c.model_dump(mode="json") for c in reduced.clusters],
        "exclusions": ctx.exclusions,
    }


def restore(ctx: PipelineContext, payload: dict) -> None:
    clusters = []
    for item in payload.get("clusters") or []:
        try:
            clusters.append(Cluster.model_validate(item))
        except Exception:
            continue
    ctx.reduced = ReducedCandidates(
        relevant=load_places(payload.get("relevant")),
        strong=load_places(payload.get("strong")),
        meal_places=load_places(payload.get("meal_places")),
        dropped_ids=list(payload.get("dropped_ids") or []),
        clusters=clusters,
        matrix_places=load_places(payload.get("matrix_places")),
    )
    raw = payload.get("exclusions")
    if isinstance(raw, list):
        ctx.exclusions = [item for item in raw if isinstance(item, dict)]
