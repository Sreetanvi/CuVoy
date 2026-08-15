"""Task names and model roles. The router is ordinary code, never an LLM."""

from __future__ import annotations

from enum import StrEnum


class AITask(StrEnum):
    PREFERENCE_EXTRACTION = "preference_extraction"
    RANK_CANDIDATES = "rank_candidates"
    NARRATIVE = "narrative"
    EXPLAINABILITY = "explainability"
    PACKING = "packing"
    REGENERATION = "regeneration"
    CROWD_REASONING = "crowd_reasoning"


class ModelRole(StrEnum):
    FAST = "CUVOY_FAST"
    BALANCED = "CUVOY_BALANCED"
    REASONING = "CUVOY_REASONING"


class Complexity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


TASK_PROFILE: dict[AITask, dict[str, object]] = {
    AITask.PREFERENCE_EXTRACTION: {
        "complexity": Complexity.LOW,
        "role": ModelRole.FAST,
        "max_output_tokens": 800,
        "prompt_version": "preference_v1.0",
    },
    AITask.RANK_CANDIDATES: {
        "complexity": Complexity.MEDIUM,
        "role": ModelRole.BALANCED,
        "max_output_tokens": 1500,
        "prompt_version": "ranking_v1.0",
    },
    AITask.NARRATIVE: {
        "complexity": Complexity.MEDIUM,
        "role": ModelRole.BALANCED,
        "max_output_tokens": 2000,
        "prompt_version": "narrative_v1.0",
    },
    AITask.EXPLAINABILITY: {
        "complexity": Complexity.LOW,
        "role": ModelRole.FAST,
        "max_output_tokens": 1200,
        "prompt_version": "explainability_v1.0",
    },
    AITask.PACKING: {
        "complexity": Complexity.LOW,
        "role": ModelRole.FAST,
        "max_output_tokens": 1200,
        "prompt_version": "packing_v1.0",
    },
    AITask.REGENERATION: {
        "complexity": Complexity.MEDIUM,
        "role": ModelRole.BALANCED,
        "max_output_tokens": 1500,
        "prompt_version": "regeneration_v1.0",
    },
    AITask.CROWD_REASONING: {
        "complexity": Complexity.LOW,
        "role": ModelRole.FAST,
        "max_output_tokens": 1000,
        "prompt_version": "crowd_v1.0",
    },
}


def profile_for(task: AITask) -> dict[str, object]:
    return TASK_PROFILE[task]
