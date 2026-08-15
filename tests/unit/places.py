from cuvoy_contracts.enums import PlaceSource
from cuvoy_contracts.place import Place


def place(
    pid: str,
    name: str,
    lat: float,
    lng: float,
    category: str = "museum",
    hours: str | None = "Mo-Su 09:00-18:00",
) -> Place:
    return Place(
        id=pid,
        name=name,
        lat=lat,
        lng=lng,
        category=category,
        opening_hours=hours,
        source=PlaceSource.OSM,
    )
