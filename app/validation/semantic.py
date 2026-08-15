"""Meal windows, ordered times, dwell present. PROJECT_SPEC §5."""

from __future__ import annotations

from cuvoy_contracts.enrichment import ValidationIssue
from cuvoy_contracts.enums import ItineraryItemType
from cuvoy_contracts.itinerary import Itinerary


def semantic_issues(itinerary: Itinerary) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for day in itinerary.days:
        if day.is_travel_day:
            continue
        types = [item.type for item in day.items]
        if ItineraryItemType.ACTIVITY not in types:
            issues.append(
                ValidationIssue(
                    code="no_activities",
                    message=f"Day {day.day_index} has no activities",
                    path=f"days.{day.day_index}",
                )
            )
        if ItineraryItemType.MEAL not in types:
            issues.append(
                ValidationIssue(
                    code="missing_meals",
                    message=f"Day {day.day_index} is missing a meal block",
                    path=f"days.{day.day_index}",
                )
            )
        previous = None
        for index, item in enumerate(day.items):
            if item.start.local_time > item.end.local_time:
                issues.append(
                    ValidationIssue(
                        code="inverted_times",
                        message="Item end is before start",
                        path=f"days.{day.day_index}.items.{index}",
                    )
                )
            if item.type == ItineraryItemType.ACTIVITY and not item.dwell_minutes:
                issues.append(
                    ValidationIssue(
                        code="missing_dwell",
                        message="Activity is missing dwell time",
                        path=f"days.{day.day_index}.items.{index}",
                    )
                )
            if previous and item.start.local_time < previous:
                issues.append(
                    ValidationIssue(
                        code="out_of_order",
                        message="Items are not in time order",
                        path=f"days.{day.day_index}.items.{index}",
                    )
                )
            previous = item.start.local_time
    return issues
