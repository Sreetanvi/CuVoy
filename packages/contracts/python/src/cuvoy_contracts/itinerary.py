"""Itinerary, stops, routes, reservations (PROJECT_SPEC §5, §9, §14)."""

from datetime import date

from pydantic import Field

from cuvoy_contracts.common import ContractModel, CostAmount, LocalDateTime
from cuvoy_contracts.enrichment import CrowdConfidence, Weather
from cuvoy_contracts.enums import ItineraryItemType, TransportMode, WarningCode
from cuvoy_contracts.place import Place


class ReservationInfo(ContractModel):
    likely_needed: bool
    website: str | None = None
    phone: str | None = None
    guidance: str


class RouteLeg(ContractModel):
    from_place_id: str
    to_place_id: str
    duration_seconds: int
    duration_buffered_seconds: int
    distance_meters: int
    mode: TransportMode
    geometry: str | None = None
    cost: CostAmount | None = None


class ItineraryItem(ContractModel):
    type: ItineraryItemType
    start: LocalDateTime
    end: LocalDateTime
    place: Place | None = None
    title: str | None = None
    dwell_minutes: int | None = None
    wait_minutes: int | None = None
    travel_minutes: int | None = None
    travel_minutes_buffered: int | None = None
    cost: CostAmount | None = None
    crowd: CrowdConfidence | None = None
    reason: str | None = None
    warnings: list[WarningCode] = Field(default_factory=list)
    reservation: ReservationInfo | None = None
    locked: bool = False
    route: RouteLeg | None = None


class DailyCost(ContractModel):
    currency: str
    activities: CostAmount | None = None
    meals: CostAmount | None = None
    transport: CostAmount | None = None
    total_excluding_transport: float | None = None
    total_including_transport: float | None = None
    transport_shown: bool = False


class ItineraryDay(ContractModel):
    day_index: int
    date: date
    timezone: str
    city: str | None = None
    is_travel_day: bool = False
    items: list[ItineraryItem]
    daily_cost: DailyCost | None = None
    weather: Weather | None = None


class Itinerary(ContractModel):
    days: list[ItineraryDay]
    timezone: str
    currency: str
    narrative: str | None = None
