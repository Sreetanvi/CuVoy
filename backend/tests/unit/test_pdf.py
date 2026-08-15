from datetime import date

from cuvoy_contracts.api import PlanResult
from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.constants import AI_DISCLAIMER
from cuvoy_contracts.enrichment import MapBounds, MapMarker, MapPayload, ValidationReport
from cuvoy_contracts.enums import CostLabel, ItineraryItemType, PlaceSource, TransportMode
from cuvoy_contracts.itinerary import Itinerary, ItineraryDay, ItineraryItem, RouteLeg
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import ExtractedPreferences

from app.export.pdf import build_pdf_document
from app.schedule.clock import combine_local, parse_hhmm, to_local_dt


def test_pdf_document_uses_local_abbrev_and_disclaimer() -> None:
    tz = "Asia/Tokyo"
    place = Place(
        id="p1",
        name="Senso-ji",
        lat=35.71,
        lng=139.79,
        category="temple",
        source=PlaceSource.OSM,
    )
    start = to_local_dt(combine_local(date(2026, 4, 10), parse_hhmm("09:00"), tz))
    end = to_local_dt(combine_local(date(2026, 4, 10), parse_hhmm("11:00"), tz))
    result = PlanResult(
        plan_id="plan-1",
        timezone=tz,
        preferences=ExtractedPreferences(),
        itinerary=Itinerary(
            timezone=tz,
            currency="JPY",
            days=[
                ItineraryDay(
                    day_index=0,
                    date=date(2026, 4, 10),
                    timezone=tz,
                    city="Tokyo",
                    items=[
                        ItineraryItem(
                            type=ItineraryItemType.ACTIVITY,
                            start=start,
                            end=end,
                            place=place,
                            title="Senso-ji",
                            reason="Open early and next to the hotel.",
                            cost=CostAmount(
                                amount=400,
                                currency="JPY",
                                label=CostLabel.ESTIMATED_COST,
                            ),
                        )
                    ],
                )
            ],
        ),
        map=MapPayload(
            markers=[MapMarker(place_id="p1", lat=35.71, lng=139.79, label="Senso-ji")],
            bounds=MapBounds(min_lat=35.7, min_lng=139.7, max_lat=35.8, max_lng=139.8),
        ),
        routes=[
            RouteLeg(
                from_place_id="p1",
                to_place_id="p2",
                duration_seconds=480,
                duration_buffered_seconds=720,
                distance_meters=900,
                mode=TransportMode.WALKING,
            )
        ],
        validation=ValidationReport(valid=True),
    )
    doc = build_pdf_document(result)
    assert doc.renderer == "client"
    assert doc.logo_placement == "corner"
    assert doc.disclaimer == AI_DISCLAIMER
    assert doc.days[0].timezone_abbrev == "JST"
    assert doc.days[0].stops[0].start_local == "09:00 JST"
    assert doc.days[0].stops[0].cost_label == "Estimated"
    assert "400 JPY" in (doc.days[0].stops[0].cost or "")
    assert doc.route_labels[0].duration_label == "12 min"
