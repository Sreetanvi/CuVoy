"""SSE event formatting. PROJECT_SPEC §7.13."""

from __future__ import annotations

import json

from cuvoy_contracts.api import SseEvent
from cuvoy_contracts.enums import PipelineStage, SseEventType
from cuvoy_contracts.itinerary import Itinerary

from app.services.jobs import STAGES

STAGE_PROGRESS = {
    PipelineStage.EXTRACT: (5, 15),
    PipelineStage.DISCOVER: (20, 30),
    PipelineStage.REDUCE: (35, 45),
    PipelineStage.CLUSTER_MATRIX: (50, 60),
    PipelineStage.OPTIMIZE_SCHEDULE: (65, 80),
    PipelineStage.NARRATIVE_VALIDATE: (85, 95),
}


def progress_for(stage: PipelineStage, *, complete: bool) -> int:
    start, end = STAGE_PROGRESS.get(stage, (0, 100))
    return end if complete else start


def encode_sse(event: SseEvent) -> str:
    payload = event.model_dump(mode="json", exclude_none=True)
    return f"event: {event.event.value}\ndata: {json.dumps(payload)}\n\n"


def stage_start(plan_id: str, stage: PipelineStage) -> SseEvent:
    return SseEvent(
        event=SseEventType.STAGE_START,
        stage=stage,
        progress=progress_for(stage, complete=False),
        plan_id=plan_id,
    )


def stage_complete(plan_id: str, stage: PipelineStage) -> SseEvent:
    return SseEvent(
        event=SseEventType.STAGE_COMPLETE,
        stage=stage,
        progress=progress_for(stage, complete=True),
        plan_id=plan_id,
    )


def plan_complete(plan_id: str, itinerary: Itinerary | None) -> SseEvent:
    return SseEvent(
        event=SseEventType.PLAN_COMPLETE,
        progress=100,
        plan_id=plan_id,
        itinerary=itinerary,
    )


def plan_error(
    plan_id: str, message: str, *, recoverable: bool, credit_refunded: bool
) -> SseEvent:
    return SseEvent(
        event=SseEventType.PLAN_ERROR,
        plan_id=plan_id,
        error=message,
        recoverable=recoverable,
        credit_refunded=credit_refunded,
    )


def stage_index(stage: PipelineStage) -> int:
    return STAGES.index(stage)
