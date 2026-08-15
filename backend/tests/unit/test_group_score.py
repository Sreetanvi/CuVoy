from cuvoy_contracts.enums import GroupPriority
from cuvoy_contracts.preferences import GroupPlanning, Traveler

from app.optimize.group_score import group_interest_score, group_score
from tests.unit.places import place


def _group() -> GroupPlanning:
    return GroupPlanning(
        enabled=True,
        priority=GroupPriority.EVERYONE,
        travelers=[
            Traveler(name="A", interests=["history"]),
            Traveler(name="B", interests=["food"]),
            Traveler(name="C", interests=["nature"]),
        ],
    )


def test_everyone_mode_balances_interests() -> None:
    group = _group()
    museum = group_interest_score(place("m", "City Museum", 12.97, 77.59, category="museum"), group)
    park = group_interest_score(place("p", "Cubbon Park", 12.97, 77.59, category="park"), group)
    restaurant = group_interest_score(
        place("r", "Local Kitchen", 12.97, 77.59, category="restaurant"), group
    )
    assert museum > 0
    assert park > 0
    assert restaurant > 0
    combined = museum + park + restaurant
    assert combined > museum * 1.5


def test_team_lead_weights_fifty_percent() -> None:
    travelers = [
        Traveler(name="Lead", interests=["history"], is_team_lead=True),
        Traveler(name="B", interests=["food"]),
        Traveler(name="C", interests=["food"]),
    ]
    lead_mode = GroupPlanning(
        enabled=True, priority=GroupPriority.TEAM_LEAD, travelers=travelers
    )
    equal = GroupPlanning(enabled=True, priority=GroupPriority.EVERYONE, travelers=travelers)
    museum = place("m", "Fort Museum", 12.97, 77.59, category="museum")
    assert group_interest_score(museum, lead_mode) > group_interest_score(museum, equal)
    assert 0 <= group_score(museum, lead_mode) <= 1
