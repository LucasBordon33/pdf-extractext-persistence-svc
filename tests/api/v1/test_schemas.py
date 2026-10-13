import json
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.api.v1.schemas import (
    DocumentResponse,
    ErrorResponse,
    HealthResponse,
    StoreRequest,
    StoreResponse,
)

NAME = "report.pdf"
TEXT = "Texto extraído del PDF."
CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
SIZE = 2048
DOC_ID = "68ff3f8a1b2c3d4e5f6a7b8c"
CREATED_AT = datetime(2026, 10, 9, 12, 30, 0, tzinfo=UTC)
ERROR_CODE = "DOCUMENT_NOT_FOUND"
ERROR_MESSAGE = "No document found for the given checksum"
STATUS = "ok"
VERSION = "0.1.0"

ALL_SCHEMAS = [StoreRequest, StoreResponse, DocumentResponse, ErrorResponse, HealthResponse]


def make_store_request() -> StoreRequest:
    return StoreRequest(name=NAME, text=TEXT, checksum=CHECKSUM, size=SIZE)


def make_store_response() -> StoreResponse:
    return StoreResponse(id=DOC_ID, checksum=CHECKSUM)


def make_document_response() -> DocumentResponse:
    return DocumentResponse(
        id=DOC_ID, name=NAME, checksum=CHECKSUM, content=TEXT, size=SIZE, created_at=CREATED_AT
    )


def make_document_payload() -> dict[str, object]:
    return {
        "id": DOC_ID,
        "name": NAME,
        "checksum": CHECKSUM,
        "content": TEXT,
        "size": SIZE,
        "created_at": CREATED_AT,
    }


def make_error_response() -> ErrorResponse:
    return ErrorResponse(error_code=ERROR_CODE, message=ERROR_MESSAGE)


def make_health_response() -> HealthResponse:
    return HealthResponse(status=STATUS, version=VERSION)


def assert_missing_required_field_rejected(
    schema: type[BaseModel], payload: dict[str, object], missing_field: str
) -> None:
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        schema(**payload)


@pytest.mark.parametrize("schema", ALL_SCHEMAS)
def test_schemas_are_pydantic_v2_base_models(schema: type[BaseModel]) -> None:
    assert issubclass(schema, BaseModel)
    assert callable(schema.model_dump)
    assert callable(schema.model_validate_json)


def test_store_request_keeps_provided_fields() -> None:
    request = make_store_request()

    assert request.name == NAME
    assert request.text == TEXT
    assert request.checksum == CHECKSUM
    assert request.size == SIZE


def test_store_request_size_defaults_to_zero() -> None:
    request = StoreRequest(name=NAME, text=TEXT, checksum=CHECKSUM)

    assert request.size == 0


def test_store_request_model_dump_contains_exactly_declared_fields() -> None:
    data = make_store_request().model_dump()

    assert data == {"name": NAME, "text": TEXT, "checksum": CHECKSUM, "size": SIZE}


def test_store_request_ignores_unknown_input_fields() -> None:
    request = StoreRequest(name=NAME, text=TEXT, checksum=CHECKSUM, unexpected="ignored")

    assert request.model_dump() == {"name": NAME, "text": TEXT, "checksum": CHECKSUM, "size": 0}


@pytest.mark.parametrize("missing_field", ["name", "text", "checksum"])
def test_store_request_missing_required_field_raises(missing_field: str) -> None:
    assert_missing_required_field_rejected(
        StoreRequest, {"name": NAME, "text": TEXT, "checksum": CHECKSUM}, missing_field
    )


def test_store_request_incompatible_type_raises() -> None:
    payload = {"name": NAME, "text": TEXT, "checksum": CHECKSUM, "size": "not-a-number"}

    with pytest.raises(ValidationError):
        StoreRequest(**payload)


def test_store_response_contains_id_and_checksum() -> None:
    response = make_store_response()

    assert response.id == DOC_ID
    assert response.checksum == CHECKSUM
    assert response.model_dump() == {"id": DOC_ID, "checksum": CHECKSUM}


@pytest.mark.parametrize("missing_field", ["id", "checksum"])
def test_store_response_missing_required_field_raises(missing_field: str) -> None:
    assert_missing_required_field_rejected(
        StoreResponse, {"id": DOC_ID, "checksum": CHECKSUM}, missing_field
    )


def test_document_response_contains_all_required_fields() -> None:
    response = make_document_response()

    assert response.model_dump() == {
        "id": DOC_ID,
        "name": NAME,
        "checksum": CHECKSUM,
        "content": TEXT,
        "size": SIZE,
        "created_at": CREATED_AT,
    }


def test_document_response_serializes_datetime_as_iso_8601() -> None:
    response = make_document_response()

    parsed = json.loads(response.model_dump_json())

    assert parsed["created_at"] == "2026-10-09T12:30:00Z"


def test_document_response_json_is_consistent_with_internal_representation() -> None:
    response = make_document_response()
    data = response.model_dump()

    parsed = json.loads(response.model_dump_json())

    assert set(parsed) == set(data)
    assert datetime.fromisoformat(parsed["created_at"]) == data["created_at"]
    assert parsed["name"] == data["name"]
    assert parsed["size"] == data["size"]


@pytest.mark.parametrize(
    "missing_field",
    ["id", "name", "checksum", "content", "size", "created_at"],
)
def test_document_response_missing_required_field_raises(missing_field: str) -> None:
    assert_missing_required_field_rejected(DocumentResponse, make_document_payload(), missing_field)


def test_document_response_incompatible_datetime_raises() -> None:
    payload = make_document_payload()
    payload["created_at"] = "not-a-date"

    with pytest.raises(ValidationError):
        DocumentResponse(**payload)


def test_error_response_uses_normalized_structure() -> None:
    response = make_error_response()

    assert response.error_code == ERROR_CODE
    assert response.message == ERROR_MESSAGE
    assert response.model_dump() == {"error_code": ERROR_CODE, "message": ERROR_MESSAGE}


@pytest.mark.parametrize("missing_field", ["error_code", "message"])
def test_error_response_missing_required_field_raises(missing_field: str) -> None:
    assert_missing_required_field_rejected(
        ErrorResponse, {"error_code": ERROR_CODE, "message": ERROR_MESSAGE}, missing_field
    )


def test_health_response_contains_status_and_version() -> None:
    response = make_health_response()

    assert response.status == STATUS
    assert response.version == VERSION
    assert response.model_dump() == {"status": STATUS, "version": VERSION}


@pytest.mark.parametrize("missing_field", ["status", "version"])
def test_health_response_missing_required_field_raises(missing_field: str) -> None:
    assert_missing_required_field_rejected(
        HealthResponse, {"status": STATUS, "version": VERSION}, missing_field
    )


@pytest.mark.parametrize(
    "schema_instance",
    [
        make_store_request(),
        make_store_response(),
        make_document_response(),
        make_error_response(),
        make_health_response(),
    ],
    ids=[
        "store_request",
        "store_response",
        "document_response",
        "error_response",
        "health_response",
    ],
)
def test_model_dump_json_is_valid_json_consistent_with_model_dump(
    schema_instance: BaseModel,
) -> None:
    parsed = json.loads(schema_instance.model_dump_json())

    assert set(parsed) == set(schema_instance.model_dump())
