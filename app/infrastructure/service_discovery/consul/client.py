import json
from typing import Any

import requests

from ..models import ServiceInstance
from ..settings import ServiceDiscoverySettings


class ConsulError(RuntimeError):
    """Fallo de comunicación con el agente de Consul."""

class ConsulAgentClient:
    def __init__(self, settings: ServiceDiscoverySettings) -> None:
        self._base_url = settings.consul_base_url.rstrip("/")
        self._timeout = settings.consul_timeout

    def register(self, payload: dict[str, Any]) -> None:
        self._request("PUT", "/v1/agent/service/register", payload)

    def deregister(self, service_id: str) -> None:
        self._request(
            "PUT",
            f"/v1/agent/service/deregister/{requests.utils.quote(service_id, safe='')}",
        )

    def healthy_instances(self, service_name: str) -> tuple[ServiceInstance, ...]:
        entries = self._request(
            "GET",
            f"/v1/health/service/{requests.utils.quote(service_name, safe='')}?passing=true",
        ) or []

        return tuple(
            ServiceInstance(
                id=entry["Service"]["ID"],
                name=entry["Service"]["Service"],
                host=entry["Service"].get("Address")
                or entry["Node"]["Address"],
                port=int(entry["Service"]["Port"]),
            )
            for entry in entries
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = requests.request(
                method=method,
                url=f"{self._base_url}{path}",
                json=payload,
                timeout=self._timeout,
            )

            response.raise_for_status()

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            raise ConsulError(
                f"Consul respondió {status} para {method} {path}"
            ) from exc

        except requests.RequestException as exc:
            raise ConsulError(
                f"Consul inalcanzable en {self._base_url}: {exc}"
            ) from exc

        if not response.content:
            return None

        try:
            return response.json()

        except json.JSONDecodeError as exc:
            raise ConsulError(
                f"Respuesta inválida de Consul para {method} {path}"
            ) from exc