"""On-demand planning jobs + Upstash stage checkpoints (PROJECT_SPEC §7.2, §7.12)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from cuvoy_contracts.constants import TTL_AI_ITINERARY, TTL_CHECKPOINT
from cuvoy_contracts.enums import JobStatus, PipelineStage

from app.services.cache import CacheBackend, cache_get_json, cache_set_json
from app.services.supabase import NullSupabase, SupabaseRest

STAGES: tuple[PipelineStage, ...] = (
    PipelineStage.EXTRACT,
    PipelineStage.DISCOVER,
    PipelineStage.REDUCE,
    PipelineStage.CLUSTER_MATRIX,
    PipelineStage.OPTIMIZE_SCHEDULE,
    PipelineStage.NARRATIVE_VALIDATE,
)

# Cache-down fallback so generation still works (PROJECT_SPEC §31 / §7.12).
_LOCAL: dict[str, dict[str, Any]] = {}

_PROGRESS = {
    PipelineStage.EXTRACT: 15,
    PipelineStage.DISCOVER: 30,
    PipelineStage.REDUCE: 45,
    PipelineStage.CLUSTER_MATRIX: 60,
    PipelineStage.OPTIMIZE_SCHEDULE: 80,
    PipelineStage.NARRATIVE_VALIDATE: 95,
}


def job_key(job_id: str) -> str:
    return f"job:{job_id}"


def result_key(job_id: str) -> str:
    return f"result:{job_id}"


def checkpoint_key(job_id: str, stage: PipelineStage | str) -> str:
    name = stage.value if isinstance(stage, PipelineStage) else stage
    return f"checkpoint:{job_id}:{name}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def create_job(
    cache: CacheBackend,
    supabase: SupabaseRest | NullSupabase,
    *,
    identity: str,
) -> dict[str, Any]:
    job_id = str(uuid4())
    record = {
        "job_id": job_id,
        "status": JobStatus.QUEUED.value,
        "stage": None,
        "progress": 0,
        "resumable": False,
        "identity_hash": identity,
        "updated_at": _now(),
    }
    await cache_set_json(cache, job_key(job_id), record, TTL_CHECKPOINT)
    _LOCAL[job_key(job_id)] = record
    user_id = identity[5:] if identity.startswith("user:") else None
    await supabase.insert(
        "planning_jobs",
        {
            "id": job_id,
            "user_id": user_id,
            "identity_hash": identity,
            "status": record["status"],
            "stage": None,
            "progress": 0,
        },
    )
    return record


async def get_job(cache: CacheBackend, job_id: str) -> dict[str, Any] | None:
    payload = await cache_get_json(cache, job_key(job_id))
    if isinstance(payload, dict):
        _LOCAL[job_key(job_id)] = payload
        return payload
    stored = _LOCAL.get(job_key(job_id))
    return stored if isinstance(stored, dict) else None


async def update_job(cache: CacheBackend, job_id: str, **fields: Any) -> dict[str, Any] | None:
    record = await get_job(cache, job_id)
    if record is None:
        return None
    record.update(fields)
    record["updated_at"] = _now()
    await cache_set_json(cache, job_key(job_id), record, TTL_CHECKPOINT)
    _LOCAL[job_key(job_id)] = record
    return record


async def append_event(cache: CacheBackend, job_id: str, event: dict[str, Any]) -> None:
    record = await get_job(cache, job_id)
    events = list(record.get("events") or []) if record else []
    events.append(event)
    await update_job(cache, job_id, events=events[-40:])


async def save_result(cache: CacheBackend, job_id: str, payload: dict[str, Any]) -> None:
    await cache_set_json(cache, result_key(job_id), payload, TTL_AI_ITINERARY)
    _LOCAL[result_key(job_id)] = payload
    await update_job(
        cache,
        job_id,
        status=JobStatus.COMPLETE.value,
        progress=100,
        resumable=False,
        stage=PipelineStage.NARRATIVE_VALIDATE.value,
    )


async def get_result(cache: CacheBackend, job_id: str) -> dict[str, Any] | None:
    payload = await cache_get_json(cache, result_key(job_id))
    if isinstance(payload, dict):
        return payload
    stored = _LOCAL.get(result_key(job_id))
    return stored if isinstance(stored, dict) else None


async def write_checkpoint(
    cache: CacheBackend,
    job_id: str,
    stage: PipelineStage,
    payload: dict[str, Any],
) -> None:
    await cache_set_json(cache, checkpoint_key(job_id, stage), payload, TTL_CHECKPOINT)
    _LOCAL[checkpoint_key(job_id, stage)] = payload
    await update_job(
        cache,
        job_id,
        status=JobStatus.RUNNING.value,
        stage=stage.value,
        progress=_PROGRESS[stage],
        resumable=True,
        last_checkpoint=stage.value,
    )


async def read_checkpoint(
    cache: CacheBackend,
    job_id: str,
    stage: PipelineStage,
) -> dict[str, Any] | None:
    payload = await cache_get_json(cache, checkpoint_key(job_id, stage))
    if isinstance(payload, dict):
        return payload
    stored = _LOCAL.get(checkpoint_key(job_id, stage))
    return stored if isinstance(stored, dict) else None


async def latest_completed_stage(cache: CacheBackend, job_id: str) -> PipelineStage | None:
    record = await get_job(cache, job_id)
    if not record:
        return None
    name = record.get("last_checkpoint")
    if not name:
        return None
    try:
        return PipelineStage(name)
    except ValueError:
        return None


def next_stage(current: PipelineStage | None) -> PipelineStage | None:
    if current is None:
        return STAGES[0]
    try:
        index = STAGES.index(current)
    except ValueError:
        return STAGES[0]
    if index + 1 >= len(STAGES):
        return None
    return STAGES[index + 1]
