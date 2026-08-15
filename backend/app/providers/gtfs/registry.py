"""GTFS registry schema. URLs stay empty until a verification pass (PROJECT_SPEC §28)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from cuvoy_contracts.common import ContractModel
from pydantic import Field


class FeedStatus(StrEnum):
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"
    OUTDATED = "outdated"


class FeedType(StrEnum):
    STATIC = "static"
    REALTIME = "realtime"


class GtfsFeed(ContractModel):
    city: str
    country: str
    agency: str = ""
    feed_url: str = ""
    feed_type: FeedType = FeedType.STATIC
    schedule_available: bool = False
    fare_available: bool = False
    last_updated: date | None = None
    status: FeedStatus = FeedStatus.UNAVAILABLE
    cache_ttl: int = Field(default=30 * 86400, ge=0)


# Do not invent official URLs. Fill after a verification pass.
REGISTRY: tuple[GtfsFeed, ...] = (
    GtfsFeed(city="Bengaluru", country="IN"),
    GtfsFeed(city="Jaipur", country="IN"),
    GtfsFeed(city="Tokyo", country="JP"),
    GtfsFeed(city="Interlaken", country="CH"),
    GtfsFeed(city="Paris", country="FR"),
)


def lookup_feed(city: str) -> GtfsFeed | None:
    needle = city.strip().lower()
    for feed in REGISTRY:
        if feed.city.lower() == needle:
            return feed
    return None
