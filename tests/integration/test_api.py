import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration

CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
NAME = "report.pdf"
TEXT = "Texto extraido del PDF."
SIZE = 2048
STORE_PAYLOAD = {"name": NAME, "text": TEXT, "checksum": CHECKSUM, "size": SIZE}


@pytest.fixture
def client(integration_settings: Settings):
    application = create_app(integration_settings)
    with TestClient(application) as test_client:
        yield test_client


def test_store_fetch_delete_flow_by_id(client: TestClient) -> None:
    store_response = client.post("/api/v1/store", json=STORE_PAYLOAD)
    assert store_response.status_code == 201
    stored = store_response.json()
    assert stored["checksum"] == CHECKSUM
    assert isinstance(stored["id"], str)

    fetch_by_id = client.get(f"/api/v1/documents/{stored['id']}")
    assert fetch_by_id.status_code == 200
    document = fetch_by_id.json()
    assert document["id"] == stored["id"]
    assert document["name"] == NAME
    assert document["content"] == TEXT
    assert document["checksum"] == CHECKSUM
    assert document["size"] == SIZE

    fetch_by_checksum = client.get(f"/api/v1/documents/checksum/{CHECKSUM}")
    assert fetch_by_checksum.status_code == 200
    assert fetch_by_checksum.json()["id"] == stored["id"]

    delete_response = client.delete(f"/api/v1/documents/{stored['id']}")
    assert delete_response.status_code == 204

    fetch_after_delete = client.get(f"/api/v1/documents/{stored['id']}")
    assert fetch_after_delete.status_code == 404
    assert fetch_after_delete.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_list_documents_returns_every_stored_document(client: TestClient) -> None:
    first = client.post("/api/v1/store", json=STORE_PAYLOAD)
    second_payload = {**STORE_PAYLOAD, "checksum": f"alt-{CHECKSUM}"}
    second = client.post("/api/v1/store", json=second_payload)
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    listed = response.json()
    assert {document["checksum"] for document in listed} == {CHECKSUM, f"alt-{CHECKSUM}"}


def test_storing_same_checksum_twice_returns_conflict(client: TestClient) -> None:
    first = client.post("/api/v1/store", json=STORE_PAYLOAD)
    second = client.post("/api/v1/store", json=STORE_PAYLOAD)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "DUPLICATE_DOCUMENT"


def test_get_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/documents/68ff3f8a1b2c3d4e5f6a7b8c")

    assert response.status_code == 404
    assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_get_unknown_checksum_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/documents/checksum/unknown-checksum")

    assert response.status_code == 404
    assert response.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_health_reports_ok_with_live_mongo(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
