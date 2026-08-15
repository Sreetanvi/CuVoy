"""Stage 4 — H3/DBSCAN already done; Mapbox Matrix on the reduced set. PROJECT_SPEC §33."""

from __future__ import annotations

import logging

from cuvoy_contracts.enums import PipelineStage

from app.pipeline.context import PipelineContext
from app.providers.mapbox_matrix import TravelMatrix, haversine_matrix

logger = logging.getLogger("cuvoy.pipeline")


async def run(ctx: PipelineContext) -> dict:
    if ctx.reduced and ctx.skip_stop_ids:
        skip = set(ctx.skip_stop_ids)
        ctx.reduced.matrix_places = [p for p in ctx.reduced.matrix_places if p.id not in skip]
        ctx.reduced.strong = [p for p in ctx.reduced.strong if p.id not in skip]
    places = ctx.reduced.matrix_places if ctx.reduced else []
    coords = [(p.lat, p.lng) for p in places]
    if len(coords) >= 2:
        ctx.matrix = await ctx.external.travel_matrix(coords, mode=ctx.mode, budget=ctx.budget)
    elif coords:
        ctx.matrix = TravelMatrix(
            durations=[[0]], distances=[[0]], approximate=False, cache_hit=True, profile="walking"
        )
    else:
        ctx.matrix = haversine_matrix([], "walking")
    logger.info("stage_complete", extra={"stage": PipelineStage.CLUSTER_MATRIX.value})
    return snapshot(ctx)


def snapshot(ctx: PipelineContext) -> dict:
    matrix = ctx.matrix
    if matrix is None:
        return {}
    return {
        "durations": matrix.durations,
        "distances": matrix.distances,
        "approximate": matrix.approximate,
        "profile": matrix.profile,
    }


def restore(ctx: PipelineContext, payload: dict) -> None:
    ctx.matrix = TravelMatrix(
        durations=payload.get("durations") or [],
        distances=payload.get("distances") or [],
        approximate=bool(payload.get("approximate")),
        cache_hit=True,
        profile=str(payload.get("profile") or "walking"),
    )
