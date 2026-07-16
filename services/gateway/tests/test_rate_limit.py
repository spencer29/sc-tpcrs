from __future__ import annotations

import fakeredis.aioredis
import pytest
from fastapi import HTTPException
from sc_tpcrs_common.redis_cache import RedisCache

from app.rate_limit import enforce_rate_limit


def _fake_cache() -> RedisCache:
    cache = RedisCache.__new__(RedisCache)
    cache._client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return cache


async def test_allows_requests_under_limit():
    cache = _fake_cache()
    for _ in range(3):
        await enforce_rate_limit(cache, identifier="user-a", limit_per_min=5)


async def test_blocks_requests_over_limit():
    cache = _fake_cache()
    for _ in range(5):
        await enforce_rate_limit(cache, identifier="user-b", limit_per_min=5)
    with pytest.raises(HTTPException) as exc_info:
        await enforce_rate_limit(cache, identifier="user-b", limit_per_min=5)
    assert exc_info.value.status_code == 429


async def test_limits_are_independent_per_identifier():
    cache = _fake_cache()
    for _ in range(5):
        await enforce_rate_limit(cache, identifier="user-c", limit_per_min=5)
    # A different identifier must not be affected by user-c's count.
    await enforce_rate_limit(cache, identifier="user-d", limit_per_min=5)


async def test_boundary_exact_limit_is_allowed():
    cache = _fake_cache()
    for _ in range(5):
        await enforce_rate_limit(cache, identifier="user-e", limit_per_min=5)
    # exactly at the limit (5th call) should succeed; the 6th should not.
    with pytest.raises(HTTPException):
        await enforce_rate_limit(cache, identifier="user-e", limit_per_min=5)
