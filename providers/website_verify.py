"""Official-site hours check. SSRF-safe, 5s timeout. PROJECT_SPEC §7.16, §8."""

from __future__ import annotations

import ipaddress
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from cuvoy_contracts.constants import WEBSITE_VERIFY_TIMEOUT_SECONDS

from app.providers.gates import can_call
from app.providers.http import USER_AGENT
from app.services.budget import PlanBudget
from app.services.cache import CacheBackend

logger = logging.getLogger("cuvoy.providers")

_HOURS = re.compile(
    r"\b(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}|closed|opening hours)\b",
    re.I,
)
_MAX_BYTES = 80_000
_MAX_REDIRECTS = 3


def _is_private_host(host: str) -> bool:
    lowered = host.strip("[]").lower()
    if lowered in {"localhost", "localhost.localdomain"}:
        return True
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def is_public_http_url(url: str, *, allowed_host: str | None = None) -> bool:
    """Block file/data/ftp, IP literals that are private, and off-allowlist hosts."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if not host:
        return False
    if _is_private_host(host):
        return False
    if allowed_host:
        want = allowed_host.lower().lstrip(".")
        got = host.lower()
        if got != want and not got.endswith("." + want):
            return False
    return True


@dataclass
class VerifyResult:
    ok: bool
    hours_snippet: str | None
    warning: str | None


async def verify_website(
    http: httpx.AsyncClient,
    cache: CacheBackend,
    url: str,
    *,
    budget: PlanBudget | None = None,
) -> VerifyResult:
    unverified = VerifyResult(
        ok=False,
        hours_snippet=None,
        warning="Opening hours couldn't be verified",
    )
    parsed = urlparse(url)
    host = parsed.hostname
    if not host or not is_public_http_url(url, allowed_host=host):
        return unverified
    if not await can_call(cache, budget, envelope="verification", quota_name=None):
        return unverified

    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        if not is_public_http_url(current, allowed_host=host):
            return unverified
        try:
            response = await http.get(
                current,
                headers={"user-agent": USER_AGENT},
                timeout=WEBSITE_VERIFY_TIMEOUT_SECONDS,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            logger.warning("website_verify_failed", extra={"provider": "website"})
            return unverified
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                return unverified
            current = urljoin(current, location)
            continue
        if response.status_code >= 400:
            return unverified
        text = response.text[:_MAX_BYTES]
        match = _HOURS.search(text)
        snippet = match.group(0) if match else None
        logger.info("website_verify", extra={"provider": "website", "cache_hit": False})
        warning = None if snippet else unverified.warning
        return VerifyResult(ok=True, hours_snippet=snippet, warning=warning)
    return unverified
