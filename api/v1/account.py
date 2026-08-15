"""GDPR account deletion (PROJECT_SPEC §12, §7.19)."""

from datetime import UTC, datetime, timedelta

from cuvoy_contracts.api import AccountDeleteResponse
from fastapi import APIRouter, Depends

from app.deps import cache_dep, current_user_dep, supabase_dep
from app.services.auth import AuthUser
from app.services.budget import credits_key
from app.services.cache import CacheBackend
from app.services.supabase import NullSupabase, SupabaseRest
from app.services.trips import purge_user_data

router = APIRouter()


async def invalidate_user_cache(cache: CacheBackend, user_id: str) -> None:
    identity = f"user:{user_id}"
    today = datetime.now(UTC).date()
    for days in range(0, 3):
        await cache.delete(credits_key(identity, today - timedelta(days=days)))
    await cache.delete(f"session:{identity}")


@router.delete("/account")
async def delete_account(
    user: AuthUser = Depends(current_user_dep),
    cache: CacheBackend = Depends(cache_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> AccountDeleteResponse:
    purged = await purge_user_data(supabase, user.id)
    await invalidate_user_cache(cache, user.id)
    return AccountDeleteResponse(deleted=True, trips_purged=int(purged.get("trips") or 0))
