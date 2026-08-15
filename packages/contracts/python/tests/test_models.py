from datetime import date

import pytest
from pydantic import ValidationError

from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.enrichment import Weather
from cuvoy_contracts.enums import CostLabel, PlaceSource, WeatherConfidence, WeatherSource
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import (
    LocationInput,
    PlanRequest,
    TransportationPreference,
    TravelDates,
    TripControls,
)


def test_place_canonical_fields() -> None:
    place = Place(
        id="osm:node:1",
        name="Example Museum",
        lat=48.8606,
        lng=2.3376,
        category="museum",
        opening_hours="Mo-Su 09:00-18:00",
        source=PlaceSource.OSM,
    )
    assert place.source == PlaceSource.OSM
    dumped = place.model_dump()
    assert set(["id", "name", "lat", "lng", "category", "source"]).issubset(dumped)


def test_cost_unavailable_rejects_amount() -> None:
    with pytest.raises(ValidationError):
        CostAmount(amount=40, currency="INR", label=CostLabel.UNAVAILABLE)


def test_cost_unavailable_ok() -> None:
    cost = CostAmount(amount=None, currency="INR", label=CostLabel.UNAVAILABLE)
    assert cost.amount is None


def test_verified_cost_requires_amount() -> None:
    with pytest.raises(ValidationError):
        CostAmount(amount=None, currency="INR", label=CostLabel.VERIFIED_FARE)


def test_historical_climate_is_not_forecast() -> None:
    with pytest.raises(ValidationError):
        Weather(
            source=WeatherSource.HISTORICAL_CLIMATE,
            is_forecast=True,
            confidence=WeatherConfidence.MODERATE,
        )
    weather = Weather(
        source=WeatherSource.HISTORICAL_CLIMATE,
        is_forecast=False,
        confidence=WeatherConfidence.MODERATE,
        climate_period="March",
    )
    assert weather.is_forecast is False


def test_owns_vehicle_requires_vehicle() -> None:
    with pytest.raises(ValidationError):
        TransportationPreference(owns_vehicle=True)
    owned = TransportationPreference(owns_vehicle=True, vehicle="car")
    assert owned.vehicle == "car"


def test_public_mode_defaults_mixed() -> None:
    pref = TransportationPreference(owns_vehicle=False)
    assert pref.public_mode == "mixed"


def test_plan_request_minimal() -> None:
    req = PlanRequest(
        user_prompt="2 weeks in Rajasthan, forts and food",
        travel_dates=TravelDates(start_date=date(2026, 4, 10), end_date=date(2026, 4, 13)),
        location=LocationInput(query="Rajasthan, India", type="state"),
    )
    assert req.user_prompt.startswith("2 weeks")


def test_custom_transit_requires_minutes() -> None:
    with pytest.raises(ValidationError):
        TripControls(max_transit_preset="custom")
    controls = TripControls(max_transit_preset="custom", max_transit_minutes=45)
    assert controls.max_transit_minutes == 45
    assert controls.show_transport_cost is False


def test_saved_trip_share_url_optional() -> None:
    from cuvoy_contracts.api import SavedTrip
    from cuvoy_contracts.constants import PUBLIC_ORIGIN

    trip = SavedTrip(
        trip_id="t1",
        slug="s1",
        title="Kyoto",
        share_url=f"{PUBLIC_ORIGIN}/trip/s1",
    )
    assert trip.share_url.endswith("/trip/s1")
