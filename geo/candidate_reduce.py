"""Rank then shrink before Matrix. ≥50% when the set is larger than the cap. PROJECT_SPEC §33."""

from __future__ import annotations

from dataclasses import dataclass, field

from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES
from cuvoy_contracts.enums import BudgetTier
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import ExtractedPreferences, GroupPlanning, TripControls

from app.geo.dbscan import cap_cluster_members, cluster_places
from app.providers.osm_filters import should_drop_candidate
from app.scoring.ranking import rank_places

MEAL_CATEGORIES = frozenset(
    {"restaurant", "cafe", "fast_food", "bar", "pub", "food_court"}
)
RELEVANT_CAP = 100
STRONG_CAP = 40
CLOSED_MARKERS = ("closed", "off", "disused")


@dataclass
class ReducedCandidates:
    relevant: list[Place]
    strong: list[Place]
    meal_places: list[Place]
    dropped_ids: list[str] = field(default_factory=list)
    clusters: list = field(default_factory=list)
    matrix_places: list[Place] = field(default_factory=list)


def _is_closed(place: Place) -> bool:
    hours = (place.opening_hours or "").strip().lower()
    if not hours:
        return False
    return any(marker == hours or marker in hours.split(";")[0] for marker in CLOSED_MARKERS)


def _is_meal(place: Place) -> bool:
    cat = place.category.lower()
    return cat in MEAL_CATEGORIES or cat.startswith("restaurant")


def reduce_candidates(
    places: list[Place],
    *,
    preferences: ExtractedPreferences | None = None,
    controls: TripControls | None = None,
    group: GroupPlanning | None = None,
    budget_tier: BudgetTier | None = None,
    hidden_gems: bool = False,
    interests: list[str] | None = None,
    destination_id: str | None = None,
) -> ReducedCandidates:
    """
    Filter closed places, rank, then shrink ~500 → ~100 relevant → ~40 strong.
    Matrix input is further capped per cluster (8–15) and globally (≤25).
    """
    open_places = [
        p
        for p in places
        if not _is_closed(p)
        and not should_drop_candidate(p.name, p.category, address=p.address)
    ]
    meals = [p for p in open_places if _is_meal(p)]
    attractions = [p for p in open_places if not _is_meal(p)] or list(open_places)

    prefs = preferences
    ctrl = controls
    gem = hidden_gems or (prefs.hidden_gems if prefs else False)
    if ctrl and ctrl.hidden_gems:
        gem = True
    tags = interests if interests is not None else (prefs.interests if prefs else [])
    grp = group if group is not None else (ctrl.group if ctrl else (prefs.group if prefs else None))
    tier = budget_tier
    if tier is None and ctrl and ctrl.daily_budget:
        tier = ctrl.daily_budget.tier
    if tier is None and prefs and prefs.budget:
        tier = prefs.budget.tier

    ranked = rank_places(
        attractions,
        interests=tags,
        group=grp,
        budget_tier=tier,
        hidden_gems=gem,
    )
    ranked_meals = rank_places(
        meals,
        interests=["food", *tags],
        group=grp,
        budget_tier=tier,
        hidden_gems=False,
    )

    n = len(ranked)
    relevant = ranked[: min(RELEVANT_CAP, n)]
    if n <= MAX_MATRIX_COORDINATES:
        strong = list(ranked)
    else:
        strong_n = min(STRONG_CAP, max(1, n // 2))
        strong = ranked[:strong_n]

    dropped = [p.id for p in ranked[len(strong) :]]
    clusters = cluster_places(strong, destination_id=destination_id)
    matrix_places = cap_cluster_members(strong, clusters)
    if len(matrix_places) > MAX_MATRIX_COORDINATES:
        matrix_places = matrix_places[:MAX_MATRIX_COORDINATES]

    return ReducedCandidates(
        relevant=relevant,
        strong=strong,
        meal_places=ranked_meals[:20],
        dropped_ids=dropped,
        clusters=clusters,
        matrix_places=matrix_places,
    )
