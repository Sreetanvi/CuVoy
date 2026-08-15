"""Deterministic ranking: interests, budget, crowd, hidden gems. PROJECT_SPEC §6, §13."""

from __future__ import annotations

from cuvoy_contracts.enums import BudgetTier, CrowdLevel
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import GroupPlanning

from app.optimize.group_score import group_interest_score, interest_affinity

HIDDEN_GEM_CATEGORIES = frozenset(
    {"park", "garden", "artwork", "viewpoint", "market", "cafe", "gallery", "historic"}
)
TOURIST_HEAVY = frozenset({"theme_park", "attraction", "zoo", "hotel"})
PRIORITY_TOURIST = frozenset(
    {
        "attraction",
        "museum",
        "gallery",
        "viewpoint",
        "artwork",
        "theme_park",
        "zoo",
        "park",
        "garden",
        "historic",
        "restaurant",
        "cafe",
        "place_of_worship",
        "theatre",
        "cinema",
    }
)
CROWD_PENALTY = {
    CrowdLevel.VERY_QUIET: 0.0,
    CrowdLevel.QUIET: 0.0,
    CrowdLevel.MODERATE: 0.04,
    CrowdLevel.BUSY: 0.10,
    CrowdLevel.VERY_BUSY: 0.18,
}


def _budget_fit(place: Place, tier: BudgetTier | None) -> float:
    if tier is None:
        return 0.5
    cat = place.category.lower()
    expensive = cat in {"theme_park", "gallery"} or "fine" in place.name.lower()
    cheap = cat in {"park", "viewpoint", "place_of_worship", "temple", "garden"}
    if tier == BudgetTier.LOW:
        return 0.2 if expensive else (1.0 if cheap else 0.7)
    if tier == BudgetTier.HIGH:
        return 0.9 if expensive else 0.6
    return 0.75


def score_place(
    place: Place,
    *,
    interests: list[str] | None = None,
    group: GroupPlanning | None = None,
    budget_tier: BudgetTier | None = None,
    hidden_gems: bool = False,
    crowd_level: CrowdLevel | None = None,
) -> float:
    if group and group.enabled and group.travelers:
        interest = group_interest_score(place, group)
    else:
        interest = interest_affinity(place, interests or [])
    budget = _budget_fit(place, budget_tier)
    crowd = 1.0 - CROWD_PENALTY.get(crowd_level, 0.05)
    gem = 0.0
    cat = place.category.lower()
    if hidden_gems:
        if cat in HIDDEN_GEM_CATEGORIES or cat.startswith("historic"):
            gem = 0.25
        if cat in TOURIST_HEAVY:
            gem -= 0.15
    priority = 0.12 if cat in PRIORITY_TOURIST or cat.startswith("historic") else 0.0
    return 0.45 * interest + 0.25 * budget + 0.20 * crowd + gem + priority


def rank_places(
    places: list[Place],
    *,
    interests: list[str] | None = None,
    group: GroupPlanning | None = None,
    budget_tier: BudgetTier | None = None,
    hidden_gems: bool = False,
    crowd_by_id: dict[str, CrowdLevel] | None = None,
) -> list[Place]:
    crowds = crowd_by_id or {}

    def key(place: Place) -> float:
        return score_place(
            place,
            interests=interests,
            group=group,
            budget_tier=budget_tier,
            hidden_gems=hidden_gems,
            crowd_level=crowds.get(place.id),
        )

    return sorted(places, key=key, reverse=True)
