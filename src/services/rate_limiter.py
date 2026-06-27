import time
import logging
from collections import defaultdict
from fastapi import HTTPException, Request
from typing import Tuple

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    def __init__(self):
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        self._attempts[key] = [t for t in self._attempts[key] if t > window_start]
        if len(self._attempts[key]) >= max_attempts:
            retry_after = int(window_seconds - (now - self._attempts[key][0]))
            return False, max(retry_after, 1)
        self._attempts[key].append(now)
        return True, 0

    def cleanup(self):
        now = time.time()
        for key in list(self._attempts.keys()):
            self._attempts[key] = [t for t in self._attempts[key] if t > now - 3600]
            if not self._attempts[key]:
                del self._attempts[key]


_rate_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    return _rate_limiter


def rate_limit(max_attempts: int = 5, window_seconds: int = 300):
    async def dependency(request: Request):
        limiter = get_rate_limiter()
        client_ip = request.client.host if request.client else "unknown"
        route_path = request.url.path
        key = f"{route_path}:{client_ip}"
        allowed, retry_after = limiter.check(key, max_attempts, window_seconds)
        if not allowed:
            logger.warning(f"Rate limit exceeded for {key}")
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
    return dependency
