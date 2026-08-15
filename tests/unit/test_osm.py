from cuvoy_contracts.enums import PlaceSource
from cuvoy_contracts.place import Place

from app.providers.osm_match import coarse_category, match_osm
from app.providers.osm_overpass import normalize_overpass, overpass_ql


def test_overpass_ql_is_single_bbox_query() -> None:
    query = overpass_ql(12.8, 77.5, 13.1, 77.7)
    assert query.count("out center") == 1
    assert "12.8,77.5,13.1,77.7" in query
    assert query.startswith("[out:json]")
    assert query.count('["name"]') == 5
    assert 'nwr["tourism"]["name"]' in query
    assert 'nwr["historic"]["name"]' in query
    assert 'nwr["leisure"]["name"]' in query
    assert 'nwr["natural"]["name"]' in query
    assert 'nwr["amenity"~"' in query
    assert '["office"!~"."]' in query
    assert '["landuse"!="residential"]' in query
    assert '["building"!="residential"]' in query
    assert '["amenity"!="student_accommodation"]' in query
    assert '["amenity"!="social_facility"]' in query
    assert '["residential"!~"."]' in query


def test_normalize_resolves_tag_fallback_names_and_dedupes() -> None:
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 12.97,
                "lon": 77.59,
                "tags": {"name": "Lalbagh", "leisure": "park"},
            },
            {
                "type": "node",
                "id": 1,
                "lat": 12.97,
                "lon": 77.59,
                "tags": {"name": "Lalbagh", "leisure": "park"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": 12.971,
                "lon": 77.591,
                "tags": {"name:en": "Cubbon Park", "leisure": "park"},
            },
            {
                "type": "node",
                "id": 9,
                "lat": 12.96,
                "lon": 77.58,
                "tags": {
                    "name": "Lion Brand Appalam Manufacturers",
                    "industrial": "yes",
                    "craft": "manufacturer",
                },
            },
            {
                "type": "node",
                "id": 8,
                "lat": 12.95,
                "lon": 77.57,
                "tags": {"tourism": "attraction"},
            },
            {
                "type": "node",
                "id": 11,
                "lat": 12.94,
                "lon": 77.56,
                "tags": {
                    "name": "Acme Works Visitor Centre",
                    "tourism": "museum",
                    "industrial": "yes",
                    "man_made": "works",
                },
            },
            {
                "type": "node",
                "id": 12,
                "lat": 12.93,
                "lon": 77.55,
                "tags": {
                    "name": "Greenview Boys Hostel",
                    "tourism": "hostel",
                    "building": "residential",
                },
            },
            {
                "type": "node",
                "id": 13,
                "lat": 12.92,
                "lon": 77.54,
                "tags": {
                    "name": "Sunrise PG",
                    "amenity": "student_accommodation",
                    "landuse": "residential",
                },
            },
            {
                "type": "way",
                "id": 3,
                "center": {"lat": 12.98, "lon": 77.60},
                "tags": {
                    "name": "Museum",
                    "tourism": "museum",
                    "opening_hours": "10:00-17:00",
                    "website": "https://museum.example",
                },
            },
        ]
    }
    places = normalize_overpass(payload)
    assert [p.id for p in places] == ["osm:node/1", "osm:node/2", "osm:way/3"]
    assert places[1].name == "Cubbon Park"
    museum = places[2]
    assert museum.category == "museum"
    assert museum.opening_hours == "10:00-17:00"
    assert museum.source == PlaceSource.OSM


def _place(pid: str, lat: float, lng: float, category: str) -> Place:
    return Place(id=pid, name=pid, lat=lat, lng=lng, category=category, source=PlaceSource.MAPBOX)


def test_match_osm_uses_proximity_and_category() -> None:
    candidate = _place("m1", 12.9716, 77.5946, "museum")
    near = Place(
        id="osm:1",
        name="City Museum",
        lat=12.9717,
        lng=77.5947,
        category="gallery",
        opening_hours="09:00-18:00",
        source=PlaceSource.OSM,
    )
    far = Place(
        id="osm:2",
        name="Other Museum",
        lat=13.05,
        lng=77.70,
        category="museum",
        source=PlaceSource.OSM,
    )
    food = Place(
        id="osm:3",
        name="Cafe",
        lat=12.9716,
        lng=77.5946,
        category="cafe",
        source=PlaceSource.OSM,
    )
    matched = match_osm(candidate, [far, food, near])
    assert matched is not None
    assert matched.id == "osm:1"
    assert coarse_category("gallery") == "museum"


def test_match_osm_rejects_distant_same_category() -> None:
    candidate = _place("m1", 12.97, 77.59, "museum")
    far = Place(
        id="osm:9",
        name="Far",
        lat=13.2,
        lng=77.9,
        category="museum",
        source=PlaceSource.OSM,
    )
    assert match_osm(candidate, [far]) is None
