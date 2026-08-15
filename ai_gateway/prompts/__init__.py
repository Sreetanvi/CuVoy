"""Task prompt registry — stable system prompt per task (architecture Part 5)."""

from __future__ import annotations

from app.ai_gateway.prompts import (
    crowd_reasoning,
    explainability,
    extract_preferences,
    narrative,
    packing,
    rank_candidates,
    regeneration,
)
from app.ai_gateway.prompts.system import GLOBAL_SYSTEM_PROMPT, JSON_OUTPUT_RULES
from app.ai_gateway.tasks import AITask


def system_for(task: AITask) -> str:
    bodies = {
        AITask.PREFERENCE_EXTRACTION: extract_preferences.SYSTEM,
        AITask.RANK_CANDIDATES: rank_candidates.SYSTEM,
        AITask.NARRATIVE: narrative.SYSTEM,
        AITask.EXPLAINABILITY: explainability.SYSTEM,
        AITask.PACKING: packing.SYSTEM,
        AITask.REGENERATION: regeneration.SYSTEM,
        AITask.CROWD_REASONING: crowd_reasoning.SYSTEM,
    }
    return f"{GLOBAL_SYSTEM_PROMPT}\n\n{bodies[task]}\n\n{JSON_OUTPUT_RULES}"
