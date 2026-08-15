"""Provider RPM limiter. RPD is enforced by app.services.quota (PROJECT_SPEC §30)."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

# Conservative free-tier RPM. RPD lives in quota.PROVIDER_RPD.
PROVIDER_RPM: dict[str, int] = {
    "gemini": 15,
    "groq": 30,
    "openrouter": 20,
}


class RateLimiter:
    def __init__(self, rpm: dict[str, int] | None = None) -> None:
        self.rpm = rpm or dict(PROVIDER_RPM)
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune(self, provider: str, now: float) -> deque[float]:
        window_start = now - 60.0
        bucket = self._hits.setdefault(provider, deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        return bucket

    def would_allow(self, provider: str) -> bool:
        cap = self.rpm.get(provider)
        if cap is None:
            return True
        now = time.monotonic()
        with self._lock:
            return len(self._prune(provider, now)) < cap

    def allow(self, provider: str) -> bool:
        cap = self.rpm.get(provider)
        if cap is None:
            return True
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(provider, now)
            if len(bucket) >= cap:
                return False
            bucket.append(now)
            return True

    def remaining(self, provider: str) -> int | None:
        cap = self.rpm.get(provider)
        if cap is None:
            return None
        now = time.monotonic()
        window_start = now - 60.0
        with self._lock:
            bucket = self._hits.get(provider, deque())
            live = sum(1 for stamp in bucket if stamp >= window_start)
            return max(0, cap - live)
