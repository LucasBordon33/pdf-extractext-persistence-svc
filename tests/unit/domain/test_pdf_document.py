import json
from datetime import UTC, datetime

from app.domain.models import PDFDocument

CREATED_AT = datetime(2026, 10, 9, 12, 30, 0, tzinfo=UTC)
CHECKSUM = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
DOCUMENT_ID = "68ff3f8a1b2c3d4e5f6a7b8c"


def make_document(**overrides):
    fields = {
        "name": "report.pdf",
        "checksum": CHECKSUM,
        "content": "Texto extraído del PDF.",
        "size": 2048,
        "created_at": CREATED_AT,
    }
    fields.update(overrides)
    return PDFDocument(**fields)


def test_optional_attributes_default_values() -> None:
    document = PDFDocument(name="report.pdf", checksum=CHECKSUM, content="Texto extraído del PDF.")

    assert document.id is None
    assert document.size == 0
    assert document.created_at is None


def test_to_dict_excludes_id_when_none() -> None:
    document = make_document()

    data = document.to_dict()

    assert "id" not in data
    assert data == {
        "name": "report.pdf",
        "checksum": CHECKSUM,
        "content": "Texto extraído del PDF.",
        "size": 2048,
        "created_at": CREATED_AT,
    }


def test_to_dict_includes_id_when_present() -> None:
    document = make_document(id=DOCUMENT_ID)

    data = document.to_dict()

    assert data["id"] == DOCUMENT_ID
    assert set(data) == {"id", "name", "checksum", "content", "size", "created_at"}


def test_to_dict_keeps_other_optional_fields_when_none() -> None:
    document = make_document(created_at=None)

    data = document.to_dict()

    assert data["created_at"] is None


def test_to_dict_does_not_transform_id_to_mongo_underscore_field() -> None:
    document = make_document(id=DOCUMENT_ID)

    data = document.to_dict()

    assert "_id" not in data
    assert "id" in data


def test_to_dict_exports_storage_compatible_primitive_values() -> None:
    document = make_document(id=DOCUMENT_ID)

    data = document.to_dict()

    assert all(isinstance(value, (str, int, datetime)) for value in data.values())


def test_to_json_is_valid_json() -> None:
    document = make_document()

    parsed = json.loads(document.to_json())

    assert isinstance(parsed, dict)


def test_to_json_excludes_id_when_none() -> None:
    document = make_document()

    parsed = json.loads(document.to_json())

    assert "id" not in parsed
    assert parsed["name"] == "report.pdf"
    assert parsed["size"] == 2048


def test_to_json_includes_id_when_present() -> None:
    document = make_document(id=DOCUMENT_ID)

    parsed = json.loads(document.to_json())

    assert parsed["id"] == DOCUMENT_ID


def test_to_json_keeps_created_at_when_none() -> None:
    document = make_document(created_at=None)

    parsed = json.loads(document.to_json())

    assert parsed["created_at"] is None


def test_to_json_serializes_datetime_as_iso_8601() -> None:
    document = make_document()

    parsed = json.loads(document.to_json())

    assert parsed["created_at"] == "2026-10-09T12:30:00Z"
    assert datetime.fromisoformat(parsed["created_at"]) == CREATED_AT


def test_to_json_structure_is_consistent_with_to_dict() -> None:
    document = make_document(id=DOCUMENT_ID)
    data = document.to_dict()

    parsed = json.loads(document.to_json())

    assert set(parsed) == set(data)
    assert parsed["name"] == data["name"]
    assert parsed["size"] == data["size"]
    assert datetime.fromisoformat(parsed["created_at"]) == data["created_at"]
