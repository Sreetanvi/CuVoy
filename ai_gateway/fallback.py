"""Deterministic fallbacks when all free LLMs are unavailable (paid_fallback = NEVER)."""

from __future__ import annotations

import re
from typing import Any

from cuvoy_contracts.enrichment import ExclusionReason, Explainability, PackingItem, PackingList
from cuvoy_contracts.enums import CrowdConfidenceLevel, CrowdLevel, Pace
from cuvoy_contracts.preferences import (
    AccessibilityPreferences,
    ExtractedPreferences,
    FoodPreferences,
    GroupPlanning,
    PlanRequest,
)

from app.ai_gateway.schemas import (
    CrowdEstimate,
    CrowdReasoningOutput,
    DayNarrative,
    NarrativeOutput,
    RankedCandidate,
    RankedCandidates,
    RegenerationIntent,
)
from app.ai_gateway.tasks import AITask
from app.providers.place_name import resolve_candidate_name

_INTEREST_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("temple", "temples"),
    ("history", "history"),
    ("museum", "museums"),
    ("food", "food"),
    ("restaurant", "food"),
    ("nature", "nature"),
    ("hike", "nature"),
    ("beach", "beach"),
    ("nightlife", "nightlife"),
    ("shop", "shopping"),
    ("photo", "photography"),
    ("art", "art"),
    ("park", "parks"),
)

_PACE_RELAXED = re.compile(r"relax|leisure|chill|\bslow\b", re.I)
_PACE_PACKED = re.compile(r"\bpacked\b|jam.?pack|see everything", re.I)


def fallback_preferences(
    user_prompt: str, request: PlanRequest | None = None
) -> ExtractedPreferences:
    text = user_prompt.lower()
    interests: list[str] = []
    seen: set[str] = set()
    for needle, label in _INTEREST_KEYWORDS:
        if needle in text and label not in seen:
            interests.append(label)
            seen.add(label)

    pace = Pace.MODERATE
    if _PACE_RELAXED.search(user_prompt):
        pace = Pace.RELAXED
    elif _PACE_PACKED.search(user_prompt):
        pace = Pace.PACKED

    controls = request.trip_controls if request else None
    if controls is not None:
        pace = controls.pace
        hidden = controls.hidden_gems
        accessibility = controls.accessibility
        food = FoodPreferences()
        transport = controls.transportation
        budget = controls.daily_budget or (request.budget if request else None)
        group = controls.group
    else:
        hidden = "hidden gem" in text or "local gem" in text
        accessibility = AccessibilityPreferences(
            kids=bool(re.search(r"\b(kids?|children|family)\b", text, re.I)),
            elderly=bool(re.search(r"\b(elderly|parents|senior)\b", text, re.I)),
            wheelchair="wheelchair" in text,
        )
        food = FoodPreferences()
        transport = request.transportation if request else None
        budget = request.budget if request else None
        group = GroupPlanning()

    dates = request.travel_dates if request else None
    return ExtractedPreferences(
        budget=budget,
        dates=dates,
        interests=interests,
        pace=pace,
        food=food,
        hidden_gems=hidden,
        accessibility=accessibility,
        group=group,
        transportation=transport,
        timezone=None,
    )


def fallback_rank(candidates: list[dict[str, Any]]) -> RankedCandidates:
    ranked: list[RankedCandidate] = []
    total = max(len(candidates), 1)
    for index, item in enumerate(candidates):
        place_id = str(item.get("place_id") or item.get("id") or "")
        if not place_id:
            continue
        ranked.append(
            RankedCandidate(
                place_id=place_id,
                score=round((total - index) / total, 4),
                reason="Deterministic order; LLM ranking unavailable",
            )
        )
    return RankedCandidates(ranked=ranked)


def fallback_narrative(itinerary: dict[str, Any] | None = None) -> NarrativeOutput:
    days_in = []
    if isinstance(itinerary, dict):
        days_in = itinerary.get("days") or []
    days = [
        DayNarrative(
            day_index=index,
            text="Schedule follows verified stops and travel times. Narrative model unavailable.",
        )
        for index, _ in enumerate(days_in)
    ]
    if not days:
        days = [
            DayNarrative(
                day_index=0,
                text="Itinerary assembled by the deterministic planner. "
                "Narrative model unavailable.",
            )
        ]
    return NarrativeOutput(
        summary="This plan was built with the deterministic engine. "
        "AI narrative is temporarily unavailable.",
        days=days,
    )


def fallback_explainability(evidence: dict[str, Any] | None = None) -> Explainability:
    exclusions: list[ExclusionReason] = []
    if isinstance(evidence, dict):
        for item in evidence.get("exclusions") or []:
            if not isinstance(item, dict):
                continue
            tags = item.get("tags") if isinstance(item.get("tags"), dict) else None
            name = resolve_candidate_name(
                name=str(item.get("name") or "").strip() or None,
                tags=tags,
                category=str(item.get("category") or "") or None,
                place_id=str(item.get("place_id") or "") or None,
            )
            if not name or name.lower().startswith("unnamed location"):
                continue
            reason = str(item.get("reason") or "Excluded by planning constraints.")
            exclusions.append(
                ExclusionReason(place_id=item.get("place_id"), name=name, reason=reason)
            )
    if not exclusions:
        exclusions.append(
            ExclusionReason(
                name="General",
                reason=(
                    "Explanations are based on hours, geography, and budget filters. "
                    "LLM explainability is unavailable."
                ),
            )
        )
    return Explainability(exclusions=exclusions)


def fallback_packing(context: dict[str, Any] | None = None) -> PackingList:
    items = [
        PackingItem(
            name="Comfortable walking shoes",
            reason="Most days include walking between stops",
            category="footwear",
        ),
        PackingItem(
            name="Reusable water bottle",
            reason="Stay hydrated during transit and outdoor time",
            category="essentials",
        ),
        PackingItem(
            name="Weather layer",
            reason="Check destination forecast before packing a heavy coat",
            category="clothing",
        ),
        PackingItem(
            name="Phone charger / power bank",
            reason="Navigation and tickets rely on a charged phone",
            category="electronics",
        ),
        PackingItem(
            name="ID and payment cards",
            reason="Required for travel and entry where applicable",
            category="documents",
        ),
    ]
    if isinstance(context, dict) and context.get("rain"):
        items.append(
            PackingItem(
                name="Light rain jacket",
                reason="Rain indicated in supplied weather context",
                category="clothing",
            )
        )
    return PackingList(items=items, summary="Template packing list; LLM packing is unavailable.")


def fallback_regeneration(user_request: str) -> RegenerationIntent:
    text = user_request.lower()
    if "skip" in text or "remove" in text:
        action = "skip"
    elif "swap" in text or "replace" in text:
        action = "swap"
    elif "lunch" in text or "dinner" in text or "meal" in text:
        action = "meal"
    elif "lock" in text or "keep" in text:
        action = "lock"
    else:
        action = "replan"
    return RegenerationIntent(
        action=action,
        scope="remaining",
        notes="Deterministic interpretation; LLM regeneration parser unavailable.",
    )


def fallback_crowd(places: list[dict[str, Any]]) -> CrowdReasoningOutput:
    estimates = []
    for item in places:
        place_id = str(item.get("place_id") or item.get("id") or "")
        if not place_id:
            continue
        estimates.append(
            CrowdEstimate(
                place_id=place_id,
                level=CrowdLevel.MODERATE,
                confidence=CrowdConfidenceLevel.LOW,
                reasons=[
                    "Insufficient crowd signals; defaulting to moderate, not a live reading."
                ],
                is_live=False,
            )
        )
    return CrowdReasoningOutput(estimates=estimates)


def run_fallback(task: AITask, payload: dict[str, Any]) -> object:
    if task == AITask.PREFERENCE_EXTRACTION:
        return fallback_preferences(str(payload.get("user_prompt") or ""), payload.get("request"))
    if task == AITask.RANK_CANDIDATES:
        return fallback_rank(list(payload.get("candidates") or []))
    if task == AITask.NARRATIVE:
        itinerary = payload.get("itinerary")
        return fallback_narrative(itinerary if isinstance(itinerary, dict) else None)
    if task == AITask.EXPLAINABILITY:
        evidence = payload.get("evidence")
        return fallback_explainability(evidence if isinstance(evidence, dict) else None)
    if task == AITask.PACKING:
        ctx = payload.get("context")
        return fallback_packing(ctx if isinstance(ctx, dict) else None)
    if task == AITask.REGENERATION:
        return fallback_regeneration(str(payload.get("user_request") or ""))
    return fallback_crowd(list(payload.get("places") or []))
