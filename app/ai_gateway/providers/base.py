"""Shared provider result + HTTP helpers."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class ProviderResult:
    ok: bool
    text: str = ""
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    status_code: int | None = None
    retry_after: float | None = None
    error: str = ""


def retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None
