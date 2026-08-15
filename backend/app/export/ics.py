"""iCalendar export. TZID = destination IANA zone. PROJECT_SPEC §12, §7.11, §7.15."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.constants import COST_LABEL_UI, ICS_FILENAME
from cuvoy_contracts.enums import CostLabel, ItineraryItemType
from cuvoy_contracts.itinerary import Itinerary, ItineraryItem

from app.schedule.clock import zone

STOP_TYPES = {
    ItineraryItemType.ACTIVITY,
    ItineraryItemType.MEAL,
    ItineraryItemType.TRAVEL_DAY,
}

_SKIP_TYPES = {ItineraryItemType.TRANSIT, ItineraryItemType.BREAK}


def ics_filename() -> str:
    return ICS_FILENAME


def _stamp(local_time: str, fallback_date: str | None = None) -> str:
    """RFC 5545 DATE-TIME: YYYYMMDDTHHMMSS (local, no Z when TZID is set)."""
    text = local_time.strip()
    date_digits = ""
    time_digits = ""
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        date_digits = "".join(ch for ch in date_part if ch.isdigit())[:8]
        clock = time_part.split("+", 1)[0]
        if clock.startswith("-"):
            clock = clock[1:]
        time_digits = "".join(ch for ch in clock.replace(":", "") if ch.isdigit())[:6]
    else:
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) >= 8:
            date_digits, time_digits = digits[:8], digits[8:14]
        else:
            time_digits = digits[:6]
    if len(date_digits) < 8 and fallback_date:
        date_digits = "".join(ch for ch in fallback_date if ch.isdigit())[:8]
    date_digits = date_digits.ljust(8, "0")[:8]
    time_digits = time_digits.ljust(6, "0")[:6]
    return f"{date_digits}T{time_digits}"


def _utc_stamp(moment: datetime | None = None) -> str:
    now = moment or datetime.now(UTC)
    return now.strftime("%Y%m%dT%H%M%SZ")


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """RFC 5545 §3.1 — 75 octets, continuation lines start with a space."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    chunks: list[bytes] = []
    rest = encoded
    first = True
    while rest:
        budget = 75 if first else 74
        piece = rest[:budget]
        while len(piece) > 1 and (piece[-1] & 0xC0) == 0x80:
            piece = piece[:-1]
        chunks.append(piece)
        rest = rest[len(piece) :]
        first = False
    parts = [chunks[0].decode("utf-8")]
    parts.extend(" " + chunk.decode("utf-8") for chunk in chunks[1:])
    return "\r\n".join(parts)


def _offset_ical(moment: datetime) -> str:
    delta = moment.utcoffset()
    seconds = int(delta.total_seconds()) if delta else 0
    sign = "+" if seconds >= 0 else "-"
    seconds = abs(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    return f"{sign}{hours:02d}{minutes:02d}"


def _vtimezone(tzid: str) -> list[str]:
    zi = zone(tzid)
    winter = datetime(2026, 1, 15, 12, 0, tzinfo=zi)
    summer = datetime(2026, 7, 15, 12, 0, tzinfo=zi)
    winter_off = _offset_ical(winter)
    summer_off = _offset_ical(summer)
    winter_name = winter.tzname() or tzid
    summer_name = summer.tzname() or tzid
    lines = ["BEGIN:VTIMEZONE", f"TZID:{tzid}", f"X-LIC-LOCATION:{tzid}"]
    if winter_off == summer_off:
        lines.extend(
            [
                "BEGIN:STANDARD",
                "DTSTART:19700101T000000",
                f"TZOFFSETFROM:{winter_off}",
                f"TZOFFSETTO:{winter_off}",
                f"TZNAME:{winter_name}",
                "END:STANDARD",
            ]
        )
    else:
        lines.extend(
            [
                "BEGIN:STANDARD",
                "DTSTART:19700101T000000",
                f"TZOFFSETFROM:{summer_off}",
                f"TZOFFSETTO:{winter_off}",
                f"TZNAME:{winter_name}",
                "END:STANDARD",
                "BEGIN:DAYLIGHT",
                "DTSTART:19700308T020000",
                f"TZOFFSETFROM:{winter_off}",
                f"TZOFFSETTO:{summer_off}",
                f"TZNAME:{summer_name}",
                "END:DAYLIGHT",
            ]
        )
    lines.append("END:VTIMEZONE")
    return lines


def _cost_text(cost: CostAmount | None) -> str | None:
    if cost is None:
        return None
    label = COST_LABEL_UI.get(cost.label.value, cost.label.value)
    if cost.label == CostLabel.UNAVAILABLE or cost.amount is None:
        return f"Cost: {label}"
    amount = int(cost.amount) if cost.amount == int(cost.amount) else cost.amount
    return f"Cost: {amount} {cost.currency} ({label})"


def _is_stop(item: ItineraryItem) -> bool:
    if item.type in _SKIP_TYPES and item.place is None:
        return False
    if item.type in STOP_TYPES:
        return True
    return item.place is not None


def _event(
    item: ItineraryItem,
    timezone: str,
    day_index: int,
    plan_id: str,
    fallback_date: str,
) -> list[str]:
    title = item.title or (item.place.name if item.place else "CuVoy stop")
    start = _stamp(item.start.local_time, fallback_date)
    end = _stamp(item.end.local_time, fallback_date)
    uid = f"{plan_id}-{day_index}-{start}-{uuid4().hex[:8]}@cuvoy.app"
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_utc_stamp()}",
        f"DTSTART;TZID={timezone}:{start}",
        f"DTEND;TZID={timezone}:{end}",
        f"SUMMARY:{_escape(title)}",
    ]
    if item.place:
        location = f"{item.place.name} ({item.place.lat:.5f}, {item.place.lng:.5f})"
        lines.append(f"LOCATION:{_escape(location)}")
        lines.append(f"GEO:{item.place.lat:.6f};{item.place.lng:.6f}")
    notes: list[str] = []
    if item.reason:
        notes.append(item.reason)
    cost_line = _cost_text(item.cost)
    if cost_line:
        notes.append(cost_line)
    if notes:
        lines.append(f"DESCRIPTION:{_escape(' '.join(notes))}")
    lines.append("END:VEVENT")
    return lines


def itinerary_to_ics(itinerary: Itinerary, *, plan_id: str = "plan") -> str:
    zones: list[str] = []
    for day in itinerary.days:
        zone_name = day.timezone or itinerary.timezone
        if zone_name not in zones:
            zones.append(zone_name)
    if itinerary.timezone and itinerary.timezone not in zones:
        zones.insert(0, itinerary.timezone)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CuVoy//Travel Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-TIMEZONE:{itinerary.timezone}",
    ]
    for tzid in zones:
        lines.extend(_vtimezone(tzid))
    for day in itinerary.days:
        zone_name = day.timezone or itinerary.timezone
        for item in day.items:
            if not _is_stop(item):
                continue
            lines.extend(
                _event(item, zone_name, day.day_index, plan_id, str(day.date))
            )
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
