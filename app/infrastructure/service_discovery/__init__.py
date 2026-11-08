from .consul import ConsulAgentClient, ConsulError, ConsulServiceDiscovery, ConsulServiceRegistry
from .fastapi import add_health_route, attach_consul_lifespan
from .interfaces import IServiceDiscovery, IServiceRegistry
from .logging import JsonFormatter, configure_logging, get_logger
from .models import ServiceInstance
from .settings import ServiceDiscoverySettings, load_settings

__version__ = "0.1.0"

__all__ = [
    "ConsulAgentClient",
    "ConsulError",
    "ConsulServiceDiscovery",
    "ConsulServiceRegistry",
    "IServiceDiscovery",
    "IServiceRegistry",
    "JsonFormatter",
    "ServiceDiscoverySettings",
    "ServiceInstance",
    "add_health_route",
    "attach_consul_lifespan",
    "configure_logging",
    "get_logger",
    "load_settings",
]
