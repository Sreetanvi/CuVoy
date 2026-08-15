"""Opening-hours conflicts and reservation hints. PROJECT_SPEC §8, §14."""

from __future__ import annotations

import re
from datetime import date, time

from cuvoy_contracts.enums import WarningCode
from cuvoy_contracts.itinerary import ReservationInfo
from cuvoy_contracts.place import Place

_DAY = {"mo": 0, "tu": 1, "we": 2, "th": 3, "fr": 4, "sa": 5, "su": 6}
_RANGE = re.compile(
    r"(?P<days>[A-Za-z]{2}(?:-[A-Za-z]{2})?(?:,[A-Za-z]{2}(?:-[A-Za-z]{2})?)*)?\s*"
    r"(?P<open>\d{1,2}:\d{2})\s*-\s*(?P<close>\d{1,2}:\d{2})"
)
_TIME = re.compile(r"(\d{1,2}):(\d{2})")

RESERVATION_LIKELY = frozenset(
    {"restaurant", "theme_park", "museum", "gallery", "theatre"}
)


def _parse_clock(raw: str) -> time:
    hour, minute = raw.split(":")
    return time(int(hour) % 24, int(minute) % 60)


def _days_from(token: str | None, fallback: set[int]) -> set[int]:
    if not token:
        return fallback
    out: set[int] = set()
    for part in token.lower().split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = _DAY.get(a[:2], 0), _DAY.get(b[:2], 6)
            if start <= end:
                out.update(range(start, end + 1))
            else:
                out.update(list(range(start, 7)) + list(range(0, end + 1)))
        elif part[:2] in _DAY:
            out.add(_DAY[part[:2]])
    return out or fallback


def hours_windows(opening_hours: str | None, on_date: date) -> list[tuple[time, time]]:
    """Best-effort OSM opening_hours. Unrecognized → empty (unverified)."""
    if not opening_hours:
        return []
    text = opening_hours.strip()
    if text.lower() in {"24/7", "open"}:
        return [(time(0, 0), time(23, 59))]
    weekday = on_date.weekday()
    windows: list[tuple[time, time]] = []
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk or "off" in chunk.lower() or "closed" in chunk.lower():
            if chunk.lower() in {"off", "closed"}:
                return []
            continue
        match = _RANGE.search(chunk)
        if not match:
            times = _TIME.findall(chunk)
            if len(times) >= 2:
                windows.append(
                    (
                        time(int(times[0][0]) % 24, int(times[0][1]) % 60),
                        time(int(times[1][0]) % 24, int(times[1][1]) % 60),
                    )
                )
            continue
        days = _days_from(match.group("days"), set(range(7)))
        if weekday not in days:
            continue
        windows.append((_parse_clock(match.group("open")), _parse_clock(match.group("close"))))
    return windows


def is_open_at(opening_hours: str | None, on_date: date, at: time) -> bool | None:
    windows = hours_windows(opening_hours, on_date)
    if not windows and not opening_hours:
        return None
    if not windows:
        return False
    minutes = at.hour * 60 + at.minute
    for start, end in windows:
        a = start.hour * 60 + start.minute
        b = end.hour * 60 + end.minute
        if a <= b and a <= minutes <= b:
            return True
        if a > b and (minutes >= a or minutes <= b):
            return True
    return False


def place_warnings(place: Place, on_date: date, arrive: time) -> list[WarningCode]:
    warnings: list[WarningCode] = []
    open_flag = is_open_at(place.opening_hours, on_date, arrive)
    if place.opening_hours is None:
        warnings.append(WarningCode.HOURS_UNVERIFIED)
    elif open_flag is False:
        warnings.append(WarningCode.CLOSES_BEFORE_ARRIVAL)
    if reservation_likely(place):
        warnings.append(WarningCode.RESERVATION_LIKELY)
    return warnings


def reservation_likely(place: Place) -> bool:
    return place.category.lower() in RESERVATION_LIKELY


def reservation_info(place: Place) -> ReservationInfo:
    if place.website and place.phone:
        guidance = "Contact the attraction by phone or through their website."
    elif place.website:
        guidance = "Reservations: Contact the attraction through the official website."
    elif place.phone:
        guidance = "Contact the attraction by phone."
    else:
        guidance = "Reservation contact information not found."
    return ReservationInfo(
        likely_needed=reservation_likely(place),
        website=place.website,
        phone=place.phone,
        guidance=guidance,
    )
