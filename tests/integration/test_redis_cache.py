import asyncio

import pytest

from app.adapters.redis.document_cache import RedisDocumentCache
from app.config import Settings

pytestmark = pytest.mark.integration

CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
VALUE = '{"id": "abc", "checksum": "..."}'
TTL = 60


@pytest.fixture
async def cache(integration_settings: Settings) -> RedisDocumentCache:
    document_cache = RedisDocumentCache(integration_settings)
    yield document_cache
    await document_cache.close()


async def test_set_get_roundtrip_and_miss_returns_none(cache: RedisDocumentCache) -> None:
    await cache.set(CHECKSUM, VALUE, TTL)

    cached = await cache.get(CHECKSUM)
    missing = await cache.get("unknown-checksum")

    assert cached == VALUE
    assert missing is None


async def test_acquire_lock_is_granted_once_until_released(cache: RedisDocumentCache) -> None:
    first = await cache.acquire_lock(CHECKSUM, TTL)
    second = await cache.acquire_lock(CHECKSUM, TTL)

    await cache.release_lock(CHECKSUM)
    third = await cache.acquire_lock(CHECKSUM, TTL)

    assert first is True
    assert second is False
    assert third is True


async def test_acquire_lock_expires_after_ttl(cache: RedisDocumentCache) -> None:
    assert await cache.acquire_lock(CHECKSUM, ttl=1) is True
    assert await cache.acquire_lock(CHECKSUM, ttl=1) is False

    await asyncio.sleep(1.5)

    assert await cache.acquire_lock(CHECKSUM, ttl=1) is True
