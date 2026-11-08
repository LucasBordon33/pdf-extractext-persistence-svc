
from app.infrastructure.service_discovery import (
    ConsulAgentClient,
    ConsulServiceRegistry,
    load_settings,
)

_SERVICE_DEFAULTS = {
    "service_name": "store",
    "service_port": 8003,
    "service_health_path": "/api/v1/health",
}


def build_registry() -> ConsulServiceRegistry:
    settings = load_settings(**_SERVICE_DEFAULTS)
    return ConsulServiceRegistry(ConsulAgentClient(settings), settings)
