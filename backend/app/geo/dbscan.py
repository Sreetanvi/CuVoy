"""Adaptive DBSCAN within a destination. Noise retained. PROJECT_SPEC §32."""

from __future__ import annotations

import logging
import statistics

from cuvoy_contracts.place import Cluster, Place

from app.providers.geo import haversine_m

logger = logging.getLogger("cuvoy.geo")

MIN_EPS_M = 400.0
MAX_EPS_M = 8_000.0
RECLUSTER_MAX_MEMBERS = 15
MATRIX_PER_CLUSTER = 15


def adaptive_epsilon_m(coords: list[tuple[float, float]]) -> float:
    """Epsilon from geographic extent + nearest-neighbor density — not a global constant."""
    n = len(coords)
    if n < 2:
        return 800.0
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    extent = haversine_m(min(lats), min(lngs), max(lats), max(lngs))
    nearest: list[float] = []
    for i, (lat1, lng1) in enumerate(coords):
        best = min(
            haversine_m(lat1, lng1, coords[j][0], coords[j][1])
            for j in range(n)
            if j != i
        )
        nearest.append(best)
    typical = statistics.median(nearest) if nearest else 800.0
    eps = max(typical * 2.2, extent / max(6.0, n**0.5))
    return min(MAX_EPS_M, max(MIN_EPS_M, eps))


def _neighbors(i: int, coords: list[tuple[float, float]], eps_m: float) -> list[int]:
    lat1, lng1 = coords[i]
    return [
        j
        for j, (lat2, lng2) in enumerate(coords)
        if haversine_m(lat1, lng1, lat2, lng2) <= eps_m
    ]


def dbscan_labels(
    coords: list[tuple[float, float]],
    *,
    eps_m: float | None = None,
    min_samples: int = 2,
) -> list[int]:
    n = len(coords)
    if n == 0:
        return []
    eps = eps_m if eps_m is not None else adaptive_epsilon_m(coords)
    visited = [False] * n
    labels = [-1] * n
    cluster_id = 0
    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        neigh = _neighbors(i, coords, eps)
        if len(neigh) < min_samples:
            continue
        labels[i] = cluster_id
        seeds = [j for j in neigh if j != i]
        k = 0
        while k < len(seeds):
            j = seeds[k]
            if not visited[j]:
                visited[j] = True
                extra = _neighbors(j, coords, eps)
                if len(extra) >= min_samples:
                    for x in extra:
                        if x not in seeds:
                            seeds.append(x)
            if labels[j] == -1:
                labels[j] = cluster_id
            k += 1
        cluster_id += 1
    return labels


def _centroid(members: list[Place]) -> tuple[float, float]:
    return (
        sum(p.lat for p in members) / len(members),
        sum(p.lng for p in members) / len(members),
    )


def _cluster(cluster_id: str, members: list[Place], destination_id: str | None) -> Cluster:
    lat, lng = _centroid(members)
    return Cluster(
        id=cluster_id,
        place_ids=[p.id for p in members],
        centroid_lat=lat,
        centroid_lng=lng,
        destination_id=destination_id,
    )


def cluster_places(
    places: list[Place],
    *,
    destination_id: str | None = None,
    min_samples: int = 2,
    eps_m: float | None = None,
    depth: int = 0,
) -> list[Cluster]:
    """
    Cluster within one destination. Noise points become single-place clusters.
    Oversized clusters are re-run with a tighter epsilon. On failure, skip clustering.
    """
    if not places:
        return []
    try:
        coords = [(p.lat, p.lng) for p in places]
        eps = eps_m if eps_m is not None else adaptive_epsilon_m(coords)
        labels = dbscan_labels(coords, eps_m=eps, min_samples=min_samples)
        grouped: dict[int, list[Place]] = {}
        noise: list[Place] = []
        for place, label in zip(places, labels, strict=True):
            if label < 0:
                noise.append(place)
            else:
                grouped.setdefault(label, []).append(place)

        clusters: list[Cluster] = []
        prefix = destination_id or "dest"
        for idx, members in grouped.items():
            if len(members) > RECLUSTER_MAX_MEMBERS and depth < 2:
                sub = cluster_places(
                    members,
                    destination_id=destination_id,
                    min_samples=max(2, min_samples),
                    eps_m=max(MIN_EPS_M, eps * 0.55),
                    depth=depth + 1,
                )
                if len(sub) > 1:
                    for j, cl in enumerate(sub):
                        cl.id = f"cluster_{prefix}_{idx}_{j:03d}"
                        clusters.append(cl)
                    continue
            clusters.append(_cluster(f"cluster_{prefix}_{idx:03d}", members, destination_id))

        for j, place in enumerate(noise):
            clusters.append(
                _cluster(f"cluster_{prefix}_noise_{j:03d}", [place], destination_id)
            )
        if not clusters:
            return [_cluster(f"cluster_{prefix}_all", places, destination_id)]
        return clusters
    except Exception:
        logger.warning("dbscan_failed_skip", extra={"stage": "cluster"})
        return [_cluster(f"cluster_{destination_id or 'dest'}_all", places, destination_id)]


def cap_cluster_members(
    places: list[Place], clusters: list[Cluster], cap: int = MATRIX_PER_CLUSTER
) -> list[Place]:
    """Keep 8–15 places per cluster (spec §27) while preserving input rank order."""
    by_id = {p.id: p for p in places}
    picked: list[Place] = []
    seen: set[str] = set()
    for cluster in clusters:
        count = 0
        for pid in cluster.place_ids:
            if pid in seen or pid not in by_id:
                continue
            picked.append(by_id[pid])
            seen.add(pid)
            count += 1
            if count >= cap:
                break
    return picked
