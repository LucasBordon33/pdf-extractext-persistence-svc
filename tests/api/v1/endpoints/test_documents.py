import ast
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import documents as documents_module
from app.api.v1.endpoints.documents import router
from app.domain.services.persistence_service import PersistenceService

CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
DOC_ID = "68ff3f8a1b2c3d4e5f6a7b8c"
NAME = "report.pdf"
TEXT = "Texto extraído del PDF."
SIZE = 2048
STORE_PAYLOAD = {"name": NAME, "text": TEXT, "checksum": CHECKSUM, "size": SIZE}
FETCHED_DOCUMENT = {
    "id": DOC_ID,
    "name": NAME,
    "checksum": CHECKSUM,
    "content": TEXT,
    "size": SIZE,
    "created_at": "2026-10-09T12:30:00Z",
}
DUPLICATE_DETAIL = "Document with this checksum already exists"

ALLOWED_ROOT_IMPORTS = {"fastapi", "typing"}
ALLOWED_APP_IMPORTS = {
    "app.api.deps",
    "app.api.v1.schemas",
    "app.domain.services.persistence_service",
}


@pytest.fixture
def persistence_service() -> AsyncMock:
    return AsyncMock(spec=PersistenceService)


@pytest.fixture
def app(persistence_service: AsyncMock) -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    application.state.persistence_service = persistence_service
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_documents_router_declares_exactly_the_requested_routes() -> None:
    declared = {(route.path, frozenset(route.methods - {"HEAD"})) for route in router.routes}

    assert declared == {
        ("/store", frozenset({"POST"})),
        ("/documents", frozenset({"GET"})),
        ("/documents/checksum/{checksum}", frozenset({"GET"})),
        ("/documents/{doc_id}", frozenset({"GET"})),
        ("/documents/{doc_id}", frozenset({"DELETE"})),
    }


def test_documents_module_contains_no_infrastructure_dependencies() -> None:
    assert documents_module.__file__ is not None

    tree = ast.parse(Path(documents_module.__file__).read_text(encoding="utf-8"))

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


def test_store_returns_201_with_store_response_contract(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.store.return_value = {"id": DOC_ID, "checksum": CHECKSUM}

    response = client.post("/store", json=STORE_PAYLOAD)

    assert response.status_code == 201
    assert response.json() == {"id": DOC_ID, "checksum": CHECKSUM}


def test_store_delegates_to_persistence_service(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.store.return_value = {"id": DOC_ID, "checksum": CHECKSUM}

    client.post("/store", json=STORE_PAYLOAD)

    persistence_service.store.assert_awaited_once_with(
        name=NAME, text=TEXT, checksum=CHECKSUM, size=SIZE
    )


def test_store_defaults_size_to_zero_when_omitted(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.store.return_value = {"id": DOC_ID, "checksum": CHECKSUM}

    client.post("/store", json={"name": NAME, "text": TEXT, "checksum": CHECKSUM})

    persistence_service.store.assert_awaited_once_with(name=NAME, text=TEXT, checksum=CHECKSUM, size=0)


def test_store_returns_409_with_duplicate_document_error(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.store.return_value = {"status": 409, "detail": DUPLICATE_DETAIL}

    response = client.post("/store", json=STORE_PAYLOAD)

    assert response.status_code == 409
    assert response.json() == {"error_code": "DUPLICATE_DOCUMENT", "message": DUPLICATE_DETAIL}


def test_store_rejects_invalid_payloads_with_422(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    response = client.post("/store", json={"name": NAME})

    assert response.status_code == 422
    persistence_service.store.assert_not_awaited()


def test_list_documents_returns_200_with_all_documents(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.list_all.return_value = [FETCHED_DOCUMENT]

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == [FETCHED_DOCUMENT]


def test_list_documents_delegates_to_persistence_service(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.list_all.return_value = []

    client.get("/documents")

    persistence_service.list_all.assert_awaited_once()


def test_get_document_by_checksum_returns_200_with_document_response_contract(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.fetch.return_value = FETCHED_DOCUMENT

    response = client.get(f"/documents/checksum/{CHECKSUM}")

    assert response.status_code == 200
    assert response.json() == FETCHED_DOCUMENT


def test_get_document_by_checksum_delegates_to_persistence_service(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.fetch.return_value = FETCHED_DOCUMENT

    client.get(f"/documents/checksum/{CHECKSUM}")

    persistence_service.fetch.assert_awaited_once_with(CHECKSUM)


def test_get_document_by_checksum_returns_404_with_document_not_found_error(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.fetch.return_value = None

    response = client.get(f"/documents/checksum/{CHECKSUM}")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "DOCUMENT_NOT_FOUND",
        "message": "No document found for the given checksum",
    }


def test_get_document_returns_200_with_document_response_contract(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.fetch_by_id.return_value = FETCHED_DOCUMENT

    response = client.get(f"/documents/{DOC_ID}")

    assert response.status_code == 200
    assert response.json() == FETCHED_DOCUMENT


def test_get_document_delegates_to_persistence_service(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.fetch_by_id.return_value = FETCHED_DOCUMENT

    client.get(f"/documents/{DOC_ID}")

    persistence_service.fetch_by_id.assert_awaited_once_with(DOC_ID)


def test_get_document_returns_404_with_document_not_found_error(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.fetch_by_id.return_value = None

    response = client.get(f"/documents/{DOC_ID}")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "DOCUMENT_NOT_FOUND",
        "message": "No document found for the given id",
    }


def test_delete_document_returns_204_without_body(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.delete_by_id.return_value = True

    response = client.delete(f"/documents/{DOC_ID}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_document_delegates_to_persistence_service(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.delete_by_id.return_value = True

    client.delete(f"/documents/{DOC_ID}")

    persistence_service.delete_by_id.assert_awaited_once_with(DOC_ID)


def test_delete_document_returns_404_when_document_not_found(
    client: TestClient, persistence_service: AsyncMock
) -> None:
    persistence_service.delete_by_id.return_value = False

    response = client.delete(f"/documents/{DOC_ID}")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "DOCUMENT_NOT_FOUND",
        "message": "No document found for the given id",
    }
