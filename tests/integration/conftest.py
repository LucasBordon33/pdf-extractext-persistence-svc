import uuid

import pytest
import redis as redis_sync
from pymongo import MongoClient as SyncMongoClient

from app.config import Settings

MONGO_URI = "mongodb://localhost:27017"
REDIS_URL = "redis://localhost:6379/15"


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    settings = Settings(
        _env_file=None,
        environment="test",
        mongo_uri=MONGO_URI,
        mongo_db=f"pdf_documents_test_{uuid.uuid4().hex[:12]}",
        redis_url=REDIS_URL,
    )
    if not _mongo_available(settings.mongo_uri):
        pytest.skip(f"MongoDB no disponible en {settings.mongo_uri}: suite de integracion saltada")
    if not _redis_available(settings.redis_url):
        pytest.skip(f"Redis no disponible en {settings.redis_url}: suite de integracion saltada")
    return settings


@pytest.fixture(autouse=True)
def _clean_state(integration_settings: Settings) -> None:
    mongo = SyncMongoClient(integration_settings.mongo_uri)
    mongo.drop_database(integration_settings.mongo_db)
    mongo.close()

    redis_client = redis_sync.Redis.from_url(integration_settings.redis_url)
    redis_client.flushdb()
    redis_client.close()


def _mongo_available(uri: str) -> bool:
    try:
        client = SyncMongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _redis_available(url: str) -> bool:
    try:
        client = redis_sync.Redis.from_url(url, socket_connect_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:  # noqa: BLE001
        return False
