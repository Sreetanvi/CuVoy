"""Supabase Auth JWT validation for protected routes (PROJECT_SPEC §12, §7.19)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from app.services.supabase import NullSupabase, SupabaseRest

AUTH_REQUIRED = {
    "error": "auth_required",
    "message": "Login is required to save or list trips.",
}


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None = None
    access_token: str | None = None


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    return token or None


def user_from_payload(payload: dict) -> AuthUser | None:
    user_id = payload.get("id")
    if not user_id:
        return None
    email = payload.get("email")
    return AuthUser(id=str(user_id), email=str(email) if email else None)


async def resolve_user(
    request: Request,
    supabase: SupabaseRest | NullSupabase,
) -> AuthUser | None:
    token = bearer_token(request)
    if not token:
        return None
    payload = await supabase.auth_user(token)
    if not payload:
        return None
    user = user_from_payload(payload)
    if user is None:
        return None
    return AuthUser(id=user.id, email=user.email, access_token=token)


async def require_user(
    request: Request,
    supabase: SupabaseRest | NullSupabase,
) -> AuthUser:
    token = bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED)
    payload = await supabase.auth_user(token)
    user = user_from_payload(payload) if payload else None
    if user is not None:
        user = AuthUser(id=user.id, email=user.email, access_token=token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "auth_invalid",
                "message": "Session expired. Sign in again to continue.",
            },
        )
    return user
