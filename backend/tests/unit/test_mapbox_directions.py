import json

import httpx
import pytest
from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES
from cuvoy_contracts.enums import TransportMode

from app.providers.mapbox_directions import directions, straight_line_geojson
from app.services.cache import InMemoryCache


def test_straight_line_is_open() -> None:
    raw = straight_line_geojson([(12.97, 77.59), (12.98, 77.60), (12.97, 77.59)])
    assert raw is not None
    geom = json.loads(raw)
    assert geom["type"] == "LineString"
    assert geom["coordinates"][0] != geom["coordinates"][-1]


def _route_response(coordinates: list[list[float]], *, duration: int = 100, distance: int = 200) -> dict:
    return {
        "routes": [
            {
                "duration": duration,
                "distance": distance,
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        ]
    }


@pytest.mark.asyncio
async def test_directions_requests_full_geojson_and_caps_waypoints() -> None:
    seen: dict = {"urls": [], "waypoints": []}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["urls"].append(str(request.url))
        seen["params"] = dict(request.url.params)
        path_coords = str(request.url.path).rsplit("/", 1)[-1]
        n = path_coords.count(";") + 1
        seen["waypoints"].append(n)
        pairs = path_coords.split(";")
        start = [float(x) for x in pairs[0].split(",")]
        end = [float(x) for x in pairs[-1].split(",")]
        mid = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
        return httpx.Response(200, json=_route_response([start, mid, end], duration=10, distance=20))

    coords = [(12.0 + i * 0.01, 77.0 + i * 0.01) for i in range(MAX_MATRIX_COORDINATES + 8)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await directions(http, InMemoryCache(), "token", coords, mode=TransportMode.CAR)
    assert len(seen["urls"]) == MAX_MATRIX_COORDINATES - 1
    assert seen["waypoints"] == [2] * (MAX_MATRIX_COORDINATES - 1)
    assert seen["params"]["geometries"] == "geojson"
    assert seen["params"]["overview"] == "full"
    assert all("/mapbox/driving/" in url for url in seen["urls"])
    geom = json.loads(result.geometry or "")
    assert geom["type"] == "LineString"
    assert len(geom["coordinates"]) > 2
    assert result.duration_seconds == 10 * (MAX_MATRIX_COORDINATES - 1)
    assert result.distance_meters == 20 * (MAX_MATRIX_COORDINATES - 1)


@pytest.mark.asyncio
async def test_directions_falls_back_to_straight_line() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "nope"})

    coords = [(12.97, 77.59), (12.98, 77.60)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await directions(http, InMemoryCache(), "token", coords, mode=TransportMode.WALKING)
    assert result.geometry is not None
    geom = json.loads(result.geometry)
    assert geom["coordinates"] == [[77.59, 12.97], [77.60, 12.98]]


@pytest.mark.asyncio
async def test_directions_fetches_leg_by_leg_and_concatenates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path_coords = str(request.url.path).rsplit("/", 1)[-1]
        if path_coords.startswith("77.59,12.97"):
            return httpx.Response(
                200,
                json=_route_response(
                    [[77.59, 12.97], [77.592, 12.971], [77.60, 12.98]],
                    duration=30,
                    distance=400,
                ),
            )
        return httpx.Response(
            200,
            json=_route_response(
                [[77.60, 12.98], [77.605, 12.985], [77.61, 12.99]],
                duration=40,
                distance=500,
            ),
        )

    coords = [(12.97, 77.59), (12.98, 77.60), (12.99, 77.61)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await directions(http, InMemoryCache(), "token", coords, mode=TransportMode.WALKING)
    geom = json.loads(result.geometry or "")
    assert geom["coordinates"] == [
        [77.59, 12.97],
        [77.592, 12.971],
        [77.60, 12.98],
        [77.605, 12.985],
        [77.61, 12.99],
    ]
    assert result.duration_seconds == 70
    assert result.distance_meters == 900


def _path_lng_lat(request: httpx.Request) -> tuple[list[float], list[float]]:
    path_coords = str(request.url.path).rsplit("/", 1)[-1]
    start_s, end_s = path_coords.split(";")
    start = [float(x) for x in start_s.split(",")]
    end = [float(x) for x in end_s.split(",")]
    return start, end


@pytest.mark.asyncio
async def test_directions_failed_leg_is_straight_others_stay_snapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        start, end = _path_lng_lat(request)
        if start == [77.60, 12.98] and end == [77.61, 12.99]:
            return httpx.Response(422, json={"message": "unroutable"})
        mid = [round((start[0] + end[0]) / 2, 5), round((start[1] + end[1]) / 2, 5)]
        return httpx.Response(
            200,
            json=_route_response([start, mid, end], duration=25, distance=300),
        )

    coords = [(12.97, 77.59), (12.98, 77.60), (12.99, 77.61), (13.00, 77.62)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await directions(http, InMemoryCache(), "token", coords, mode=TransportMode.WALKING)
    geom = json.loads(result.geometry or "")
    assert geom["coordinates"] == [
        [77.59, 12.97],
        [77.595, 12.975],
        [77.60, 12.98],
        [77.61, 12.99],
        [77.615, 12.995],
        [77.62, 13.00],
    ]
    assert result.duration_seconds == 50
    assert result.distance_meters == 600


@pytest.mark.asyncio
async def test_directions_ignores_exhausted_matrix_budget() -> None:
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        start, end = _path_lng_lat(request)
        mid = [round((start[0] + end[0]) / 2, 5), round((start[1] + end[1]) / 2, 5)]
        return httpx.Response(200, json=_route_response([start, mid, end], duration=12, distance=80))

    from app.providers.mapbox_directions import get_road_snapped_route
    from app.services.budget import PlanBudget

    budget = PlanBudget(plan_id="p", remaining={"mapbox_matrix": 0})
    coords = [(12.97, 77.59), (12.98, 77.60)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await get_road_snapped_route(
            http, InMemoryCache(), "token", coords, mode=TransportMode.WALKING, budget=budget
        )
    assert seen["n"] == 1
    assert result.legs
    assert result.legs[0].snapped is True
    geom = json.loads(result.geometry or "")
    assert len(geom["coordinates"]) == 3
