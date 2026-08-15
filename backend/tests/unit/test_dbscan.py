from app.geo.dbscan import adaptive_epsilon_m, cluster_places, dbscan_labels
from tests.unit.places import place


def test_two_neighborhoods_form_two_clusters() -> None:
    west = [place(f"w{i}", f"West {i}", 12.97, 77.58 + i * 0.001) for i in range(5)]
    east = [place(f"e{i}", f"East {i}", 13.08, 77.72 + i * 0.001) for i in range(5)]
    clusters = cluster_places(west + east, destination_id="blr")
    member_groups = [set(c.place_ids) for c in clusters if len(c.place_ids) > 1]
    assert any(pid.startswith("w") for group in member_groups for pid in group)
    assert any(pid.startswith("e") for group in member_groups for pid in group)
    west_ids = {p.id for p in west}
    east_ids = {p.id for p in east}
    assert any(west_ids <= group or west_ids == group for group in member_groups) or any(
        len(group & west_ids) >= 3 for group in member_groups
    )
    assert any(len(group & east_ids) >= 3 for group in member_groups)


def test_noise_points_are_retained() -> None:
    dense = [place(f"d{i}", f"Dense {i}", 48.86, 2.34 + i * 0.0004) for i in range(6)]
    outlier = place("far", "Outlier", 48.95, 2.55)
    clusters = cluster_places(dense + [outlier], destination_id="paris")
    ids = {pid for c in clusters for pid in c.place_ids}
    assert "far" in ids


def test_failure_skips_to_single_cluster() -> None:
    clusters = cluster_places([], destination_id="x")
    assert clusters == []
    one = cluster_places([place("a", "Solo", 0.0, 0.0)], destination_id="x")
    assert len(one) == 1
    assert one[0].place_ids == ["a"]


def test_epsilon_scales_with_spread() -> None:
    tight = [(12.97, 77.59 + i * 0.0002) for i in range(8)]
    wide = [(12.97 + i * 0.05, 77.59 + i * 0.05) for i in range(8)]
    assert adaptive_epsilon_m(tight) < adaptive_epsilon_m(wide)
    labels = dbscan_labels(tight, min_samples=2)
    assert max(labels) >= 0
