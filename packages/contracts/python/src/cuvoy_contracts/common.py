"""Shared primitives: destination-local times and three-tier costs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cuvoy_contracts.enums import CostLabel


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalDateTime(ContractModel):
    """Itinerary instant in destination-local time (PROJECT_SPEC §5.3, §7.11)."""

    timezone: str = Field(..., min_length=1, description="IANA ID, e.g. Asia/Tokyo")
    local_time: str = Field(..., min_length=1, description="Naive local ISO-8601 or HH:MM")
    utc: datetime | None = None


class CostAmount(ContractModel):
    """Show a number only when trustworthy (PROJECT_SPEC §9)."""

    amount: float | None = None
    currency: str = Field(..., min_length=1)
    label: CostLabel

    @model_validator(mode="after")
    def unavailable_has_no_amount(self) -> "CostAmount":
        if self.label == CostLabel.UNAVAILABLE and self.amount is not None:
            raise ValueError("Cost unavailable must not include an amount")
        if self.label != CostLabel.UNAVAILABLE and self.amount is None:
            raise ValueError("Verified or estimated cost requires an amount")
        return self
