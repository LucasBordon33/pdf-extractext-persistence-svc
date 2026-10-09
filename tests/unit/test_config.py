from pathlib import Path

import pytest

from app.config import Settings

EXPECTED_DEFAULTS = {
    "environment": "development",
    "log_level": "INFO",
    "host": "0.0.0.0",
    "port": 8003,
    "mongo_uri": "mongodb://localhost:27017",
    "mongo_db": "pdf_documents",
    "redis_url": "redis://localhost:6379/0",
    "cache_ttl_seconds": 300,
    "lock_ttl_seconds": 10,
}


def test_settings_defaults(settings: Settings) -> None:
    for field_name, expected_value in EXPECTED_DEFAULTS.items():
        assert getattr(settings, field_name) == expected_value


def test_settings_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("MONGO_DB", "pdf_documents_test")

    settings = Settings(_env_file=None)

    assert settings.port == 9000
    assert settings.mongo_db == "pdf_documents_test"


def test_settings_reads_dotenv_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MONGO_URI", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("MONGO_URI=mongodb://mongo:27017\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.mongo_uri == "mongodb://mongo:27017"


def test_env_vars_take_precedence_over_dotenv_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/2")
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_URL=redis://redis:6379/1\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.redis_url == "redis://redis:6379/2"


def test_explicit_kwargs_win_over_env_for_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CACHE_TTL_SECONDS", "60")

    settings = Settings(_env_file=None, cache_ttl_seconds=5)

    assert settings.cache_ttl_seconds == 5
