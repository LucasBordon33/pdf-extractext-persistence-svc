from typing import Annotated
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.adapters.mongo.client import MongoClient
from app.adapters.redis.document_cache import RedisDocumentCache
from app.api.deps import get_settings
from app.config import Settings
from app.domain.services.persistence_service import PersistenceService
from app.main import create_app


def test_create_app_attaches_settings_to_app_state(settings: Settings) -> None:
    application = create_app(settings)

    assert application.state.settings is settings


def test_create_app_composes_dependency_graph(settings: Settings) -> None:
    application = create_app(settings)

    assert isinstance(application.state.mongo_client, MongoClient)
    assert isinstance(application.state.persistence_service, PersistenceService)


def test_lifespan_closes_mongo_and_redis_clients_on_shutdown(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    mongo_client = AsyncMock(spec=MongoClient)
    redis_cache = AsyncMock(spec=RedisDocumentCache)
    monkeypatch.setattr("app.main.MongoClient", lambda _: mongo_client)
    monkeypatch.setattr("app.main.RedisDocumentCache", lambda _: redis_cache)

    application = create_app(settings)
    with TestClient(application):
        pass

    mongo_client.close.assert_awaited_once()
    redis_cache.close.assert_awaited_once()


def test_unhandled_exception_returns_error_response_500(settings: Settings) -> None:
    application = create_app(settings)

    @application.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    response = TestClient(application, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error_code": "INTERNAL_ERROR",
        "message": "Internal server error",
    }


def test_dependency_provider_serves_composed_settings(settings: Settings) -> None:
    application = create_app(settings)

    @application.get("/probe")
    def probe(payload: Annotated[Settings, Depends(get_settings)]) -> dict:
        return {"environment": payload.environment, "port": payload.port}

    response = TestClient(application).get("/probe")

    assert response.status_code == 200
    assert response.json() == {"environment": "development", "port": 8003}


def test_module_level_app_is_composed_with_settings() -> None:
    from app.main import app as module_app

    assert isinstance(module_app.state.settings, Settings)
