import pytest
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError

from app.adapters.mongo.client import MongoClient
from app.adapters.mongo.document_repository import MongoDocumentRepository
from app.config import Settings
from app.domain.models import PDFDocument

pytestmark = pytest.mark.integration

CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
NAME = "report.pdf"
CONTENT = "Texto extraido del PDF."
SIZE = 2048


@pytest.fixture
async def mongo_client(integration_settings: Settings) -> MongoClient:
    client = MongoClient(integration_settings)
    yield client
    await client.close()


@pytest.fixture
async def repository(mongo_client: MongoClient) -> MongoDocumentRepository:
    return await MongoDocumentRepository.create(mongo_client)


def make_document(checksum: str = CHECKSUM) -> PDFDocument:
    return PDFDocument(name=NAME, content=CONTENT, checksum=checksum, size=SIZE)


async def test_save_returns_id_and_document_is_retrievable_by_id(
    repository: MongoDocumentRepository,
) -> None:
    saved_id = await repository.save(make_document())

    found = await repository.find_by_id(saved_id)

    assert found is not None
    assert found.id == saved_id
    assert found.name == NAME
    assert found.content == CONTENT
    assert found.checksum == CHECKSUM
    assert found.size == SIZE


async def test_find_by_checksum_returns_document_or_none(
    repository: MongoDocumentRepository,
) -> None:
    await repository.save(make_document())

    found = await repository.find_by_checksum(CHECKSUM)
    missing = await repository.find_by_checksum("unknown-checksum")

    assert found is not None
    assert found.checksum == CHECKSUM
    assert missing is None


async def test_saving_same_checksum_twice_raises_duplicate_key_error(
    repository: MongoDocumentRepository,
) -> None:
    await repository.save(make_document())

    with pytest.raises(DuplicateKeyError):
        await repository.save(make_document())


async def test_delete_returns_true_for_existing_document_and_false_for_unknown_id(
    repository: MongoDocumentRepository,
) -> None:
    saved_id = await repository.save(make_document())

    deleted = await repository.delete(saved_id)
    deleted_again = await repository.delete(saved_id)

    assert deleted is True
    assert deleted_again is False
    assert await repository.find_by_id(saved_id) is None


async def test_delete_returns_false_for_never_seen_valid_id(
    repository: MongoDocumentRepository,
) -> None:
    deleted = await repository.delete(str(ObjectId()))

    assert deleted is False
