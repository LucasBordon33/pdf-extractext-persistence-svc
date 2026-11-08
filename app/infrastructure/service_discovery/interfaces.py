
from typing import Protocol, runtime_checkable

from .models import ServiceInstance


@runtime_checkable
class IServiceRegistry(Protocol):
    def register(self) -> bool:
        ...

    def deregister(self) -> bool:
        ...


@runtime_checkable
class IServiceDiscovery(Protocol):

    def discover(self, service_name: str) -> ServiceInstance | None:
        ...

    def discover_all(self, service_name: str) -> tuple[ServiceInstance, ...]:
        ...
