"""Six-stage planner orchestrator + checkpoints. PROJECT_SPEC §7.22."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from cuvoy_contracts.api import SseEvent
from cuvoy_contracts.enums import JobStatus, PipelineStage

from app.pipeline.context import PipelineContext
from app.pipeline.sse import plan_complete, plan_error, stage_complete, stage_start
from app.pipeline.stages import (
    cluster_matrix_stage,
    discover_stage,
    extract_stage,
    narrative_stage,
    optimize_stage,
    reduce_stage,
)
from app.services import jobs
from app.services.budget import persist_budget, refund_credit

logger = logging.getLogger("cuvoy.pipeline")

STAGE_RUNNERS: list[tuple[PipelineStage, object]] = [
    (PipelineStage.EXTRACT, extract_stage),
    (PipelineStage.DISCOVER, discover_stage),
    (PipelineStage.REDUCE, reduce_stage),
    (PipelineStage.CLUSTER_MATRIX, cluster_matrix_stage),
    (PipelineStage.OPTIMIZE_SCHEDULE, optimize_stage),
    (PipelineStage.NARRATIVE_VALIDATE, narrative_stage),
]

Emit = Callable[[SseEvent], Awaitable[None]]


async def _restore_prior(ctx: PipelineContext, start: PipelineStage) -> None:
    for stage, module in STAGE_RUNNERS:
        if stage == start:
            break
        payload = await jobs.read_checkpoint(ctx.cache, ctx.plan_id, stage)
        if payload:
            module.restore(ctx, payload)


async def run_pipeline(
    ctx: PipelineContext,
    *,
    start_from: PipelineStage | None = None,
    emit: Emit | None = None,
) -> None:
    async def _emit(event: SseEvent) -> None:
        await jobs.append_event(ctx.cache, ctx.plan_id, event.model_dump(mode="json"))
        if emit is not None:
            await emit(event)

    await jobs.update_job(ctx.cache, ctx.plan_id, status=JobStatus.RUNNING.value)
    start = start_from or PipelineStage.EXTRACT
    if start != PipelineStage.EXTRACT:
        await _restore_prior(ctx, start)

    began = False
    try:
        for stage, module in STAGE_RUNNERS:
            if not began:
                if stage != start:
                    continue
                began = True
            await _emit(stage_start(ctx.plan_id, stage))
            payload = await module.run(ctx)
            await jobs.write_checkpoint(ctx.cache, ctx.plan_id, stage, payload)
            await persist_budget(ctx.cache, ctx.budget)
            await _emit(stage_complete(ctx.plan_id, stage))
        if ctx.result is not None:
            await jobs.save_result(ctx.cache, ctx.plan_id, ctx.result.model_dump(mode="json"))
            await _emit(plan_complete(ctx.plan_id, ctx.itinerary))
        else:
            raise RuntimeError("Planner finished without a result")
    except Exception as exc:
        logger.exception("pipeline_failed", extra={"stage": "orchestrator", "plan_id": ctx.plan_id})
        refund = False
        if not ctx.regeneration:
            await refund_credit(ctx.cache, ctx.identity)
            refund = True
        await jobs.update_job(
            ctx.cache,
            ctx.plan_id,
            status=JobStatus.FAILED.value,
            error=str(exc),
            resumable=True,
        )
        await _emit(
            plan_error(ctx.plan_id, str(exc), recoverable=True, credit_refunded=refund)
        )
