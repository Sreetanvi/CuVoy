"""PDF is client-side; ICS is generated on the server. PROJECT_SPEC §7.4, §7.15."""

from __future__ import annotations

from cuvoy_contracts.api import PdfExportResponse
from cuvoy_contracts.constants import ICS_FILENAME
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.deps import cache_dep, supabase_dep
from app.export.ics import itinerary_to_ics
from app.export.pdf import build_pdf_document
from app.export.resolve import load_plan_result
from app.services.cache import CacheBackend
from app.services.supabase import NullSupabase, SupabaseRest

router = APIRouter()


@router.get("/plan/{plan_id}/export/pdf")
async def export_pdf(
    plan_id: str,
    cache: CacheBackend = Depends(cache_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> PdfExportResponse:
    result = await load_plan_result(cache, supabase, plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return build_pdf_document(result)


@router.get("/plan/{plan_id}/export/ics")
async def export_ics(
    plan_id: str,
    cache: CacheBackend = Depends(cache_dep),
    supabase: SupabaseRest | NullSupabase = Depends(supabase_dep),
) -> Response:
    result = await load_plan_result(cache, supabase, plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    body = itinerary_to_ics(result.itinerary, plan_id=plan_id).encode("utf-8")
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{ICS_FILENAME}"',
            "Cache-Control": "no-store",
        },
    )
