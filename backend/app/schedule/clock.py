"""Local-time helpers. Itinerary instants are destination-local. PROJECT_SPEC §7.11."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from cuvoy_contracts.common import LocalDateTime


def parse_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return time(hour % 24, minute % 60)


def zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except Exception:
        return ZoneInfo("UTC")


def combine_local(on_date: date, at: time, tz: str) -> datetime:
    return datetime.combine(on_date, at, tzinfo=zone(tz))


def as_local(moment: datetime, tz: str) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=zone(tz))
    return moment.astimezone(zone(tz))


def timezone_abbrev(tz: str, on: date | None = None) -> str:
    when = on or date.today()
    moment = datetime(when.year, when.month, when.day, 12, 0, tzinfo=zone(tz))
    return moment.tzname() or tz


def clock_hm(local_time: str) -> str:
    """HH:MM from a local ISO timestamp or HH:MM string."""
    if "T" in local_time:
        clock = local_time.split("T", 1)[1]
        return clock[:5]
    if len(local_time) >= 5 and local_time[2] == ":":
        return local_time[:5]
    return local_time


def to_local_dt(moment: datetime) -> LocalDateTime:
    tz_name = str(moment.tzinfo) if moment.tzinfo else "UTC"
    if hasattr(moment.tzinfo, "key"):
        tz_name = moment.tzinfo.key  # type: ignore[union-attr]
    aware = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return LocalDateTime(
        timezone=tz_name,
        local_time=aware.strftime("%Y-%m-%dT%H:%M:%S"),
        utc=aware.astimezone(UTC),
    )
