"""Liveness + dependency status. Always HTTP 200 so Render keep-alive stays green."""

from __future__ import annotations

import logging

from cuvoy_contracts.api import HealthResponse
from cuvoy_contracts.enums import HealthState
from fastapi import APIRouter, Request

from app.services.cache import CacheBackend, NullCache
from app.services.supabase import NullSupabase, SupabaseRest

logger = logging.getLogger("cuvoy.health")
router = APIRouter(tags=["health"])


def _overall(cache: HealthState, db: HealthState) -> HealthState:
    if cache == HealthState.OK and db == HealthState.OK:
        return HealthState.OK
    return HealthState.DEGRADED


def _from_bool(ok: bool) -> HealthState:
    return HealthState.OK if ok else HealthState.UNAVAILABLE


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    cache: CacheBackend = getattr(request.app.state, "cache", NullCache())
    supabase: SupabaseRest | NullSupabase = getattr(request.app.state, "supabase", NullSupabase())
    cache_state = _from_bool(await cache.ping())
    db_state = _from_bool(await supabase.ping())
    status = _overall(cache_state, db_state)
    logger.info(
        "health",
        extra={"cache_hit": False, "provider": "health", "cache": cache_state, "db": db_state},
    )
    return HealthResponse(status=status, cache=cache_state, db=db_state)
