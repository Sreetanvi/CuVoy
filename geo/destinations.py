"""Parse multi-city requests and allocate calendar days. PROJECT_SPEC §7."""

from __future__ import annotations

import re
from typing import Any

from app.providers.geo import haversine_m

DURATION = re.compile(
    r"\bfor\s+\d+\s+(?:days?|nights?|weeks?)\b|\b\d+\s+(?:days?|nights?)\s+(?:in|to|across)?",
    re.IGNORECASE,
)
TRAILING_INTERESTS = re.compile(
    r"\b(?:for|with)\s+(?:museums?|food|forts?|temples?|beaches?|family|kids|friends|history).*$",
    re.IGNORECASE,
)
LEAD_IN = re.compile(
    r"^(?:plan(?:\s+a)?(?:\s+trip)?|visit(?:ing)?|travel(?:ling)?(?:\s+to)?|go(?:ing)?\s+to|trip\s+to)\s+",
    re.IGNORECASE,
)
IN_TO = re.compile(r"\b(?:in|to|visiting|visit|across)\s+(.+)$", re.IGNORECASE)
IN_REGION = re.compile(r"\s+\bin\s+[A-Za-z].*$", re.IGNORECASE)
SPLIT = re.compile(r"\s*(?:,|/|;|\band\b|\bthen\b)\s*", re.IGNORECASE)
CITY_NAME = re.compile(r"^[A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3}$")
STOP = frozenset(
    {
        "and",
        "or",
        "the",
        "a",
        "an",
        "for",
        "with",
        "from",
        "trip",
        "tour",
        "holiday",
        "vacation",
        "india",
        "kerala",
        "rajasthan",
        "karnataka",
        "goa",
        "days",
        "day",
        "nights",
        "week",
    }
)
# Drop a geocoded "city" that is far from the corridor unless the user named it.
MAX_OUTLIER_FROM_CORRIDOR_KM = 750
MAX_POI_FROM_CITY_KM = 50


def _clean_token(raw: str) -> str | None:
    text = re.sub(r"\b(?:for|with|from)\b.*$", "", raw, flags=re.IGNORECASE)
    text = IN_REGION.sub("", text)
    text = text.strip(" .,;:—-")
    if not text or not CITY_NAME.match(text):
        return None
    if text.lower() in STOP:
        return None
    return text


def _split_cities(span: str) -> list[str]:
    parts = [part.strip() for part in SPLIT.split(span) if part.strip()]
    cities: list[str] = []
    seen: set[str] = set()
    for part in parts:
        token = _clean_token(part)
        if token is None:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        cities.append(token)
    return cities


def _destination_span(text: str) -> str:
    stripped = DURATION.sub(" ", text)
    stripped = TRAILING_INTERESTS.sub("", stripped)
    stripped = LEAD_IN.sub("", stripped.strip())
    stripped = IN_REGION.sub("", stripped).strip(" .,")
    if SPLIT.search(stripped):
        return stripped
    match = IN_TO.search(stripped)
    if match:
        return match.group(1).strip(" .,")
    return stripped


def parse_city_names(location_query: str, user_prompt: str = "") -> list[str]:
    """The destination field wins. The prompt is used only when that field is empty."""
    location = (location_query or "").strip()
    if location:
        found = _split_cities(_destination_span(location))
        if found:
            return found[:6]
        return [location]
    found = _split_cities(_destination_span(user_prompt or ""))
    if found:
        return found[:6]
    fallback = (user_prompt or "").strip()
    return [fallback] if fallback else []


def allocate_days(n_days: int, n_cities: int) -> list[int]:
    """Spread days across cities. 5 days / 3 cities → [2, 2, 1]."""
    days = max(1, int(n_days))
    cities = max(1, int(n_cities))
    if cities == 1:
        return [days]
    if days < cities:
        return [1] * days + [0] * (cities - days)
    base, rem = divmod(days, cities)
    return [base + (1 if index < rem else 0) for index in range(cities)]


def short_city_name(name: str, fallback: str) -> str:
    text = (name or fallback).split(",")[0].strip()
    return text or fallback


def city_of_place(place_id: str, place_city: dict[str, str], default: str) -> str:
    return place_city.get(place_id) or default


def destination_key(city: dict[str, Any]) -> str:
    return str(city.get("query") or city.get("name") or "").strip()


PLACE_ALIASES: dict[str, tuple[str, ...]] = {
    "ooty": ("udhagamandalam", "ootacamund", "udhagai"),
    "udhagamandalam": ("ooty", "ootacamund"),
    "coonoor": ("kunnur",),
    "thekkady": ("kumily", "periyar"),
    "alleppey": ("alappuzha",),
    "alappuzha": ("alleppey",),
    "bangalore": ("bengaluru",),
    "bengaluru": ("bangalore",),
    "bombay": ("mumbai",),
    "calcutta": ("kolkata",),
    "pondicherry": ("puducherry", "pondy"),
    "trivandrum": ("thiruvananthapuram",),
}


def _normalize_place_token(value: str) -> str:
    return re.sub(r"[^a-z]+", "", (value or "").lower())


def query_matches_place_name(query: str, place_name: str) -> bool:
    needle = _normalize_place_token(query)
    hay = _normalize_place_token(place_name)
    if len(needle) < 3 or not hay:
        return False
    if needle in hay or hay.startswith(needle[:4]):
        return True
    return any(alias in hay for alias in PLACE_ALIASES.get(needle, ()))


def accept_geocoded_city(
    query: str,
    geo: dict[str, Any],
    previous: list[dict[str, Any]],
) -> bool:
    """Keep explicit far destinations; drop hubs whose name does not match the query."""
    name = str(geo.get("name") or "")
    matched = query_matches_place_name(query, name)
    if not previous:
        return matched
    try:
        lat = float(geo["lat"])
        lng = float(geo["lng"])
    except (KeyError, TypeError, ValueError):
        return False
    nearest_km = min(
        haversine_m(lat, lng, float(row["lat"]), float(row["lng"])) / 1000.0 for row in previous
    )
    if nearest_km <= MAX_OUTLIER_FROM_CORRIDOR_KM:
        return True
    return matched


def order_cities_corridor(cities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first requested city, then walk nearest-neighbor so legs stay local."""
    if len(cities) <= 2:
        return list(cities)
    remaining = list(cities)
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        nearest_i = min(
            range(len(remaining)),
            key=lambda i: haversine_m(
                float(last["lat"]),
                float(last["lng"]),
                float(remaining[i]["lat"]),
                float(remaining[i]["lng"]),
            ),
        )
        ordered.append(remaining.pop(nearest_i))
    return ordered


def place_near_city(lat: float, lng: float, city: dict[str, Any], *, max_km: float = MAX_POI_FROM_CITY_KM) -> bool:
    try:
        return haversine_m(lat, lng, float(city["lat"]), float(city["lng"])) <= max_km * 1000.0
    except (KeyError, TypeError, ValueError):
        return False


def dump_destinations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def load_destinations(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("name"):
            out.append(item)
    return out
