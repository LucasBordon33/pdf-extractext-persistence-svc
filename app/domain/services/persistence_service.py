import json
from datetime import UTC, datetime
from typing import Any

from app.domain.models import PDFDocument
from app.domain.ports.cache import DocumentCache
from app.domain.ports.repository import DocumentRepository


class PersistenceService:
    def __init__(
        self,
        repository: DocumentRepository,
        cache: DocumentCache,
        cache_ttl_seconds: int,
        lock_ttl_seconds: int,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._lock_ttl_seconds = lock_ttl_seconds

    async def store(self, name: str, text: str, checksum: str, size: int = 0) -> dict[str, Any]:
        acquired = await self._cache.acquire_lock(checksum, self._lock_ttl_seconds)
        if not acquired:
            return self._duplicate_response()

        try:
            if await self._repository.find_by_checksum(checksum) is not None:
                return self._duplicate_response()

            document = PDFDocument(
                name=name, content=text, checksum=checksum, size=size, created_at=datetime.now(UTC)
            )
            generated_id = await self._repository.save(document)
            stored_document = document.model_copy(update={"id": generated_id})
            await self._cache.set(checksum, stored_document.to_json(), self._cache_ttl_seconds)
            return {"id": generated_id, "checksum": checksum}
        finally:
            await self._cache.release_lock(checksum)

    async def fetch(self, checksum: str) -> dict[str, Any] | None:
        cached = await self._cache.get(checksum)
        if cached is not None:
            return json.loads(cached)

        document = await self._repository.find_by_checksum(checksum)
        if document is None:
            return None

        json_document = document.to_json()
        await self._cache.set(checksum, json_document, self._cache_ttl_seconds)
        return json.loads(json_document)

    async def delete(self, checksum: str) -> bool:
        document = await self._repository.find_by_checksum(checksum)
        if document is None:
            return False

        return await self._repository.delete(document.id)

    async def delete_by_id(self, doc_id: str) -> bool:
        document = await self._repository.find_by_id(doc_id)
        if document is None:
            return False

        return await self._repository.delete(doc_id)

    async def list_all(self) -> list[dict[str, Any]]:
        documents = await self._repository.find_all()
        return [json.loads(document.to_json()) for document in documents]

    async def fetch_by_id(self, doc_id: str) -> dict[str, Any] | None:
        document = await self._repository.find_by_id(doc_id)
        if document is None:
            return None
        return json.loads(document.to_json())

    def _duplicate_response(self) -> dict[str, Any]:
        return {"status": 409, "detail": "Document with this checksum already exists"}
