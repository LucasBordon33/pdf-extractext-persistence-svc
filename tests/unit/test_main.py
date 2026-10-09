from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.deps import get_settings
from app.config import Settings
from app.main import create_app


def test_create_app_attaches_settings_to_app_state(settings: Settings) -> None:
    application = create_app(settings)

    assert application.state.settings is settings


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
