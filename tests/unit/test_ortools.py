from cuvoy_contracts.constants import OR_TOOLS_MAX_STOPS_PER_DAY

from app.optimize.greedy import nearest_neighbor_order
from app.optimize.ortools_solver import optimize_visit_order


def _line_matrix(n: int, step: int = 10) -> list[list[int]]:
    return [[abs(i - j) * step for j in range(n)] for i in range(n)]


def test_ortools_orders_a_cheap_path() -> None:
    durations = [
        [0, 10, 100],
        [10, 0, 10],
        [100, 10, 0],
    ]
    result = optimize_visit_order(durations, start=0, timeout_seconds=2)
    assert result.order[0] == 0
    assert set(result.order) == {0, 1, 2}
    assert result.order == [0, 1, 2] or result.objective_seconds == 20


def test_locked_stops_are_a_hard_prefix() -> None:
    durations = _line_matrix(5)
    result = optimize_visit_order(durations, locked=[3, 1], timeout_seconds=2)
    assert result.order[:2] == [3, 1]
    assert set(result.order) == set(range(5))


def test_greedy_fallback_visits_all() -> None:
    durations = _line_matrix(6)
    order = nearest_neighbor_order(durations, start=0)
    assert order[0] == 0
    assert set(order) == set(range(6))


def test_over_cap_still_returns_full_order() -> None:
    n = OR_TOOLS_MAX_STOPS_PER_DAY + 3
    result = optimize_visit_order(_line_matrix(n), timeout_seconds=2)
    assert len(result.order) == n
    assert result.used_greedy is True
