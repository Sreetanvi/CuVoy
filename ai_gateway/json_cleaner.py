"""Deterministic LLM JSON cleaning (PROJECT_SPEC §29.1). Never invents fields."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


class JSONCleanError(ValueError):
    """Raw model output could not be reduced to JSON without semantic repair."""


def strip_fences(raw: str) -> str:
    text = raw.strip()
    match = _FENCE.search(text)
    if match:
        return match.group(1).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, count=1, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[: -3].strip()
    return text


def strip_trailing_commas(text: str) -> str:
    previous = None
    current = text
    while previous != current:
        previous = current
        current = _TRAILING_COMMA.sub(r"\1", current)
    return current


def _extract_balanced(text: str, start: int) -> str | None:
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json_text(raw: str) -> str:
    text = strip_trailing_commas(strip_fences(raw))
    if not text:
        raise JSONCleanError("empty model output")
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    for index, char in enumerate(text):
        if char in "{[":
            candidate = _extract_balanced(text, index)
            if candidate is None:
                continue
            normalized = strip_trailing_commas(candidate)
            try:
                json.loads(normalized)
                return normalized
            except json.JSONDecodeError:
                continue
    raise JSONCleanError("no valid JSON object or array found")


def loads_llm_json(raw: str) -> Any:
    """Parse model text to JSON. Does not add or fill missing fields."""
    return json.loads(extract_json_text(raw))
