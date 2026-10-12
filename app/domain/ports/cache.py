from abc import ABC, abstractmethod


class DocumentCache(ABC):
    @abstractmethod
    async def get(self, checksum: str) -> str | None:
        ...

    @abstractmethod
    async def set(self, checksum: str, value: str, ttl: int) -> None:
        ...

    @abstractmethod
    async def acquire_lock(self, checksum: str, ttl: int) -> bool:
        ...

    @abstractmethod
    async def release_lock(self, checksum: str) -> None:
        ...
