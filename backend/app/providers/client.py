"""Cache-first external data facade. Pipeline talks to this, not raw APIs."""

from __future__ import annotations

from datetime import date

import httpx
from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.enrichment import Weather
from cuvoy_contracts.enums import TransportMode
from cuvoy_contracts.place import Place

from app.config import Settings
from app.providers import (
    mapbox_directions,
    mapbox_geocoding,
    mapbox_matrix,
    mapbox_search,
    nager,
    openmeteo,
    osm_match,
    osm_overpass,
    sunrise,
    website_verify,
)
from app.providers.geo import bbox_from_center
from app.providers.gtfs.fares import transit_fare
from app.providers.mapbox_directions import DirectionsResult
from app.providers.mapbox_matrix import TravelMatrix
from app.providers.opentripmap import geonames_lookup, opentripmap_nearby, wikipedia_summary
from app.providers.website_verify import VerifyResult
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend


class ExternalData:
    def __init__(self, settings: Settings, http: httpx.AsyncClient, cache: CacheBackend) -> None:
        self.settings = settings
        self.http = http
        self.cache = cache

    async def search_places(
        self,
        query: str,
        *,
        proximity: tuple[float, float] | None = None,
        limit: int = 10,
        budget: PlanBudget | None = None,
    ) -> list[Place]:
        return await mapbox_search.search_places(
            self.http,
            self.cache,
            self.settings.mapbox_access_token,
            query,
            proximity=proximity,
            limit=limit,
            budget=budget,
        )

    async def geocode(
        self,
        query: str,
        *,
        budget: PlanBudget | None = None,
        proximity: tuple[float, float] | None = None,
        country: str | None = None,
    ) -> dict | None:
        return await mapbox_geocoding.geocode(
            self.http,
            self.cache,
            self.settings.mapbox_access_token,
            query,
            budget=budget,
            proximity=proximity,
            country=country,
        )

    async def travel_matrix(
        self,
        coords: list[tuple[float, float]],
        *,
        mode: TransportMode = TransportMode.WALKING,
        budget: PlanBudget | None = None,
    ) -> TravelMatrix:
        return await mapbox_matrix.travel_matrix(
            self.http,
            self.cache,
            self.settings.mapbox_access_token,
            coords,
            mode=mode,
            budget=budget,
        )

    async def directions(
        self,
        coords: list[tuple[float, float]],
        *,
        mode: TransportMode = TransportMode.WALKING,
        budget: PlanBudget | None = None,
    ) -> DirectionsResult:
        return await mapbox_directions.get_road_snapped_route(
            self.http,
            self.cache,
            self.settings.mapbox_access_token,
            coords,
            mode=mode,
            budget=budget,
        )

    async def osm_city_batch(
        self,
        city: str,
        *,
        lat: float,
        lng: float,
        radius_km: float = 15.0,
        budget: PlanBudget | None = None,
    ) -> list[Place]:
        bbox = bbox_from_center(lat, lng, radius_km)
        return await osm_overpass.fetch_city_pois(
            self.http, self.cache, city, bbox, budget=budget
        )

    def match_and_enrich(self, candidates: list[Place], osm_places: list[Place]) -> list[Place]:
        enriched: list[Place] = []
        for candidate in candidates:
            osm = osm_match.match_osm(candidate, osm_places)
            if osm is None:
                enriched.append(candidate)
            else:
                enriched.append(osm_match.enrich_from_osm(candidate, osm))
        return enriched

    async def weather(
        self,
        lat: float,
        lng: float,
        day: date,
        *,
        budget: PlanBudget | None = None,
        today: date | None = None,
    ) -> Weather:
        return await openmeteo.weather_for_date(
            self.http, self.cache, lat, lng, day, budget=budget, today=today
        )

    async def holidays(self, country_code: str, year: int) -> list[dict]:
        return await nager.public_holidays(self.http, self.cache, country_code, year)

    async def sunrise_sunset(self, lat: float, lng: float, day: date) -> dict | None:
        return await sunrise.sunrise_sunset(self.http, self.cache, lat, lng, day)

    async def verify_website(self, url: str, *, budget: PlanBudget | None = None) -> VerifyResult:
        return await website_verify.verify_website(self.http, self.cache, url, budget=budget)

    async def opentripmap(
        self, lat: float, lng: float, *, budget: PlanBudget | None = None
    ) -> list[Place]:
        return await opentripmap_nearby(
            self.http,
            self.cache,
            self.settings.opentripmap_api_key,
            lat,
            lng,
            budget=budget,
        )

    async def geonames(self, query: str) -> dict | None:
        return await geonames_lookup(
            self.http, self.cache, self.settings.geonames_username, query
        )

    async def wikipedia(self, title: str) -> str | None:
        return await wikipedia_summary(self.http, self.cache, title)

    def transit_fare(self, city: str) -> CostAmount:
        return transit_fare(city)
