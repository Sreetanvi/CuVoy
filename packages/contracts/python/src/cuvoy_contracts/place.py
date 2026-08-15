"""Canonical Place and cluster metadata (PROJECT_SPEC §31)."""

from pydantic import Field, field_validator

from cuvoy_contracts.common import ContractModel
from cuvoy_contracts.enums import PlaceSource


class Place(ContractModel):
    """Required: id, name, lat, lng, category. Optional hours/contact. Never LLM-invented."""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    lat: float
    lng: float
    category: str = Field(..., min_length=1)
    opening_hours: str | None = None
    website: str | None = None
    phone: str | None = None
    address: str | None = None
    source: PlaceSource

    @field_validator("lat")
    @classmethod
    def valid_lat(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("lat must be between -90 and 90")
        return value

    @field_validator("lng")
    @classmethod
    def valid_lng(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("lng must be between -180 and 180")
        return value


class Cluster(ContractModel):
    """Stores place ID references, not full place objects (PROJECT_SPEC §32)."""

    id: str
    place_ids: list[str]
    centroid_lat: float
    centroid_lng: float
    destination_id: str | None = None
