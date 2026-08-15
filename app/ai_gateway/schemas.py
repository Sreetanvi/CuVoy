"""Internal structured-output contracts for gateway tasks (pipeline consumes these)."""

from __future__ import annotations

from cuvoy_contracts.common import ContractModel
from cuvoy_contracts.enrichment import Explainability, PackingList
from cuvoy_contracts.enums import CrowdConfidenceLevel, CrowdLevel
from cuvoy_contracts.preferences import ExtractedPreferences
from pydantic import Field


class RankedCandidate(ContractModel):
    place_id: str
    score: float = Field(..., ge=0, le=1)
    reason: str | None = None


class RankedCandidates(ContractModel):
    ranked: list[RankedCandidate] = Field(default_factory=list)


class DayNarrative(ContractModel):
    day_index: int = Field(..., ge=0)
    text: str


class NarrativeOutput(ContractModel):
    summary: str
    days: list[DayNarrative] = Field(default_factory=list)


class RegenerationIntent(ContractModel):
    action: str
    scope: str = "remaining"
    skip_stop_ids: list[str] = Field(default_factory=list)
    locked_stop_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class CrowdEstimate(ContractModel):
    place_id: str
    level: CrowdLevel
    confidence: CrowdConfidenceLevel
    reasons: list[str] = Field(default_factory=list)
    is_live: bool = False


class CrowdReasoningOutput(ContractModel):
    estimates: list[CrowdEstimate] = Field(default_factory=list)


TASK_SCHEMA: dict[str, type[ContractModel]] = {
    "preference_extraction": ExtractedPreferences,
    "rank_candidates": RankedCandidates,
    "narrative": NarrativeOutput,
    "explainability": Explainability,
    "packing": PackingList,
    "regeneration": RegenerationIntent,
    "crowd_reasoning": CrowdReasoningOutput,
}
