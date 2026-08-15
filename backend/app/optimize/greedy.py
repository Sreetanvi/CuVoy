"""Greedy nearest-neighbor if OR-Tools times out. PROJECT_SPEC §7.10."""

from __future__ import annotations


def nearest_neighbor_order(
    durations: list[list[int]],
    *,
    start: int = 0,
    locked: list[int] | None = None,
    max_leg_seconds: int | None = None,
) -> list[int]:
    n = len(durations)
    if n == 0:
        return []
    if n == 1:
        return [0]
    locked = [i for i in (locked or []) if 0 <= i < n]
    order = list(locked)
    remaining = [i for i in range(n) if i not in set(order)]
    if not order:
        order = [start if 0 <= start < n else 0]
        remaining = [i for i in remaining if i != order[0]]
    while remaining:
        last = order[-1]
        feasible = remaining
        if max_leg_seconds is not None:
            within = [i for i in remaining if durations[last][i] <= max_leg_seconds]
            if within:
                feasible = within
        nxt = min(feasible, key=lambda i: durations[last][i] if durations[last][i] > 0 else 10**9)
        order.append(nxt)
        remaining.remove(nxt)
    return order
