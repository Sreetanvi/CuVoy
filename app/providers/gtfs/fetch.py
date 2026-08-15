"""GTFS fetch: compact artifacts only. Never Pandas, never full CSV parse."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.providers.gtfs.registry import GtfsFeed, lookup_feed

logger = logging.getLogger("cuvoy.providers")

_ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def artifact_path(city: str) -> Path:
    return _ARTIFACTS / f"{city.strip().lower()}.json"


def load_artifact(city: str) -> dict:
    path = artifact_path(city)
    if not path.is_file():
        return {"city": city, "fare_available": False, "fares": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("gtfs_artifact_invalid", extra={"provider": "gtfs"})
        return {"city": city, "fare_available": False, "fares": []}
    if not isinstance(data, dict):
        return {"city": city, "fare_available": False, "fares": []}
    return data


def compact_for_city(city: str) -> tuple[GtfsFeed | None, dict]:
    feed = lookup_feed(city)
    artifact = load_artifact(city)
    return feed, artifact
