import os
import socket
from functools import lru_cache
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache(maxsize=1)
def _detect_container_ip() -> str | None:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return None


class ServiceDiscoverySettings(BaseSettings):
    """Ajustes de service discovery leídos de env vars o de `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_discovery_enabled: bool = True

    consul_host: str = "consul"
    consul_port: int = 8500
    consul_timeout: float = 2.0

    service_name: str = ""  
    service_id: str = ""  
    service_host: str = ""  
    service_address_mode: Literal["ip", "dns"] = "ip"
    service_port: int = 8000
    service_health_path: str = "/health"

    # --- Health check registrado en Consul ---
    health_check_interval: str = "10s"
    health_check_timeout: str = "5s"
    deregister_critical_after: str = "60s"

    # --- Registro y descubrimiento ---
    register_retries: int = 1
    register_retry_backoff: float = 0.5
    discovery_cache_ttl: float = 5.0

    @property
    def consul_base_url(self) -> str:
        return f"http://{self.consul_host}:{self.consul_port}"

    @property
    def resolved_service_address(self) -> str:
        if self.service_host:
            return self.service_host
        if self.service_address_mode == "ip":
            detected = _detect_container_ip()
            if detected:
                return detected
        return self.service_name

    @property
    def health_check_url(self) -> str:
        return (
            f"http://{self.resolved_service_address}:{self.service_port}"
            f"{self.service_health_path}"
        )


def load_settings(**service_defaults: Any) -> ServiceDiscoverySettings:
    applied = {
        key: value
        for key, value in service_defaults.items()
        if os.getenv(key.upper()) is None
    }
    return ServiceDiscoverySettings(**applied)
