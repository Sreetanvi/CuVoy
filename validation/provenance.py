"""Every scheduled stop must have a non-LLM place source. PROJECT_SPEC §8."""

from __future__ import annotations

from cuvoy_contracts.enrichment import ValidationIssue
from cuvoy_contracts.enums import ItineraryItemType
from cuvoy_contracts.itinerary import Itinerary


def provenance_issues(itinerary: Itinerary) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for day in itinerary.days:
        for index, item in enumerate(day.items):
            if item.type != ItineraryItemType.ACTIVITY:
                continue
            if item.place is None:
                issues.append(
                    ValidationIssue(
                        code="missing_place",
                        message="Activity has no place",
                        path=f"days.{day.day_index}.items.{index}",
                    )
                )
                continue
            if not item.place.source:
                issues.append(
                    ValidationIssue(
                        code="missing_source",
                        message="Place is missing a data source",
                        path=f"days.{day.day_index}.items.{index}",
                    )
                )
    return issues
