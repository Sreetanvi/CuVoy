"""Formula + GTFS costs. Never LLM prices. PROJECT_SPEC §9."""

from __future__ import annotations

from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.enums import CostLabel, ItineraryItemType, TransportMode
from cuvoy_contracts.itinerary import DailyCost, ItineraryItem
from cuvoy_contracts.place import Place

from app.providers.gtfs.fares import transit_fare

# Configured estimates in the trip currency. Labeled Estimated — never Verified.
RATES: dict[str, dict[str, float]] = {
    "INR": {
        "taxi_base": 50, "taxi_km": 18, "car_km": 8, "bike_km": 3,
        "meal_low": 200, "meal_mid": 500, "meal_high": 1500,
    },
    "USD": {
        "taxi_base": 3.5, "taxi_km": 2.0, "car_km": 0.22, "bike_km": 0.08,
        "meal_low": 12, "meal_mid": 25, "meal_high": 60,
    },
    "EUR": {
        "taxi_base": 3.5, "taxi_km": 1.8, "car_km": 0.20, "bike_km": 0.08,
        "meal_low": 12, "meal_mid": 28, "meal_high": 65,
    },
    "JPY": {
        "taxi_base": 500, "taxi_km": 300, "car_km": 20, "bike_km": 8,
        "meal_low": 800, "meal_mid": 1500, "meal_high": 4000,
    },
    "GBP": {
        "taxi_base": 3.2, "taxi_km": 2.2, "car_km": 0.20, "bike_km": 0.08,
        "meal_low": 10, "meal_mid": 22, "meal_high": 55,
    },
}

MEAL_CATS = frozenset({"restaurant", "cafe", "fast_food", "bar", "pub"})
FREE_CATS = frozenset({"park", "viewpoint", "place_of_worship", "temple", "garden", "artwork"})

ACTIVITY_ESTIMATE = {
    "museum": {"low": 5, "mid": 15, "high": 30},
    "gallery": {"low": 5, "mid": 18, "high": 35},
    "theme_park": {"low": 25, "mid": 50, "high": 90},
    "zoo": {"low": 10, "mid": 20, "high": 40},
    "default": {"low": 0, "mid": 10, "high": 25},
}

def _rates(currency: str) -> dict[str, float]:
    return RATES.get(currency.upper(), RATES["USD"])


def _tier(currency: str, daily_budget: float | None) -> str:
    if daily_budget is None:
        return "mid"
    mid = _rates(currency)["meal_mid"]
    if daily_budget < mid * 6:
        return "low"
    if daily_budget > mid * 20:
        return "high"
    return "mid"


def transport_cost(
    mode: TransportMode,
    *,
    distance_m: int,
    currency: str,
    city: str | None = None,
    show_transport: bool = False,
) -> CostAmount | None:
    if not show_transport:
        return None
    if mode == TransportMode.WALKING:
        return CostAmount(amount=0, currency=currency, label=CostLabel.VERIFIED_FARE)
    if mode in {TransportMode.METRO, TransportMode.BUS}:
        return transit_fare(city or "")
    km = max(0.0, distance_m / 1000.0)
    table = _rates(currency)
    if mode == TransportMode.TAXI:
        amount = round(table["taxi_base"] + table["taxi_km"] * km, 2)
        return CostAmount(amount=amount, currency=currency, label=CostLabel.ESTIMATED_COST)
    if mode in {TransportMode.CAR, TransportMode.CAMPER}:
        amount = round(table["car_km"] * km, 2)
        return CostAmount(amount=amount, currency=currency, label=CostLabel.ESTIMATED_COST)
    if mode in {TransportMode.BIKE, TransportMode.BICYCLE}:
        amount = round(table["bike_km"] * km, 2)
        return CostAmount(amount=amount, currency=currency, label=CostLabel.ESTIMATED_COST)
    # Mixed: no trustworthy single formula
    return CostAmount(amount=None, currency=currency, label=CostLabel.UNAVAILABLE)


def meal_cost(
    *,
    currency: str,
    price_level: str | None = None,
    daily_budget: float | None = None,
) -> CostAmount:
    table = _rates(currency)
    level = (price_level or _tier(currency, daily_budget)).lower()
    if level not in {"low", "mid", "high"}:
        level = "mid"
    amount = table[f"meal_{level}"]
    return CostAmount(amount=amount, currency=currency, label=CostLabel.ESTIMATED_COST)


def activity_cost(
    place: Place,
    *,
    currency: str,
    price_level: str | None = None,
    daily_budget: float | None = None,
) -> CostAmount:
    cat = place.category.lower()
    if cat in FREE_CATS or cat.startswith("historic"):
        return CostAmount(amount=0, currency=currency, label=CostLabel.ESTIMATED_COST)
    if cat in MEAL_CATS:
        return meal_cost(currency=currency, price_level=price_level, daily_budget=daily_budget)
    band = ACTIVITY_ESTIMATE.get(cat, ACTIVITY_ESTIMATE["default"])
    level = (price_level or "mid").lower()
    if level not in band:
        level = "mid"
    fx = _rates(currency)
    # Scale USD-ish table into local currency using meal_mid ratio vs USD meal_mid.
    scale = fx["meal_mid"] / RATES["USD"]["meal_mid"]
    amount = round(band[level] * scale, 2)
    return CostAmount(amount=amount, currency=currency, label=CostLabel.ESTIMATED_COST)


def _sum_amounts(items: list[CostAmount | None], currency: str) -> CostAmount | None:
    found = [c for c in items if c is not None]
    if not found:
        return None
    if any(c.label == CostLabel.UNAVAILABLE for c in found):
        numbered = [c.amount for c in found if c.amount is not None]
        if not numbered:
            return CostAmount(amount=None, currency=currency, label=CostLabel.UNAVAILABLE)
    total = sum(c.amount or 0 for c in found)
    labels = {c.label for c in found if c.amount is not None}
    if labels == {CostLabel.VERIFIED_FARE}:
        label = CostLabel.VERIFIED_FARE
    else:
        label = CostLabel.ESTIMATED_COST
    return CostAmount(amount=round(total, 2), currency=currency, label=label)


def daily_cost(
    items: list[ItineraryItem],
    *,
    currency: str,
    show_transport: bool = False,
) -> DailyCost:
    acts = [i.cost for i in items if i.type == ItineraryItemType.ACTIVITY]
    meals = [i.cost for i in items if i.type == ItineraryItemType.MEAL]
    trans = [i.cost for i in items if i.type == ItineraryItemType.TRANSIT]
    if not show_transport:
        trans = []
    activities = _sum_amounts(acts, currency)
    meal_total = _sum_amounts(meals, currency)
    transport = _sum_amounts(trans, currency) if show_transport else None
    ex = (activities.amount if activities and activities.amount is not None else 0) + (
        meal_total.amount if meal_total and meal_total.amount is not None else 0
    )
    inc = ex + (transport.amount if transport and transport.amount is not None else 0)
    return DailyCost(
        currency=currency,
        activities=activities,
        meals=meal_total,
        transport=transport,
        total_excluding_transport=round(ex, 2),
        total_including_transport=round(inc, 2) if show_transport else None,
        transport_shown=show_transport,
    )
