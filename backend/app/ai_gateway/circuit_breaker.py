"""Per-provider circuit breaker (CLOSED → OPEN → HALF_OPEN)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitSnapshot:
    state: CircuitState
    failures: int
    opened_at: float | None


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, cooldown_seconds: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._half_open_probe: dict[str, bool] = {}
        self._lock = Lock()

    def snapshot(self, provider: str) -> CircuitSnapshot:
        with self._lock:
            return CircuitSnapshot(
                state=self._state_unlocked(provider, time.monotonic()),
                failures=self._failures.get(provider, 0),
                opened_at=self._opened_at.get(provider),
            )

    def peek(self, provider: str) -> CircuitState:
        with self._lock:
            return self._state_unlocked(provider, time.monotonic())

    def allow(self, provider: str) -> bool:
        now = time.monotonic()
        with self._lock:
            state = self._state_unlocked(provider, now)
            if state == CircuitState.OPEN:
                return False
            if state == CircuitState.HALF_OPEN:
                if self._half_open_probe.get(provider):
                    return False
                self._half_open_probe[provider] = True
            return True

    def record_success(self, provider: str) -> None:
        with self._lock:
            self._failures[provider] = 0
            self._opened_at.pop(provider, None)
            self._half_open_probe.pop(provider, None)

    def record_failure(self, provider: str) -> CircuitState:
        now = time.monotonic()
        with self._lock:
            failures = self._failures.get(provider, 0) + 1
            self._failures[provider] = failures
            self._half_open_probe.pop(provider, None)
            if failures >= self.failure_threshold:
                self._opened_at[provider] = now
                return CircuitState.OPEN
            return self._state_unlocked(provider, now)

    def _state_unlocked(self, provider: str, now: float) -> CircuitState:
        opened = self._opened_at.get(provider)
        if opened is None:
            return CircuitState.CLOSED
        if now - opened >= self.cooldown_seconds:
            return CircuitState.HALF_OPEN
        return CircuitState.OPEN
