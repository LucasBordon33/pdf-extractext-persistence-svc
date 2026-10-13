from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.mongo.client import MongoClient
from app.config import Settings

MONGO_URI = "mongodb://mongo-test:27017"
MONGO_DB = "pdf_documents_test"


@pytest.fixture
def motor_factory() -> MagicMock:
    with patch("app.adapters.mongo.client.AsyncIOMotorClient") as factory:
        yield factory


@pytest.fixture
def mongo_settings() -> Settings:
    return Settings(_env_file=None, mongo_uri=MONGO_URI, mongo_db=MONGO_DB)


@pytest.fixture
def adapter(mongo_settings: Settings, motor_factory: MagicMock) -> MongoClient:
    return MongoClient(mongo_settings)


@pytest.fixture
def motor_database(motor_factory: MagicMock) -> MagicMock:
    return motor_factory.return_value.__getitem__.return_value


def test_constructor_creates_motor_client_with_configured_uri(
    mongo_settings: Settings, motor_factory: MagicMock
) -> None:
    MongoClient(mongo_settings)

    motor_factory.assert_called_once_with(MONGO_URI)


def test_adapter_keeps_reference_to_internal_motor_client(
    adapter: MongoClient, motor_factory: MagicMock
) -> None:
    assert adapter._client is motor_factory.return_value


def test_db_returns_database_configured_in_settings(
    adapter: MongoClient, mongo_settings: Settings, motor_factory: MagicMock
) -> None:
    database = adapter.db

    assert database is motor_factory.return_value.__getitem__.return_value
    motor_factory.return_value.__getitem__.assert_called_once_with(mongo_settings.mongo_db)


async def test_ping_returns_true_when_mongodb_responds(
    adapter: MongoClient, motor_database: MagicMock
) -> None:
    motor_database.command = AsyncMock(return_value={"ok": 1})

    result = await adapter.ping()

    assert result is True
    motor_database.command.assert_awaited_once_with("ping")


async def test_ping_returns_false_when_healthcheck_fails(
    adapter: MongoClient, motor_database: MagicMock
) -> None:
    motor_database.command = AsyncMock(side_effect=Exception("connection refused"))

    result = await adapter.ping()

    assert result is False


async def test_close_delegates_closing_to_motor_client(
    adapter: MongoClient, motor_factory: MagicMock
) -> None:
    await adapter.close()

    motor_factory.return_value.close.assert_called_once_with()


async def test_adapter_lifecycle_uses_a_single_mocked_motor_client(
    mongo_settings: Settings, motor_factory: MagicMock
) -> None:
    motor_database = motor_factory.return_value.__getitem__.return_value
    motor_database.command = AsyncMock(return_value={"ok": 1})
    adapter = MongoClient(mongo_settings)

    assert adapter.db is not None
    assert await adapter.ping() is True
    await adapter.close()

    motor_factory.assert_called_once_with(MONGO_URI)
