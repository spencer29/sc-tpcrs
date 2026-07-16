from __future__ import annotations

from fastapi import HTTPException, status
from sc_tpcrs_common.redis_cache import RedisCache

RATE_LIMIT_WINDOW_SECONDS = 60


async def enforce_rate_limit(cache: RedisCache, *, identifier: str, limit_per_min: int) -> None:
    """Atomic per-minute counter via RedisCache.incr_with_ttl. Raises 429 once
    `identifier` exceeds `limit_per_min` requests within the rolling window.
    If Redis itself is unreachable, `incr_with_ttl` will raise -- caller
    (main.py) is responsible for deciding whether that should fail open or
    closed; this pass fails closed (a Redis outage surfaces as a 5xx) since
    unmetered traffic during an outage is the greater risk for a rate limiter.
    """
    key = f"ratelimit:{identifier}"
    count = await cache.incr_with_ttl(key, RATE_LIMIT_WINDOW_SECONDS)
    if count > limit_per_min:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
