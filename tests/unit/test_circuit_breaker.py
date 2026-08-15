import time

from app.ai_gateway.circuit_breaker import CircuitBreaker, CircuitState


def test_opens_after_threshold_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
    assert breaker.peek("gemini") == CircuitState.CLOSED
    breaker.record_failure("gemini")
    breaker.record_failure("gemini")
    assert breaker.peek("gemini") == CircuitState.CLOSED
    assert breaker.record_failure("gemini") == CircuitState.OPEN
    assert breaker.allow("gemini") is False


def test_half_open_then_close_on_success() -> None:
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.01)
    breaker.record_failure("groq")
    breaker.record_failure("groq")
    assert breaker.peek("groq") == CircuitState.OPEN
    time.sleep(0.02)
    assert breaker.peek("groq") == CircuitState.HALF_OPEN
    assert breaker.allow("groq") is True
    assert breaker.allow("groq") is False
    breaker.record_success("groq")
    assert breaker.peek("groq") == CircuitState.CLOSED
    assert breaker.allow("groq") is True
