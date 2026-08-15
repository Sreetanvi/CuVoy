from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from cuvoy_contracts.constants import TTL_CHECKPOINT
from cuvoy_contracts.enums import PlaceSource, TransportMode
from cuvoy_contracts.place import Place
from cuvoy_contracts.preferences import LocationInput, PlanRequest, TravelDates

from app.geo.candidate_reduce import reduce_candidates
from app.geo.timezone import iana_timezone
from app.optimize.ortools_solver import optimize_visit_order
from app.pipeline.context import PipelineContext
from app.pipeline.orchestrator import run_pipeline
from app.providers.mapbox_matrix import haversine_matrix
from app.services.budget import new_envelope
from app.services.cache import InMemoryCache, cache_set_json
from app.services.jobs import job_key
from tests.unit.test_pipeline import FakeExternal, FakeGateway

FIXTURE_DIR = Path(__file__).parent / "fixtures"
CITIES = ("bengaluru", "jaipur", "tokyo", "interlaken", "paris")


def _load(city: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{city}.json").read_text(encoding="utf-8"))


def _places(fixture: dict) -> list[Place]:
    return [
        Place(
            id=row["id"],
            name=row["name"],
            lat=row["lat"],
            lng=row["lng"],
            category=row["category"],
            opening_hours="Mo-Su 09:00-18:00",
            source=PlaceSource.OSM,
        )
        for row in fixture["places"]
    ]


class FixtureExternal(FakeExternal):
    def __init__(self, fixture: dict) -> None:
        super().__init__()
        self.fixture = fixture
        self.places = _places(fixture)
        self.osm_calls = 0

    async def geocode(self, query: str, *, budget=None, **kwargs) -> dict:
        return {
            "lat": self.fixture["lat"],
            "lng": self.fixture["lng"],
            "name": self.fixture["name"],
            "country_code": self.fixture["country_code"],
        }

    async def search_places(self, query: str, *, proximity=None, limit=10, budget=None):
        return list(self.places)

    async def osm_city_batch(self, city, *, lat, lng, radius_km=15.0, budget=None):
        self.osm_calls += 1
        return list(self.places)


@pytest.mark.parametrize("city", CITIES)
def test_benchmark_timezone_matches_fixture(city: str) -> None:
    fixture = _load(city)
    assert iana_timezone(fixture["lat"], fixture["lng"]) == fixture["timezone"]


@pytest.mark.parametrize("city", CITIES)
def test_benchmark_reduce_and_optimize(city: str) -> None:
    fixture = _load(city)
    seed = _places(fixture)
    extras = [
        Place(
            id=f"{fixture['id']}-x{i}",
            name=f"{fixture['name']} Museum {i}",
            lat=fixture["lat"] + (i % 8) * 0.004,
            lng=fixture["lng"] + (i // 8) * 0.004,
            category="museum",
            opening_hours="Mo-Su 09:00-18:00",
            source=PlaceSource.OSM,
        )
        for i in range(40)
    ]
    reduced = reduce_candidates(seed + extras, destination_id=fixture["id"])
    assert len(reduced.strong) <= len(seed + extras) // 2
    coords = [(place.lat, place.lng) for place in reduced.matrix_places[:8]]
    matrix = haversine_matrix(coords, TransportMode.WALKING.value)
    ordered = optimize_visit_order(matrix.durations)
    assert len(ordered.order) == len(coords)
    assert set(ordered.order) == set(range(len(coords)))


@pytest.mark.parametrize("city", CITIES)
@pytest.mark.asyncio
async def test_benchmark_pipeline_local_times(city: str) -> None:
    fixture = _load(city)
    cache = InMemoryCache()
    plan_id = f"bench-{city}"
    await cache_set_json(
        cache,
        job_key(plan_id),
        {"job_id": plan_id, "status": "queued", "events": []},
        TTL_CHECKPOINT,
    )
    external = FixtureExternal(fixture)
    ctx = PipelineContext(
        plan_id=plan_id,
        request=PlanRequest(
            user_prompt=fixture["prompt"],
            travel_dates=TravelDates(start_date=date(2026, 4, 10), end_date=date(2026, 4, 12)),
            location=LocationInput(query=fixture["query"]),
        ),
        budget=new_envelope(plan_id),
        cache=cache,
        external=external,
        gateway=FakeGateway(),
        identity="anon:bench",
    )
    await run_pipeline(ctx)
    assert ctx.result is not None
    assert ctx.result.validation.valid is True
    assert ctx.itinerary is not None
    assert ctx.itinerary.timezone == fixture["timezone"]
    assert external.osm_calls == 1
    for day in ctx.itinerary.days:
        assert day.timezone == fixture["timezone"]
        for item in day.items:
            assert item.start.timezone == fixture["timezone"]
            assert item.end.timezone == fixture["timezone"]
            assert "T" in item.start.local_time
    categories = {place.category for place in _places(fixture)}
    if "heritage" in fixture["focus"] or "forts" in fixture["focus"]:
        assert "historic" in categories
    if "gtfs" in fixture["focus"] or "transit" in fixture["focus"]:
        assert categories & {"station", "bus_station", "metro"}
    if "nature" in fixture["focus"]:
        assert "viewpoint" in categories
    if "walking" in fixture["focus"] or "culture" in fixture["focus"]:
        assert "museum" in categories
