"""HTTP/SSE contracts (PROJECT_SPEC §7.4, §7.13, §7.17)."""

from datetime import date

from pydantic import Field

from cuvoy_contracts.common import ContractModel
from cuvoy_contracts.enrichment import (
    Alternatives,
    Explainability,
    MapPayload,
    PackingList,
    Provenance,
    ValidationReport,
)
from cuvoy_contracts.enums import HealthState, JobStatus, PipelineStage, SseEventType
from cuvoy_contracts.itinerary import Itinerary, RouteLeg
from cuvoy_contracts.preferences import ExtractedPreferences, PlanRequest, TripControls


class HealthResponse(ContractModel):
    status: HealthState
    cache: HealthState
    db: HealthState


class PlanAccepted(ContractModel):
    plan_id: str
    status: JobStatus = JobStatus.QUEUED


class PlanStatus(ContractModel):
    plan_id: str
    status: JobStatus
    stage: PipelineStage | None = None
    progress: int = Field(default=0, ge=0, le=100)
    resumable: bool = False


class PlanResult(ContractModel):
    plan_id: str
    timezone: str
    preferences: ExtractedPreferences
    itinerary: Itinerary
    map: MapPayload
    routes: list[RouteLeg] = Field(default_factory=list)
    packing_list: PackingList | None = None
    explainability: Explainability | None = None
    alternatives: Alternatives | None = None
    provenance: list[Provenance] = Field(default_factory=list)
    validation: ValidationReport


class SwapRequest(ContractModel):
    from_place_id: str
    to_place_id: str


class MealOverride(ContractModel):
    day_index: int
    meal: str
    start_local: str | None = None
    end_local: str | None = None
    skip: bool = False


class RegenerateRequest(ContractModel):
    trip_controls: TripControls | None = None
    skip_stop_ids: list[str] = Field(default_factory=list)
    locked_stop_ids: list[str] = Field(default_factory=list)
    swap: SwapRequest | None = None
    meal_override: MealOverride | None = None


class SseEvent(ContractModel):
    event: SseEventType
    stage: PipelineStage | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    plan_id: str | None = None
    itinerary: Itinerary | None = None
    error: str | None = None
    recoverable: bool | None = None
    credit_refunded: bool | None = None


class PlanError(ContractModel):
    error: str
    retryable: bool
    credit_refunded: bool
    message: str


class SavedTrip(ContractModel):
    trip_id: str
    slug: str
    title: str
    plan_id: str | None = None
    share_url: str | None = None


class SaveTripRequest(ContractModel):
    plan_id: str
    title: str | None = None
    user_id: str | None = None


class TripList(ContractModel):
    trips: list[SavedTrip]


class SharedTrip(ContractModel):
    trip: SavedTrip
    result: PlanResult
    read_only: bool = True


class AccountDeleteResponse(ContractModel):
    deleted: bool = True
    trips_purged: int = 0


class PdfStopLine(ContractModel):
    start_local: str
    end_local: str
    title: str
    notes: str | None = None
    cost: str | None = None
    cost_label: str | None = None


class PdfDayBlock(ContractModel):
    day_index: int
    date: date
    timezone: str
    timezone_abbrev: str
    city: str | None = None
    stops: list[PdfStopLine] = Field(default_factory=list)
    daily_total: str | None = None


class PdfRouteLabel(ContractModel):
    from_place_id: str
    to_place_id: str
    duration_label: str
    distance_label: str | None = None


class PdfExportResponse(ContractModel):
    plan_id: str
    renderer: str = "client"
    title: str
    logo_placement: str = "corner"
    disclaimer: str
    timezone: str
    days: list[PdfDayBlock] = Field(default_factory=list)
    route_labels: list[PdfRouteLabel] = Field(default_factory=list)
    map_hint: str = (
        "Snapshot the Mapbox canvas and label average travel times along the route."
    )


# Re-export request body used at POST /api/v1/plan
PlanCreateRequest = PlanRequest
