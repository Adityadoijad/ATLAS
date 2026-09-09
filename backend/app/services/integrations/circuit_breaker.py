from collections.abc import Awaitable, Callable
from time import monotonic
from typing import TypeVar

T = TypeVar("T")


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 2, recovery_seconds: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at: float | None = None

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        if self.opened_at and monotonic() - self.opened_at < self.recovery_seconds:
            raise RuntimeError("Integration circuit is open")
        try:
            result = await operation()
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = monotonic()
            raise
        self.failures = 0
        self.opened_at = None
        return result
