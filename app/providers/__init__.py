"""External data providers (Mapbox, OSM, weather, GTFS). Not the LLM adapters."""

from app.providers.client import ExternalData

__all__ = ["ExternalData"]
