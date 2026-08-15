"""Weather, crowd, packing, explainability, provenance, validation (PROJECT_SPEC §9–10, §29)."""

from datetime import datetime

from pydantic import Field, model_validator

from cuvoy_contracts.common import ContractModel
from cuvoy_contracts.enums import (
    CrowdConfidenceLevel,
    CrowdLevel,
    WeatherConfidence,
    WeatherSource,
)


class Weather(ContractModel):
    source: WeatherSource
    is_forecast: bool
    confidence: WeatherConfidence
    retrieved_at: datetime | None = None
    climate_period: str | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    summary: str | None = None

    @model_validator(mode="after")
    def forecast_flag(self) -> "Weather":
        if self.source == WeatherSource.FORECAST and not self.is_forecast:
            raise ValueError("Live forecast must set is_forecast=true")
        if self.source != WeatherSource.FORECAST and self.is_forecast:
            raise ValueError("Historical climate or unavailable must not be labeled forecast")
        return self


class CrowdConfidence(ContractModel):
    """Crowd Confidence — never presented as a live measurement (PROJECT_SPEC §10)."""

    level: CrowdLevel
    confidence: CrowdConfidenceLevel
    reasons: list[str] = Field(default_factory=list)


class PackingItem(ContractModel):
    name: str
    reason: str
    category: str


class PackingList(ContractModel):
    items: list[PackingItem]
    summary: str | None = None


class ExclusionReason(ContractModel):
    place_id: str | None = None
    name: str
    reason: str


class Explainability(ContractModel):
    exclusions: list[ExclusionReason] = Field(default_factory=list)


class AlternativePlace(ContractModel):
    place_id: str
    name: str
    reason: str
    swap_for_place_id: str | None = None


class Alternatives(ContractModel):
    nearby_cities: list[str] = Field(default_factory=list)
    swap_suggestions: list[AlternativePlace] = Field(default_factory=list)


class Provenance(ContractModel):
    field: str
    source: str
    retrieved_at: datetime | None = None
    confidence: CrowdConfidenceLevel | WeatherConfidence | None = None


class ValidationIssue(ContractModel):
    code: str
    message: str
    path: str | None = None


class ValidationReport(ContractModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class MapMarker(ContractModel):
    place_id: str
    lat: float
    lng: float
    label: str
    day_index: int | None = None


class MapBounds(ContractModel):
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


class MapPayload(ContractModel):
    markers: list[MapMarker]
    bounds: MapBounds | None = None
