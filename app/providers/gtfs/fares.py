"""GTFS fares from compact artifacts. Missing fares → Cost unavailable. §9, §28."""

from __future__ import annotations

from cuvoy_contracts.common import CostAmount
from cuvoy_contracts.enums import CostLabel

from app.providers.gtfs.fetch import compact_for_city


def transit_fare(
    city: str, *, from_stop: str | None = None, to_stop: str | None = None
) -> CostAmount:
    _feed, artifact = compact_for_city(city)
    currency = str(artifact.get("currency") or "USD")
    if not artifact.get("fare_available"):
        return CostAmount(amount=None, currency=currency, label=CostLabel.UNAVAILABLE)
    fares = artifact.get("fares") or []
    if from_stop and to_stop:
        for row in fares:
            if not isinstance(row, dict):
                continue
            if row.get("from") == from_stop and row.get("to") == to_stop:
                try:
                    return CostAmount(
                        amount=float(row["amount"]),
                        currency=str(row.get("currency") or currency),
                        label=CostLabel.VERIFIED_FARE,
                    )
                except (KeyError, TypeError, ValueError):
                    break
    return CostAmount(amount=None, currency=currency, label=CostLabel.UNAVAILABLE)
