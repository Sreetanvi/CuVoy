"""Save/list/share trips. Auth required except public slug read (PROJECT_SPEC §12, §7.15)."""

from cuvoy_contracts.api import PlanResult, SavedTrip, SaveTripRequest, SharedTrip, TripList
from fastapi import APIRouter, Depends, HTTPException

from app.deps import cache_dep, current_user_dep, supabase_dep
from app.services.auth import AuthUser
from app.services.cache import CacheBackend
from app.services.jobs import get_result
from app.services.supabase import NullSupabase, SupabaseRest
from app.services.trips import get_owned, get_shared, list_trips, save_trip

router = APIRouter()


@router.post("/trips", status_code=201)
async def create_trip(
    body: SaveTripRequest,
    user: AuthUser = Depends(current_user_dep),
    cache: CacheBackend = Depends(cache_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> SavedTrip:
    if body.user_id and body.user_id != user.id:
        raise HTTPException(status_code=403, detail="user_id does not match the signed-in account")
    result_payload = await get_result(cache, body.plan_id)
    if result_payload is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    result = PlanResult.model_validate(result_payload)
    saved = await save_trip(
        supabase,
        user,
        plan_id=body.plan_id,
        title=body.title,
        result=result,
    )
    if saved is None:
        raise HTTPException(status_code=503, detail="Trip storage is unavailable")
    return saved


@router.get("/trips")
async def get_trips(
    user: AuthUser = Depends(current_user_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> TripList:
    return await list_trips(supabase, user)


@router.get("/trips/shared/{slug}")
async def get_shared_trip(
    slug: str,
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> SharedTrip:
    shared = await get_shared(supabase, slug)
    if shared is None:
        raise HTTPException(status_code=404, detail="Shared trip not found")
    return shared


@router.get("/trips/{trip_id}")
async def get_owned_trip(
    trip_id: str,
    user: AuthUser = Depends(current_user_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> SharedTrip:
    owned = await get_owned(supabase, user, trip_id)
    if owned is None:
        raise HTTPException(status_code=404, detail="Saved trip not found")
    return owned
