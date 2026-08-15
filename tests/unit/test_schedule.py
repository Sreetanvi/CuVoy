from datetime import date, time

from cuvoy_contracts.enums import ItineraryItemType, Pace, TransportMode, WarningCode
from cuvoy_contracts.preferences import TripControls

from app.providers.geo import haversine_m
from app.providers.mapbox_matrix import haversine_matrix
from app.schedule.builder import build_day, dwell_minutes
from app.schedule.conflicts import is_open_at, place_warnings
from app.schedule.travel_days import build_travel_day, destinations_need_travel
from tests.unit.places import place


def test_dwell_uses_spec_defaults() -> None:
    assert dwell_minutes(place("m", "Louvre", 48.86, 2.34, category="museum"), Pace.MODERATE) == 120
    view = place("v", "Lookout", 48.86, 2.34, category="viewpoint")
    assert dwell_minutes(view, Pace.MODERATE) == 30


def test_day_includes_meals_and_local_timezone() -> None:
    stops = [
        place("a", "Museum A", 35.68, 139.76),
        place("b", "Museum B", 35.681, 139.765),
        place("c", "Park C", 35.682, 139.77, category="park"),
    ]
    meals = [place("r", "Ramen", 35.68, 139.76, category="restaurant")]
    coords = [(p.lat, p.lng) for p in stops]
    matrix = haversine_matrix(coords, "walking")
    day = build_day(
        day_index=0,
        on_date=date(2026, 4, 10),
        timezone="Asia/Tokyo",
        city="Tokyo",
        ordered=stops,
        matrix=matrix,
        matrix_places=stops,
        mode=TransportMode.WALKING,
        controls=TripControls(),
        meal_places=meals,
        currency="JPY",
    )
    types = [item.type for item in day.items]
    assert ItineraryItemType.MEAL in types
    assert ItineraryItemType.ACTIVITY in types
    assert day.timezone == "Asia/Tokyo"
    assert all(item.start.timezone == "Asia/Tokyo" for item in day.items)
    assert day.daily_cost is not None
    assert day.daily_cost.transport_shown is False


def test_hours_conflict_and_unverified() -> None:
    closed = place("x", "Night Museum", 35.68, 139.76, hours="Mo-Su 09:00-11:00")
    assert is_open_at(closed.opening_hours, date(2026, 4, 10), time(15, 0)) is False
    warnings = place_warnings(closed, date(2026, 4, 10), time(15, 0))
    assert WarningCode.CLOSES_BEFORE_ARRIVAL in warnings
    unknown = place("y", "Mystery", 35.68, 139.76, hours=None)
    assert WarningCode.HOURS_UNVERIFIED in place_warnings(unknown, date(2026, 4, 10), time(10, 0))


def test_travel_day_between_cities() -> None:
    assert destinations_need_travel("tokyo", "kyoto") is True
    assert destinations_need_travel("tokyo", "tokyo") is False
    day = build_travel_day(
        day_index=3,
        on_date=date(2026, 4, 13),
        timezone="Asia/Tokyo",
        from_city="Tokyo",
        to_city="Kyoto",
        controls=TripControls(),
        evening_place=place("e", "Gion walk", 35.0, 135.76, category="park"),
    )
    assert day.is_travel_day is True
    titles = [item.title or "" for item in day.items]
    assert any("checkout" in t.lower() for t in titles)
    assert any("Tokyo → Kyoto" in t for t in titles)
    assert any("check-in" in t.lower() for t in titles)
    assert any(item.type == ItineraryItemType.MEAL for item in day.items)


def test_haversine_positive() -> None:
    assert haversine_m(35.68, 139.76, 35.0, 135.76) > 1000
