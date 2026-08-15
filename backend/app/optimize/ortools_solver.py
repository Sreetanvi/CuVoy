"""OR-Tools visit order from a travel-time matrix. No routing. PROJECT_SPEC §7.10, §27."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cuvoy_contracts.constants import OR_TOOLS_MAX_STOPS_PER_DAY, OR_TOOLS_TIMEOUT_SECONDS

from app.optimize.greedy import nearest_neighbor_order

logger = logging.getLogger("cuvoy.optimize")

BIG = 10**7


@dataclass
class OptimizeResult:
    order: list[int]
    used_greedy: bool
    objective_seconds: int | None = None


def _apply_max_leg(durations: list[list[int]], max_leg_seconds: int | None) -> list[list[int]]:
    if max_leg_seconds is None:
        return durations
    n = len(durations)
    out = [row[:] for row in durations]
    for i in range(n):
        for j in range(n):
            if i != j and out[i][j] > max_leg_seconds:
                out[i][j] = BIG
    return out


def _objective(durations: list[list[int]], order: list[int]) -> int:
    total = 0
    for a, b in zip(order, order[1:], strict=False):
        total += durations[a][b]
    return total


def _solve_ortools(
    durations: list[list[int]],
    start: int,
    timeout_seconds: int,
) -> list[int] | None:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    n = len(durations)
    manager = pywrapcp.RoutingIndexManager(n, 1, start)
    routing = pywrapcp.RoutingModel(manager)

    def transit_callback(from_index: int, to_index: int) -> int:
        a = manager.IndexToNode(from_index)
        b = manager.IndexToNode(to_index)
        return int(durations[a][b])

    cb = routing.RegisterTransitCallback(transit_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromSeconds(max(1, timeout_seconds))
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None
    order: list[int] = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        order.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    return order


def optimize_visit_order(
    durations: list[list[int]],
    *,
    locked: list[int] | None = None,
    max_leg_seconds: int | None = None,
    timeout_seconds: int = OR_TOOLS_TIMEOUT_SECONDS,
    start: int = 0,
) -> OptimizeResult:
    """
    TSP-style order for ≤20 stops. Locked indices stay a prefix (hard constraints).
    Timeout or solver failure → greedy nearest-neighbor.
    """
    n = len(durations)
    if n == 0:
        return OptimizeResult(order=[], used_greedy=False, objective_seconds=0)
    if n == 1:
        return OptimizeResult(order=[0], used_greedy=False, objective_seconds=0)

    locked = [i for i in (locked or []) if 0 <= i < n]
    costs = _apply_max_leg(durations, max_leg_seconds)

    if n > OR_TOOLS_MAX_STOPS_PER_DAY:
        logger.warning("ortools_input_capped", extra={"stage": "optimize"})
        subset = locked + [i for i in range(n) if i not in set(locked)]
        subset = subset[:OR_TOOLS_MAX_STOPS_PER_DAY]
        sub = [[costs[i][j] for j in subset] for i in subset]
        inner = optimize_visit_order(
            sub,
            locked=list(range(len(locked))),
            timeout_seconds=timeout_seconds,
            start=0,
        )
        mapped = [subset[i] for i in inner.order]
        rest = [i for i in range(n) if i not in set(mapped)]
        if rest:
            extra = nearest_neighbor_order(
                durations, start=mapped[-1], locked=mapped, max_leg_seconds=max_leg_seconds
            )
            mapped = extra
        return OptimizeResult(
            order=mapped, used_greedy=True, objective_seconds=_objective(durations, mapped)
        )

    prefix = list(locked)
    remaining = [i for i in range(n) if i not in set(prefix)]
    if not remaining:
        return OptimizeResult(
            order=prefix, used_greedy=False, objective_seconds=_objective(durations, prefix)
        )

    # Solve open TSP on remaining nodes, starting from last locked (or `start`).
    if prefix:
        origin = prefix[-1]
        nodes = [origin, *remaining]
        sub = [[costs[i][j] for j in nodes] for i in nodes]
        try:
            sub_order = _solve_ortools(sub, start=0, timeout_seconds=timeout_seconds)
        except Exception:
            sub_order = None
        if not sub_order:
            tail = nearest_neighbor_order(
                durations, start=origin, locked=prefix, max_leg_seconds=max_leg_seconds
            )
            return OptimizeResult(
                order=tail, used_greedy=True, objective_seconds=_objective(durations, tail)
            )
        mapped = [nodes[i] for i in sub_order]
        if mapped[0] == origin:
            mapped = mapped[1:]
        order = prefix + [i for i in mapped if i not in set(prefix)]
        for i in remaining:
            if i not in order:
                order.append(i)
        return OptimizeResult(
            order=order, used_greedy=False, objective_seconds=_objective(durations, order)
        )

    origin = start if 0 <= start < n else 0
    try:
        order = _solve_ortools(costs, start=origin, timeout_seconds=timeout_seconds)
    except Exception:
        logger.warning("ortools_failed_greedy", extra={"stage": "optimize"})
        order = None
    if not order:
        greedy = nearest_neighbor_order(
            durations, start=origin, max_leg_seconds=max_leg_seconds
        )
        return OptimizeResult(
            order=greedy, used_greedy=True, objective_seconds=_objective(durations, greedy)
        )
    return OptimizeResult(
        order=order, used_greedy=False, objective_seconds=_objective(durations, order)
    )
