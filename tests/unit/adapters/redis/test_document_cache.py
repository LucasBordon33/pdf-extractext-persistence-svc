import ast
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.redis.document_cache import RedisDocumentCache
from app.config import Settings
from app.domain.ports.cache import DocumentCache

CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
REDIS_URL = "redis://redis-test:6379/1"
DOCUMENT_KEY = f"doc:{CHECKSUM}"
LOCK_KEY = f"lock:{CHECKSUM}"
CACHED_VALUE = '{"id":"68ff3f8a1b2c3d4e5f6a7b8c","size":2048}'
CACHE_TTL = 300
LOCK_TTL = 10

ALLOWED_ROOT_IMPORTS = {"redis"}
ALLOWED_APP_IMPORTS = {"app.config", "app.domain.ports.cache"}


@pytest.fixture
def from_url() -> MagicMock:
    with patch("app.adapters.redis.document_cache.from_url") as factory:
        yield factory


@pytest.fixture
def redis_settings() -> Settings:
    return Settings(_env_file=None, redis_url=REDIS_URL)


@pytest.fixture
def redis_client(from_url: MagicMock) -> AsyncMock:
    client = AsyncMock(name="redis_client")
    from_url.return_value = client
    return client


@pytest.fixture
def cache(redis_settings: Settings, redis_client: AsyncMock) -> RedisDocumentCache:
    return RedisDocumentCache(redis_settings)


def test_cache_implements_document_cache_port(cache: RedisDocumentCache) -> None:
    assert issubclass(RedisDocumentCache, DocumentCache)
    assert isinstance(cache, DocumentCache)


def test_constructor_creates_redis_client_from_configured_url(
    redis_settings: Settings, from_url: MagicMock
) -> None:
    RedisDocumentCache(redis_settings)

    from_url.assert_called_once_with(REDIS_URL)


def test_constructor_keeps_reference_to_internal_redis_client(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    assert cache._client is redis_client


async def test_get_returns_stored_value_using_document_key(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    redis_client.get.return_value = CACHED_VALUE

    result = await cache.get(CHECKSUM)

    assert result == CACHED_VALUE
    redis_client.get.assert_awaited_once_with(DOCUMENT_KEY)


async def test_get_returns_none_when_key_does_not_exist(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    redis_client.get.return_value = None

    result = await cache.get(CHECKSUM)

    assert result is None
    redis_client.get.assert_awaited_once_with(DOCUMENT_KEY)


async def test_set_stores_exact_value_with_document_key_and_ttl(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    await cache.set(CHECKSUM, CACHED_VALUE, CACHE_TTL)

    redis_client.set.assert_awaited_once_with(DOCUMENT_KEY, CACHED_VALUE, ex=CACHE_TTL)


async def test_acquire_lock_uses_set_nx_ex_on_lock_key(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    redis_client.set.return_value = True

    await cache.acquire_lock(CHECKSUM, LOCK_TTL)

    redis_client.set.assert_awaited_once_with(LOCK_KEY, 1, nx=True, ex=LOCK_TTL)


async def test_acquire_lock_returns_true_when_redis_confirms_creation(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    redis_client.set.return_value = True

    result = await cache.acquire_lock(CHECKSUM, LOCK_TTL)

    assert result is True


async def test_acquire_lock_returns_false_when_lock_already_exists(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    redis_client.set.return_value = None

    result = await cache.acquire_lock(CHECKSUM, LOCK_TTL)

    assert result is False


async def test_release_lock_deletes_lock_key(
    cache: RedisDocumentCache, redis_client: AsyncMock
) -> None:
    result = await cache.release_lock(CHECKSUM)

    assert result is None
    redis_client.delete.assert_awaited_once_with(LOCK_KEY)


def test_cache_module_contains_only_translation_dependencies() -> None:
    module = inspect.getmodule(RedisDocumentCache)
    assert module is not None
    assert module.__file__ is not None

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in ALLOWED_ROOT_IMPORTS
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            if node.module.startswith("app."):
                assert node.module in ALLOWED_APP_IMPORTS
            else:
                assert node.module.split(".")[0] in ALLOWED_ROOT_IMPORTS
