"""POST /api/v1/plan/{id}/regenerate — no extra user credit. PROJECT_SPEC §7.3."""

from __future__ import annotations

from cuvoy_contracts.api import PlanAccepted, PlanCreateRequest, RegenerateRequest
from cuvoy_contracts.enums import JobStatus
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.ai_gateway.gateway import AIGateway
from app.deps import ai_gateway_dep, cache_dep, external_dep, identity_dep
from app.pipeline.context import PipelineContext
from app.pipeline.regenerate import regenerate
from app.providers.client import ExternalData
from app.services import jobs
from app.services.budget import new_envelope, persist_budget
from app.services.cache import CacheBackend

router = APIRouter()


@router.post("/plan/{plan_id}/regenerate", status_code=202, response_model=None)
async def regenerate_plan(
    plan_id: str,
    body: RegenerateRequest,
    background: BackgroundTasks,
    cache: CacheBackend = Depends(cache_dep),
    identity: str = Depends(identity_dep),
    gateway: AIGateway = Depends(ai_gateway_dep),
    external: ExternalData = Depends(external_dep),
) -> PlanAccepted:
    job = await jobs.get_job(cache, plan_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    raw_request = job.get("request")
    if not isinstance(raw_request, dict):
        raise HTTPException(status_code=409, detail="Original plan request is not available")
    request = PlanCreateRequest.model_validate(raw_request)
    budget = new_envelope(plan_id, regeneration=True)
    await persist_budget(cache, budget)
    await jobs.update_job(cache, plan_id, status=JobStatus.RUNNING.value, progress=45)
    ctx = PipelineContext(
        plan_id=plan_id,
        request=request,
        budget=budget,
        cache=cache,
        external=external,
        gateway=gateway,
        identity=identity,
        regeneration=True,
    )

    async def _run() -> None:
        await regenerate(ctx, body)

    background.add_task(_run)
    return PlanAccepted(plan_id=plan_id, status=JobStatus.RUNNING)
