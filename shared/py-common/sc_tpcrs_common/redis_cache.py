"""Redis-backed cache/rate-limit helper shared across services."""

from __future__ import annotations

import functools
import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis

# TTL presets from the architecture doc.
TTL_RISK_SCORE = 3600  # 1 hour
TTL_DASHBOARD_SUMMARY = 300  # 5 minutes
TTL_THREAT_INTEL = 86400  # 24 hours


class RedisCache:
    def __init__(self, url: str) -> None:
        self._client = redis.from_url(url, decode_responses=True)

    async def get_json(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        return json.loads(raw) if raw is not None else None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._client.set(key, json.dumps(value, default=str), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        """Atomically increment a counter, setting an expiry only if not already set.
        Used for rate limiting and login-lockout counters.
        """
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, nx=True)
        results = await pipe.execute()
        return int(results[0])

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        await self._client.close()


def cached(cache_attr: str, key_fn: Callable[..., str], ttl_seconds: int):
    """Decorator for async instance methods. `self` must expose `cache_attr` -> RedisCache.

    On cache-read failure (e.g. Redis briefly unavailable) falls through to
    computing the value fresh rather than raising, matching the project's
    "external dependency down should degrade, not crash" posture.
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            cache: RedisCache = getattr(self, cache_attr)
            key = key_fn(*args, **kwargs)
            try:
                cached_value = await cache.get_json(key)
            except Exception:  # noqa: BLE001
                cached_value = None
            if cached_value is not None:
                return cached_value
            result = await func(self, *args, **kwargs)
            try:
                await cache.set_json(key, result, ttl_seconds)
            except Exception:  # noqa: BLE001
                pass
            return result

        return wrapper

    return decorator
