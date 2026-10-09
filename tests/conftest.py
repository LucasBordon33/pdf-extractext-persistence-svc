import pytest

from app.config import Settings

SETTINGS_ENV_VARS = (
    "ENVIRONMENT",
    "LOG_LEVEL",
    "HOST",
    "PORT",
    "MONGO_URI",
    "MONGO_DB",
    "REDIS_URL",
    "CACHE_TTL_SECONDS",
    "LOCK_TTL_SECONDS",
)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name in SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None)
