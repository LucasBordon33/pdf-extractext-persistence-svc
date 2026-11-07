"""Integración Consul del microservicio de persistencia.

La implementación (cliente, registro, health, lifespan) vive en el
paquete compartido `app.infrastructure.service_discovery`; aquí solo se
liga la identidad del servicio con el entorno (composition root).

`SERVICE_NAME` por defecto es `store`: es el nombre con el que el
orquestador y el alias de red del compose ya lo identifican, de modo
que el discovery devuelve exactamente la misma dirección que la config
estática de fallback.
"""

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
    """Registro de Consul configurado con la identidad del store.

    El lifespan propio de `create_app` invoca `registry.register()` al
    iniciar y `registry.deregister()` al apagar, antes de cerrar
    MongoDB/Redis (Consul deja de enviar tráfico primero).
    """
    settings = load_settings(**_SERVICE_DEFAULTS)
    return ConsulServiceRegistry(ConsulAgentClient(settings), settings)
