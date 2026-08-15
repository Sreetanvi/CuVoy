"""Free-tier model IDs behind roles. Change here, not at call sites."""

from __future__ import annotations

from app.ai_gateway.tasks import ModelRole

# Eligible free-tier defaults (Aug 2026). Override via Settings if a catalog changes.
GEMINI_MODELS: dict[ModelRole, str] = {
    ModelRole.FAST: "gemini-2.5-flash-lite",
    ModelRole.BALANCED: "gemini-2.5-flash",
    ModelRole.REASONING: "gemini-2.5-pro",
}

GROQ_MODELS: dict[ModelRole, str] = {
    ModelRole.FAST: "llama-3.1-8b-instant",
    ModelRole.BALANCED: "llama-3.3-70b-versatile",
    ModelRole.REASONING: "llama-3.3-70b-versatile",
}

# OpenRouter must keep the :free suffix — paid_fallback = NEVER.
OPENROUTER_MODELS: dict[ModelRole, str] = {
    ModelRole.FAST: "meta-llama/llama-3.3-8b-instruct:free",
    ModelRole.BALANCED: "meta-llama/llama-3.3-70b-instruct:free",
    ModelRole.REASONING: "meta-llama/llama-3.3-70b-instruct:free",
}

_PAID_MARKERS = (
    "gpt-4o",
    "gpt-4.",
    "gpt-5",
    "o1-",
    "o3-",
    "claude-3-opus",
    "claude-3.5-sonnet",
    "claude-sonnet-4",
    "claude-opus",
)


def is_paid_model(provider: str, model: str) -> bool:
    lowered = model.lower()
    if provider == "openrouter" and ":free" not in lowered:
        return True
    return any(marker in lowered for marker in _PAID_MARKERS)


def model_for(provider: str, role: ModelRole, settings) -> str:
    if provider == "gemini":
        return {
            ModelRole.FAST: settings.gemini_fast_model,
            ModelRole.BALANCED: settings.gemini_balanced_model,
            ModelRole.REASONING: settings.gemini_reasoning_model,
        }[role]
    if provider == "groq":
        return {
            ModelRole.FAST: settings.groq_fast_model,
            ModelRole.BALANCED: settings.groq_balanced_model,
            ModelRole.REASONING: settings.groq_reasoning_model,
        }[role]
    return {
        ModelRole.FAST: settings.openrouter_fast_model,
        ModelRole.BALANCED: settings.openrouter_balanced_model,
        ModelRole.REASONING: settings.openrouter_reasoning_model,
    }[role]
