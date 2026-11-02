from typing import Any, Self

from bson.errors import InvalidId
from bson.objectid import ObjectId

from app.adapters.mongo.client import MongoClient
from app.domain.models import PDFDocument
from app.domain.ports.repository import DocumentRepository


class MongoDocumentRepository(DocumentRepository):
    def __init__(self, mongo_client: MongoClient) -> None:
        self._collection = mongo_client.db["documents"]

    @classmethod
    async def create(cls, mongo_client: MongoClient) -> Self:
        repository = cls(mongo_client)
        await repository._collection.create_index("checksum", unique=True)
        return repository

    async def save(self, doc: PDFDocument) -> str:
        result = await self._collection.insert_one(doc.to_dict())
        return str(result.inserted_id)

    async def find_by_checksum(self, checksum: str) -> PDFDocument | None:
        raw = await self._collection.find_one({"checksum": checksum})
        return self._to_document(raw)

    async def find_by_id(self, doc_id: str) -> PDFDocument | None:
        object_id = self._object_id(doc_id)
        if object_id is None:
            return None
        raw = await self._collection.find_one({"_id": object_id})
        return self._to_document(raw)

    async def update(self, doc: PDFDocument) -> bool:
        object_id = self._object_id(doc.id)
        if object_id is None:
            return False
        fields = doc.to_dict()
        fields.pop("id")
        result = await self._collection.replace_one({"_id": object_id}, fields)
        return result.matched_count > 0

    async def delete(self, doc_id: str) -> bool:
        object_id = self._object_id(doc_id)
        if object_id is None:
            return False
        result = await self._collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def find_all(self) -> list[PDFDocument]:
        return [
            document
            async for raw in self._collection.find()
            if (document := self._to_document(raw)) is not None
        ]

    def _object_id(self, doc_id: str | None) -> ObjectId | None:
        if doc_id is None:
            return None
        try:
            return ObjectId(doc_id)
        except InvalidId:
            return None

    def _to_document(self, raw: dict[str, Any] | None) -> PDFDocument | None:
        if raw is None:
            return None
        fields = dict(raw)
        fields["id"] = str(fields.pop("_id"))
        return PDFDocument(**fields)
