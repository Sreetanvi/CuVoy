"""Load a plan result from cache, then saved trips (PROJECT_SPEC §7.12)."""

from __future__ import annotations

from cuvoy_contracts.api import PlanResult

from app.services import jobs
from app.services.cache import CacheBackend
from app.services.supabase import NullSupabase, SupabaseRest


async def load_plan_result(
    cache: CacheBackend,
    supabase: SupabaseRest | NullSupabase,
    plan_id: str,
) -> PlanResult | None:
    cached = await jobs.get_result(cache, plan_id)
    if isinstance(cached, dict):
        return PlanResult.model_validate(cached)
    rows = await supabase.select("trips", filters={"plan_id": plan_id}, limit=1)
    if not rows:
        return None
    payload = rows[0].get("payload")
    if not isinstance(payload, dict):
        return None
    return PlanResult.model_validate(payload)
