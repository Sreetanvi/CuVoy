from datetime import date

from cuvoy_contracts.constants import TTL_CHECKPOINT
from cuvoy_contracts.enrichment import Weather
from cuvoy_contracts.enums import PlaceSource, TransportMode, WeatherConfidence, WeatherSource
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import LocationInput, PlanRequest, TravelDates

from app.ai_gateway.fallback import run_fallback
from app.ai_gateway.gateway import AIRequest, AIResult
from app.pipeline.context import PipelineContext
from app.pipeline.orchestrator import run_pipeline
from app.providers.mapbox_directions import DirectionsResult
from app.providers.mapbox_matrix import haversine_matrix
from app.providers.website_verify import VerifyResult
from app.services.budget import new_envelope
from app.services.cache import InMemoryCache, cache_set_json
from app.services.jobs import job_key


def _place(pid: str, name: str, lat: float, lng: float, category: str = "museum") -> Place:
    return Place(
        id=pid,
        name=name,
        lat=lat,
        lng=lng,
        category=category,
        opening_hours="Mo-Su 09:00-18:00",
        source=PlaceSource.OSM,
    )


class FakeGateway:
    async def complete(self, request: AIRequest, budget=None) -> AIResult:
        parsed = run_fallback(request.task, request.fallback_payload)
        output = parsed.model_dump(mode="json") if hasattr(parsed, "model_dump") else None
        return AIResult(
            success=True,
            provider="deterministic",
            model="deterministic",
            output=output,
            parsed=parsed,
            fallback_used=True,
        )


class FakeExternal:
    def __init__(self) -> None:
        self.places = [
            _place("m1", "Museum One", 12.9716, 77.5946),
            _place("m2", "Museum Two", 12.9720, 77.5950),
            _place("p1", "Cubbon Park", 12.9760, 77.5929, "park"),
            _place("v1", "Viewpoint", 12.9800, 77.6000, "viewpoint"),
            _place("r1", "Local Kitchen", 12.9740, 77.5935, "restaurant"),
        ]

    async def geocode(self, query: str, *, budget=None, **kwargs) -> dict:
        key = query.lower().split(",")[0].strip()
        known = {
            "jaipur": {"lat": 26.9124, "lng": 75.7873, "name": "Jaipur, Rajasthan, India", "country_code": "IN"},
            "jodhpur": {"lat": 26.2389, "lng": 73.0243, "name": "Jodhpur, Rajasthan, India", "country_code": "IN"},
            "udaipur": {"lat": 24.5854, "lng": 73.7125, "name": "Udaipur, Rajasthan, India", "country_code": "IN"},
            "ooty": {"lat": 11.4102, "lng": 76.6950, "name": "Ooty, Tamil Nadu, India", "country_code": "IN"},
            "coonoor": {"lat": 11.3530, "lng": 76.7959, "name": "Coonoor, Tamil Nadu, India", "country_code": "IN"},
            "kolkata": {"lat": 22.5726, "lng": 88.3639, "name": "Kolkata, West Bengal, India", "country_code": "IN"},
        }
        if key in known:
            return known[key]
        return {"lat": 12.9716, "lng": 77.5946, "name": "Bengaluru", "country_code": "IN"}

    async def search_places(self, query: str, *, proximity=None, limit=10, budget=None):
        text = query.lower()
        if any(city in text for city in ("jaipur", "jodhpur", "udaipur", "ooty", "coonoor", "kolkata")):
            return []
        return list(self.places)

    async def osm_city_batch(self, city, *, lat, lng, radius_km=15.0, budget=None):
        label = str(city).split(",")[0].strip() or "City"
        slug = label.lower().replace(" ", "-")
        if slug in {"jaipur", "jodhpur", "udaipur", "ooty", "coonoor", "kolkata"}:
            return [
                _place(f"{slug}-m1", f"{label} Museum", lat, lng),
                _place(f"{slug}-f1", f"{label} Fort", lat + 0.01, lng + 0.01, "historic"),
                _place(f"{slug}-p1", f"{label} Garden", lat + 0.02, lng + 0.01, "park"),
                _place(f"{slug}-v1", f"{label} Viewpoint", lat + 0.015, lng + 0.02, "viewpoint"),
                _place(f"{slug}-r1", f"{label} Kitchen", lat + 0.005, lng + 0.005, "restaurant"),
            ]
        return list(self.places)

    def match_and_enrich(self, candidates, osm_places):
        return candidates

    async def travel_matrix(self, coords, *, mode=TransportMode.WALKING, budget=None):
        return haversine_matrix(coords, "walking")

    async def directions(self, coords, *, mode=TransportMode.WALKING, budget=None):
        return DirectionsResult("poly", 120, 400, False)

    async def weather(self, lat, lng, day, *, budget=None, today=None):
        return Weather(
            source=WeatherSource.FORECAST,
            is_forecast=True,
            confidence=WeatherConfidence.HIGH,
            summary="Clear",
        )

    async def holidays(self, country_code, year):
        return []

    async def verify_website(self, url, *, budget=None):
        return VerifyResult(ok=True, hours_snippet=None, warning=None)


def plan_request() -> PlanRequest:
    return PlanRequest(
        user_prompt="3 days in Bengaluru for museums and food",
        travel_dates=TravelDates(start_date=date(2026, 4, 10), end_date=date(2026, 4, 12)),
        location=LocationInput(query="Bengaluru"),
    )


async def test_pipeline_builds_itinerary() -> None:
    cache = InMemoryCache()
    await cache_set_json(
        cache,
        job_key("plan-test"),
        {"job_id": "plan-test", "status": "queued", "events": []},
        TTL_CHECKPOINT,
    )
    ctx = PipelineContext(
        plan_id="plan-test",
        request=plan_request(),
        budget=new_envelope("plan-test"),
        cache=cache,
        external=FakeExternal(),
        gateway=FakeGateway(),
        identity="anon:test",
    )
    await run_pipeline(ctx)
    assert ctx.result is not None
    assert ctx.result.validation.valid is True
    assert ctx.itinerary is not None
    assert len(ctx.itinerary.days) >= 1
    assert ctx.itinerary.timezone == "Asia/Kolkata"
    assert any(day.items for day in ctx.itinerary.days)


async def test_pipeline_allocates_days_across_three_cities() -> None:
    cache = InMemoryCache()
    await cache_set_json(
        cache,
        job_key("plan-multi"),
        {"job_id": "plan-multi", "status": "queued", "events": []},
        TTL_CHECKPOINT,
    )
    request = PlanRequest(
        user_prompt="Jaipur, Jodhpur, Udaipur for 5 days",
        travel_dates=TravelDates(start_date=date(2026, 4, 10), end_date=date(2026, 4, 14)),
        location=LocationInput(query="Jaipur, Jodhpur, Udaipur"),
    )
    ctx = PipelineContext(
        plan_id="plan-multi",
        request=request,
        budget=new_envelope("plan-multi"),
        cache=cache,
        external=FakeExternal(),
        gateway=FakeGateway(),
        identity="anon:test",
    )
    await run_pipeline(ctx)
    assert ctx.destinations
    assert [int(row["day_count"]) for row in ctx.destinations] == [2, 2, 1]
    cities = [day.city for day in (ctx.itinerary.days if ctx.itinerary else [])]
    assert cities.count("Jaipur") == 2
    assert cities.count("Jodhpur") == 2
    assert cities.count("Udaipur") == 1


async def test_pipeline_honors_destination_box_over_prompt_city() -> None:
    cache = InMemoryCache()
    await cache_set_json(
        cache,
        job_key("plan-ooty"),
        {"job_id": "plan-ooty", "status": "queued", "events": []},
        TTL_CHECKPOINT,
    )
    request = PlanRequest(
        user_prompt="Weekend in Kolkata for food",
        travel_dates=TravelDates(start_date=date(2026, 4, 10), end_date=date(2026, 4, 13)),
        location=LocationInput(query="Ooty and Coonoor"),
    )
    ctx = PipelineContext(
        plan_id="plan-ooty",
        request=request,
        budget=new_envelope("plan-ooty"),
        cache=cache,
        external=FakeExternal(),
        gateway=FakeGateway(),
        identity="anon:test",
    )
    await run_pipeline(ctx)
    names = [str(row["query"]).lower() for row in ctx.destinations]
    assert names == ["ooty", "coonoor"]
    assert all("kolkata" not in str(row.get("name") or "").lower() for row in ctx.destinations)
    titles = [
        item.title or ""
        for day in (ctx.itinerary.days if ctx.itinerary else [])
        for item in day.items
    ]
    assert any("Ooty" in title and "Coonoor" in title for title in titles)
