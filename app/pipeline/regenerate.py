"""Fast-path regeneration: reuse stages 1–3. PROJECT_SPEC §7.13."""

from __future__ import annotations

from cuvoy_contracts.api import RegenerateRequest
from cuvoy_contracts.enums import PipelineStage
from cuvoy_contracts.preferences import TripControls

from app.pipeline.context import PipelineContext
from app.pipeline.orchestrator import run_pipeline
from app.services import jobs


def apply_regenerate_request(ctx: PipelineContext, body: RegenerateRequest) -> None:
    if body.trip_controls is not None:
        ctx.request = ctx.request.model_copy(update={"trip_controls": body.trip_controls})
        ctx.controls = body.trip_controls
    ctx.skip_stop_ids = list(body.skip_stop_ids)
    ctx.locked_stop_ids = list(body.locked_stop_ids)
    if body.meal_override and ctx.controls:
        lunch = ctx.controls.lunch
        dinner = ctx.controls.dinner
        meal = body.meal_override.meal.lower()
        updates = {
            "start_local": body.meal_override.start_local,
            "end_local": body.meal_override.end_local,
        }
        updates = {k: v for k, v in updates.items() if v}
        if meal == "lunch" and updates:
            lunch = lunch.model_copy(update=updates)
        elif meal == "dinner" and updates:
            dinner = dinner.model_copy(update=updates)
        ctx.controls = ctx.controls.model_copy(update={"lunch": lunch, "dinner": dinner})
        ctx.request = ctx.request.model_copy(update={"trip_controls": ctx.controls})
    if body.swap:
        ctx.skip_stop_ids.append(body.swap.from_place_id)
        ctx.locked_stop_ids.append(body.swap.to_place_id)


async def regenerate(ctx: PipelineContext, body: RegenerateRequest) -> None:
    apply_regenerate_request(ctx, body)
    if ctx.controls is None:
        ctx.controls = ctx.request.trip_controls or TripControls()
    extract_ok = await jobs.read_checkpoint(ctx.cache, ctx.plan_id, PipelineStage.EXTRACT)
    reduce_ok = await jobs.read_checkpoint(ctx.cache, ctx.plan_id, PipelineStage.REDUCE)
    if reduce_ok:
        start = PipelineStage.CLUSTER_MATRIX
    elif extract_ok:
        start = PipelineStage.REDUCE
    else:
        start = PipelineStage.EXTRACT
    ctx.regeneration = True
    await run_pipeline(ctx, start_from=start)
