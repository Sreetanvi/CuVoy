"""Google Gemini generateContent adapter (free-tier key only)."""

from __future__ import annotations

import httpx

from app.ai_gateway.providers.base import ProviderResult, retry_after_seconds

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


async def generate(
    http: httpx.AsyncClient,
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_output_tokens: int,
    timeout: float,
) -> ProviderResult:
    url = GEMINI_URL.format(model=model)
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    try:
        response = await http.post(
            url,
            headers={"x-goog-api-key": api_key, "content-type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    except httpx.TimeoutException:
        return ProviderResult(ok=False, model=model, error="timeout")
    except httpx.HTTPError as exc:
        return ProviderResult(ok=False, model=model, error=str(exc))

    if response.status_code >= 400:
        return ProviderResult(
            ok=False,
            model=model,
            status_code=response.status_code,
            retry_after=retry_after_seconds(response),
            error=f"http_{response.status_code}",
        )

    body = response.json()
    text = ""
    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(str(part.get("text") or "") for part in parts)
    except (KeyError, IndexError, TypeError):
        return ProviderResult(
            ok=False,
            model=model,
            status_code=response.status_code,
            error="empty_output",
        )

    usage = body.get("usageMetadata") or {}
    return ProviderResult(
        ok=True,
        text=text,
        model=model,
        input_tokens=usage.get("promptTokenCount"),
        output_tokens=usage.get("candidatesTokenCount"),
        status_code=response.status_code,
    )
