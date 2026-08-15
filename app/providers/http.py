"""Shared HTTP JSON fetch. Timeouts are per-call; never log secrets."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("cuvoy.providers")

USER_AGENT = "CuVoy/0.1 (https://cuvoy.vercel.app)"


async def get_json(
    http: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    provider: str,
) -> Any | None:
    merged = {"user-agent": USER_AGENT, **(headers or {})}
    try:
        response = await http.get(url, params=params, headers=merged, timeout=timeout)
    except httpx.TimeoutException:
        logger.warning("provider_timeout", extra={"provider": provider})
        return None
    except httpx.HTTPError as exc:
        logger.warning("provider_http_error", extra={"provider": provider, "error": str(exc)})
        return None
    if response.status_code >= 400:
        logger.warning(
            "provider_status",
            extra={"provider": provider, "status_code": response.status_code},
        )
        return None
    try:
        return response.json()
    except ValueError:
        logger.warning("provider_invalid_json", extra={"provider": provider})
        return None


async def post_text(
    http: httpx.AsyncClient,
    url: str,
    *,
    content: str,
    timeout: float,
    provider: str,
) -> Any | None:
    try:
        response = await http.post(
            url,
            content=content.encode("utf-8"),
            headers={"content-type": "text/plain; charset=utf-8", "user-agent": USER_AGENT},
            timeout=timeout,
        )
    except httpx.TimeoutException:
        logger.warning("provider_timeout", extra={"provider": provider})
        return None
    except httpx.HTTPError as exc:
        logger.warning("provider_http_error", extra={"provider": provider, "error": str(exc)})
        return None
    if response.status_code >= 400:
        logger.warning(
            "provider_status",
            extra={"provider": provider, "status_code": response.status_code},
        )
        return None
    try:
        return response.json()
    except ValueError:
        return None
