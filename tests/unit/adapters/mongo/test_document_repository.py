import ast
import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError

from app.adapters.mongo.document_repository import MongoDocumentRepository
from app.domain.models import PDFDocument
from app.domain.ports.repository import DocumentRepository

DOC_ID = "68ff3f8a1b2c3d4e5f6a7b8c"
CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
NAME = "report.pdf"
TEXT = "Texto extraído del PDF."
SIZE = 2048
CREATED_AT = datetime(2026, 10, 9, 12, 30, 0, tzinfo=UTC)

ALLOWED_ROOT_IMPORTS = {"bson", "typing"}
ALLOWED_APP_IMPORTS = {
    "app.adapters.mongo.client",
    "app.domain.models",
    "app.domain.ports.repository",
}


@pytest.fixture
def collection() -> AsyncMock:
    return AsyncMock(name="documents_collection")


@pytest.fixture
def mongo_client(collection: AsyncMock) -> MagicMock:
    client = MagicMock(name="mongo_client")
    client.db.__getitem__.return_value = collection
    return client


@pytest.fixture
def repository(mongo_client: MagicMock) -> MongoDocumentRepository:
    return MongoDocumentRepository(mongo_client)


def make_document() -> PDFDocument:
    return PDFDocument(name=NAME, checksum=CHECKSUM, content=TEXT, size=SIZE)


def make_stored_document() -> dict[str, Any]:
    return {
        "_id": ObjectId(DOC_ID),
        "name": NAME,
        "checksum": CHECKSUM,
        "content": TEXT,
        "size": SIZE,
        "created_at": CREATED_AT,
    }


def make_expected_document() -> PDFDocument:
    return PDFDocument(
        id=DOC_ID, name=NAME, checksum=CHECKSUM, content=TEXT, size=SIZE, created_at=CREATED_AT
    )


def test_repository_implements_document_repository_port(repository: MongoDocumentRepository) -> None:
    assert issubclass(MongoDocumentRepository, DocumentRepository)
    assert isinstance(repository, DocumentRepository)


def test_repository_uses_documents_collection(mongo_client: MagicMock) -> None:
    MongoDocumentRepository(mongo_client)

    mongo_client.db.__getitem__.assert_called_once_with("documents")


async def test_create_ensures_unique_index_on_checksum(
    mongo_client: MagicMock, collection: AsyncMock
) -> None:
    created = await MongoDocumentRepository.create(mongo_client)

    assert isinstance(created, MongoDocumentRepository)
    collection.create_index.assert_awaited_once_with("checksum", unique=True)


async def test_save_persists_entity_dict_via_insert_one(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    document = make_document()

    await repository.save(document)

    collection.insert_one.assert_awaited_once_with(document.to_dict())


async def test_save_returns_generated_objectid_as_str_without_mutating_entity(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.insert_one.return_value.inserted_id = ObjectId(DOC_ID)
    document = make_document()

    generated_id = await repository.save(document)

    assert isinstance(generated_id, str)
    assert generated_id == DOC_ID
    assert document.id is None


async def test_save_propagates_duplicate_key_error(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error")
    document = make_document()

    with pytest.raises(DuplicateKeyError):
        await repository.save(document)


async def test_find_by_checksum_returns_none_when_no_document(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find_one.return_value = None

    result = await repository.find_by_checksum(CHECKSUM)

    assert result is None
    collection.find_one.assert_awaited_once_with({"checksum": CHECKSUM})


async def test_find_by_checksum_rebuilds_domain_document_from_objectid(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find_one.return_value = make_stored_document()

    result = await repository.find_by_checksum(CHECKSUM)

    assert result == make_expected_document()
    assert isinstance(result.id, str)


async def test_find_by_id_queries_by_object_id(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find_one.return_value = make_stored_document()

    await repository.find_by_id(DOC_ID)

    collection.find_one.assert_awaited_once_with({"_id": ObjectId(DOC_ID)})


async def test_find_by_id_rebuilds_domain_document(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find_one.return_value = make_stored_document()

    result = await repository.find_by_id(DOC_ID)

    assert result == make_expected_document()


async def test_find_by_id_returns_none_when_no_document(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find_one.return_value = None

    result = await repository.find_by_id(DOC_ID)

    assert result is None


async def test_delete_returns_true_when_documents_were_deleted(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.delete_one.return_value.deleted_count = 1

    result = await repository.delete(DOC_ID)

    assert result is True
    collection.delete_one.assert_awaited_once_with({"_id": ObjectId(DOC_ID)})


async def test_delete_returns_false_when_no_document_was_deleted(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.delete_one.return_value.deleted_count = 0

    result = await repository.delete(DOC_ID)

    assert result is False


async def test_find_all_rebuilds_every_document_from_the_cursor(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find = MagicMock(return_value=_async_iterable([make_stored_document()]))

    result = await repository.find_all()

    assert result == [make_expected_document()]
    collection.find.assert_called_once_with()


async def test_find_all_returns_empty_list_when_there_are_no_documents(
    repository: MongoDocumentRepository, collection: AsyncMock
) -> None:
    collection.find = MagicMock(return_value=_async_iterable([]))

    result = await repository.find_all()

    assert result == []


def _async_iterable(items: list[dict[str, Any]]) -> Any:
    class _Cursor:
        def __aiter__(self) -> Any:
            return self

        async def __anext__(self) -> dict[str, Any]:
            if not items:
                raise StopAsyncIteration
            return items.pop(0)

    return _Cursor()


def test_repository_module_contains_only_translation_dependencies() -> None:
    module = inspect.getmodule(MongoDocumentRepository)
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
