import httpx
import pytest
from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES
from cuvoy_contracts.enums import CostLabel, TransportMode

from app.providers.gtfs.fares import transit_fare
from app.providers.gtfs.registry import lookup_feed
from app.providers.mapbox_matrix import travel_matrix
from app.providers.mapbox_search import search_places
from app.services.cache import InMemoryCache


@pytest.mark.asyncio
async def test_matrix_over_cap_does_not_call_mapbox() -> None:
    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(500, json={})

    coords = [(12.0 + i * 0.01, 77.0) for i in range(MAX_MATRIX_COORDINATES + 1)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        matrix = await travel_matrix(
            http, InMemoryCache(), "token", coords, mode=TransportMode.WALKING
        )
    assert called["n"] == 0
    assert matrix.approximate is True
    assert len(matrix.durations) == MAX_MATRIX_COORDINATES + 1
    assert matrix.durations[0][1] > 0


@pytest.mark.asyncio
async def test_search_cache_skips_second_http() -> None:
    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [77.59, 12.97]},
                        "properties": {
                            "name": "Cubbon Park",
                            "mapbox_id": "abc",
                            "poi_category": ["park"],
                        },
                    }
                ]
            },
        )

    cache = InMemoryCache()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        first = await search_places(
            http, cache, "token", "parks in bengaluru", proximity=(12.97, 77.59)
        )
        second = await search_places(
            http, cache, "token", "parks in bengaluru", proximity=(12.97, 77.59)
        )
    assert called["n"] == 1
    assert first[0].name == "Cubbon Park"
    assert second[0].id == first[0].id


def test_gtfs_unverified_is_cost_unavailable() -> None:
    feed = lookup_feed("Bengaluru")
    assert feed is not None
    assert feed.feed_url == ""
    assert feed.fare_available is False
    cost = transit_fare("Bengaluru")
    assert cost.label == CostLabel.UNAVAILABLE
    assert cost.amount is None
