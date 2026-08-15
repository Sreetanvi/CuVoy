from cuvoy_contracts.enums import CostLabel, TransportMode
from cuvoy_contracts.preferences import TripControls

from app.scoring.costs import activity_cost, meal_cost, transport_cost
from tests.unit.places import place


def test_walking_is_verified_zero_when_toggle_on() -> None:
    cost = transport_cost(
        TransportMode.WALKING, distance_m=1200, currency="INR", show_transport=True
    )
    assert cost is not None
    assert cost.amount == 0
    assert cost.label == CostLabel.VERIFIED_FARE


def test_transport_hidden_when_toggle_off() -> None:
    hidden = transport_cost(
        TransportMode.TAXI, distance_m=5000, currency="INR", show_transport=False
    )
    assert hidden is None
    assert TripControls().show_transport_cost is False


def test_transit_without_gtfs_is_unavailable() -> None:
    cost = transport_cost(
        TransportMode.METRO, distance_m=4000, currency="INR", city="Bengaluru", show_transport=True
    )
    assert cost.label == CostLabel.UNAVAILABLE
    assert cost.amount is None


def test_taxi_is_estimated_from_formula() -> None:
    cost = transport_cost(
        TransportMode.TAXI, distance_m=10_000, currency="INR", show_transport=True
    )
    assert cost.label == CostLabel.ESTIMATED_COST
    assert cost.amount == 50 + 18 * 10


def test_meal_and_park_estimates() -> None:
    meal = meal_cost(currency="INR", price_level="mid")
    assert meal.label == CostLabel.ESTIMATED_COST
    assert meal.amount == 500
    park = activity_cost(place("p", "Cubbon Park", 12.97, 77.59, category="park"), currency="INR")
    assert park.amount == 0
    assert park.label == CostLabel.ESTIMATED_COST
