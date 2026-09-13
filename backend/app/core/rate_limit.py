"""Small in-process fixed-window limiter for local and single-instance deployments."""
from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def enforce(self, request: Request, *, scope: str, subject: str | None = None, limit: int, window_seconds: int) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"{scope}:{subject or client}"
        now = monotonic()
        timestamps = self._requests[key]
        while timestamps and now - timestamps[0] >= window_seconds:
            timestamps.popleft()
        if len(timestamps) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait before requesting another AI response.",
                headers={"Retry-After": str(window_seconds)},
            )
        timestamps.append(now)

    def reset(self) -> None:
        self._requests.clear()


ai_rate_limiter = FixedWindowRateLimiter()
