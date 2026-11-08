from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.types import ASGIApp

from .interfaces import IServiceRegistry
from .logging import get_logger

logger = get_logger()


def add_health_route(app: FastAPI, service_name: str, path: str = "/health") -> None:

    @app.get(path, include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "healthy", "service": service_name}


def attach_consul_lifespan(app: FastAPI, registry: IServiceRegistry) -> None:
    previous_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: ASGIApp) -> AsyncIterator[None]:
        async with previous_lifespan(application):
            registry.register()
            try:
                yield
            finally:
                registry.deregister()

    app.router.lifespan_context = lifespan
    logger.debug(
        "Lifespan de Consul acoplado a la app",
        extra={"event": "lifespan_attached"},
    )
