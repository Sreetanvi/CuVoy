"""Enums from PROJECT_SPEC (transport, cost labels, crowd, weather, jobs)."""

from enum import StrEnum


class OwnedVehicle(StrEnum):
    CAR = "car"
    BIKE = "bike"
    CAMPER = "camper"
    BICYCLE = "bicycle"


class PublicTransportMode(StrEnum):
    WALKING = "walking"
    METRO = "metro"
    TAXI = "taxi"
    BUS = "bus"
    MIXED = "mixed"


class TransportMode(StrEnum):
    """Any leg mode after vehicle-ownership is resolved."""

    WALKING = "walking"
    METRO = "metro"
    TAXI = "taxi"
    BUS = "bus"
    MIXED = "mixed"
    CAR = "car"
    BIKE = "bike"
    CAMPER = "camper"
    BICYCLE = "bicycle"


class MaxTransitPreset(StrEnum):
    WALKABLE = "walkable"
    RELAXED = "relaxed"
    BALANCED = "balanced"
    EXPLORER = "explorer"
    NO_LIMIT = "no_limit"
    CUSTOM = "custom"


class Pace(StrEnum):
    RELAXED = "relaxed"
    MODERATE = "moderate"
    PACKED = "packed"


class BudgetTier(StrEnum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class LocationType(StrEnum):
    CITY = "city"
    STATE = "state"
    COUNTRY = "country"
    REGION = "region"
    MULTI_CITY = "multi_city"
    MULTI_COUNTRY = "multi_country"


class CostLabel(StrEnum):
    """Three-tier cost display (PROJECT_SPEC §9). Never LLM-guessed."""

    VERIFIED_FARE = "verified_fare"
    ESTIMATED_COST = "estimated_cost"
    UNAVAILABLE = "unavailable"


class CrowdLevel(StrEnum):
    VERY_QUIET = "very_quiet"
    QUIET = "quiet"
    MODERATE = "moderate"
    BUSY = "busy"
    VERY_BUSY = "very_busy"


class CrowdConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WeatherSource(StrEnum):
    FORECAST = "forecast"
    HISTORICAL_CLIMATE = "historical_climate"
    UNAVAILABLE = "unavailable"


class WeatherConfidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    NONE = "none"


class PlaceSource(StrEnum):
    MAPBOX = "mapbox"
    OSM = "osm"
    OPENTRIPMAP = "opentripmap"
    GEONAMES = "geonames"
    WIKIPEDIA = "wikipedia"
    OFFICIAL = "official"


class GroupPriority(StrEnum):
    EVERYONE = "everyone"
    TEAM_LEAD = "team_lead"


class ItineraryItemType(StrEnum):
    ACTIVITY = "activity"
    MEAL = "meal"
    TRANSIT = "transit"
    BREAK = "break"
    TRAVEL_DAY = "travel_day"


class WarningCode(StrEnum):
    CLOSES_BEFORE_ARRIVAL = "closes_before_arrival"
    RESERVATION_LIKELY = "reservation_likely"
    HOURS_UNVERIFIED = "hours_unverified"
    COST_UNAVAILABLE = "cost_unavailable"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RESUMABLE = "resumable"
    COMPLETE = "complete"
    FAILED = "failed"


class PipelineStage(StrEnum):
    EXTRACT = "extract"
    DISCOVER = "discover"
    REDUCE = "reduce"
    CLUSTER_MATRIX = "cluster_matrix"
    OPTIMIZE_SCHEDULE = "optimize_schedule"
    NARRATIVE_VALIDATE = "narrative_validate"


class SseEventType(StrEnum):
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    PLAN_COMPLETE = "plan_complete"
    PLAN_ERROR = "plan_error"


class HealthState(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
