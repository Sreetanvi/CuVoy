"""Visit-order optimization. Mapbox routes; OR-Tools orders. PROJECT_SPEC §27."""

from app.optimize.greedy import nearest_neighbor_order
from app.optimize.group_score import group_interest_score, group_score
from app.optimize.ortools_solver import OptimizeResult, optimize_visit_order

__all__ = [
    "OptimizeResult",
    "group_interest_score",
    "group_score",
    "nearest_neighbor_order",
    "optimize_visit_order",
]
