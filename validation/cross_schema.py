"""Cross-schema gate: times, costs, geography, provenance. PROJECT_SPEC §29."""

from __future__ import annotations

from cuvoy_contracts.enrichment import ValidationIssue, ValidationReport
from cuvoy_contracts.enums import CostLabel
from cuvoy_contracts.itinerary import Itinerary
from cuvoy_contracts.preferences import TripControls

from app.validation.geographic import geographic_issues
from app.validation.provenance import provenance_issues
from app.validation.schema import schema_issues
from app.validation.semantic import semantic_issues

BLOCKING = {
    "missing_timezone",
    "empty_itinerary",
    "inverted_times",
    "missing_place",
}


def cost_issues(itinerary: Itinerary) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for day in itinerary.days:
        for index, item in enumerate(day.items):
            cost = item.cost
            if cost is None:
                continue
            if cost.label == CostLabel.UNAVAILABLE and cost.amount is not None:
                issues.append(
                    ValidationIssue(
                        code="unavailable_has_amount",
                        message="Unavailable cost must not include an amount",
                        path=f"days.{day.day_index}.items.{index}.cost",
                    )
                )
    return issues


def validate_plan(itinerary: Itinerary, controls: TripControls | None) -> ValidationReport:
    issues = [
        *schema_issues(itinerary),
        *semantic_issues(itinerary),
        *geographic_issues(itinerary, controls),
        *provenance_issues(itinerary),
        *cost_issues(itinerary),
    ]
    blocking = [issue for issue in issues if issue.code in BLOCKING]
    return ValidationReport(valid=len(blocking) == 0, issues=issues)
