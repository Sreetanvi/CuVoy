"""Intra-city transit limits; travel days exempt. PROJECT_SPEC §5.1."""

from __future__ import annotations

from cuvoy_contracts.enrichment import ValidationIssue
from cuvoy_contracts.enums import ItineraryItemType
from cuvoy_contracts.itinerary import Itinerary
from cuvoy_contracts.preferences import TripControls

from app.schedule.builder import max_leg_seconds


def geographic_issues(itinerary: Itinerary, controls: TripControls | None) -> list[ValidationIssue]:
    cap = max_leg_seconds(controls)
    if cap is None:
        return []
    issues: list[ValidationIssue] = []
    for day in itinerary.days:
        if day.is_travel_day:
            continue
        for index, item in enumerate(day.items):
            if item.type != ItineraryItemType.TRANSIT:
                continue
            buffered = item.travel_minutes_buffered
            if buffered is None and item.route is not None:
                buffered = item.route.duration_buffered_seconds // 60
            if buffered is not None and buffered * 60 > cap:
                issues.append(
                    ValidationIssue(
                        code="max_transit_exceeded",
                        message="Transit between stops exceeds the selected max transit",
                        path=f"days.{day.day_index}.items.{index}",
                    )
                )
    return issues
