"""Schema-level itinerary checks after Pydantic parse. PROJECT_SPEC §29."""

from __future__ import annotations

from cuvoy_contracts.enrichment import ValidationIssue
from cuvoy_contracts.itinerary import Itinerary


def schema_issues(itinerary: Itinerary) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not itinerary.timezone:
        issues.append(
            ValidationIssue(code="missing_timezone", message="Itinerary timezone is required")
        )
    if not itinerary.days:
        issues.append(ValidationIssue(code="empty_itinerary", message="No days were scheduled"))
    return issues
