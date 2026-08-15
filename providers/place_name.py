"""Human-readable place labels from OSM tags / Place fields."""

from __future__ import annotations

import re
from typing import Any

from cuvoy_contracts.place import Place

OSM_ID = re.compile(r"^(osm:)?(node|way|relation)/", re.IGNORECASE)
GENERIC = frozenset({"", "unnamed place", "unknown place", "poi", "yes"})


def is_raw_place_id(value: str | None) -> bool:
    if not value:
        return True
    stripped = value.strip()
    return bool(OSM_ID.match(stripped) or stripped.startswith("osm:"))


def _titleize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _usable(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in GENERIC or is_raw_place_id(text):
        return None
    return text


def name_from_tags(tags: dict[str, Any] | None) -> str | None:
    if not tags:
        return None
    for key in ("name", "name:en", "int_name", "loc_name"):
        found = _usable(tags.get(key))
        if found:
            return found
    for key in ("amenity", "tourism", "leisure", "historic", "shop"):
        found = _usable(tags.get(key))
        if found:
            return _titleize(found)
    return None


def unnamed_location(place_id: str | None = None) -> str:
    if place_id:
        return f"Unnamed Location ({place_id})"
    return "Unnamed Location"


def resolve_candidate_name(
    *,
    name: str | None = None,
    tags: dict[str, Any] | None = None,
    category: str | None = None,
    place_id: str | None = None,
) -> str:
    """name || tags.name || tags['name:en'] || amenity || tourism || Unnamed Location (id)."""
    direct = _usable(name)
    if direct:
        return direct
    tagged = name_from_tags(tags)
    if tagged:
        return tagged
    cat = _usable(category)
    if cat:
        return _titleize(cat)
    return unnamed_location(place_id)


def display_place_name(place: Place | None, tags: dict[str, Any] | None = None) -> str:
    if place is None:
        return resolve_candidate_name(tags=tags)
    return resolve_candidate_name(
        name=place.name,
        tags=tags,
        category=place.category,
        place_id=place.id,
    )
