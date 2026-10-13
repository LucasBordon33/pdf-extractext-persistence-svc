from redis.asyncio import from_url

from app.config import Settings
from app.domain.ports.cache import DocumentCache


class RedisDocumentCache(DocumentCache):
    def __init__(self, settings: Settings) -> None:
        self._client = from_url(settings.redis_url)

    async def get(self, checksum: str) -> str | None:
        return await self._client.get(self._document_key(checksum))

    async def set(self, checksum: str, value: str, ttl: int) -> None:
        await self._client.set(self._document_key(checksum), value, ex=ttl)

    async def acquire_lock(self, checksum: str, ttl: int) -> bool:
        acquired = await self._client.set(self._lock_key(checksum), 1, nx=True, ex=ttl)
        return acquired is True

    async def release_lock(self, checksum: str) -> None:
        await self._client.delete(self._lock_key(checksum))

    def _document_key(self, checksum: str) -> str:
        return f"doc:{checksum}"

    def _lock_key(self, checksum: str) -> str:
        return f"lock:{checksum}"
