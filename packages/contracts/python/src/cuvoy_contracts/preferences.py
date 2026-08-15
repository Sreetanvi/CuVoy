"""Trip input, extracted preferences, and Trip Controls (PROJECT_SPEC §4, §13, §18)."""

from datetime import date

from pydantic import Field, model_validator

from cuvoy_contracts.common import ContractModel
from cuvoy_contracts.constants import (
    DEFAULT_DAY_END_LOCAL,
    DEFAULT_DAY_START_LOCAL,
    DEFAULT_DINNER_END,
    DEFAULT_DINNER_START,
    DEFAULT_LUNCH_END,
    DEFAULT_LUNCH_START,
    MEAL_MIN_DURATION_MINUTES,
)
from cuvoy_contracts.enums import (
    BudgetTier,
    GroupPriority,
    LocationType,
    MaxTransitPreset,
    OwnedVehicle,
    Pace,
    PublicTransportMode,
)


class BudgetInput(ContractModel):
    daily_amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=1)
    raw: str | None = None
    tier: BudgetTier | None = None


class TravelDates(ContractModel):
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_span(self) -> "TravelDates":
        has_range = self.start_date is not None and self.end_date is not None
        if not has_range and self.duration_days is None:
            raise ValueError("Provide start_date+end_date or duration_days")
        if has_range and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LocationInput(ContractModel):
    query: str = Field(..., min_length=1)
    type: LocationType | None = None
    radius_km: float | None = Field(default=None, gt=0)


class TransportationPreference(ContractModel):
    owns_vehicle: bool
    vehicle: OwnedVehicle | None = None
    public_mode: PublicTransportMode | None = None

    @model_validator(mode="after")
    def resolve_mode(self) -> "TransportationPreference":
        if self.owns_vehicle:
            if self.vehicle is None:
                raise ValueError("vehicle is required when owns_vehicle is true")
        elif self.public_mode is None:
            self.public_mode = PublicTransportMode.MIXED
        return self


class Traveler(ContractModel):
    name: str | None = None
    interests: list[str] = Field(default_factory=list)
    is_team_lead: bool = False


class GroupPlanning(ContractModel):
    enabled: bool = False
    travelers: list[Traveler] = Field(default_factory=list)
    priority: GroupPriority = GroupPriority.EVERYONE


class AccessibilityPreferences(ContractModel):
    kids: bool = False
    elderly: bool = False
    wheelchair: bool = False
    notes: str | None = None


class FoodPreferences(ContractModel):
    dietary_restrictions: list[str] = Field(default_factory=list)
    cuisines: list[str] = Field(default_factory=list)


class MealWindow(ContractModel):
    start_local: str
    end_local: str
    min_duration_minutes: int = Field(default=MEAL_MIN_DURATION_MINUTES, ge=60)


class TripControls(ContractModel):
    max_transit_preset: MaxTransitPreset = MaxTransitPreset.BALANCED
    max_transit_minutes: int | None = Field(default=None, ge=1)
    pace: Pace = Pace.MODERATE
    day_start_local: str = DEFAULT_DAY_START_LOCAL
    day_end_local: str = DEFAULT_DAY_END_LOCAL
    lunch: MealWindow = MealWindow(
        start_local=DEFAULT_LUNCH_START,
        end_local=DEFAULT_LUNCH_END,
    )
    dinner: MealWindow = MealWindow(
        start_local=DEFAULT_DINNER_START,
        end_local=DEFAULT_DINNER_END,
    )
    transportation: TransportationPreference | None = None
    daily_budget: BudgetInput | None = None
    hidden_gems: bool = False
    group: GroupPlanning = Field(default_factory=GroupPlanning)
    show_transport_cost: bool = False
    accessibility: AccessibilityPreferences = Field(default_factory=AccessibilityPreferences)

    @model_validator(mode="after")
    def custom_transit(self) -> "TripControls":
        if self.max_transit_preset == MaxTransitPreset.CUSTOM and self.max_transit_minutes is None:
            raise ValueError("max_transit_minutes required when preset is custom")
        return self


class PlanRequest(ContractModel):
    user_prompt: str = Field(..., min_length=1)
    budget: BudgetInput | None = None
    transportation: TransportationPreference | None = None
    travel_dates: TravelDates
    location: LocationInput
    trip_controls: TripControls | None = None


class ExtractedPreferences(ContractModel):
    budget: BudgetInput | None = None
    dates: TravelDates | None = None
    interests: list[str] = Field(default_factory=list)
    pace: Pace = Pace.MODERATE
    food: FoodPreferences = Field(default_factory=FoodPreferences)
    hidden_gems: bool = False
    accessibility: AccessibilityPreferences = Field(default_factory=AccessibilityPreferences)
    group: GroupPlanning = Field(default_factory=GroupPlanning)
    transportation: TransportationPreference | None = None
    timezone: str | None = None
