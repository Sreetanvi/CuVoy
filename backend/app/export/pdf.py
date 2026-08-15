"""Client-side PDF document model. No server pixels. PROJECT_SPEC §12, §7.15."""

from __future__ import annotations

from cuvoy_contracts.api import (
    PdfDayBlock,
    PdfExportResponse,
    PdfRouteLabel,
    PdfStopLine,
    PlanResult,
)
from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.constants import AI_DISCLAIMER, COST_LABEL_UI
from cuvoy_contracts.enums import CostLabel, ItineraryItemType
from cuvoy_contracts.itinerary import ItineraryItem

from app.export.ics import STOP_TYPES
from app.schedule.clock import clock_hm, timezone_abbrev


def _cost_display(cost: CostAmount | None) -> tuple[str | None, str | None]:
    if cost is None:
        return None, None
    label = COST_LABEL_UI.get(cost.label.value, cost.label.value)
    if cost.label == CostLabel.UNAVAILABLE or cost.amount is None:
        return label, label
    amount = int(cost.amount) if cost.amount == int(cost.amount) else cost.amount
    return f"{amount} {cost.currency} ({label})", label


def _is_pdf_stop(item: ItineraryItem) -> bool:
    if item.type in {ItineraryItemType.TRANSIT, ItineraryItemType.BREAK} and item.place is None:
        return False
    return item.type in STOP_TYPES or item.place is not None


def _local_labeled(local_time: str, abbrev: str) -> str:
    return f"{clock_hm(local_time)} {abbrev}"


def build_pdf_document(result: PlanResult) -> PdfExportResponse:
    itinerary = result.itinerary
    city = next((day.city for day in itinerary.days if day.city), None)
    title = f"Trip to {city}" if city else "CuVoy itinerary"
    days: list[PdfDayBlock] = []
    for day in itinerary.days:
        abbrev = timezone_abbrev(day.timezone or itinerary.timezone, day.date)
        include_transport = bool(day.daily_cost and day.daily_cost.transport_shown)
        stops: list[PdfStopLine] = []
        for item in day.items:
            if not _is_pdf_stop(item):
                continue
            heading = item.title or (item.place.name if item.place else "Stop")
            cost_text, cost_label = _cost_display(item.cost)
            if item.type == ItineraryItemType.TRANSIT and not include_transport:
                cost_text, cost_label = None, None
            stops.append(
                PdfStopLine(
                    start_local=_local_labeled(item.start.local_time, abbrev),
                    end_local=_local_labeled(item.end.local_time, abbrev),
                    title=heading,
                    notes=item.reason,
                    cost=cost_text,
                    cost_label=cost_label,
                )
            )
        daily_total = None
        if day.daily_cost:
            total = (
                day.daily_cost.total_including_transport
                if include_transport
                else day.daily_cost.total_excluding_transport
            )
            if total is not None:
                daily_total = f"{total} {day.daily_cost.currency}"
        days.append(
            PdfDayBlock(
                day_index=day.day_index,
                date=day.date,
                timezone=day.timezone or itinerary.timezone,
                timezone_abbrev=abbrev,
                city=day.city,
                stops=stops,
                daily_total=daily_total,
            )
        )

    route_labels: list[PdfRouteLabel] = []
    for leg in result.routes:
        minutes = max(1, round(leg.duration_buffered_seconds / 60))
        distance = None
        if leg.distance_meters >= 1000:
            distance = f"{leg.distance_meters / 1000:.1f} km"
        elif leg.distance_meters:
            distance = f"{leg.distance_meters} m"
        route_labels.append(
            PdfRouteLabel(
                from_place_id=leg.from_place_id,
                to_place_id=leg.to_place_id,
                duration_label=f"{minutes} min",
                distance_label=distance,
            )
        )

    return PdfExportResponse(
        plan_id=result.plan_id,
        renderer="client",
        title=title,
        logo_placement="corner",
        disclaimer=AI_DISCLAIMER,
        timezone=result.timezone or itinerary.timezone,
        days=days,
        route_labels=route_labels,
    )
