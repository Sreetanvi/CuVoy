"""Request-scoped dependencies (PROJECT_SPEC §7.5, §7.19)."""

from fastapi import Depends, Request

from app.ai_gateway.gateway import AIGateway
from app.config import Settings, get_settings
from app.jsonlog import request_id_ctx
from app.providers.client import ExternalData
from app.services.auth import AuthUser, require_user, resolve_user
from app.services.cache import CacheBackend, NullCache
from app.services.identity import identity_from_request
from app.services.supabase import NullSupabase, SupabaseRest


def settings_dep() -> Settings:
    return get_settings()


def request_id_dep(request: Request) -> str:
    header = request.headers.get("x-request-id")
    return header or request_id_ctx.get() or ""


def cache_dep(request: Request) -> CacheBackend:
    return getattr(request.app.state, "cache", NullCache())


def supabase_dep(request: Request) -> SupabaseRest | NullSupabase:
    return getattr(request.app.state, "supabase", NullSupabase())


async def optional_user_dep(
    request: Request,
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> AuthUser | None:
    return await resolve_user(request, supabase)


async def current_user_dep(
    request: Request,
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> AuthUser:
    return await require_user(request, supabase)


async def identity_dep(
    request: Request,
    user: AuthUser | None = Depends(optional_user_dep),
) -> str:
    return identity_from_request(request, user_id=user.id if user else None)


def ai_gateway_dep(request: Request) -> AIGateway:
    gateway = getattr(request.app.state, "ai_gateway", None)
    if gateway is None:
        raise RuntimeError("AI gateway is not initialized")
    return gateway


def external_dep(request: Request) -> ExternalData:
    external = getattr(request.app.state, "external", None)
    if external is None:
        raise RuntimeError("External data client is not initialized")
    return external
