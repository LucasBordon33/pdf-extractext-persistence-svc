import inspect
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call

from app.domain.models import PDFDocument
from app.domain.ports.cache import DocumentCache
from app.domain.ports.repository import DocumentRepository
from app.domain.services.persistence_service import PersistenceService

CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
NAME = "report.pdf"
TEXT = "Texto extraído del PDF."
SIZE = 2048
DOC_ID = "68ff3f8a1b2c3d4e5f6a7b8c"
CACHE_TTL = 300
LOCK_TTL = 10
EXPECTED_DOCUMENT = {
    "id": DOC_ID,
    "name": NAME,
    "checksum": CHECKSUM,
    "content": TEXT,
    "size": SIZE,
    "created_at": "2026-10-09T12:30:00Z",
}


def make_ports() -> tuple[DocumentRepository, DocumentCache]:
    return AsyncMock(spec=DocumentRepository), AsyncMock(spec=DocumentCache)


def make_service(repository: DocumentRepository, cache: DocumentCache) -> PersistenceService:
    return PersistenceService(
        repository=repository,
        cache=cache,
        cache_ttl_seconds=CACHE_TTL,
        lock_ttl_seconds=LOCK_TTL,
    )


def make_existing_document() -> PDFDocument:
    return PDFDocument(
        id=DOC_ID,
        name=NAME,
        checksum=CHECKSUM,
        content=TEXT,
        size=SIZE,
        created_at=datetime(2026, 10, 9, 12, 30, 0, tzinfo=UTC),
    )


async def test_store_persists_new_document_and_returns_id_and_checksum() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = None
    repository.save.return_value = DOC_ID
    service = make_service(repository, cache)

    result = await service.store(name=NAME, text=TEXT, checksum=CHECKSUM, size=SIZE)

    assert result == {"id": DOC_ID, "checksum": CHECKSUM}


async def test_store_returns_conflict_when_lock_is_already_taken() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = False
    service = make_service(repository, cache)

    result = await service.store(name=NAME, text=TEXT, checksum=CHECKSUM)

    assert result["status"] == 409
    assert "id" not in result
    repository.find_by_checksum.assert_not_awaited()
    repository.save.assert_not_awaited()
    cache.set.assert_not_awaited()
    cache.release_lock.assert_not_awaited()


async def test_store_returns_conflict_when_document_already_exists() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = make_existing_document()
    service = make_service(repository, cache)

    result = await service.store(name=NAME, text=TEXT, checksum=CHECKSUM)

    assert result["status"] == 409
    assert "id" not in result
    repository.save.assert_not_awaited()
    cache.set.assert_not_awaited()
    cache.release_lock.assert_awaited_once_with(CHECKSUM)


async def test_store_builds_domain_document_and_passes_it_to_repository() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = None
    repository.save.return_value = DOC_ID
    service = make_service(repository, cache)

    await service.store(name=NAME, text=TEXT, checksum=CHECKSUM, size=SIZE)

    repository.find_by_checksum.assert_awaited_once_with(CHECKSUM)
    saved_document = repository.save.await_args.args[0]
    assert isinstance(saved_document, PDFDocument)
    assert saved_document.id is None
    assert saved_document.name == NAME
    assert saved_document.content == TEXT
    assert saved_document.checksum == CHECKSUM
    assert saved_document.size == SIZE


async def test_store_caches_serialized_document_with_configured_ttl() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = None
    repository.save.return_value = DOC_ID
    service = make_service(repository, cache)

    await service.store(name=NAME, text=TEXT, checksum=CHECKSUM, size=SIZE)

    cache.set.assert_awaited_once()
    cached_checksum, cached_json, cached_ttl = cache.set.await_args.args
    assert cached_checksum == CHECKSUM
    assert cached_ttl == CACHE_TTL
    cached_document = json.loads(cached_json)
    assert cached_document["id"] == DOC_ID
    assert cached_document["checksum"] == CHECKSUM


async def test_store_acquires_lock_with_lock_ttl_and_releases_it() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = None
    repository.save.return_value = DOC_ID
    service = make_service(repository, cache)

    await service.store(name=NAME, text=TEXT, checksum=CHECKSUM)

    cache.acquire_lock.assert_awaited_once_with(CHECKSUM, LOCK_TTL)
    cache.release_lock.assert_awaited_once_with(CHECKSUM)


async def test_store_defaults_size_to_zero_when_not_provided() -> None:
    repository, cache = make_ports()
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = None
    repository.save.return_value = DOC_ID
    service = make_service(repository, cache)

    await service.store(name=NAME, text=TEXT, checksum=CHECKSUM)

    assert repository.save.await_args.args[0].size == 0


async def test_store_coordinates_dependencies_in_expected_order() -> None:
    repository, cache = make_ports()
    manager = MagicMock()
    manager.attach_mock(repository, "repository")
    manager.attach_mock(cache, "cache")
    cache.acquire_lock.return_value = True
    repository.find_by_checksum.return_value = None
    repository.save.return_value = DOC_ID
    service = make_service(repository, cache)

    await service.store(name=NAME, text=TEXT, checksum=CHECKSUM, size=SIZE)

    saved_document = repository.save.await_args.args[0]
    cached_json = cache.set.await_args.args[1]
    assert manager.mock_calls == [
        call.cache.acquire_lock(CHECKSUM, LOCK_TTL),
        call.repository.find_by_checksum(CHECKSUM),
        call.repository.save(saved_document),
        call.cache.set(CHECKSUM, cached_json, CACHE_TTL),
        call.cache.release_lock(CHECKSUM),
    ]


async def test_fetch_returns_cached_document_without_querying_repository() -> None:
    repository, cache = make_ports()
    cache.get.return_value = make_existing_document().to_json()
    service = make_service(repository, cache)

    result = await service.fetch(CHECKSUM)

    assert result == EXPECTED_DOCUMENT
    cache.get.assert_awaited_once_with(CHECKSUM)
    repository.find_by_checksum.assert_not_awaited()
    cache.set.assert_not_awaited()


async def test_fetch_reads_repository_and_repopulates_cache_on_cache_miss() -> None:
    repository, cache = make_ports()
    cache.get.return_value = None
    document = make_existing_document()
    repository.find_by_checksum.return_value = document
    service = make_service(repository, cache)

    result = await service.fetch(CHECKSUM)

    assert result == EXPECTED_DOCUMENT
    repository.find_by_checksum.assert_awaited_once_with(CHECKSUM)
    cache.set.assert_awaited_once_with(CHECKSUM, document.to_json(), CACHE_TTL)


async def test_fetch_returns_none_when_document_not_found() -> None:
    repository, cache = make_ports()
    cache.get.return_value = None
    repository.find_by_checksum.return_value = None
    service = make_service(repository, cache)

    result = await service.fetch(CHECKSUM)

    assert result is None
    cache.set.assert_not_awaited()


async def test_delete_removes_existing_document_by_id_and_returns_true() -> None:
    repository, cache = make_ports()
    repository.find_by_checksum.return_value = make_existing_document()
    repository.delete.return_value = True
    service = make_service(repository, cache)

    result = await service.delete(CHECKSUM)

    assert result is True
    repository.find_by_checksum.assert_awaited_once_with(CHECKSUM)
    repository.delete.assert_awaited_once_with(DOC_ID)
    cache.get.assert_not_awaited()
    cache.set.assert_not_awaited()
    cache.acquire_lock.assert_not_awaited()
    cache.release_lock.assert_not_awaited()


async def test_delete_returns_false_when_checksum_unknown() -> None:
    repository, cache = make_ports()
    repository.find_by_checksum.return_value = None
    service = make_service(repository, cache)

    result = await service.delete(CHECKSUM)

    assert result is False
    repository.delete.assert_not_awaited()


async def test_delete_returns_false_when_repository_reports_failure() -> None:
    repository, cache = make_ports()
    repository.find_by_checksum.return_value = make_existing_document()
    repository.delete.return_value = False
    service = make_service(repository, cache)

    result = await service.delete(CHECKSUM)

    assert result is False


def test_document_cache_contract_has_no_invalidation_operation() -> None:
    public_methods = {
        method_name
        for method_name, _ in inspect.getmembers(DocumentCache, inspect.isfunction)
        if not method_name.startswith("_")
    }

    assert public_methods == {"get", "set", "acquire_lock", "release_lock"}
