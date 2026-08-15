from datetime import date

from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.enums import CostLabel, ItineraryItemType, PlaceSource
from cuvoy_contracts.itinerary import Itinerary, ItineraryDay, ItineraryItem
from cuvoy_contracts.place import Place

from app.export.ics import itinerary_to_ics
from app.schedule.clock import combine_local, parse_hhmm, to_local_dt


def _place() -> Place:
    return Place(
        id="p1",
        name="Senso-ji",
        lat=35.71,
        lng=139.79,
        category="temple",
        source=PlaceSource.OSM,
    )


def _slot(tz: str, hour: str, end: str, on: date | None = None):
    day = on or date(2026, 4, 10)
    return (
        to_local_dt(combine_local(day, parse_hhmm(hour), tz)),
        to_local_dt(combine_local(day, parse_hhmm(end), tz)),
    )


def test_ics_includes_tzid_location_geo_and_notes() -> None:
    tz = "Asia/Tokyo"
    start, end = _slot(tz, "09:00", "11:00")
    itinerary = Itinerary(
        timezone=tz,
        currency="JPY",
        days=[
            ItineraryDay(
                day_index=0,
                date=date(2026, 4, 10),
                timezone=tz,
                items=[
                    ItineraryItem(
                        type=ItineraryItemType.ACTIVITY,
                        start=start,
                        end=end,
                        place=_place(),
                        title="Senso-ji",
                        reason="Closest temple to your hotel and open all morning.",
                        cost=CostAmount(
                            amount=0, currency="JPY", label=CostLabel.ESTIMATED_COST
                        ),
                    ),
                    ItineraryItem(
                        type=ItineraryItemType.TRANSIT,
                        start=end,
                        end=end,
                        title="Walk",
                    ),
                ],
            )
        ],
    )
    ics = itinerary_to_ics(itinerary, plan_id="plan-tokyo")
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VTIMEZONE" in ics
    assert "TZID:Asia/Tokyo" in ics
    assert "TZID=Asia/Tokyo" in ics
    assert "LOCATION:Senso-ji (35.71000\\, 139.79000)" in ics
    assert "GEO:35.710000;139.790000" in ics
    assert "Closest temple" in ics
    assert "Estimated" in ics
    assert "SUMMARY:Walk" not in ics
    assert 'filename' not in ics
    assert ics.endswith("\r\n")


def test_ics_uses_each_day_timezone() -> None:
    tokyo = "Asia/Tokyo"
    zurich = "Europe/Zurich"
    t_start, t_end = _slot(tokyo, "10:00", "12:00")
    z_start, z_end = _slot(zurich, "09:00", "11:00", on=date(2026, 4, 11))
    itinerary = Itinerary(
        timezone=tokyo,
        currency="JPY",
        days=[
            ItineraryDay(
                day_index=0,
                date=date(2026, 4, 10),
                timezone=tokyo,
                city="Tokyo",
                items=[
                    ItineraryItem(
                        type=ItineraryItemType.ACTIVITY,
                        start=t_start,
                        end=t_end,
                        place=_place(),
                        title="Senso-ji",
                    )
                ],
            ),
            ItineraryDay(
                day_index=1,
                date=date(2026, 4, 11),
                timezone=zurich,
                city="Zurich",
                items=[
                    ItineraryItem(
                        type=ItineraryItemType.ACTIVITY,
                        start=z_start,
                        end=z_end,
                        title="Old Town walk",
                    )
                ],
            ),
        ],
    )
    ics = itinerary_to_ics(itinerary)
    assert "TZID=Asia/Tokyo" in ics
    assert "TZID=Europe/Zurich" in ics
    assert ics.count("BEGIN:VTIMEZONE") == 2


def test_ics_folds_long_description() -> None:
    tz = "Asia/Tokyo"
    start, end = _slot(tz, "09:00", "11:00")
    reason = "Chosen because " + ("it is nearby, well rated, and fits the morning window. " * 8)
    itinerary = Itinerary(
        timezone=tz,
        currency="JPY",
        days=[
            ItineraryDay(
                day_index=0,
                date=date(2026, 4, 10),
                timezone=tz,
                items=[
                    ItineraryItem(
                        type=ItineraryItemType.ACTIVITY,
                        start=start,
                        end=end,
                        place=_place(),
                        title="Senso-ji",
                        reason=reason,
                    )
                ],
            )
        ],
    )
    ics = itinerary_to_ics(itinerary)
    assert "\r\n " in ics
    for raw_line in ics.split("\r\n"):
        if raw_line:
            assert len(raw_line.encode("utf-8")) <= 75
