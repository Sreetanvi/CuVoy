from app.providers.place_name import resolve_candidate_name


def test_prefers_explicit_name() -> None:
    assert resolve_candidate_name(name="Lalbagh", tags={"tourism": "attraction"}) == "Lalbagh"


def test_uses_name_en_then_amenity() -> None:
    assert resolve_candidate_name(tags={"name:en": "City Park"}) == "City Park"
    assert resolve_candidate_name(tags={"amenity": "place_of_worship"}) == "Place Of Worship"
    assert resolve_candidate_name(tags={"tourism": "viewpoint"}) == "Viewpoint"


def test_skips_osm_ids_and_falls_back() -> None:
    assert (
        resolve_candidate_name(name="osm:node/11806680476", tags={"tourism": "museum"})
        == "Museum"
    )
    assert resolve_candidate_name(name="osm:way/1", place_id="osm:way/1") == "Unnamed Location (osm:way/1)"
