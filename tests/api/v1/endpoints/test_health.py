from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.mongo.client import MongoClient
from app.api.v1.endpoints.health import router
from app.api.v1.schemas import HealthResponse

EXPECTED_OK = {"status": "ok", "version": "0.1.0"}
EXPECTED_DEGRADED = {"status": "degraded", "version": "0.1.0"}


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def mongo_client() -> AsyncMock:
    return AsyncMock(spec=MongoClient)


def test_health_route_declares_get_with_health_response_schema() -> None:
    (health_route,) = router.routes

    assert health_route.path == "/health"
    assert "GET" in health_route.methods
    assert health_route.response_model is HealthResponse


def test_health_without_mongo_returns_ok_with_exact_contract(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_OK


def test_health_returns_ok_when_mongo_ping_succeeds(
    app: FastAPI, client: TestClient, mongo_client: AsyncMock
) -> None:
    mongo_client.ping.return_value = True
    app.state.mongo_client = mongo_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_OK
    mongo_client.ping.assert_awaited_once()


def test_health_returns_degraded_when_mongo_ping_fails(
    app: FastAPI, client: TestClient, mongo_client: AsyncMock
) -> None:
    mongo_client.ping.return_value = False
    app.state.mongo_client = mongo_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_DEGRADED
    mongo_client.ping.assert_awaited_once()


def test_health_returns_degraded_when_mongo_ping_raises(
    app: FastAPI, client: TestClient, mongo_client: AsyncMock
) -> None:
    mongo_client.ping.side_effect = Exception("ECONNREFUSED 127.0.0.1:27017")
    app.state.mongo_client = mongo_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == EXPECTED_DEGRADED
    assert "ECONNREFUSED" not in response.text


def test_health_invokes_ping_once_per_request(
    app: FastAPI, client: TestClient, mongo_client: AsyncMock
) -> None:
    mongo_client.ping.return_value = True
    app.state.mongo_client = mongo_client

    client.get("/health")
    client.get("/health")

    assert mongo_client.ping.await_count == 2
