"""Shared HTTP client + cache/db handles for the FastAPI process."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.services.cache import CacheBackend, NullCache, UpstashCache
from app.services.supabase import NullSupabase, SupabaseRest

_TIMEOUT = httpx.Timeout(10.0, connect=2.0)


def new_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=_TIMEOUT,
        headers={"user-agent": "CuVoy/0.1 (https://cuvoy.vercel.app)"},
        follow_redirects=False,
    )


def build_cache(settings: Settings, http: httpx.AsyncClient | None = None) -> CacheBackend:
    if not settings.cache_configured:
        return NullCache()
    return UpstashCache(settings.upstash_redis_rest_url, settings.upstash_redis_rest_token)


def build_supabase(settings: Settings, http: httpx.AsyncClient) -> SupabaseRest | NullSupabase:
    if not settings.db_configured:
        return NullSupabase()
    return SupabaseRest(settings.supabase_url, settings.supabase_service_role_key, http)
