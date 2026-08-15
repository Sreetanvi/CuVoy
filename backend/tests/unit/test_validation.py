from datetime import date

from cuvoy_contracts.enums import ItineraryItemType, PlaceSource, WarningCode
from cuvoy_contracts.itinerary import Itinerary, ItineraryDay, ItineraryItem
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import TripControls

from app.schedule.clock import combine_local, parse_hhmm, to_local_dt
from app.validation.cross_schema import validate_plan


def _item(
    kind: ItineraryItemType, start: str, end: str, place: Place | None = None
) -> ItineraryItem:
    tz = "Asia/Kolkata"
    day = date(2026, 4, 10)
    return ItineraryItem(
        type=kind,
        start=to_local_dt(combine_local(day, parse_hhmm(start), tz)),
        end=to_local_dt(combine_local(day, parse_hhmm(end), tz)),
        place=place,
        title=place.name if place else kind.value,
        dwell_minutes=60 if kind == ItineraryItemType.ACTIVITY else None,
        warnings=[WarningCode.HOURS_UNVERIFIED] if place and not place.opening_hours else [],
    )


def test_empty_itinerary_is_invalid() -> None:
    report = validate_plan(Itinerary(days=[], timezone="Asia/Kolkata", currency="INR"), None)
    assert report.valid is False
    assert any(issue.code == "empty_itinerary" for issue in report.issues)


def test_valid_day_passes_gate() -> None:
    museum = Place(
        id="m1",
        name="Museum",
        lat=12.97,
        lng=77.59,
        category="museum",
        source=PlaceSource.OSM,
        opening_hours="Mo-Su 09:00-18:00",
    )
    day = ItineraryDay(
        day_index=0,
        date=date(2026, 4, 10),
        timezone="Asia/Kolkata",
        items=[
            _item(ItineraryItemType.ACTIVITY, "09:00", "11:00", museum),
            _item(ItineraryItemType.MEAL, "13:00", "14:00"),
        ],
    )
    report = validate_plan(
        Itinerary(days=[day], timezone="Asia/Kolkata", currency="INR"),
        TripControls(),
    )
    assert report.valid is True
