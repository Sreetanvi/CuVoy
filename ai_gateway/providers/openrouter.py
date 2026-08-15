"""OpenRouter free models only (:free suffix enforced in models.is_paid_model)."""

from __future__ import annotations

import httpx

from app.ai_gateway.providers.base import ProviderResult, retry_after_seconds

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


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
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_output_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        response = await http.post(
            OPENROUTER_URL,
            headers={
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
                "http-referer": "https://cuvoy.vercel.app",
                "x-title": "CuVoy",
            },
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
    try:
        text = body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ProviderResult(
            ok=False,
            model=model,
            status_code=response.status_code,
            error="empty_output",
        )

    usage = body.get("usage") or {}
    return ProviderResult(
        ok=True,
        text=text,
        model=model,
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        status_code=response.status_code,
    )
