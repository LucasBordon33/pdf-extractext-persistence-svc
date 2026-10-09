from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8003
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "pdf_documents"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300
    lock_ttl_seconds: int = 10
