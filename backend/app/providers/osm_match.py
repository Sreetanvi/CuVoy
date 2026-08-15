"""Mapbox–OSM identity: proximity + category only. Never LLM. PROJECT_SPEC §34."""

from __future__ import annotations

from cuvoy_contracts.constants import OSM_MATCH_MAX_METERS
from cuvoy_contracts.place import Place

from app.providers.geo import haversine_m

GROUPS: dict[str, frozenset[str]] = {
    "museum": frozenset({"museum", "gallery", "arts_centre", "artwork"}),
    "food": frozenset({"restaurant", "cafe", "fast_food", "food", "bar", "pub"}),
    "worship": frozenset(
        {"place_of_worship", "temple", "church", "mosque", "shrine", "cathedral"}
    ),
    "park": frozenset({"park", "garden", "nature_reserve", "viewpoint"}),
    "attraction": frozenset({"attraction", "theme_park", "zoo", "monument", "castle"}),
    "historic": frozenset({"historic", "memorial", "ruins", "archaeological_site"}),
}


def coarse_category(category: str) -> str:
    lowered = category.lower().split(",")[0].strip()
    if lowered.startswith("historic:"):
        lowered = "historic"
    for group, members in GROUPS.items():
        if lowered == group or lowered in members:
            return group
    return lowered


def match_osm(
    candidate: Place,
    osm_places: list[Place],
    *,
    max_meters: float = OSM_MATCH_MAX_METERS,
) -> Place | None:
    want = coarse_category(candidate.category)
    limit = max_meters
    if want == "poi":
        limit = min(max_meters, 75.0)
    best: Place | None = None
    best_d = limit
    for osm in osm_places:
        if want != "poi" and coarse_category(osm.category) != want:
            continue
        distance = haversine_m(candidate.lat, candidate.lng, osm.lat, osm.lng)
        if distance <= best_d:
            best = osm
            best_d = distance
    return best


def enrich_from_osm(candidate: Place, osm: Place) -> Place:
    """Copy verified OSM hours/contact onto a Mapbox candidate. Keep Mapbox id."""
    return candidate.model_copy(
        update={
            "opening_hours": osm.opening_hours or candidate.opening_hours,
            "website": osm.website or candidate.website,
            "phone": osm.phone or candidate.phone,
            "address": candidate.address or osm.address,
            "category": candidate.category if candidate.category != "poi" else osm.category,
        }
    )
