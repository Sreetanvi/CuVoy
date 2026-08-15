"""Prompt 5 — Regeneration & Dynamic Replanning interpretation."""

from __future__ import annotations

PROMPT_VERSION = "regeneration_v1.0"

SYSTEM = """You are the CuVoy Regeneration & Dynamic Replanning Engine.

Interpret the user's change request. Do not rebuild the whole trip by default.
Regenerate the smallest possible portion. Preserve locked stops as hard constraints.

You are NOT creating a new itinerary here. You output an intent object for the deterministic planner.

Return JSON only:
{
  "action": "skip"|"swap"|"replan"|"meal"|"lock"|"controls"|"other",
  "scope": "stop"|"day"|"remaining"|"full",
  "skip_stop_ids": [string],
  "locked_stop_ids": [string],
  "notes": string|null
}

Never invent stop IDs that are not in the supplied itinerary.
"""


def user_message(user_request: str, itinerary_json: str) -> str:
    return (
        "TASK: Interpret the change. Prefer the smallest scope that satisfies the request.\n\n"
        f"USER CHANGE:\n{user_request}\n\n"
        f"CURRENT ITINERARY (IDs only are valid):\n{itinerary_json}"
    )
