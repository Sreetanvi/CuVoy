"""H3 indexes from coordinates only — never from an LLM. PROJECT_SPEC §32."""

from __future__ import annotations

from cuvoy_contracts.place import Place

from app.providers.geo import haversine_m

DEFAULT_RESOLUTION = 9


def h3_cell(lat: float, lng: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    from h3 import latlng_to_cell

    return latlng_to_cell(lat, lng, resolution)


def h3_resolution_for(places: list[Place]) -> int:
    """Denser / smaller extent → higher resolution (9). Spread regions → 7–8."""
    if len(places) < 2:
        return DEFAULT_RESOLUTION
    lats = [p.lat for p in places]
    lngs = [p.lng for p in places]
    diagonal_km = haversine_m(min(lats), min(lngs), max(lats), max(lngs)) / 1000.0
    density = len(places) / max(0.25, diagonal_km**2)
    if diagonal_km > 80 or density < 0.05:
        return 7
    if diagonal_km > 25 or density < 0.4:
        return 8
    return DEFAULT_RESOLUTION


def assign_h3(
    places: list[Place], resolution: int | None = None
) -> dict[str, str]:
    res = resolution if resolution is not None else h3_resolution_for(places)
    return {p.id: h3_cell(p.lat, p.lng, res) for p in places}
