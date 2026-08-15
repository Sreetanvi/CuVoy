"""Mutable pipeline state. Checkpoints are JSON-only. PROJECT_SPEC §7.12, §7.22."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from cuvoy_contracts.api import PlanResult
from cuvoy_contracts.enums import TransportMode
from cuvoy_contracts.itinerary import Itinerary
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import ExtractedPreferences, PlanRequest, TripControls

from app.ai_gateway.gateway import AIGateway
from app.geo.candidate_reduce import ReducedCandidates
from app.providers.client import ExternalData
from app.providers.mapbox_matrix import TravelMatrix
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend


def resolve_mode(request: PlanRequest, prefs: ExtractedPreferences | None) -> TransportMode:
    transport = None
    if request.trip_controls and request.trip_controls.transportation:
        transport = request.trip_controls.transportation
    elif request.transportation:
        transport = request.transportation
    elif prefs and prefs.transportation:
        transport = prefs.transportation
    if transport is None:
        return TransportMode.MIXED
    if transport.owns_vehicle and transport.vehicle is not None:
        return TransportMode(transport.vehicle.value)
    if transport.public_mode is not None:
        return TransportMode(transport.public_mode.value)
    return TransportMode.MIXED


def trip_day_count(request: PlanRequest) -> int:
    dates = request.travel_dates
    if dates.start_date and dates.end_date:
        span = (dates.end_date - dates.start_date).days + 1
        return max(1, min(span, 10))
    return max(1, min(dates.duration_days or 3, 10))


def trip_dates(request: PlanRequest) -> list[date]:
    n = trip_day_count(request)
    start = request.travel_dates.start_date
    if start is None:
        start = date.today()
    return [start + timedelta(days=i) for i in range(n)]


def dump_places(places: list[Place]) -> list[dict]:
    return [p.model_dump(mode="json") for p in places]


def load_places(raw: object) -> list[Place]:
    if not isinstance(raw, list):
        return []
    out: list[Place] = []
    for item in raw:
        try:
            out.append(Place.model_validate(item))
        except Exception:
            continue
    return out


@dataclass
class PipelineContext:
    plan_id: str
    request: PlanRequest
    budget: PlanBudget
    cache: CacheBackend
    external: ExternalData
    gateway: AIGateway
    identity: str
    regeneration: bool = False
    skip_stop_ids: list[str] = field(default_factory=list)
    locked_stop_ids: list[str] = field(default_factory=list)
    preferences: ExtractedPreferences | None = None
    controls: TripControls | None = None
    dest_lat: float = 0.0
    dest_lng: float = 0.0
    dest_name: str = ""
    country_code: str | None = None
    timezone: str = "UTC"
    mode: TransportMode = TransportMode.MIXED
    destinations: list[dict] = field(default_factory=list)
    place_city: dict[str, str] = field(default_factory=dict)
    discovered: list[Place] = field(default_factory=list)
    reduced: ReducedCandidates | None = None
    matrix: TravelMatrix | None = None
    itinerary: Itinerary | None = None
    result: PlanResult | None = None
    exclusions: list[dict] = field(default_factory=list)

    def apply_controls(self) -> TripControls:
        if self.request.trip_controls is not None:
            self.controls = self.request.trip_controls
        elif self.controls is None:
            self.controls = TripControls()
        return self.controls
