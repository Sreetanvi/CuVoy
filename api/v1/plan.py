"""POST/GET plan + SSE/poll status. PROJECT_SPEC §7.4, §7.13."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from cuvoy_contracts.api import PlanAccepted, PlanCreateRequest, PlanError, PlanResult, PlanStatus
from cuvoy_contracts.enums import JobStatus, SseEventType
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.ai_gateway.gateway import AIGateway
from app.deps import (
    ai_gateway_dep,
    cache_dep,
    external_dep,
    identity_dep,
    supabase_dep,
)
from app.pipeline.context import PipelineContext
from app.pipeline.orchestrator import run_pipeline
from app.providers.client import ExternalData
from app.services import idempotency, jobs
from app.services.budget import consume_credit, new_envelope, persist_budget
from app.services.cache import CacheBackend
from app.services.supabase import NullSupabase, SupabaseRest

router = APIRouter()


def _plan_error(status: int, message: str, *, retryable: bool, refunded: bool) -> JSONResponse:
    body = PlanError(
        error="plan_error",
        retryable=retryable,
        credit_refunded=refunded,
        message=message,
    )
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


async def _execute(ctx: PipelineContext) -> None:
    await run_pipeline(ctx)


@router.post("/plan", status_code=202, response_model=None)
async def create_plan(
    body: PlanCreateRequest,
    background: BackgroundTasks,
    cache: CacheBackend = Depends(cache_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
    identity: str = Depends(identity_dep),
    gateway: AIGateway = Depends(ai_gateway_dep),
    external: ExternalData = Depends(external_dep),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlanAccepted | JSONResponse:
    if idempotency_key:
        existing = await idempotency.begin(cache, idempotency_key)
        if isinstance(existing, dict) and existing.get("status") == "complete":
            return PlanAccepted(
                plan_id=str(existing.get("plan_id")),
                status=JobStatus(existing.get("job_status") or JobStatus.QUEUED.value),
            )
        if isinstance(existing, dict) and existing.get("status") == "in_flight":
            plan_id = existing.get("plan_id")
            if plan_id:
                return PlanAccepted(plan_id=str(plan_id), status=JobStatus.QUEUED)

    credits = await consume_credit(cache, identity)
    if not credits.allowed:
        return _plan_error(429, credits.message, retryable=True, refunded=False)

    record = await jobs.create_job(cache, supabase, identity=identity)
    plan_id = str(record["job_id"])
    budget = new_envelope(plan_id)
    await persist_budget(cache, budget)
    await jobs.update_job(cache, plan_id, request=body.model_dump(mode="json"))
    if idempotency_key:
        await idempotency.store_result(
            cache,
            idempotency_key,
            {"plan_id": plan_id, "job_status": JobStatus.QUEUED.value},
        )

    ctx = PipelineContext(
        plan_id=plan_id,
        request=body,
        budget=budget,
        cache=cache,
        external=external,
        gateway=gateway,
        identity=identity,
    )
    background.add_task(_execute, ctx)
    return PlanAccepted(plan_id=plan_id, status=JobStatus.QUEUED)


@router.get("/plan/{plan_id}", response_model=None)
async def get_plan(
    plan_id: str, cache: CacheBackend = Depends(cache_dep)
) -> PlanResult | JSONResponse:
    result = await jobs.get_result(cache, plan_id)
    if result is not None:
        return PlanResult.model_validate(result)
    job = await jobs.get_job(cache, plan_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if job.get("status") == JobStatus.FAILED.value:
        return _plan_error(
            500,
            str(job.get("error") or "Planning failed"),
            retryable=True,
            refunded=True,
        )
    raise HTTPException(status_code=409, detail="Plan is still running")


@router.get("/plan/{plan_id}/status", response_model=None)
async def plan_status(
    plan_id: str,
    request: Request,
    cache: CacheBackend = Depends(cache_dep),
) -> PlanStatus | StreamingResponse:
    job = await jobs.get_job(cache, plan_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    accept = request.headers.get("accept", "")
    stream = request.query_params.get("stream") == "1" or "text/event-stream" in accept
    if not stream:
        stage = job.get("stage")
        from cuvoy_contracts.enums import PipelineStage

        parsed_stage = None
        if stage:
            try:
                parsed_stage = PipelineStage(stage)
            except ValueError:
                parsed_stage = None
        try:
            status = JobStatus(job.get("status") or JobStatus.QUEUED.value)
        except ValueError:
            status = JobStatus.QUEUED
        return PlanStatus(
            plan_id=plan_id,
            status=status,
            stage=parsed_stage,
            progress=int(job.get("progress") or 0),
            resumable=bool(job.get("resumable")),
        )

    async def events() -> AsyncIterator[str]:
        sent = 0
        while True:
            record = await jobs.get_job(cache, plan_id)
            if record is None:
                break
            items = list(record.get("events") or [])
            for item in items[sent:]:
                event_name = item.get("event") or SseEventType.STAGE_START.value
                yield f"event: {event_name}\ndata: {json.dumps(item)}\n\n"
                sent += 1
            status = record.get("status")
            if status in {JobStatus.COMPLETE.value, JobStatus.FAILED.value}:
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
