from cuvoy_contracts.constants import MAX_MATRIX_COORDINATES

from app.geo.candidate_reduce import reduce_candidates
from app.geo.h3_index import assign_h3, h3_cell
from tests.unit.places import place


def test_reduce_shrinks_at_least_half_when_large() -> None:
    places = [
        place(f"p{i}", f"Museum {i}", 12.97 + (i % 10) * 0.01, 77.59 + (i // 10) * 0.01)
        for i in range(60)
    ]
    reduced = reduce_candidates(places, interests=["history"], destination_id="blr")
    assert len(reduced.strong) <= len(places) // 2
    assert len(reduced.strong) <= 40
    assert len(reduced.matrix_places) <= MAX_MATRIX_COORDINATES
    assert len(reduced.relevant) <= 100


def test_industrial_names_never_reach_ranking() -> None:
    places = [
        place("open", "City Museum", 12.97, 77.59),
        place("fac", "Acme Widget Factory", 12.98, 77.60, category="museum"),
        place("off", "Downtown Office Park", 12.99, 77.61, category="office"),
    ]
    reduced = reduce_candidates(places, destination_id="blr")
    ids = {p.id for p in reduced.strong + reduced.relevant + reduced.matrix_places}
    assert "open" in ids
    assert "fac" not in ids
    assert "off" not in ids


def test_residential_places_never_reach_ranking() -> None:
    places = [
        place("open", "City Museum", 12.97, 77.59),
        place("host", "Greenview Boys Hostel", 12.98, 77.60, category="attraction"),
        place("pg", "Sri Sai PG", 12.99, 77.61, category="museum"),
        place("apt", "Lakeview Apartment", 13.00, 77.62, category="attraction"),
        place("res", "Oakwood Residency", 13.01, 77.63, category="poi"),
        place("hotel", "Hotel Lake Residency", 13.02, 77.64, category="hotel"),
    ]
    reduced = reduce_candidates(places, destination_id="blr")
    ids = {p.id for p in reduced.strong + reduced.relevant + reduced.matrix_places}
    assert "open" in ids
    assert "hotel" in ids
    assert "host" not in ids
    assert "pg" not in ids
    assert "apt" not in ids
    assert "res" not in ids


def test_closed_places_dropped() -> None:
    places = [
        place("open", "Open Museum", 12.97, 77.59, hours="Mo-Su 09:00-18:00"),
        place("shut", "Closed Museum", 12.98, 77.60, hours="closed"),
    ]
    reduced = reduce_candidates(places, destination_id="blr")
    ids = {p.id for p in reduced.strong}
    assert "open" in ids
    assert "shut" not in ids


def test_small_set_is_not_over_shrunk() -> None:
    places = [
        place(f"p{i}", f"Park {i}", 12.97, 77.59 + i * 0.002, category="park")
        for i in range(8)
    ]
    reduced = reduce_candidates(places)
    assert len(reduced.strong) == 8


def test_h3_is_deterministic() -> None:
    a = h3_cell(12.9716, 77.5946, 9)
    b = h3_cell(12.9716, 77.5946, 9)
    assert a == b
    mapped = assign_h3([place("a", "Cubbon", 12.9716, 77.5946, category="park")])
    assert mapped["a"] == a
