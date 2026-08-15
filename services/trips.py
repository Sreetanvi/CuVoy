"""Saved trips + UUID share slugs (PROJECT_SPEC §12, §7.15)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from cuvoy_contracts.api import PlanResult, SavedTrip, SharedTrip, TripList
from cuvoy_contracts.constants import PUBLIC_ORIGIN

from app.services.auth import AuthUser
from app.services.supabase import NullSupabase, SupabaseRest


def trip_share_url(slug: str) -> str:
    return f"{PUBLIC_ORIGIN}/trip/{slug}"


def _row_trip_id(row: dict[str, Any]) -> str:
    return str(row.get("id") or row.get("trip_id") or "").strip()


def saved_from_row(row: dict[str, Any]) -> SavedTrip:
    trip_id = _row_trip_id(row)
    slug = str(row.get("slug") or trip_id).strip()
    plan_id = row.get("plan_id")
    return SavedTrip(
        trip_id=trip_id,
        slug=slug,
        title=str(row.get("title") or "Untitled trip"),
        plan_id=str(plan_id) if plan_id else None,
        share_url=trip_share_url(slug) if slug else None,
    )


async def ensure_profile(supabase: SupabaseRest | NullSupabase, user: AuthUser) -> None:
    await supabase.upsert(
        "users",
        {
            "id": user.id,
            "email": user.email,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )


def default_title(result: PlanResult, requested: str | None) -> str:
    if requested and requested.strip():
        return requested.strip()[:120]
    if result.itinerary.days and result.itinerary.days[0].city:
        return f"Trip to {result.itinerary.days[0].city}"
    return "Saved trip"


async def save_trip(
    supabase: SupabaseRest | NullSupabase,
    user: AuthUser,
    *,
    plan_id: str,
    title: str | None,
    result: PlanResult,
) -> SavedTrip | None:
    await ensure_profile(supabase, user)
    existing = await supabase.select(
        "trips",
        filters={"user_id": user.id, "plan_id": plan_id},
        limit=1,
    )
    resolved_title = default_title(result, title)
    payload = result.model_dump(mode="json")
    if existing:
        row = existing[0]
        updated = await supabase.patch(
            "trips",
            {"id": str(row["id"])},
            {"title": resolved_title, "payload": payload},
        )
        if not updated and not isinstance(supabase, NullSupabase):
            return None
        confirmed = await supabase.select("trips", filters={"id": str(row["id"])}, limit=1)
        if not confirmed:
            return None
        return saved_from_row({**confirmed[0], "title": resolved_title, "payload": payload})

    trip_id = str(uuid4())
    slug = str(uuid4())
    inserted = await supabase.insert(
        "trips",
        {
            "id": trip_id,
            "user_id": user.id,
            "plan_id": plan_id,
            "slug": slug,
            "title": resolved_title,
            "payload": payload,
        },
    )
    if not inserted:
        return None
    confirmed = await supabase.select(
        "trips",
        filters={"id": str(inserted.get("id") or trip_id)},
        limit=1,
    )
    if not confirmed:
        return None
    return saved_from_row(confirmed[0])


async def list_trips(supabase: SupabaseRest | NullSupabase, user: AuthUser) -> TripList:
    rows = await supabase.select(
        "trips",
        filters={"user_id": user.id},
        order="created_at.desc",
    )
    return TripList(trips=[saved_from_row(row) for row in rows])


def _shared_from_row(row: dict[str, Any], *, read_only: bool) -> SharedTrip | None:
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return None
    return SharedTrip(
        trip=saved_from_row(row),
        result=PlanResult.model_validate(payload),
        read_only=read_only,
    )


async def get_shared(supabase: SupabaseRest | NullSupabase, slug: str) -> SharedTrip | None:
    rows = await supabase.select("trips", filters={"slug": slug}, limit=1)
    if not rows:
        rows = await supabase.select("trips", filters={"id": slug}, limit=1)
    if not rows:
        return None
    return _shared_from_row(rows[0], read_only=True)


async def get_owned(
    supabase: SupabaseRest | NullSupabase,
    user: AuthUser,
    key: str,
) -> SharedTrip | None:
    for field in ("id", "slug", "plan_id"):
        rows = await supabase.select(
            "trips",
            filters={field: key, "user_id": user.id},
            limit=1,
        )
        if rows:
            owned = _shared_from_row(rows[0], read_only=False)
            if owned is not None:
                return owned
    return None


async def purge_user_data(supabase: SupabaseRest | NullSupabase, user_id: str) -> dict[str, int]:
    exports = await supabase.delete("exports", filters={"user_id": user_id})
    trips = await supabase.delete("trips", filters={"user_id": user_id})
    jobs = await supabase.delete("planning_jobs", filters={"user_id": user_id})
    await supabase.delete("users", filters={"id": user_id})
    auth_deleted = await supabase.delete_auth_user(user_id)
    return {
        "exports": exports,
        "trips": trips,
        "planning_jobs": jobs,
        "auth_user": 1 if auth_deleted else 0,
    }
