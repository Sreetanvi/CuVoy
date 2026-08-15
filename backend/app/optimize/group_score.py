"""Group satisfaction score. PROJECT_SPEC §13."""

from __future__ import annotations

from cuvoy_contracts.enums import GroupPriority
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import GroupPlanning, Traveler

INTEREST_CATEGORIES: dict[str, tuple[str, ...]] = {
    "history": ("museum", "historic", "castle", "fort", "monument", "temple", "palace", "gallery"),
    "heritage": ("museum", "historic", "castle", "fort", "monument", "temple", "palace"),
    "food": ("restaurant", "cafe", "market", "fast_food", "bar", "pub"),
    "nature": ("park", "garden", "beach", "viewpoint", "hiking", "zoo"),
    "shopping": ("shop", "mall", "market", "clothes"),
    "nightlife": ("bar", "pub", "nightclub", "theatre", "cinema"),
    "art": ("gallery", "artwork", "museum", "theatre"),
    "religion": ("place_of_worship", "temple", "mosque", "church", "shrine"),
    "adventure": ("hiking", "theme_park", "viewpoint", "beach"),
    "family": ("zoo", "theme_park", "park", "museum", "beach"),
}


def _blob(place: Place) -> str:
    return f"{place.category} {place.name}".lower()


def interest_affinity(place: Place, interests: list[str]) -> float:
    if not interests:
        return 0.5
    text = _blob(place)
    hits = 0.0
    for raw in interests:
        key = raw.strip().lower()
        tokens = INTEREST_CATEGORIES.get(key, (key,))
        if any(token in text for token in tokens):
            hits += 1.0
        elif key and key in text:
            hits += 0.6
    return min(1.0, hits / max(1, len(interests)) * 1.2)


def _traveler_score(place: Place, traveler: Traveler) -> float:
    return interest_affinity(place, traveler.interests)


def group_interest_score(place: Place, group: GroupPlanning) -> float:
    """
    Everyone: equal weight per traveler.
    Team lead: lead 50%, remaining 50% split among others.
    """
    travelers = group.travelers
    if not travelers:
        return 0.5
    scores = [_traveler_score(place, t) for t in travelers]
    if group.priority != GroupPriority.TEAM_LEAD:
        return sum(scores) / len(scores)
    leads = [i for i, t in enumerate(travelers) if t.is_team_lead]
    if not leads:
        return sum(scores) / len(scores)
    lead_score = scores[leads[0]]
    others = [s for i, s in enumerate(scores) if i not in set(leads)]
    other_mean = sum(others) / len(others) if others else lead_score
    return 0.5 * lead_score + 0.5 * other_mean


def group_score(
    place: Place,
    group: GroupPlanning,
    *,
    geographic_efficiency: float = 0.7,
    budget_fit: float = 0.7,
) -> float:
    """interest coverage + preference satisfaction + geographic efficiency + budget fit."""
    interest = group_interest_score(place, group)
    return 0.40 * interest + 0.25 * interest + 0.20 * geographic_efficiency + 0.15 * budget_fit
