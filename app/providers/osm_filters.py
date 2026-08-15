"""Reject industrial / residential / non-tourist OSM nodes. PROJECT_SPEC §8, §31."""

from __future__ import annotations

import re
from typing import Any

INDUSTRIAL_MAN_MADE = frozenset(
    {"works", "wastewater_plant", "warehouse", "chimney", "silo", "storage_tank"}
)
INDUSTRIAL_NAME = re.compile(
    r"\b("
    r"factory|factories|manufacturer|manufacturers|industries|industry|industrial|"
    r"pvt\.?\s*ltd|works|warehouse|godown"
    r")\b",
    re.IGNORECASE,
)
INDUSTRIAL_CATEGORIES = frozenset(
    {
        "industrial",
        "factory",
        "works",
        "office",
        "warehouse",
        "craft",
        "manufacturer",
        "workshop",
    }
)
RESIDENTIAL_CATEGORIES = frozenset(
    {
        "residential",
        "apartments",
        "apartment",
        "hostel",
        "dormitory",
        "student_accommodation",
        "social_facility",
    }
)
RESIDENTIAL_BUILDINGS = frozenset({"residential", "apartments", "dormitory"})
RESIDENTIAL_AMENITY = frozenset({"dormitory", "social_facility", "student_accommodation"})
HOTEL_OR_RESORT = re.compile(r"\b(hotel|resort|inn)\b", re.IGNORECASE)
# Always drop: hostels, PGs, dorms — never rescued by hotel/resort in the name.
RESIDENTIAL_NAME_ALWAYS = re.compile(
    r"\b("
    r"hostels?|"
    r"p\.?\s*g\.?|"
    r"paying\s+guests?|"
    r"dormitor(?:y|ies)|"
    r"boys\s+(?:pg|p\.g\.)|"
    r"girls\s+(?:pg|p\.g\.)"
    r")\b",
    re.IGNORECASE,
)
# Apartment / residency names are private housing unless clearly a hotel or resort.
RESIDENTIAL_NAME_UNLESS_HOTEL = re.compile(
    r"\b(apartments?|residency|residences?)\b",
    re.IGNORECASE,
)
PRIVATE_ADDRESS = re.compile(
    r"\b(house\s*no\.?|h\.?\s*no\.?|flat\s*(?:no\.?)?|plot\s*no\.?|door\s*no\.?)\b|"
    r"\b\d{1,4}\s*,\s*\d{1,3}(?:st|nd|rd|th)?\s+(?:main|cross)\b",
    re.IGNORECASE,
)
ALLOWED_AMENITY = frozenset(
    {"restaurant", "cafe", "place_of_worship", "arts_centre"}
)
OVERPASS_AMENITY = "restaurant|cafe|place_of_worship|arts_centre"
OVERPASS_EXCLUDE = (
    '["industrial"!~"."]'
    '["craft"!~"."]'
    '["man_made"!="works"]'
    '["office"!~"."]'
    '["landuse"!="industrial"]'
    '["landuse"!="residential"]'
    '["building"!="residential"]'
    '["building"!="apartments"]'
    '["amenity"!="student_accommodation"]'
    '["amenity"!="social_facility"]'
    '["amenity"!="dormitory"]'
    '["tourism"!="hostel"]'
    '["residential"!~"."]'
)


def osm_display_name(tags: dict[str, Any] | None) -> str | None:
    """tags.name || tags['name:en'] only — no amenity fallbacks."""
    if not tags:
        return None
    for key in ("name", "name:en"):
        value = tags.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _tag(tags: dict[str, Any], key: str) -> str:
    return str(tags.get(key) or "").strip().lower()


def is_allowlisted_tags(tags: dict[str, Any] | None) -> bool:
    """tourism / historic / leisure / natural, or a specific amenity."""
    if not tags:
        return False
    if _tag(tags, "tourism") == "hostel":
        return False
    if tags.get("tourism") or tags.get("historic") or tags.get("leisure") or tags.get("natural"):
        return True
    return _tag(tags, "amenity") in ALLOWED_AMENITY


def is_industrial_tags(tags: dict[str, Any] | None) -> bool:
    """Hard drop even when overlapping tourism=museum (factory visitor centre)."""
    if not tags:
        return False
    industrial = _tag(tags, "industrial")
    if industrial and industrial not in {"no", "false"}:
        return True
    if _tag(tags, "landuse") == "industrial":
        return True
    man_made = _tag(tags, "man_made")
    if man_made == "works" or man_made in INDUSTRIAL_MAN_MADE:
        return True
    office = _tag(tags, "office")
    if office and office not in {"no", "false"}:
        return True
    craft = _tag(tags, "craft")
    if craft and craft not in {"no", "false"}:
        return True
    return False


def is_residential_tags(tags: dict[str, Any] | None) -> bool:
    """Hard drop private housing even when overlapping tourism/leisure tags."""
    if not tags:
        return False
    if _tag(tags, "building") in RESIDENTIAL_BUILDINGS:
        return True
    if _tag(tags, "amenity") in RESIDENTIAL_AMENITY:
        return True
    if _tag(tags, "landuse") == "residential":
        return True
    residential = _tag(tags, "residential")
    if residential and residential not in {"no", "false"}:
        return True
    if _tag(tags, "tourism") == "hostel":
        return True
    if "hostel" in _tag(tags, "operator"):
        return True
    return False


def is_industrial_place(name: str, category: str = "") -> bool:
    if INDUSTRIAL_NAME.search(name or ""):
        return True
    return (category or "").strip().lower() in INDUSTRIAL_CATEGORIES


def _is_hotel_or_resort(name: str, category: str = "") -> bool:
    return bool(HOTEL_OR_RESORT.search(f"{name} {category}"))


def is_residential_place(
    name: str,
    category: str = "",
    *,
    description: str | None = None,
    address: str | None = None,
) -> bool:
    cat = (category or "").strip().lower()
    if cat in RESIDENTIAL_CATEGORIES:
        return True
    blob = " ".join(part for part in (name, description, address) if part)
    if not blob:
        return False
    if RESIDENTIAL_NAME_ALWAYS.search(blob):
        return True
    if RESIDENTIAL_NAME_UNLESS_HOTEL.search(blob) and not _is_hotel_or_resort(name, category):
        return True
    if PRIVATE_ADDRESS.search(blob):
        return True
    return False


def should_drop_candidate(
    name: str,
    category: str = "",
    *,
    description: str | None = None,
    address: str | None = None,
    tags: dict[str, Any] | None = None,
) -> bool:
    """True if the place must never reach ranking (industrial or residential)."""
    if is_industrial_tags(tags) or is_residential_tags(tags):
        return True
    if is_industrial_place(name, category):
        return True
    return is_residential_place(name, category, description=description, address=address)


def is_tourist_tags(tags: dict[str, Any] | None) -> bool:
    return (
        is_allowlisted_tags(tags)
        and not is_industrial_tags(tags)
        and not is_residential_tags(tags)
    )
